"""
Lambda handler: GET /v1/congress/bills/{bill_id}/actions

Get full action history timeline for a bill with pagination.
"""

import os
import json
import logging
import math
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    parse_pagination_params
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def clean_nan(obj):
    """Replace NaN/Inf values with None for JSON serialization."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    elif isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    return obj


def handler(event, context):
    """
    GET /v1/congress/bills/{bill_id}/actions

    Path parameter:
    - bill_id: Bill ID in format "congress-type-number" (e.g., "118-hr-1")

    Query parameters:
    - limit: Records per page (default 100, max 500)
    - offset: Records to skip (default 0)

    Returns:
    {
      "bill_id": "118-hr-1234",
      "actions": [
        {
          "action_date": "2023-06-10",
          "action_text": "Passed House",
          "chamber": "House",
          "action_code": "H123",
          "action_type": "Floor"
        },
        ...
      ],
      "total_count": 87,
      "limit": 100,
      "offset": 0,
      "has_next": false,
      "has_previous": false
    }
    """
    try:
        # Extract bill_id from path
        path_params = event.get('pathParameters') or {}
        bill_id = path_params.get('bill_id', '')

        if not bill_id:
            return error_response(
                message="Missing bill_id parameter",
                status_code=400
            )

        # Parse bill_id: "118-hr-1" -> congress=118, bill_type=hr, bill_number=1
        parts = bill_id.split('-')
        if len(parts) != 3:
            return error_response(
                message="Invalid bill_id format. Expected: congress-type-number (e.g., 118-hr-1)",
                status_code=400
            )

        try:
            congress = int(parts[0])
            bill_type = parts[1].lower()
            bill_number = int(parts[2])
        except ValueError:
            return error_response(
                message="Invalid bill_id format",
                status_code=400
            )

        # Parse pagination
        query_params = event.get('queryStringParameters') or {}
        limit = int(query_params.get('limit', 100))
        offset = int(query_params.get('offset', 0))

        # Validate limits
        if limit < 1 or limit > 500:
            limit = 100
        if offset < 0:
            offset = 0

        logger.info(f"Fetching actions for bill: {bill_id}, limit={limit}, offset={offset}")

        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)

        # Count total actions first
        filters = {'bill_id': bill_id}

        # Try to count from Silver layer
        total_count = qb.count_records(
            'silver/congress/bill_actions',
            filters=filters
        )

        # Query actions with pagination
        actions_df = qb.query_parquet(
            'silver/congress/bill_actions',
            filters=filters,
            order_by='action_date DESC',
            limit=limit,
            offset=offset
        )

        actions = []
        if not actions_df.empty:
            for _, action in actions_df.iterrows():
                actions.append({
                    'action_date': str(action.get('action_date', '')),
                    'action_text': action.get('action_text', ''),
                    'chamber': action.get('chamber', ''),
                    'action_code': action.get('action_code', ''),
                    'action_type': action.get('action_type', ''),
                    'source_system': action.get('source_system', '')
                })

        # Build pagination response
        has_next = (offset + limit) < total_count
        has_previous = offset > 0

        response = {
            'bill_id': bill_id,
            'actions': actions,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_next': has_next,
            'has_previous': has_previous
        }

        # Add next/previous URLs
        if has_next:
            response['next_url'] = f"/v1/congress/bills/{bill_id}/actions?limit={limit}&offset={offset + limit}"
        if has_previous:
            prev_offset = max(0, offset - limit)
            response['previous_url'] = f"/v1/congress/bills/{bill_id}/actions?limit={limit}&offset={prev_offset}"

        # Determine cache duration
        cache_max_age = 86400 if congress <= 118 else 300  # 24h for archived, 5min for current

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': f'public, max-age={cache_max_age}'
            },
            'body': json.dumps(clean_nan(response), default=str)
        }

    except Exception as e:
        logger.error(f"Error fetching bill actions: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve bill actions",
            status_code=500,
            details=str(e)
        )
