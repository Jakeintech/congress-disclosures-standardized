"""
Lambda handler: GET /v1/filings/{doc_id}/transactions

List transactions for a specific filing.
"""

import os
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    parse_pagination_params,
    build_pagination_response
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def handler(event, context):
    """GET /v1/filings/{doc_id}/transactions - List transactions for a filing."""
    try:
        # Get doc_id from path parameters
        path_params = event.get('pathParameters') or {}
        doc_id = path_params.get('doc_id')
        
        if not doc_id:
            return error_response("Missing doc_id parameter", 400)
            
        query_params = event.get('queryStringParameters') or {}
        limit, offset = parse_pagination_params(query_params)
        
        # Build filters
        filters = {'doc_id': doc_id}
        
        # Optional filters
        if 'ticker' in query_params:
            filters['ticker'] = query_params['ticker'].upper()
            
        if 'asset_type' in query_params:
            filters['asset_type'] = query_params['asset_type']
            
        if 'transaction_type' in query_params:
            filters['transaction_type'] = query_params['transaction_type']
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Count total transactions for this filing
        total_count = qb.count_records(
            'gold/house/financial/facts/fact_ptr_transactions',
            filters=filters
        )
        
        # Query transactions
        transactions_df = qb.query_parquet(
            'gold/house/financial/facts/fact_ptr_transactions',
            filters=filters,
            order_by='transaction_date DESC',
            limit=limit,
            offset=offset
        )
        
        transactions_list = transactions_df.to_dict('records')
        
        response = build_pagination_response(
            data=transactions_list,
            total_count=total_count,
            limit=limit,
            offset=offset,
            base_url=f'/v1/filings/{doc_id}/transactions',
            query_params={k: v for k, v in query_params.items() if k not in ['limit', 'offset']}
        )
        
        return success_response(response)
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve transactions", 500, str(e))
