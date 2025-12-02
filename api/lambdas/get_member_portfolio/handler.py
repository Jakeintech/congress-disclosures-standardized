"""Lambda handler: GET /v1/members/{bioguide_id}/portfolio - Member portfolio."""
import os
import logging
from api.lib import ParquetQueryBuilder, success_response, error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """GET /v1/members/{bioguide_id}/portfolio - Current portfolio."""
    try:
        bioguide_id = (event.get('pathParameters') or {}).get('bioguide_id')
        if not bioguide_id:
            return error_response("bioguide_id is required", 400)
        
        qb = ParquetQueryBuilder(s3_bucket=None)
        
        # Get asset holdings (if available)
        try:
            holdings_df = qb.query_parquet(
                'gold/house/financial/facts/fact_asset_holdings',
                filters={'bioguide_id': bioguide_id},
                order_by='filing_date DESC',
                limit=100
            )
            portfolio = holdings_df.to_dict('records')
        except:
            # Fallback: aggregate from recent transactions
            trades_df = qb.query_parquet(
                'gold/house/financial/facts/fact_ptr_transactions',
                filters={'bioguide_id': bioguide_id},
                limit=500
            )
            portfolio = trades_df.groupby('ticker').size().reset_index(name='trade_count').to_dict('records')
        
        return success_response({'bioguide_id': bioguide_id, 'holdings': portfolio})
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve portfolio", 500, str(e))
