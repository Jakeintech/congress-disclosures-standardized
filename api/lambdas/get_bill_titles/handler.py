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

def handler(event, context):
    """
    GET /v1/congress/bills/{bill_id}/titles
    """
    try:
        path_params = event.get('pathParameters') or {}
        
        # Priority 1: Direct components from route {congress}/{type}/{number}
        congress_val = path_params.get('congress')
        type_val = path_params.get('type')
        number_val = path_params.get('number')
        
        if congress_val and type_val and number_val:
            bill_id = f"{congress_val}-{type_val}-{number_val}"
        else:
            # Priority 2: Full bill_id if provided
            bill_id = path_params.get('bill_id', '')

        if not bill_id:
            return error_response(message="Missing bill_id (or congress/type/number)", status_code=400)

        if not CONGRESS_API_KEY:
            return error_response(message="Congress API key not configured", status_code=500)

        # Parse bill_id: "119-hr-1"
        try:
            parts = bill_id.split('-')
            congress = int(parts[0])
            bill_type = parts[1].lower()
            bill_number = int(parts[2])
        except:
             return error_response(message="Invalid bill_id format", status_code=400)

        # Call Congress.gov API
        api_url = f"{CONGRESS_API_BASE}/bill/{congress}/{bill_type}/{bill_number}/titles"

        try:
            headers = {'X-API-Key': CONGRESS_API_KEY}
            params = {'limit': 250}  # Get more results
            resp = requests.get(api_url, headers=headers, params=params, timeout=10)

            if resp.status_code == 404:
                return error_response(message="Bill titles not found", status_code=404)

            if resp.status_code != 200:
                logger.error(f"Congress.gov API error: {resp.status_code} - {resp.text}")
                return error_response(message="Failed to fetch bill titles from Congress.gov", status_code=502)

            data = resp.json()

            # Extract data from response
            items = data.get('titles', [])
            
            cleaned_items = []
            for item in items:
                cleaned_items.append({
                    'type': item.get('titleType', 'Unknown'),
                    'title': item.get('title', ''),
                    'chamber': item.get('chamberName'),
                    'congress': item.get('congress')
                })

            return success_response({
                'bill_id': bill_id,
                'titles': cleaned_items,
                'count': len(cleaned_items)
            })

        except requests.exceptions.Timeout:
            logger.error("Congress.gov API timeout")
            return error_response(message="Congress.gov API timeout", status_code=504)
        except Exception as e:
            logger.error(f"Failed to fetch from Congress.gov API: {e}", exc_info=True)
            return error_response(message="Failed to fetch bill titles", status_code=502)

    except Exception as e:
        logger.error(f"Error fetching bill titles: {e}", exc_info=True)
        return error_response(message="Internal error", status_code=500)
