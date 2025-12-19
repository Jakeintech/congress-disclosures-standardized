"""
Lambda handler: GET /v1/congress/members

List Congress members with filters and pagination.
"""

import os
import json
import logging
import math
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    parse_pagination_params,
    build_pagination_response
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
    GET /v1/congress/members
    
    Query parameters:
    - limit: Records per page (default 50, max 500)
    - offset: Records to skip (default 0)
    - chamber: Filter by chamber ('House', 'Senate')
    - state: Filter by state (e.g., 'CA')
    - party: Filter by party ('D', 'R', 'I')
    
    Returns paginated list of Congress members.
    """
    try:
        query_params = event.get('queryStringParameters') or {}
        limit, offset = parse_pagination_params(query_params)
        
        filters = {}
        if 'chamber' in query_params:
            chamber = query_params['chamber'].lower()
            filters['chamber'] = 'house' if chamber in ['house', 'h'] else 'senate'
        if 'state' in query_params:
            filters['state'] = query_params['state'].upper()
        if 'party' in query_params:
            filters['party'] = query_params['party'].upper()
        
        logger.info(f"Fetching Congress members: limit={limit}, offset={offset}, filters={filters}")
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        total_count = qb.count_records(
            'gold/house/financial/dimensions/dim_members',
            filters=filters if filters else None
        )
        
        members_df = qb.query_parquet(
            'gold/house/financial/dimensions/dim_members',
            filters=filters if filters else None,
            order_by='last_name ASC, first_name ASC',
            limit=limit,
            offset=offset
        )
        
        members_list = members_df.to_dict('records')
        
        response = build_pagination_response(
            data=members_list,
            total_count=total_count,
            limit=limit,
            offset=offset,
            base_url='/v1/congress/members',
            query_params={k: v for k, v in query_params.items() if k not in ['limit', 'offset']}
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=300'
            },
            'body': json.dumps(clean_nan(response), default=str)
        }
    
    except Exception as e:
        logger.error(f"Error fetching Congress members: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve Congress members",
            status_code=500,
            details=str(e)
        )
