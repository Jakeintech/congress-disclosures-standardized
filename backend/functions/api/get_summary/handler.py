"""
Lambda handler: GET /v1/analytics/summary

Platform-wide summary statistics.
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

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def handler(event, context):
    """
    GET /v1/analytics/summary
    
    Returns platform-wide summary statistics:
    - Total members
    - Total trades
    - Total stocks traded
    - Latest filing date
    - Data coverage period
    """
    try:
        # Initialize query builder
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Get member count
        try:
            members_df = qb.query_parquet(
                'gold/house/financial/dimensions/dim_members',
                columns=['bioguide_id']
            )
            total_members = len(members_df)
        except Exception as e:
            logger.warning(f"Could not get member count: {e}")
            total_members = 0
        
        # Get trade statistics
        try:
            trades_df = qb.query_parquet(
                'gold/house/financial/facts/fact_ptr_transactions',
                columns=['transaction_key', 'transaction_date', 'ticker']
            )
            total_trades = len(trades_df)
            unique_stocks = len(trades_df['ticker'].unique()) if len(trades_df) > 0 else 0
            latest_transaction = trades_df['transaction_date'].max() if len(trades_df) > 0 else None
        except Exception as e:
            logger.warning(f"Could not get trade stats: {e}")
            total_trades = 0
            unique_stocks = 0
            latest_transaction = None
        
        # Get filing statistics
        try:
            filings_df = qb.query_parquet(
                'gold/house/financial/facts/fact_filings',
                columns=['doc_id', 'filing_date_key', 'year']
            )
            total_filings = len(filings_df)
            # filing_date_key is stored as YYYYMMDD double/int
            latest_filing = (
                int(filings_df['filing_date_key'].max())
                if len(filings_df) > 0 and filings_df['filing_date_key'].notna().any()
                else None
            )
            earliest_filing = (
                int(filings_df['filing_date_key'].min())
                if len(filings_df) > 0 and filings_df['filing_date_key'].notna().any()
                else None
            )
            filing_years = sorted(filings_df['year'].dropna().unique().tolist()) if len(filings_df) > 0 else []
        except Exception as e:
            logger.warning(f"Could not get filing stats: {e}")
            total_filings = 0
            latest_filing = None
            earliest_filing = None
            filing_years = []
        
        # Get bill statistics
        try:
            bills_df = qb.query_parquet(
                'gold/congress/dim_bill',
                columns=['bill_id']
            )
            total_bills = len(bills_df)
        except Exception as e:
            logger.warning(f"Could not get bill stats: {e}")
            total_bills = 0
            
        # Build summary response
        summary = {
            'members': {
                'total': total_members
            },
            'trades': {
                'total': total_trades,
                'unique_stocks': unique_stocks,
                'latest_transaction': str(latest_transaction) if latest_transaction else None
            },
            'filings': {
                'total': total_filings,
                'latest_filing': str(latest_filing) if latest_filing else None,
                'earliest_filing': str(earliest_filing) if earliest_filing else None,
                'coverage_years': filing_years
            },
            'bills': {
                'total': total_bills
            },
            'last_updated': str(latest_filing) if latest_filing else None
        }
        
        return success_response(summary)
    
    except Exception as e:
        logger.error(f"Error getting summary: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve platform summary",
            status_code=500,
            details=str(e)
        )
