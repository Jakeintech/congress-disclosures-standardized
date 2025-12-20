"""
Lambda handler: GET /v1/members

List all members with optional filters and pagination.
"""

import os
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    parse_pagination_params,
    paginate,
    build_pagination_response,
    parse_query_params
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def handler(event, context):
    """
    GET /v1/members
    
    Query parameters:
    - limit: Records per page (default 50, max 500)
    - offset: Records to skip (default 0)
    - state: Filter by state (e.g., 'CA')
    - district: Filter by district (e.g., '12')
    - party: Filter by party ('D', 'R', 'I')
    
    Returns paginated list of members with summary stats.
    """
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        limit, offset = parse_pagination_params(query_params)
        
        # Parse filters
        filters = {}
        if 'state' in query_params:
            filters['state'] = query_params['state'].upper()
        if 'district' in query_params:
            filters['district'] = query_params['district']
        if 'party' in query_params:
            filters['party'] = query_params['party'].upper()
        
        logger.info(f"Fetching members: limit={limit}, offset={offset}, filters={filters}")
        
        # Initialize query builder
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Count total matching records
        total_count = qb.count_records(
            'gold/house/financial/dimensions/dim_members',
            filters=filters if filters else None
        )
        
        # Query members with pagination
        members_df = qb.query_parquet(
            'gold/house/financial/dimensions/dim_members',
            filters=filters if filters else None,
            order_by='last_name ASC, first_name ASC',
            limit=limit,
            offset=offset
        )
        
        # Convert to list of dicts
        members_list = members_df.to_dict('records')
        
        # Build paginated response
        response = build_pagination_response(
            data=members_list,
            total_count=total_count,
            limit=limit,
            offset=offset,
            base_url='/v1/members',
            query_params={k: v for k, v in query_params.items() if k not in ['limit', 'offset']}
        )
        
        return success_response(response)
    
    except Exception as e:
        logger.error(f"Error fetching members: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve members",
            status_code=500,
            details=str(e)
        )
