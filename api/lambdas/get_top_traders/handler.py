"""
Lambda handler: GET /v1/analytics/top-traders

Get top traders by trading volume.
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
    """GET /v1/analytics/top-traders - Top traders by volume."""
    try:
        query_params = event.get('queryStringParameters') or {}
        
        # Default to top 20, max 100
        try:
            limit = int(query_params.get('limit', 20))
            limit = min(max(1, limit), 100)
        except ValueError:
            limit = 20
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Aggregate by member
        filters = {}
        if 'year' in query_params:
            try:
                year = int(query_params['year'])
                filters['filing_year'] = year
            except ValueError:
                pass
        
        traders_df = qb.aggregate_parquet(
            'gold/house/financial/facts/fact_ptr_transactions',
            group_by=['bioguide_id', 'first_name', 'last_name', 'party', 'state'],
            aggregations={
                'total_trades': 'COUNT(*)',
                'unique_stocks': 'COUNT(DISTINCT ticker)',
                'purchase_count': 'SUM(CASE WHEN transaction_type = \'Purchase\' THEN 1 ELSE 0 END)',
                'sale_count': 'SUM(CASE WHEN transaction_type = \'Sale\' THEN 1 ELSE 0 END)'
            },
            filters=filters if filters else None,
            order_by='total_trades DESC',
            limit=limit
        )
        
        traders_list = traders_df.to_dict('records')
        
        return success_response({
            'top_traders': traders_list,
            'count': len(traders_list)
        })
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve top traders", 500, str(e))
