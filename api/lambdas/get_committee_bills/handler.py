"""
Lambda handler: GET /v1/congress/committees/{chamber}/{code}/bills
Get bills referred to a committee from Congress.gov API with caching.
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
DEFAULT_CACHE_SECONDS = 1800  # 30 minutes cache


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
    GET /v1/congress/committees/{chamber}/{code}/bills
    GET /v1/congress/committees/{code}/bills (Legacy)
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

        limit = min(int(query_params.get('limit', 250)), 250)
        offset = int(query_params.get('offset', 0))

        # Build API URL
        api_url = f"{CONGRESS_API_BASE}/committee/{chamber.lower()}/{system_code.lower()}/bills"

        logger.info(f"Fetching bills for committee {chamber}/{system_code}: limit={limit}, offset={offset}")

        try:
            params = {
                'api_key': CONGRESS_API_KEY,
                'limit': limit,
                'offset': offset,
                'format': 'json'
            }
            headers = {'X-API-Key': CONGRESS_API_KEY}

            resp = requests.get(api_url, headers=headers, params=params, timeout=15)

            if resp.status_code == 404:
                return error_response(
                    message=f"Bills not found for committee: {chamber}/{system_code}",
                    status_code=404
                )

            if resp.status_code != 200:
                logger.error(f"Congress.gov API error: {resp.status_code} - {resp.text}")
                return error_response(
                    message=f"Failed to fetch committee bills ({resp.status_code})",
                    status_code=502
                )

            data = resp.json()
            bills = data.get('bills', [])
            pagination_info = data.get('pagination', {})

            # Clean and standardize bill data
            cleaned_bills = []
            for bill in bills:
                item = {
                    'billId': f"{bill.get('congress', '')}-{bill.get('type', '').lower()}-{bill.get('number', '')}",
                    'congress': bill.get('congress', ''),
                    'type': bill.get('type', ''),
                    'number': bill.get('number', ''),
                    'title': bill.get('title', ''),
                    'originChamber': bill.get('originChamber', ''),
                    'introducedDate': bill.get('introducedDate', ''),
                    'latestAction': {
                        'date': bill.get('latestAction', {}).get('actionDate', ''),
                        'text': bill.get('latestAction', {}).get('text', '')
                    },
                    'url': bill.get('url', ''),
                    'updateDate': bill.get('updateDate', '')
                }
                cleaned_bills.append(item)

            return success_response(
                clean_nan_values({
                    'committeeCode': system_code,
                    'bills': cleaned_bills,
                    'count': len(cleaned_bills),
                    'pagination': pagination_info,
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
        logger.error(f"Error fetching committee bills: {e}", exc_info=True)
        return error_response(
            message="Internal error",
            status_code=500,
            details=str(e)
        )
