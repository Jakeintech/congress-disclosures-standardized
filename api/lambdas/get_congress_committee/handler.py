"""
Lambda handler: GET /v1/congress/committees/{code}

Get single committee details from Congress.gov API with caching.
"""

import os
import logging
import requests
from api.lib import (
    success_response,
    error_response
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CONGRESS_API_KEY = os.environ.get('CONGRESS_GOV_API_KEY', '')
CONGRESS_API_BASE = 'https://api.congress.gov/v3'
DEFAULT_CACHE_SECONDS = 3600  # 1 hour cache


def parse_committee_code(code):
    """Parse committee code to extract chamber and system code.

    Examples:
    - "hsif00" -> chamber="house", code="hsif00"
    - "sscm00" -> chamber="senate", code="sscm00"
    - "jslc00" -> chamber="joint", code="jslc00"
    """
    code = code.lower()

    # First two characters indicate chamber
    if code.startswith('hs'):
        chamber = 'house'
    elif code.startswith('ss'):
        chamber = 'senate'
    elif code.startswith('js'):
        chamber = 'joint'
    else:
        # Default to house if unclear
        chamber = 'house'

    return chamber, code


def handler(event, context):
    """
    GET /v1/congress/committees/{code}

    Path parameter:
    - code: Committee system code (e.g., "hsif00", "sscm00")

    Returns:
    {
      "committee": {...}
    }
    """
    try:
        path_params = event.get('pathParameters') or {}
        committee_code = path_params.get('code', '')

        if not committee_code:
            return error_response(message="Missing committee code", status_code=400)

        if not CONGRESS_API_KEY:
            return error_response(message="Congress API key not configured", status_code=500)

        # Parse committee code to determine chamber
        chamber, system_code = parse_committee_code(committee_code)

        # Build API URL
        api_url = f"{CONGRESS_API_BASE}/committee/{chamber}/{system_code}"

        logger.info(f"Fetching committee from Congress.gov: {api_url}")

        try:
            headers = {'X-API-Key': CONGRESS_API_KEY}
            resp = requests.get(api_url, headers=headers, timeout=15)

            if resp.status_code == 404:
                return error_response(
                    message=f"Committee not found: {committee_code}",
                    status_code=404
                )

            if resp.status_code != 200:
                logger.error(f"Congress.gov API error: {resp.status_code} - {resp.text}")
                return error_response(
                    message="Failed to fetch committee from Congress.gov",
                    status_code=502
                )

            data = resp.json()

            # Extract committee from response
            committee = data.get('committee', {})

            # Clean committee data
            cleaned_committee = {
                'system_code': committee.get('systemCode', ''),
                'name': committee.get('name', ''),
                'chamber': committee.get('chamber', ''),
                'type': committee.get('type', ''),
                'subcommittees': committee.get('subcommittees', []),
                'history': committee.get('history', []),
                'url': committee.get('url', ''),
                'update_date': committee.get('updateDate', ''),
                'parent': committee.get('parent', None),
                'official_website_url': committee.get('officialWebsiteUrl', ''),
                'phone': committee.get('phone', ''),
                'location': committee.get('location', '')
            }

            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Cache-Control': f'public, max-age={DEFAULT_CACHE_SECONDS}'
                },
                'body': success_response({
                    'committee': cleaned_committee,
                    'raw_source': 'congress.gov'
                })['body']
            }

        except requests.exceptions.Timeout:
            logger.error("Congress.gov API timeout")
            return error_response(message="Congress.gov API timeout", status_code=504)
        except Exception as e:
            logger.error(f"Failed to fetch from Congress.gov API: {e}", exc_info=True)
            return error_response(message="Failed to fetch committee", status_code=502)

    except Exception as e:
        logger.error(f"Error fetching committee: {e}", exc_info=True)
        return error_response(
            message="Internal error",
            status_code=500,
            details=str(e)
        )
