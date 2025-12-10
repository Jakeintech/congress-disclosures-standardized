"""
Lambda handler: GET /v1/trades

List all trades with comprehensive filtering and pagination.
"""

import os
import json
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    parse_pagination_params,
    parse_query_params,
    parse_date_range,
    parse_amount_range,
    build_pagination_response
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def handler(event, context):
    """
    GET /v1/trades
    
    Query parameters:
    - limit: Records per page (default 50, max 500)
    - offset: Records to skip (default 0)
    - ticker: Filter by stock ticker (e.g., 'AAPL')
    - bioguide_id: Filter by member
    - transaction_type: Filter by type ('Purchase', 'Sale', 'Exchange')
    - start_date: Filter by transaction_date >= start_date
    - end_date: Filter by transaction_date <= end_date
    - min_amount: Filter by amount >= min_amount
    - max_amount: Filter by amount <= max_amount
    
    Returns paginated list of trades.
    """
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        limit, offset = parse_pagination_params(query_params)
        
        # Parse filters
        filters = parse_query_params(event)
        
        # Add date range filters
        date_filters = parse_date_range(query_params)
        filters.update(date_filters)
        
        # Add amount range filters
        amount_filters = parse_amount_range(query_params)
        filters.update(amount_filters)
        
        # Remove pagination params from filters
        for key in ['limit', 'offset', 'start_date', 'end_date', 'min_amount', 'max_amount']:
            filters.pop(key, None)
        
        logger.info(f"Fetching trades: limit={limit}, offset={offset}, filters={filters}")
        
        # Initialize query builder
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Count total matching records
        total_count = qb.count_records(
            'gold/house/financial/facts/fact_ptr_transactions',
            filters=filters if filters else None
        )
        
        # Query trades with pagination
        trades_df = qb.query_parquet(
            'gold/house/financial/facts/fact_ptr_transactions',
            filters=filters if filters else None,
            order_by='transaction_date DESC',
            limit=limit,
            offset=offset
        )
        
        # Convert to list of dicts
        trades_list = trades_df.to_dict('records')
        
        # Build paginated response
        response = build_pagination_response(
            data=trades_list,
            total_count=total_count,
            limit=limit,
            offset=offset,
            base_url='/v1/trades',
            query_params={k: v for k, v in query_params.items() if k not in ['limit', 'offset']}
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=300'
            },
            'body': json.dumps(response, default=str)
        }
    
    except Exception as e:
        logger.error(f"Error fetching trades: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve trades",
            status_code=500,
            details=str(e)
        )
