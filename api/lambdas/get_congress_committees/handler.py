"""
Lambda handler: GET /v1/congress/committees
List all congressional committees from Congress.gov API with caching.
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


def handler(event, context):
    """
    GET /v1/congress/committees
    """
    try:
        query_params = event.get('queryStringParameters') or {}

        if not CONGRESS_API_KEY:
            return error_response(message="Congress API key not configured", status_code=500)

        # Parse parameters
        chamber = query_params.get('chamber', '').lower()
        limit = int(query_params.get('limit', 250))
        offset = int(query_params.get('offset', 0))

        # Validate chamber
        valid_chambers = ['house', 'senate', 'joint', '']
        if chamber and chamber not in valid_chambers:
            return error_response(
                message=f"Invalid chamber. Must be one of: {', '.join(valid_chambers[:-1])}",
                status_code=400
            )

        # Build API URL
        if chamber:
            api_url = f"{CONGRESS_API_BASE}/committee/{chamber}"
        else:
            api_url = f"{CONGRESS_API_BASE}/committee"

        logger.info(f"Fetching committees from Congress.gov: chamber={chamber}, limit={limit}, offset={offset}")

        try:
            params = {
                'api_key': CONGRESS_API_KEY,
                'limit': min(limit, 250),
                'offset': offset,
                'format': 'json'
            }
            headers = {'X-API-Key': CONGRESS_API_KEY}

            resp = requests.get(api_url, headers=headers, params=params, timeout=15)

            if resp.status_code == 404:
                return error_response(message="Committees not found", status_code=404)

            if resp.status_code != 200:
                logger.error(f"Congress.gov API error: {resp.status_code} - {resp.text}")
                return error_response(
                    message=f"Failed to fetch committees ({resp.status_code})",
                    status_code=502
                )

            data = resp.json()
            committees = data.get('committees', [])
            pagination_info = data.get('pagination', {})

            # Clean and standardize committee data
            cleaned_committees = []
            for committee in committees:
                cleaned_committees.append({
                    'systemCode': committee.get('systemCode', ''),
                    'name': committee.get('name', ''),
                    'chamber': committee.get('chamber', ''),
                    'type': committee.get('type', ''),
                    'subcommitteeCount': committee.get('subcommitteeCount', 0),
                    'url': committee.get('url', ''),
                    'updateDate': committee.get('updateDate', '')
                })

            result = {
                'committees': cleaned_committees,
                'count': len(cleaned_committees),
                'pagination': pagination_info,
                'raw_source': 'congress.gov'
            }

            return success_response(
                clean_nan_values(result),
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
        logger.error(f"Error fetching committees: {e}", exc_info=True)
        return error_response(
            message="Internal error",
            status_code=500,
            details=str(e)
        )
