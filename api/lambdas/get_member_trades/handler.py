"""
Lambda handler: GET /v1/members/{bioguide_id}/trades
OPTIMIZED: DuckDB with connection pooling (10-50x faster)
"""

import json
import logging
import os
import duckdb
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    clean_nan_values,
    parse_pagination_params
)
from api.lib.response_models import (
    Transaction,
    PaginationMetadata,
    PaginatedResponse
)

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def handler(event, context):
    """GET /v1/members/{bioguide_id}/trades - Member's trading history."""
    try:
        path_params = event.get('pathParameters') or {}
        query_params = event.get('queryStringParameters') or {}

        bioguide_id = path_params.get('bioguide_id')
        if not bioguide_id:
            return error_response(message="bioguide_id is required", status_code=400)

        limit, offset = parse_pagination_params(query_params)
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Filters
        filters = {'bioguide_id': bioguide_id}
        if query_params.get('ticker'):
            filters['ticker'] = query_params['ticker'].upper()
        if query_params.get('transaction_type'):
            filters['transaction_type'] = query_params['transaction_type']
            
        # 1. Total count
        total_count = qb.count_records(
            'gold/house/financial/facts/fact_ptr_transactions',
            filters=filters
        )
        
        # 2. Fetch records
        result_df = qb.query_parquet(
            'gold/house/financial/facts/fact_ptr_transactions',
            filters=filters,
            order_by='transaction_date DESC',
            limit=limit,
            offset=offset
        )
        
        trades_data = clean_nan_values(result_df.to_dict('records'))
        
        # 3. Map to Pydantic
        transactions = []
        for row in trades_data:
            try:
                tx = Transaction(
                    transaction_id=str(row.get('transaction_id') or row.get('doc_id', '')),
                    disclosure_date=row.get('disclosure_date'),
                    transaction_date=row.get('transaction_date'),
                    ticker=row.get('ticker'),
                    asset_description=row.get('asset_description') or row.get('asset_name', 'Unknown'),
                    transaction_type=row.get('transaction_type').lower() if row.get('transaction_type') else 'purchase',
                    amount_low=int(row.get('amount_low', 0)) if row.get('amount_low') is not None else 0,
                    amount_high=int(row.get('amount_high', 0)) if row.get('amount_high') is not None else 0,
                    bioguide_id=row.get('bioguide_id'),
                    member_name=row.get('member_name') or row.get('full_name', 'Unknown'),
                    first_name=row.get('first_name'),
                    last_name=row.get('last_name'),
                    party=row.get('party'),
                    state=row.get('state'),
                    chamber=row.get('chamber').lower() if row.get('chamber') else 'house',
                    owner=row.get('owner')
                )
                transactions.append(tx)
            except Exception as e:
                logger.warning(f"Error mapping trade: {e}")
                continue

        # 4. Build pagination
        has_next = (offset + len(transactions)) < total_count
        has_prev = offset > 0
        
        pagination = PaginationMetadata(
            total=total_count,
            count=len(transactions),
            limit=limit,
            offset=offset,
            has_next=has_next,
            has_prev=has_prev
        )
        
        paginated = PaginatedResponse(
            items=transactions,
            pagination=pagination
        )
        
        return success_response(paginated.model_dump())

    except Exception as e:
        logger.error(f"Error retrieving member trades: {str(e)}", exc_info=True)
        return error_response(
            message="Failed to retrieve member trades",
            status_code=500,
            details=str(e)
        )
