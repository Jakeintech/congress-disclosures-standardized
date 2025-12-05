"""
Lambda handler: GET /v1/congress/bills

List Congress bills with optional filters and pagination.
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
    GET /v1/congress/bills
    
    Query parameters:
    - limit: Records per page (default 50, max 500)
    - offset: Records to skip (default 0)
    - congress: Filter by congress number (e.g., '118', '119')
    - bill_type: Filter by bill type (e.g., 'hr', 's', 'hres')
    - sponsor: Filter by sponsor name (partial match)
    
    Returns paginated list of bills.
    """
    try:
        query_params = event.get('queryStringParameters') or {}
        limit, offset = parse_pagination_params(query_params)
        
        filters = {}
        if 'congress' in query_params:
            filters['congress'] = int(query_params['congress'])
        if 'bill_type' in query_params:
            filters['bill_type'] = query_params['bill_type'].lower()
        
        logger.info(f"Fetching bills: limit={limit}, offset={offset}, filters={filters}")
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Build S3 prefix for partition pruning
        s3_prefix = 'gold/congress/dim_bill'
        
        # Count total
        total_count = qb.count_records(s3_prefix, filters=filters if filters else None)
        
        # Query bills
        bills_df = qb.query_parquet(
            s3_prefix,
            filters=filters if filters else None,
            order_by='congress DESC, bill_number ASC',
            limit=limit,
            offset=offset
        )
        
        # Filter by sponsor if specified (text search)
        if 'sponsor' in query_params:
            sponsor_filter = query_params['sponsor'].lower()
            if 'sponsor_name' in bills_df.columns:
                bills_df = bills_df[
                    bills_df['sponsor_name'].str.lower().str.contains(sponsor_filter, na=False)
                ]
        
        bills_list = bills_df.to_dict('records')
        
        response = build_pagination_response(
            data=bills_list,
            total_count=total_count,
            limit=limit,
            offset=offset,
            base_url='/v1/congress/bills',
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
        logger.error(f"Error fetching bills: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve bills",
            status_code=500,
            details=str(e)
        )
