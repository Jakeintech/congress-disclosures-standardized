import os
import logging
import requests
import re
from api.lib import (
    success_response,
    error_response
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CONGRESS_API_KEY = os.environ.get('CONGRESS_GOV_API_KEY', '')
CONGRESS_API_BASE = 'https://api.congress.gov/v3'

def clean_html(raw_html):
    """Remove HTML tags and extra whitespace."""
    if not raw_html:
        return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return ' '.join(cleantext.split())

def handler(event, context):
    """
    GET /v1/congress/bills/{bill_id}/summaries
    """
    try:
        path_params = event.get('pathParameters') or {}
        bill_id = path_params.get('bill_id', '')

        if not bill_id:
            return error_response(message="Missing bill_id", status_code=400)

        if not CONGRESS_API_KEY:
            return error_response(message="Congress API key not configured", status_code=500)

        try:
            parts = bill_id.split('-')
            congress = int(parts[0])
            bill_type = parts[1].lower()
            bill_number = int(parts[2])
        except:
             return error_response(message="Invalid bill_id format", status_code=400)

        api_url = f"{CONGRESS_API_BASE}/bill/{congress}/{bill_type}/{bill_number}/summaries"

        try:
            headers = {'X-API-Key': CONGRESS_API_KEY}
            params = {'limit': 250}
            resp = requests.get(api_url, headers=headers, params=params, timeout=10)

            if resp.status_code == 404:
                return error_response(message="Bill summaries not found", status_code=404)

            if resp.status_code != 200:
                logger.error(f"Congress.gov API error: {resp.status_code} - {resp.text}")
                return error_response(message="Failed to fetch bill summaries from Congress.gov", status_code=502)

            data = resp.json()

            # Congress.gov may return either a top-level list or nest items
            # under an object (e.g., { "summaries": { "summaries": [...] } })
            raw = data.get('summaries', [])
            if isinstance(raw, dict):
                # Prefer common keys that hold the array
                items = (
                    raw.get('summaries')
                    or raw.get('items')
                    or raw.get('data')
                    or []
                )
            else:
                items = raw

            cleaned_items = []
            for item in items or []:
                # Fallback to textMarkup if text is absent
                text_val = item.get('text') or item.get('textMarkup') or ''
                cleaned_items.append({
                    'updateDate': item.get('updateDate'),
                    'actionDate': item.get('actionDate'),
                    'actionDesc': item.get('actionDesc'),
                    'text': clean_html(text_val),
                    'versionCode': item.get('versionCode')
                })

            return success_response({
                'bill_id': bill_id,
                'summaries': cleaned_items,
                'count': len(cleaned_items)
            })

        except requests.exceptions.Timeout:
            logger.error("Congress.gov API timeout")
            return error_response(message="Congress.gov API timeout", status_code=504)
        except Exception as e:
            logger.error(f"Failed to fetch from Congress.gov API: {e}", exc_info=True)
            return error_response(message="Failed to fetch bill summaries", status_code=502)

    except Exception as e:
        logger.error(f"Error fetching bill summaries: {e}", exc_info=True)
        return error_response(message="Internal error", status_code=500)
