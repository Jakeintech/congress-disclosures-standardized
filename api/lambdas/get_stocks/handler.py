"""
Lambda handler: GET /v1/stocks

List all stocks with trading activity.
"""

import os
import logging
from urllib.parse import urlencode
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    parse_pagination_params
)
from api.lib.response_models import Stock, PaginationMetadata, PaginatedResponse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def handler(event, context):
    """GET /v1/stocks - List stocks with trading statistics."""
    try:
        query_params = event.get('queryStringParameters') or {}
        limit, offset = parse_pagination_params(query_params)
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Aggregate stocks from transactions
        stocks_df = qb.aggregate_parquet(
            'gold/house/financial/facts/fact_ptr_transactions',
            group_by=['ticker'],
            aggregations={
                'total_trades': 'COUNT(*)',
                'unique_members': 'COUNT(DISTINCT bioguide_id)',
                'purchase_count': 'SUM(CASE WHEN transaction_type = \'Purchase\' THEN 1 ELSE 0 END)',
                'sale_count': 'SUM(CASE WHEN transaction_type = \'Sale\' THEN 1 ELSE 0 END)',
                'latest_trade': 'MAX(transaction_date)'
            },
            order_by='total_trades DESC'
        )
        
        # Apply filters
        if 'min_trades' in query_params:
            try:
                min_trades = int(query_params['min_trades'])
                stocks_df = stocks_df[stocks_df['total_trades'] >= min_trades]
            except ValueError:
                pass
        
        total_count = len(stocks_df)
        
        # Apply pagination
        paged_df = stocks_df.iloc[offset:offset + limit]
        stocks_data = paged_df.to_dict('records')
        
        # Map to Pydantic models
        stocks = []
        for row in stocks_data:
            try:
                stocks.append(Stock(
                    ticker=row['ticker'],
                    trade_count=int(row['total_trades']),
                    purchase_count=int(row.get('purchase_count', 0)),
                    sale_count=int(row.get('sale_count', 0))
                    # Note: company name and sector might require a join with dim_assets/dim_stocks
                    # which is not currently in the handler. To be consistent with existing API
                    # we only return what was aggregated.
                ))
            except Exception as e:
                logger.warning(f"Error mapping stock {row.get('ticker')}: {e}")
                continue

        # Build pagination metadata
        has_next = (offset + len(stocks)) < total_count
        has_prev = offset > 0
        
        base_url = "/v1/stocks"
        other_params = {k: v for k, v in query_params.items() if k not in ['limit', 'offset']}
        
        next_url = None
        if has_next:
            next_params = {**other_params, 'limit': limit, 'offset': offset + limit}
            next_url = f"{base_url}?{urlencode(next_params)}"
            
        prev_url = None
        if has_prev:
            prev_offset = max(0, offset - limit)
            prev_params = {**other_params, 'limit': limit, 'offset': prev_offset}
            prev_url = f"{base_url}?{urlencode(prev_params)}"

        pagination = PaginationMetadata(
            total=total_count,
            count=len(stocks),
            limit=limit,
            offset=offset,
            has_next=has_next,
            has_prev=has_prev,
            next=next_url,
            prev=prev_url
        )
        
        paginated = PaginatedResponse(
            items=stocks,
            pagination=pagination
        )
        
        return success_response(paginated.model_dump())
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve stocks", 500, str(e))
