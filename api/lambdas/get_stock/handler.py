"""
Lambda handler: GET /v1/stocks/{ticker}

Get stock summary with trading statistics and recent congressional trades.
"""

import os
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def handler(event, context):
    """GET /v1/stocks/{ticker} - Stock trading summary."""
    try:
        path_params = event.get('pathParameters') or {}
        ticker = path_params.get('ticker', '').upper()
        
        if not ticker:
            return error_response("ticker is required", 400)
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Get recent trades for this stock (limit reduced for performance)
        trades_df = qb.query_parquet(
            'gold/house/financial/facts/fact_ptr_transactions',
            filters={'ticker': ticker},
            order_by='transaction_date DESC',
            limit=50
        )
        
        if len(trades_df) == 0:
            return error_response(f"No trades found for ticker: {ticker}", 404)
        
        # Calculate statistics
        total_trades = len(trades_df)
        unique_members = len(trades_df['bioguide_id'].unique())
        purchase_count = len(trades_df[trades_df['transaction_type'] == 'Purchase'])
        sale_count = len(trades_df[trades_df['transaction_type'] == 'Sale'])
        latest_trade = str(trades_df['transaction_date'].max())
        
        # Get recent trades (last 20)
        recent_trades = trades_df.head(20).to_dict('records')
        
        result = {
            'ticker': ticker,
            'statistics': {
                'total_trades': total_trades,
                'unique_members': unique_members,
                'purchase_count': purchase_count,
                'sale_count': sale_count,
                'latest_trade_date': latest_trade
            },
            'recent_trades': recent_trades
        }
        
        return success_response(result)
    
    except Exception as e:
        logger.error(f"Error fetching stock: {e}", exc_info=True)
        return error_response("Failed to retrieve stock data", 500, str(e))
