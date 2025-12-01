"""
Lambda handler: GET /v1/members/{bioguide_id}

Get individual member profile with trading stats and compliance metrics.
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
    GET /v1/members/{bioguide_id}
    
    Path parameters:
    - bioguide_id: Member's bioguide ID (e.g., 'C001059')
    
    Returns full member profile with:
    - Basic info (name, party, state, district)
    - Trading statistics
    - Compliance metrics
    - Recent filings
    """
    try:
        # Get bioguide_id from path parameters
        path_params = event.get('pathParameters') or {}
        bioguide_id = path_params.get('bioguide_id')
        
        if not bioguide_id:
            return error_response(
                message="bioguide_id is required",
                status_code=400
            )
        
        logger.info(f"Fetching member profile: {bioguide_id}")
        
        # Initialize query builder
        qb = ParquetQueryBuilder(s3_bucket=None)
        
        # Get member basic info
        try:
            member_df = qb.query_parquet(
                'gold/house/financial/dimensions/dim_members',
                filters={'bioguide_id': bioguide_id},
                limit=1
            )
            
            if len(member_df) == 0:
                return error_response(
                    message=f"Member not found: {bioguide_id}",
                    status_code=404,
                    details={'bioguide_id': bioguide_id}
                )
            
            member_info = member_df.to_dict('records')[0]
        except Exception as e:
            logger.error(f"Error fetching member info: {e}")
            return error_response(
                message=f"Member not found: {bioguide_id}",
                status_code=404
            )
        
        # Get trading statistics
        try:
            trades_df = qb.query_parquet(
                'gold/house/financial/facts/fact_ptr_transactions',
                filters={'bioguide_id': bioguide_id}
            )
            
            trading_stats = {
                'total_trades': len(trades_df),
                'unique_stocks': len(trades_df['ticker'].unique()) if len(trades_df) > 0 else 0,
                'latest_trade_date': str(trades_df['transaction_date'].max()) if len(trades_df) > 0 else None
            }
        except Exception as e:
            logger.warning(f"Could not get trading stats: {e}")
            trading_stats = {
                'total_trades': 0,
                'unique_stocks': 0,
                'latest_trade_date': None
            }
        
        # Get recent filings
        try:
            filings_df = qb.query_parquet(
                'gold/house/financial/facts/fact_filings',
                filters={'bioguide_id': bioguide_id},
                order_by='filing_date DESC',
                limit=10
            )
            
            recent_filings = filings_df[['doc_id', 'filing_type', 'filing_date']].to_dict('records')
        except Exception as e:
            logger.warning(f"Could not get filings: {e}")
            recent_filings = []
        
        # Build complete profile
        profile = {
            **member_info,
            'trading_stats': trading_stats,
            'recent_filings': recent_filings
        }
        
        return success_response(profile)
    
    except Exception as e:
        logger.error(f"Error fetching member profile: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve member profile",
            status_code=500,
            details=str(e)
        )
