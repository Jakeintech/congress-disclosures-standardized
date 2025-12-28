import json
import logging
import os
import duckdb
from typing import List, Dict, Any
from urllib.parse import urlencode
from api.lib import ParquetQueryBuilder, success_response, error_response, clean_nan_values
from api.lib.response_models import Transaction, PaginationMetadata, PaginatedResponse

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

# Global connection (reused across warm invocations)
_conn = None


def get_duckdb_connection():
    """Get or create DuckDB connection with S3 support."""
    global _conn
    if _conn is None:
        logger.info("Creating new DuckDB connection (cold start)")
        _conn = duckdb.connect(':memory:')
        _conn.execute("SET home_directory='/tmp';")
        _conn.execute("INSTALL httpfs; LOAD httpfs;")
        _conn.execute("SET enable_http_metadata_cache=true;")
        _conn.execute("SET s3_region='us-east-1';")
    return _conn


def handler(event, context):
    """
    GET /v1/trades - Get all trades with filtering and pagination.
    """
    try:
        query_params = event.get('queryStringParameters') or {}

        # Pagination parameters
        limit = min(int(query_params.get('limit', 50)), 500)
        offset = int(query_params.get('offset', 0))

        # Filters
        ticker = query_params.get('ticker')
        bioguide_id = query_params.get('bioguide_id')
        party = query_params.get('party')
        transaction_type = query_params.get('transaction_type')
        start_date = query_params.get('start_date')
        end_date = query_params.get('end_date')
        min_amount = query_params.get('min_amount')
        max_amount = query_params.get('max_amount')

        conn = get_duckdb_connection()

        # Build WHERE clause
        where_clauses: List[str] = []
        if ticker:
            where_clauses.append(f"ticker = '{ticker.upper()}'")
        if bioguide_id:
            where_clauses.append(f"bioguide_id = '{bioguide_id}'")
        if party:
            where_clauses.append(f"party = '{party.upper()}'")
        if transaction_type:
            where_clauses.append(f"transaction_type = '{transaction_type}'")
        if start_date:
            where_clauses.append(f"transaction_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"transaction_date <= '{end_date}'")
        if min_amount:
            where_clauses.append(f"amount_low >= {min_amount}")
        if max_amount:
            where_clauses.append(f"amount_high <= {max_amount}")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # 1. Count total records
        count_sql = f"SELECT COUNT(*) FROM read_parquet('s3://{S3_BUCKET}/gold/house/financial/facts/fact_ptr_transactions/**/*.parquet', union_by_name=True) WHERE {where_sql}"
        logger.info(f"Counting trades with filters: {where_sql}")
        total_count = qb.conn.execute(count_sql).fetchone()[0]
        
        # 2. Get paginated results
        fetch_sql = f"""
            SELECT * 
            FROM read_parquet('s3://{S3_BUCKET}/gold/house/financial/facts/fact_ptr_transactions/**/*.parquet', union_by_name=True)
            WHERE {where_sql}
            ORDER BY transaction_date DESC
            LIMIT {limit} OFFSET {offset}
        """
        logger.info(f"Querying trades: limit={limit}, offset={offset}, total={total_count}")
        result_df = qb.conn.execute(fetch_sql).fetchdf()

        # 3. Map to Pydantic models
        trades_data = clean_nan_values(result_df.to_dict('records'))
        transactions = []
        for row in trades_data:
            try:
                # Map DuckDB types/names to Pydantic Transaction fields
                tx = Transaction(
                    transaction_id=str(row.get('transaction_id') or row.get('doc_id', '')),
                    disclosure_date=row.get('disclosure_date') or row.get('filing_date'),
                    transaction_date=row.get('transaction_date'),
                    ticker=row.get('ticker'),
                    asset_description=row.get('asset_description') or row.get('description', 'Unknown'),
                    transaction_type=row.get('transaction_type').lower() if row.get('transaction_type') else 'purchase',
                    amount_low=int(row.get('amount_low', 0)) if row.get('amount_low') is not None else 0,
                    amount_high=int(row.get('amount_high', 0)) if row.get('amount_high') is not None else 0,
                    amount=f"${int(row.get('amount_low', 0)):,}" + (f" - ${int(row.get('amount_high', 0)):,}" if row.get('amount_high') else "+"),
                    bioguide_id=row.get('bioguide_id'),
                    member_name=row.get('member_name') or row.get('filer_name') or row.get('full_name') or 'Unknown',
                    filer_name=row.get('member_name') or row.get('filer_name') or row.get('full_name') or 'Unknown',
                    first_name=row.get('first_name'),
                    last_name=row.get('last_name'),
                    party=row.get('party'),
                    state=row.get('state'),
                    chamber=row.get('chamber').lower() if row.get('chamber') else 'house',
                    owner=row.get('owner'),
                    cap_gains_over_200=bool(row.get('cap_gains_over_200')) if row.get('cap_gains_over_200') is not None else None
                )
                transactions.append(tx)
            except Exception as e:
                logger.warning(f"Error mapping trade {row.get('transaction_id')}: {e}")
                continue

        # 4. Build pagination metadata
        has_next = (offset + len(transactions)) < total_count
        has_prev = offset > 0
        
        base_url = "/v1/trades"
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
            count=len(transactions),
            limit=limit,
            offset=offset,
            has_next=has_next,
            has_prev=has_prev,
            next=next_url,
            prev=prev_url
        )
        
        # 5. Build Final Response
        paginated = PaginatedResponse(
            items=transactions,
            pagination=pagination
        )
        
        # Include metadata about filters used
        metadata = {
            'filters': {k: v for k, v in other_params.items() if v is not None}
        }
        
        return success_response(
            paginated.model_dump(),
            metadata=metadata
        )

    except Exception as e:
        logger.error(f"Error retrieving trades: {str(e)}", exc_info=True)
        return error_response(
            message="Failed to retrieve trades",
            status_code=500,
            details=str(e)
        )
