"""
Lambda handler: GET /v1/analytics/stocks/{ticker}/legislative-exposure

Get stock's legislative exposure and trading activity.
"""

import os
import json
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
    """
    GET /v1/analytics/stocks/{ticker}/legislative-exposure
    
    Path parameter:
    - ticker: Stock ticker symbol (e.g., "AAPL")
    
    Returns stock's legislative exposure and trading stats.
    """
    try:
        path_params = event.get('pathParameters') or {}
        ticker = path_params.get('ticker', '')
        
        if not ticker:
            return error_response(
                message="Missing ticker parameter",
                status_code=400
            )
        
        ticker = ticker.upper()
        logger.info(f"Fetching legislative exposure for: {ticker}")
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Get stock congress activity
        activity_df = qb.query_parquet(
            'gold/analytics/fact_stock_congress_activity',
            filters={'ticker': ticker},
            limit=1
        )
        
        if activity_df.empty:
            # Return empty response if no data
            return success_response({
                'ticker': ticker,
                'legislative_activity': None,
                'trading_activity': None,
                'message': 'No data found for this ticker'
            })
        
        activity = activity_df.iloc[0].to_dict()
        
        # Get trades for this ticker
        trades = []
        try:
            trades_df = qb.query_parquet(
                'gold/house/financial/facts/fact_ptr_transactions',
                filters={'ticker': ticker},
                limit=50
            )
            trades = trades_df.to_dict('records') if not trades_df.empty else []
        except Exception as e:
            logger.warning(f"Could not fetch trades: {e}")
        
        response_data = {
            'ticker': ticker,
            'legislative_activity': {
                'exposure_score': activity.get('legislative_exposure_score', 0),
                'members_trading': activity.get('members_trading_count', 0),
                'total_transactions': activity.get('total_transactions', 0),
                'buy_count': activity.get('buy_count', 0),
                'sell_count': activity.get('sell_count', 0)
            },
            'trading_activity': {
                'recent_trades': trades[:20]
            }
        }

        return success_response(response_data)

    except Exception as e:
        logger.error(f"Error fetching legislative exposure: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve legislative exposure",
            status_code=500,
            details=str(e)
        )
