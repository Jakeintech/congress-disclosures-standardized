"""
Lambda handler: GET /v1/search

Unified search across members, stocks, and trades.
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
    """GET /v1/search?q={query} - Search members, stocks, trades."""
    try:
        query_params = event.get('queryStringParameters') or {}
        search_query = query_params.get('q', '').strip()
        
        if not search_query or len(search_query) < 2:
            return error_response("Search query must be at least 2 characters", 400)
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Search members (by name)
        search_pattern = f"%{search_query}%"
        try:
            members_df = qb.query_parquet(
                'gold/house/financial/dimensions/dim_members',
                filters={
                    'last_name': {'like': search_pattern}
                },
                limit=10
            )
            members_results = members_df[['bioguide_id', 'first_name', 'last_name', 'party', 'state']].to_dict('records')
        except Exception as e:
            logger.warning(f"Member search failed: {e}")
            members_results = []
        
        # Search stocks (by ticker)
        try:
            trades_df = qb.query_parquet(
                'gold/house/financial/facts/fact_ptr_transactions',
                filters={'ticker': {'like': search_pattern.upper()}},
                columns=['ticker'],
                limit=1000
            )
            unique_tickers = trades_df['ticker'].unique().tolist()[:10]
            stocks_results = [{'ticker': t} for t in unique_tickers]
        except Exception as e:
            logger.warning(f"Stock search failed: {e}")
            stocks_results = []
        
        result = {
            'query': search_query,
            'results': {
                'members': members_results,
                'stocks': stocks_results
            }
        }
        
        return success_response(result)
    
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return error_response("Search failed", 500, str(e))
