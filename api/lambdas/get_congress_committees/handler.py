"""
Lambda handler: GET /v1/congress/committees
List all congressional committees from Congress.gov API with caching.
"""

import os
import logging
import requests
from api.lib import (
    success_response,
    error_response
)
from api.lib.response_models import Committee

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CONGRESS_API_KEY = os.environ.get('CONGRESS_GOV_API_KEY', '')
CONGRESS_API_BASE = 'https://api.congress.gov/v3'
DEFAULT_CACHE_SECONDS = 3600


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
            committees_data = data.get('committees', [])
            pagination_info = data.get('pagination', {})

            # Map to Pydantic models
            committees = []
            for committee_data in committees_data:
                # Skip subcommittees (loaded within parent)
                if committee_data.get('parent'):
                    continue
                
                try:
                    committees.append(Committee(
                        systemCode=committee_data.get('systemCode', ''),
                        name=committee_data.get('name', ''),
                        chamber=committee_data.get('chamber', ''),
                        type=committee_data.get('type', ''),
                        subcommitteeCount=committee_data.get('subcommitteeCount', 0),
                        url=committee_data.get('url'),
                        updateDate=committee_data.get('updateDate')
                    ))
                except Exception as e:
                    logger.warning(f"Error mapping committee {committee_data.get('systemCode')}: {e}")
                    continue

            result = {
                'committees': [c.model_dump() for c in committees],
                'count': len(committees),
                'pagination': pagination_info,
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
        logger.error(f"Error fetching committees: {e}", exc_info=True)
        return error_response(
            message="Internal error",
            status_code=500,
            details=str(e)
        )
