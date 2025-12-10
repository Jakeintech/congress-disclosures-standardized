"""
Lambda handler: GET /v1/congress/committees/{code}/members

Get committee roster (members) from Congress.gov API with caching.
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
DEFAULT_CACHE_SECONDS = 3600  # 1 hour cache (membership changes infrequently)


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
    GET /v1/congress/committees/{code}/members

    Path parameter:
    - code: Committee system code (e.g., "hsif00", "sscm00")

    Query parameters:
    - limit: Records per page (default 250)
    - offset: Records to skip (default 0)

    Returns:
    {
      "members": [...],
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
        # Note: Congress.gov API endpoint is /committee/{chamber}/{code}
        # Members are included in the main committee response
        api_url = f"{CONGRESS_API_BASE}/committee/{chamber}/{system_code}"

        logger.info(f"Fetching members for committee {committee_code}")

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

            # Extract committee and members from response
            committee = data.get('committee', {})

            # Members might be in different locations depending on API version
            # Check common locations
            members = []

            # Try direct members array
            if 'members' in committee:
                members = committee['members']
            # Try current membership
            elif 'currentMembership' in committee:
                members = committee['currentMembership']

            # If no members found, try making a separate request to members endpoint
            if not members:
                members_url = f"{api_url}/members"
                logger.info(f"Trying separate members endpoint: {members_url}")

                members_resp = requests.get(members_url, headers=headers, timeout=15)
                if members_resp.status_code == 200:
                    members_data = members_resp.json()
                    members = members_data.get('members', [])

            # Clean member data
            cleaned_members = []
            for member in members:
                cleaned_members.append({
                    'bioguide_id': member.get('bioguideId', ''),
                    'name': member.get('name', ''),
                    'party': member.get('party', ''),
                    'state': member.get('state', ''),
                    'rank': member.get('rank', ''),
                    'title': member.get('title', ''),
                    'is_chair': member.get('isChair', False) or member.get('title', '').lower() in ['chair', 'chairman', 'chairwoman'],
                    'is_ranking_member': member.get('isRankingMember', False) or member.get('title', '').lower() == 'ranking member',
                    'update_date': member.get('updateDate', '')
                })

            # Apply pagination manually
            total_count = len(cleaned_members)
            cleaned_members = cleaned_members[offset:offset + limit]

            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Cache-Control': f'public, max-age={DEFAULT_CACHE_SECONDS}'
                },
                'body': success_response({
                    'committee_code': committee_code,
                    'members': cleaned_members,
                    'count': len(cleaned_members),
                    'total_count': total_count,
                    'pagination': {
                        'count': total_count,
                        'offset': offset,
                        'limit': limit
                    },
                    'raw_source': 'congress.gov'
                })['body']
            }

        except requests.exceptions.Timeout:
            logger.error("Congress.gov API timeout")
            return error_response(message="Congress.gov API timeout", status_code=504)
        except Exception as e:
            logger.error(f"Failed to fetch from Congress.gov API: {e}", exc_info=True)
            return error_response(message="Failed to fetch committee members", status_code=502)

    except Exception as e:
        logger.error(f"Error fetching committee members: {e}", exc_info=True)
        return error_response(
            message="Internal error",
            status_code=500,
            details=str(e)
        )
