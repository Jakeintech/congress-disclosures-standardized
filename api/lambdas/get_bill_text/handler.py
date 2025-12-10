
import os
import json
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
    GET /v1/congress/bills/{bill_id}/text?version={version_index}

    Returns text versions available for the bill from Congress.gov API.
    Optional query param 'version' specifies which version to fetch content for (default: 0).
    """
    try:
        path_params = event.get('pathParameters') or {}
        bill_id = path_params.get('bill_id', '')

        # Get optional version index from query string
        query_params = event.get('queryStringParameters') or {}
        version_index = int(query_params.get('version', '0'))

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

        # Call Congress.gov API for text versions
        # https://api.congress.gov/v3/bill/{congress}/{billType}/{billNumber}/text
        api_url = f"{CONGRESS_API_BASE}/bill/{congress}/{bill_type}/{bill_number}/text"

        try:
            headers = {'X-API-Key': CONGRESS_API_KEY}
            resp = requests.get(api_url, headers=headers, timeout=10)

            if resp.status_code == 404:
                return error_response(message="Bill text not found", status_code=404)

            if resp.status_code != 200:
                logger.error(f"Congress.gov API error: {resp.status_code} - {resp.text}")
                return error_response(message="Failed to fetch bill text from Congress.gov", status_code=502)

            data = resp.json()

            # Extract text versions from response
            text_versions = data.get('textVersions', [])

            # Process text versions to include formats
            versions = []
            for version in text_versions:
                version_info = {
                    'type': version.get('type', ''),
                    'date': version.get('date', ''),
                    'formats': []
                }

                # Extract format URLs
                for fmt in version.get('formats', []):
                    version_info['formats'].append({
                        'type': fmt.get('type', ''),
                        'url': fmt.get('url', '')
                    })

                versions.append(version_info)

            # Fetch the requested version's text content
            content = None
            content_url = None
            format_type = None

            if 0 <= version_index < len(versions):
                target_version = versions[version_index]
                for fmt in target_version['formats']:
                    if fmt['type'] in ['Formatted Text', 'Formatted XML']:
                        content_url = fmt['url']
                        format_type = fmt['type']
                        break

            # Fetch the actual text content from Congress.gov (no API key needed for HTML)
            if content_url:
                try:
                    # Don't send API key to congress.gov HTML pages
                    text_resp = requests.get(content_url, timeout=15)
                    if text_resp.status_code == 200:
                        content = text_resp.text
                except Exception as e:
                    logger.warning(f"Failed to fetch text content from {content_url}: {e}")

            return success_response({
                'bill_id': bill_id,
                'text_versions': versions,
                'content': content,
                'content_url': content_url,
                'format': format_type
            })

        except requests.exceptions.Timeout:
            logger.error("Congress.gov API timeout")
            return error_response(message="Congress.gov API timeout", status_code=504)
        except Exception as e:
            logger.error(f"Failed to fetch from Congress.gov API: {e}", exc_info=True)
            return error_response(message="Failed to fetch bill text", status_code=502)

    except Exception as e:
        logger.error(f"Error fetching bill text: {e}", exc_info=True)
        return error_response(message="Internal error", status_code=500)
