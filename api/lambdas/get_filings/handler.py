"""
Lambda handler: GET /v1/filings

List filings with filters and pagination.
"""

import os
import json
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    parse_pagination_params,
    parse_date_range,
    build_pagination_response
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def handler(event, context):
    """GET /v1/filings - List filings."""
    try:
        query_params = event.get('queryStringParameters') or {}
        limit, offset = parse_pagination_params(query_params)
        
        filters = {}
        
        # Member filter
        if 'bioguide_id' in query_params:
            filters['bioguide_id'] = query_params['bioguide_id']
        
        # Filing type filter
        if 'filing_type' in query_params:
            filters['filing_type'] = query_params['filing_type'].lower()
        
        # Date range (using filing_date_key which is stored as YYYYMMDD integer)
        if 'start_date' in query_params or 'end_date' in query_params:
            date_field = 'filing_date_key'
            if 'start_date' in query_params:
                # Convert YYYY-MM-DD to YYYYMMDD integer
                start_int = int(query_params['start_date'].replace('-', ''))
                filters[date_field] = filters.get(date_field, {})
                filters[date_field]['gte'] = start_int
            if 'end_date' in query_params:
                end_int = int(query_params['end_date'].replace('-', ''))
                filters[date_field] = filters.get(date_field, {})
                filters[date_field]['lte'] = end_int
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        total_count = qb.count_records(
            'gold/house/financial/facts/fact_filings',
            filters=filters if filters else None
        )
        
        filings_df = qb.query_parquet(
            'gold/house/financial/facts/fact_filings',
            filters=filters if filters else None,
            order_by='filing_date_key DESC',
            limit=limit,
            offset=offset
        )
        
        filings_list = filings_df.to_dict('records')
        
        response = build_pagination_response(
            data=filings_list,
            total_count=total_count,
            limit=limit,
            offset=offset,
            base_url='/v1/filings',
            query_params={k: v for k, v in query_params.items() if k not in ['limit', 'offset']}
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response, default=str)
        }
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve filings", 500, str(e))
