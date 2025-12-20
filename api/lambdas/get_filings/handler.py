"""
Lambda handler: GET /v1/filings

List filings with filters and pagination.
"""

import os
import json
import logging
from urllib.parse import urlencode
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    parse_pagination_params
)
from api.lib.response_models import Filing, PaginationMetadata, PaginatedResponse

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
        
        filings_data = filings_df.to_dict('records')
        
        if filings_data:
            logger.info(f"Sample row keys: {list(filings_data[0].keys())}")
        
        # Map to Pydantic models
        filings = []
        for row in filings_data:
            try:
                filings.append(Filing(
                    doc_id=row['doc_id'],
                    bioguide_id=row.get('bioguide_id'),
                    member_name=row.get('member_name') or row.get('filer_name', 'Unknown'),
                    first_name=row.get('first_name'),
                    last_name=row.get('last_name'),
                    filing_type=row.get('filing_type', 'P'),
                    filing_date=row.get('filing_date'),
                    disclosure_year=row.get('disclosure_year'),
                    filing_year=row.get('filing_year') or row.get('disclosure_year') or 0,
                    pdf_url=row.get('filing_url')
                ))
            except Exception as e:
                logger.warning(f"Error mapping filing {row.get('doc_id')}: {e}")
                continue

        # Build pagination metadata
        has_next = (offset + len(filings)) < total_count
        has_prev = offset > 0
        
        base_url = "/v1/filings"
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
            count=len(filings),
            limit=limit,
            offset=offset,
            has_next=has_next,
            has_prev=has_prev,
            next=next_url,
            prev=prev_url
        )
        
        paginated = PaginatedResponse(
            items=filings,
            pagination=pagination
        )

        return success_response(paginated.model_dump())

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve filings", 500, str(e))
