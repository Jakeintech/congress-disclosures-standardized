"""
Lambda handler: GET /v1/analytics/members/{bioguide_id}/legislation-trades

Get member's legislative activity with correlated trade windows.
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
    GET /v1/analytics/members/{bioguide_id}/legislation-trades
    
    Path parameter:
    - bioguide_id: Member's bioguide ID
    
    Returns member's bills with trade window analysis.
    """
    try:
        path_params = event.get('pathParameters') or {}
        bioguide_id = path_params.get('bioguide_id', '')
        
        if not bioguide_id:
            return error_response(
                message="Missing bioguide_id parameter",
                status_code=400
            )
        
        logger.info(f"Fetching legislation-trades for: {bioguide_id}")
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Get member info
        members_df = qb.query_parquet(
            'gold/congress/dim_member',
            filters={'bioguide_id': bioguide_id.upper()},
            limit=1
        )
        
        if members_df.empty:
            return error_response(
                message=f"Member not found: {bioguide_id}",
                status_code=404
            )
        
        member = members_df.iloc[0].to_dict()
        
        # Get member's bill roles
        bills_df = qb.query_parquet(
            'gold/congress/fact_member_bill_role',
            filters={'bioguide_id': bioguide_id.upper()},
            limit=100
        )
        
        bills_list = bills_df.to_dict('records') if not bills_df.empty else []
        
        # Get trade windows
        trade_windows = []
        try:
            windows_df = qb.query_parquet(
                'gold/analytics/fact_member_bill_trade_window',
                filters={'bioguide_id': bioguide_id.upper()},
                limit=100
            )
            trade_windows = windows_df.to_dict('records') if not windows_df.empty else []
        except Exception as e:
            logger.warning(f"Could not fetch trade windows: {e}")
        
        # Combine bills with their trade windows
        bills_with_trades = []
        for bill in bills_list:
            bill_id = bill.get('bill_id')
            bill_windows = [w for w in trade_windows if w.get('bill_id') == bill_id]
            bills_with_trades.append({
                **bill,
                'trade_windows': bill_windows
            })
        
        response = {
            'member': member,
            'bills_count': len(bills_list),
            'bills': bills_with_trades,
            'trades_in_windows': sum(w.get('transaction_count', 0) for w in trade_windows)
        }
        
        return success_response(response, metadata={'cache_seconds': 300})
    
    except Exception as e:
        logger.error(f"Error fetching legislation-trades: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve legislation-trades",
            status_code=500,
            details=str(e)
        )
