"""
Lambda handler: GET /v1/congress/committees/{code}/bills

Get bills referred to a committee from Congress.gov API with caching.
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
DEFAULT_CACHE_SECONDS = 1800  # 30 minutes cache (bills change more frequently)


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
    GET /v1/congress/committees/{code}/bills

    Path parameter:
    - code: Committee system code (e.g., "hsif00", "sscm00")

    Query parameters:
    - limit: Records per page (default 250)
    - offset: Records to skip (default 0)

    Returns:
    {
      "bills": [...],
      "count": 10,
      "pagination": {...}
    }
    """
    try:
        path_params = event.get('pathParameters') or {}
        query_params = event.get('queryStringParameters') or {}

        committee_code = path_params.get('code', '')

        if not committee_code:
            return error_response(message="Missing committee code", status_code=400)

        if not CONGRESS_API_KEY:
            return error_response(message="Congress API key not configured", status_code=500)

        # Parse committee code to determine chamber
        chamber, system_code = parse_committee_code(committee_code)

        # Parse parameters
        limit = int(query_params.get('limit', 250))
        offset = int(query_params.get('offset', 0))

        # Build API URL
        api_url = f"{CONGRESS_API_BASE}/committee/{chamber}/{system_code}/bills"

        logger.info(f"Fetching bills for committee {committee_code}: limit={limit}, offset={offset}")

        try:
            headers = {'X-API-Key': CONGRESS_API_KEY}
            params = {
                'limit': min(limit, 250),  # Congress.gov max is 250
                'offset': offset
            }

            resp = requests.get(api_url, headers=headers, params=params, timeout=15)

            if resp.status_code == 404:
                return error_response(
                    message=f"Bills not found for committee: {committee_code}",
                    status_code=404
                )

            if resp.status_code != 200:
                logger.error(f"Congress.gov API error: {resp.status_code} - {resp.text}")
                return error_response(
                    message="Failed to fetch committee bills from Congress.gov",
                    status_code=502
                )

            data = resp.json()

            # Extract bills from response
            bills = data.get('bills', [])
            pagination_info = data.get('pagination', {})

            # Clean bill data
            cleaned_bills = []
            for bill in bills:
                # Parse bill identifiers
                bill_number = bill.get('number', '')
                bill_type = bill.get('type', '')
                congress = bill.get('congress', '')

                cleaned_bills.append({
                    'bill_id': f"{congress}-{bill_type.lower()}-{bill_number}" if all([congress, bill_type, bill_number]) else '',
                    'congress': congress,
                    'bill_type': bill_type,
                    'bill_number': bill_number,
                    'title': bill.get('title', ''),
                    'origin_chamber': bill.get('originChamber', ''),
                    'introduced_date': bill.get('introducedDate', ''),
                    'latest_action': {
                        'date': bill.get('latestAction', {}).get('actionDate', ''),
                        'text': bill.get('latestAction', {}).get('text', '')
                    },
                    'url': bill.get('url', ''),
                    'update_date': bill.get('updateDate', '')
                })

            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Cache-Control': f'public, max-age={DEFAULT_CACHE_SECONDS}'
                },
                'body': success_response({
                    'committee_code': committee_code,
                    'bills': cleaned_bills,
                    'count': len(cleaned_bills),
                    'pagination': pagination_info,
                    'raw_source': 'congress.gov'
                })['body']
            }

        except requests.exceptions.Timeout:
            logger.error("Congress.gov API timeout")
            return error_response(message="Congress.gov API timeout", status_code=504)
        except Exception as e:
            logger.error(f"Failed to fetch from Congress.gov API: {e}", exc_info=True)
            return error_response(message="Failed to fetch committee bills", status_code=502)

    except Exception as e:
        logger.error(f"Error fetching committee bills: {e}", exc_info=True)
        return error_response(
            message="Internal error",
            status_code=500,
            details=str(e)
        )
