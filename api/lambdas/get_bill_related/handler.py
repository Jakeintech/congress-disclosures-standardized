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
    GET /v1/congress/bills/{bill_id}/related
    """
    try:
        path_params = event.get('pathParameters') or {}
        bill_id = path_params.get('bill_id', '')

        # Fallback for direct path params
        if not bill_id:
            congress_str = path_params.get('congress')
            bill_type = path_params.get('type')
            bill_number_str = path_params.get('number')
            if congress_str and bill_type and bill_number_str:
                bill_id = f"{congress_str}-{bill_type}-{bill_number_str}"

        if not bill_id:
            return error_response(message="Missing bill_id", status_code=400)

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
        api_url = f"{CONGRESS_API_BASE}/bill/{congress}/{bill_type}/{bill_number}/relatedbills"

        try:
            headers = {'X-API-Key': CONGRESS_API_KEY}
            params = {'limit': 250}  # Get more results
            resp = requests.get(api_url, headers=headers, params=params, timeout=10)

            if resp.status_code == 404:
                return error_response(message="Bill relatedbills not found", status_code=404)

            if resp.status_code != 200:
                logger.error(f"Congress.gov API error: {resp.status_code} - {resp.text}")
                return error_response(message="Failed to fetch bill relatedbills from Congress.gov", status_code=502)

            data = resp.json()

            # Extract data from response
            items = data.get('relatedBills', [])
            
            cleaned_items = []
            for item in items:
                cleaned_items.append({
                    'type': item.get('type'),
                    'number': item.get('number'),
                    'congress': item.get('congress'),
                    'title': item.get('title'),
                    'relationshipType': item.get('relationshipDetails', [{}])[0].get('type', 'Unknown'),
                    'identifiedBy': item.get('relationshipDetails', [{}])[0].get('identifiedBy', 'Unknown')
                })

            return success_response({
                'bill_id': bill_id,
                'relatedBills': cleaned_items,
                'count': len(cleaned_items)
            })

        except requests.exceptions.Timeout:
            logger.error("Congress.gov API timeout")
            return error_response(message="Congress.gov API timeout", status_code=504)
        except Exception as e:
            logger.error(f"Failed to fetch from Congress.gov API: {e}", exc_info=True)
            return error_response(message="Failed to fetch bill relatedbills", status_code=502)

    except Exception as e:
        logger.error(f"Error fetching bill relatedbills: {e}", exc_info=True)
        return error_response(message="Internal error", status_code=500)
