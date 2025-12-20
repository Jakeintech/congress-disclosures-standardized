"""
Lambda handler: GET /v1/stocks/{ticker}

Get stock summary with trading statistics and recent congressional trades.
"""

import os
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    clean_nan_values
)
from api.lib.response_models import (
    StockDetail,
    StockStatistics,
    Transaction
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
        
        # Get recent trades for this stock
        trades_df = qb.query_parquet(
            'gold/house/financial/facts/fact_ptr_transactions',
            filters={'ticker': ticker},
            order_by='transaction_date DESC',
            limit=50
        )
        
        if trades_df.empty:
            return error_response(f"No trades found for ticker: {ticker}", 404)
        
        # Calculate statistics
        total_trades = len(trades_df)
        unique_members = len(trades_df['bioguide_id'].unique())
        purchase_count = len(trades_df[trades_df['transaction_type'] == 'Purchase'])
        sale_count = len(trades_df[trades_df['transaction_type'] == 'Sale'])
        latest_trade = str(trades_df['transaction_date'].max())
        
        stats = StockStatistics(
            total_trades=total_trades,
            unique_members=unique_members,
            purchase_count=purchase_count,
            sale_count=sale_count,
            latest_trade_date=latest_trade
        )
        
        # Get recent trades mapped to Pydantic
        trades_data = clean_nan_values(trades_df.head(20).to_dict('records'))
        recent_transactions = []
        for row in trades_data:
            try:
                recent_transactions.append(Transaction(
                    transaction_id=str(row.get('transaction_id') or row.get('doc_id', '')),
                    disclosure_date=row.get('disclosure_date') or row.get('filing_date'),
                    transaction_date=row.get('transaction_date'),
                    ticker=row.get('ticker'),
                    asset_description=row.get('asset_description') or row.get('description', 'Unknown'),
                    transaction_type=row.get('transaction_type').lower() if row.get('transaction_type') else 'purchase',
                    amount_low=int(row.get('amount_low', 0)) if row.get('amount_low') is not None else 0,
                    amount_high=int(row.get('amount_high', 0)) if row.get('amount_high') is not None else 0,
                    bioguide_id=row.get('bioguide_id'),
                    member_name=row.get('member_name') or row.get('filer_name') or row.get('full_name') or 'Unknown',
                    first_name=row.get('first_name'),
                    last_name=row.get('last_name'),
                    party=row.get('party'),
                    state=row.get('state'),
                    chamber=row.get('chamber').lower() if row.get('chamber') else 'house'
                ))
            except Exception as e:
                logger.warning(f"Error mapping trade in stock detail {row.get('transaction_id')}: {e}")
                continue
                
        # Build Detail Object
        detail = StockDetail(
            ticker=ticker,
            statistics=stats,
            recent_trades=recent_transactions
        )
        
        return success_response(detail.model_dump())
    
    except Exception as e:
        logger.error(f"Error fetching stock: {e}", exc_info=True)
        return error_response("Failed to retrieve stock data", 500, str(e))
