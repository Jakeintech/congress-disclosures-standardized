"""
Lambda handler: GET /v1/members/{bioguide_id}/trades

Get all trades for a specific member with filtering.
"""

import os
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    parse_pagination_params,
    parse_date_range,
    parse_amount_range,
    build_pagination_response
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def handler(event, context):
    """GET /v1/members/{bioguide_id}/trades - Member's trading history."""
    try:
        # Get bioguide_id from path
        path_params = event.get('pathParameters') or {}
        bioguide_id = path_params.get('bioguide_id')
        
        if not bioguide_id:
            return error_response("bioguide_id is required", 400)
        
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        limit, offset = parse_pagination_params(query_params)
        
        # Build filters
        filters = {'bioguide_id': bioguide_id}
        
        # Add date range
        date_filters = parse_date_range(query_params)
        filters.update(date_filters)
        
        # Add amount range
        amount_filters = parse_amount_range(query_params)
        filters.update(amount_filters)
        
        # Add optional filters
        if 'ticker' in query_params:
            filters['ticker'] = query_params['ticker'].upper()
        if 'transaction_type' in query_params:
            filters['transaction_type'] = query_params['transaction_type']
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Count total
        total_count = qb.count_records(
            'gold/house/financial/facts/fact_ptr_transactions',
            filters=filters
        )
        
        # Query trades
        trades_df = qb.query_parquet(
            'gold/house/financial/facts/fact_ptr_transactions',
            filters=filters,
            order_by='transaction_date DESC',
            limit=limit,
            offset=offset
        )
        
        trades_list = trades_df.to_dict('records')
        
        response = build_pagination_response(
            data=trades_list,
            total_count=total_count,
            limit=limit,
            offset=offset,
            base_url=f'/v1/members/{bioguide_id}/trades',
            query_params={k: v for k, v in query_params.items() if k not in ['limit', 'offset']}
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': str(response).replace("'", '"').replace('True', 'true').replace('False', 'false').replace('None', 'null')
        }
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve member trades", 500, str(e))
