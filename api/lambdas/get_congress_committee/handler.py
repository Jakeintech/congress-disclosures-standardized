"""
Lambda handler: GET /v1/congress/committees/{chamber}/{code}
Get single committee details from Congress.gov API with caching.
"""

import os
import logging
import requests
from api.lib import (
    success_response,
    error_response,
    clean_nan_values
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CONGRESS_API_KEY = os.environ.get('CONGRESS_GOV_API_KEY', '')
CONGRESS_API_BASE = 'https://api.congress.gov/v3'
DEFAULT_CACHE_SECONDS = 3600  # 1 hour cache


def parse_committee_code(code):
    """Parse committee code to extract chamber and system code if chamber not provided.
    
    Examples:
    - "hsif00" -> chamber="house", code="hsif00"
    - "sscm00" -> chamber="senate", code="sscm00"
    """
    code = code.lower()
    if code.startswith('hs'):
        chamber = 'house'
    elif code.startswith('ss'):
        chamber = 'senate'
    elif code.startswith('js'):
        chamber = 'joint'
    else:
        chamber = 'house'
    return chamber, code


def handler(event, context):
    """
    GET /v1/congress/committees/{chamber}/{code}
    GET /v1/congress/committees/{code} (Legacy/Fallback)
    """
    try:
        path_params = event.get('pathParameters') or {}
        chamber = path_params.get('chamber')
        committee_code = path_params.get('code') or path_params.get('bill_id') # Handle potential naming inconsistency

        if not committee_code:
            return error_response(message="Missing committee code", status_code=400)

        if not CONGRESS_API_KEY:
            return error_response(message="Congress API key not configured", status_code=500)

        # If chamber not in path, try to parse from code
        if not chamber:
            chamber, system_code = parse_committee_code(committee_code)
        else:
            system_code = committee_code

        # Build API URL
        api_url = f"{CONGRESS_API_BASE}/committee/{chamber.lower()}/{system_code.lower()}"

        logger.info(f"Fetching committee from Congress.gov: {api_url}")

        try:
            # Congress.gov API accepts X-API-Key header OR api_key query param
            params = {'api_key': CONGRESS_API_KEY, 'format': 'json'}
            headers = {'X-API-Key': CONGRESS_API_KEY}
            
            resp = requests.get(api_url, headers=headers, params=params, timeout=15)

            if resp.status_code == 404:
                return error_response(
                    message=f"Committee not found: {chamber}/{system_code}",
                    status_code=404
                )

            if resp.status_code != 200:
                logger.error(f"Congress.gov API error: {resp.status_code} - {resp.text}")
                return error_response(
                    message=f"Failed to fetch committee ({resp.status_code})",
                    status_code=502
                )

            data = resp.json()
            committee_data = data.get('committee', {})

            # Try to fetch members if they are not in the main response
            members = committee_data.get('members', []) or committee_data.get('currentMembership', [])
            if not members:
                try:
                    members_url = f"{api_url}/members"
                    members_resp = requests.get(members_url, headers=headers, params=params, timeout=5)
                    if members_resp.status_code == 200:
                        members_data = members_resp.json()
                        members = members_data.get('members', []) or members_data.get('currentMembership', [])
                except Exception as e:
                    logger.warning(f"Failed to fetch committee members: {e}")

            # Try to fetch subcommittees if not in main response
            subcommittees = committee_data.get('subcommittees', [])
            if not subcommittees:
                try:
                    subs_url = f"{api_url}/subcommittees"
                    subs_resp = requests.get(subs_url, headers=headers, params=params, timeout=5)
                    if subs_resp.status_code == 200:
                        subs_data = subs_resp.json()
                        subcommittees = subs_data.get('subcommittees', [])
                except Exception as e:
                    logger.warning(f"Failed to fetch subcommittees: {e}")

            # Clean and standardize committee data
            cleaned_committee = {
                'systemCode': committee_data.get('systemCode', system_code),
                'name': committee_data.get('name', ''),
                'chamber': committee_data.get('chamber', chamber.capitalize()),
                'type': committee_data.get('type', ''),
                'subcommitteeCount': committee_data.get('subcommitteeCount', len(subcommittees)),
                'subcommittees': [{
                    'systemCode': sub.get('systemCode', ''),
                    'name': sub.get('name', ''),
                    'url': sub.get('url', '')
                } for sub in subcommittees],
                'members': [{
                    'bioguideId': m.get('bioguideId', ''),
                    'name': m.get('name', ''),
                    'party': m.get('party', ''),
                    'state': m.get('state', ''),
                    'role': m.get('role', m.get('title', ''))
                } for m in members if m.get('bioguideId')],
                'history': committee_data.get('history', []),
                'url': committee_data.get('url', ''),
                'updateDate': committee_data.get('updateDate', ''),
                'parent': committee_data.get('parent', None),
                'officialWebsiteUrl': committee_data.get('officialWebsiteUrl', ''),
                'phone': committee_data.get('phone', ''),
                'location': committee_data.get('location', '')
            }

            return success_response(
                clean_nan_values(cleaned_committee),
                status_code=200,
                metadata={'cache_seconds': DEFAULT_CACHE_SECONDS}
            )

        except requests.exceptions.Timeout:
            logger.error("Congress.gov API timeout")
            return error_response(message="Congress.gov API timeout", status_code=504)
        except Exception as e:
            logger.error(f"Failed to fetch from Congress.gov API: {e}", exc_info=True)
            return error_response(message=f"Fetch failed: {str(e)}", status_code=502)

    except Exception as e:
        logger.error(f"Error fetching committee: {e}", exc_info=True)
        return error_response(
            message="Internal error",
            status_code=500,
            details=str(e)
        )
