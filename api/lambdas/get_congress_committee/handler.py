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
            committee = data.get('committee', {})

            # Clean and standardize committee data
            result = {
                'committee': clean_nan_values({
                    'systemCode': committee.get('systemCode', system_code),
                    'name': committee.get('name', ''),
                    'chamber': committee.get('chamber', chamber.capitalize()),
                    'type': committee.get('type', ''),
                    'subcommittees': committee.get('subcommittees', []),
                    'history': committee.get('history', []),
                    'url': committee.get('url', ''),
                    'updateDate': committee.get('updateDate', ''),
                    'parent': committee.get('parent', None),
                    'officialWebsiteUrl': committee.get('officialWebsiteUrl', ''),
                    'phone': committee.get('phone', ''),
                    'location': committee.get('location', '')
                }),
                'raw_source': 'congress.gov'
            }

            return success_response(
                result,
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
