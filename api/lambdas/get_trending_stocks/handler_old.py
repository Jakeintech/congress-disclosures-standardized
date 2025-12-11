
"""Lambda handler: GET /v1/analytics/trending-stocks - Recently active stocks."""
import os
import logging
from api.lib import ParquetQueryBuilder, success_response, error_response
from datetime import datetime, timedelta

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """GET /v1/analytics/trending-stocks - Stocks with most recent activity."""
    try:
        query_params = event.get('queryStringParameters') or {}
        days = int(query_params.get('days', 30))  # Default 30 days
        limit = min(int(query_params.get('limit', 20)), 100)
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        trending = qb.aggregate_parquet(
            'gold/house/financial/facts/fact_ptr_transactions',
            group_by=['ticker'],
            aggregations={'trade_count': 'COUNT(*)', 'unique_members': 'COUNT(DISTINCT bioguide_id)', 'latest_trade': 'MAX(transaction_date)'},
            filters={'transaction_date': {'gte': cutoff_date}},
            order_by='trade_count DESC',
            limit=limit
        )
        
        return success_response({'period_days': days, 'trending_stocks': trending.to_dict('records'), 'count': len(trending)})
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve trending stocks", 500, str(e))
