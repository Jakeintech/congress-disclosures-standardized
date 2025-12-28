"""
Lambda handler: GET /v1/congress/committees/{chamber}/{code}/members
Get committee roster (members) from Congress.gov API with caching.
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
    """Parse committee code to extract chamber and system code if chamber not provided."""
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
    GET /v1/congress/committees/{chamber}/{code}/members
    GET /v1/congress/committees/{code}/members (Legacy)
    """
    try:
        path_params = event.get('pathParameters') or {}
        query_params = event.get('queryStringParameters') or {}

        chamber = path_params.get('chamber')
        committee_code = path_params.get('code')

        if not committee_code:
            return error_response(message="Missing committee code", status_code=400)

        if not CONGRESS_API_KEY:
            return error_response(message="Congress API key not configured", status_code=500)

        # Parse chamber if not provided
        if not chamber:
            chamber, system_code = parse_committee_code(committee_code)
        else:
            system_code = committee_code

        limit = int(query_params.get('limit', 250))
        offset = int(query_params.get('offset', 0))

        # Build API URL
        api_url = f"{CONGRESS_API_BASE}/committee/{chamber.lower()}/{system_code.lower()}"

        logger.info(f"Fetching members for committee {chamber}/{system_code}")

        try:
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
                    message=f"Failed to fetch committee members ({resp.status_code})",
                    status_code=502
                )

            data = resp.json()
            committee = data.get('committee', {})

            # Try to get members from common locations
            members = committee.get('members', []) or committee.get('currentMembership', [])

            # If no members found, try separate endpoint
            if not members:
                members_url = f"{api_url}/members"
                logger.info(f"Trying separate members endpoint: {members_url}")
                members_resp = requests.get(members_url, headers=headers, params=params, timeout=15)
                if members_resp.status_code == 200:
                    members_data = members_resp.json()
                    members = members_data.get('members', [])

            # Clean and standardize member data
            cleaned_members = []
            for member in members:
                cleaned_members.append({
                    'bioguideId': member.get('bioguideId', ''),
                    'name': member.get('name', ''),
                    'party': member.get('party', ''),
                    'state': member.get('state', ''),
                    'rank': member.get('rank', ''),
                    'title': member.get('title', ''),
                    'isChair': member.get('isChair', False) or member.get('title', '').lower() in ['chair', 'chairman', 'chairwoman'],
                    'isRankingMember': member.get('isRankingMember', False) or member.get('title', '').lower() == 'ranking member',
                    'updateDate': member.get('updateDate', '')
                })

            total_count = len(cleaned_members)
            paged_members = cleaned_members[offset:offset + limit]

            return success_response(
                clean_nan_values({
                    'committeeCode': system_code,
                    'members': paged_members,
                    'count': len(paged_members),
                    'total_count': total_count,
                    'pagination': {
                        'count': total_count,
                        'offset': offset,
                        'limit': limit
                    },
                    'raw_source': 'congress.gov'
                }),
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
        logger.error(f"Error fetching committee members: {e}", exc_info=True)
        return error_response(
            message="Internal error",
            status_code=500,
            details=str(e)
        )
