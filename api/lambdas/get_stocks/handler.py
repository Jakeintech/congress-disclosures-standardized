"""
Lambda handler: GET /v1/stocks

List all stocks with trading activity.
"""

import os
import logging
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


def handler(event, context):
    """GET /v1/stocks - List stocks with trading statistics."""
    try:
        query_params = event.get('queryStringParameters') or {}
        limit, offset = parse_pagination_params(query_params)
        
        qb = ParquetQueryBuilder(s3_bucket=None)
        
        # Aggregate stocks from transactions
        stocks_df = qb.aggregate_parquet(
            'gold/house/financial/facts/fact_ptr_transactions',
            group_by=['ticker'],
            aggregations={
                'total_trades': 'COUNT(*)',
                'unique_members': 'COUNT(DISTINCT bioguide_id)',
                'purchase_count': 'SUM(CASE WHEN transaction_type = \'Purchase\' THEN 1 ELSE 0 END)',
                'sale_count': 'SUM(CASE WHEN transaction_type = \'Sale\' THEN 1 ELSE 0 END)',
                'latest_trade': 'MAX(transaction_date)'
            },
            order_by='total_trades DESC'
        )
        
        # Apply filters
        if 'min_trades' in query_params:
            try:
                min_trades = int(query_params['min_trades'])
                stocks_df = stocks_df[stocks_df['total_trades'] >= min_trades]
            except ValueError:
                pass
        
        total_count = len(stocks_df)
        
        # Apply pagination
        stocks_df = stocks_df.iloc[offset:offset + limit]
        stocks_list = stocks_df.to_dict('records')
        
        response = build_pagination_response(
            data=stocks_list,
            total_count=total_count,
            limit=limit,
            offset=offset,
            base_url='/v1/stocks',
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
        return error_response("Failed to retrieve stocks", 500, str(e))
