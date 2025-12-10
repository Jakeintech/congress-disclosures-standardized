"""
Lambda handler: GET /v1/congress/bills/{bill_id}/actions

Get full action history timeline for a bill from Congress.gov API.
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

def handler(event, context):
    """
    GET /v1/congress/bills/{bill_id}/actions

    Path parameter:
    - bill_id: Bill ID in format "congress-type-number" (e.g., "118-hr-1")

    Query parameters:
    - limit: Records per page (default 250)
    
    Returns:
    {
      "bill_id": "118-hr-1",
      "actions": [...],
      "count": 10
    }
    """
    try:
        # Extract bill_id from path
        path_params = event.get('pathParameters') or {}
        bill_id = path_params.get('bill_id', '')

        if not bill_id:
            return error_response(message="Missing bill_id", status_code=400)

        if not CONGRESS_API_KEY:
            return error_response(message="Congress API key not configured", status_code=500)

        # Parse bill_id: "118-hr-1" -> congress=118, bill_type=hr, bill_number=1
        try:
            parts = bill_id.split('-')
            congress = int(parts[0])
            bill_type = parts[1].lower()
            bill_number = int(parts[2])
        except:
             return error_response(message="Invalid bill_id format", status_code=400)

        # Call Congress.gov API
        api_url = f"{CONGRESS_API_BASE}/bill/{congress}/{bill_type}/{bill_number}/actions"

        try:
            headers = {'X-API-Key': CONGRESS_API_KEY}
            params = {'limit': 250}  # Get more results
            resp = requests.get(api_url, headers=headers, params=params, timeout=10)

            if resp.status_code == 404:
                return error_response(message="Bill actions not found", status_code=404)

            if resp.status_code != 200:
                logger.error(f"Congress.gov API error: {resp.status_code} - {resp.text}")
                return error_response(message="Failed to fetch bill actions from Congress.gov", status_code=502)

            data = resp.json()

            # Extract actions from response
            actions = data.get('actions', [])
            
            # Helper to safely clean data
            cleaned_actions = []
            for action in actions:
                cleaned_actions.append({
                    'action_date': action.get('actionDate', ''),
                    'action_text': action.get('text', ''),
                    'type': action.get('type', ''),
                    'action_code': action.get('actionCode', ''),
                    'source_system': action.get('sourceSystem', {}).get('name', '')
                })

            return success_response({
                'bill_id': bill_id,
                'actions': cleaned_actions,
                'count': len(cleaned_actions),
                'raw_source': 'congress.gov'
            })

        except requests.exceptions.Timeout:
            logger.error("Congress.gov API timeout")
            return error_response(message="Congress.gov API timeout", status_code=504)
        except Exception as e:
            logger.error(f"Failed to fetch from Congress.gov API: {e}", exc_info=True)
            return error_response(message="Failed to fetch bill actions", status_code=502)

    except Exception as e:
        logger.error(f"Error fetching bill actions: {e}", exc_info=True)
        return error_response(
            message="Internal error",
            status_code=500,
            details=str(e)
        )
