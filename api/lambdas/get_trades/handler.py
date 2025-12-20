"""
Lambda handler: GET /v1/trades
OPTIMIZED: DuckDB with connection pooling and comprehensive filtering
"""

import json
import logging
import os
import duckdb
from typing import List, Dict, Any
from api.lib import success_response, error_response, clean_nan_values

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
        # Set home directory to /tmp for Lambda environment
        _conn.execute("SET home_directory='/tmp';")
        _conn.execute("INSTALL httpfs; LOAD httpfs;")
        _conn.execute("SET enable_http_metadata_cache=true;")
        _conn.execute("SET s3_region='us-east-1';")
    return _conn


def handler(event, context):
    """
    GET /v1/trades - Get all trades with filtering and pagination.

    Query parameters:
    - limit: Records per page (default 50, max 500)
    - offset: Records to skip (default 0)
    - ticker: Filter by stock ticker (e.g., 'AAPL')
    - bioguide_id: Filter by member
    - party: Filter by party ('D', 'R', 'I')
    - transaction_type: Filter by type ('Purchase', 'Sale', 'Exchange')
    - start_date: Filter by transaction_date >= start_date
    - end_date: Filter by transaction_date <= end_date
    - min_amount: Filter by amount >= min_amount (uses amount_low)
    - max_amount: Filter by amount <= max_amount (uses amount_high)
    """
    try:
        query_params = event.get('queryStringParameters') or {}

        # Pagination
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

        # Count total matching records
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM read_parquet('s3://{S3_BUCKET}/gold/house/financial/facts/fact_ptr_transactions/**/*.parquet')
            WHERE {where_sql}
        """

        logger.info(f"Counting trades with filters: {where_sql}")
        total_count = conn.execute(count_query).fetchone()[0]

        # Query trades with member information
        query = f"""
            SELECT
                transaction_key,
                doc_id,
                transaction_date,
                filing_date AS disclosure_date,
                ticker,
                asset_description AS asset_name,
                transaction_type,
                COALESCE(amount_low, 0) AS amount_low,
                COALESCE(amount_high, 0) AS amount_high,
                COALESCE((amount_low + amount_high) / 2.0, 0) AS amount_midpoint,
                comment,
                bioguide_id,
                filer_name AS full_name,
                party,
                state,
                chamber,
                -- Compliance metric (date diff in days)
                CAST((CAST(filing_date AS DATE) - CAST(transaction_date AS DATE)) AS INTEGER) AS disclosure_delay_days
            FROM read_parquet('s3://{S3_BUCKET}/gold/house/financial/facts/fact_ptr_transactions/**/*.parquet')
            WHERE {where_sql}
            ORDER BY transaction_date DESC, filing_date DESC
            LIMIT {limit} OFFSET {offset}
        """

        logger.info(f"Querying trades: limit={limit}, offset={offset}, total={total_count}")
        result_df = conn.execute(query).fetchdf()

        # Clean NaN values before serialization
        trades = clean_nan_values(result_df.to_dict('records'))

        # Build pagination metadata
        has_next = (offset + limit) < total_count
        has_prev = offset > 0

        pagination = {
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'has_next': has_next,
            'has_prev': has_prev
        }

        if has_next:
            pagination['next_offset'] = offset + limit

        if has_prev:
            pagination['prev_offset'] = max(0, offset - limit)

        response = {
            'trades': trades,
            'pagination': pagination,
            'filters': {
                'ticker': ticker,
                'bioguide_id': bioguide_id,
                'party': party,
                'transaction_type': transaction_type,
                'start_date': start_date,
                'end_date': end_date,
                'min_amount': min_amount,
                'max_amount': max_amount
            }
        }

        return success_response(response)

    except Exception as e:
        logger.error(f"Error retrieving trades: {str(e)}", exc_info=True)
        return error_response(
            message="Failed to retrieve trades",
            status_code=500,
            details=str(e)
        )
