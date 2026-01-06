
"""Lambda handler: GET /v1/analytics/trading-timeline - Daily trading volume over time."""
import os
import logging
from api.lib import ParquetQueryBuilder, success_response, error_response
from datetime import datetime, timedelta

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """GET /v1/analytics/trading-timeline - Timeline of daily trading activity."""
    try:
        query_params = event.get('queryStringParameters') or {}
        
        # Default to last 365 days
        end_date = query_params.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        start_date = query_params.get('start_date', (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'))
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Try gold aggregate first
        try:
            timeline_df = qb.query_parquet(
                'gold/aggregates/agg_trading_timeline_daily',
                filters={'date': {'gte': start_date, 'lte': end_date}},
                order_by='date ASC',
                limit=365
            )
            return success_response({
                'timeline': timeline_df.to_dict('records'),
                'start_date': start_date,
                'end_date': end_date
            })
        except:
            # Fallback: aggregate from transactions (limit reduced for performance)
            trades_df = qb.query_parquet(
                'gold/house/financial/facts/fact_ptr_transactions',
                filters={'transaction_date': {'gte': start_date, 'lte': end_date}},
                limit=2000
            )
            daily = trades_df.groupby('transaction_date').size().reset_index(name='trade_count')
            return success_response({
                'timeline': daily.to_dict('records'),
                'start_date': start_date,
                'end_date': end_date,
                'note': 'Calculated from transactions'
            })
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve trading timeline", 500, str(e))
