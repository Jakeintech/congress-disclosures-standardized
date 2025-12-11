"""
Lambda handler: GET /v1/trades
OPTIMIZED: DuckDB with connection pooling and comprehensive filtering
"""

import json
import logging
import os
import duckdb
from typing import List, Dict, Any

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
            where_clauses.append(f"t.ticker = '{ticker.upper()}'")

        if bioguide_id:
            where_clauses.append(f"m.bioguide_id = '{bioguide_id}'")

        if party:
            where_clauses.append(f"m.party = '{party.upper()}'")

        if transaction_type:
            where_clauses.append(f"t.transaction_type = '{transaction_type}'")

        if start_date:
            where_clauses.append(f"t.transaction_date >= '{start_date}'")

        if end_date:
            where_clauses.append(f"t.transaction_date <= '{end_date}'")

        if min_amount:
            where_clauses.append(f"t.amount_low >= {min_amount}")

        if max_amount:
            where_clauses.append(f"t.amount_high <= {max_amount}")

        # Add is_current filter for member dimension
        where_clauses.append("m.is_current = true")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Count total matching records
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM read_parquet('s3://{S3_BUCKET}/gold/facts/fact_ptr_transactions/*.parquet') t
            JOIN read_parquet('s3://{S3_BUCKET}/gold/dimensions/dim_member/*.parquet') m
                ON t.member_key = m.member_key
            WHERE {where_sql}
        """

        logger.info(f"Counting trades with filters: {where_sql}")
        total_count = conn.execute(count_query).fetchone()[0]

        # Query trades with member information
        query = f"""
            SELECT
                t.transaction_id,
                t.doc_id,
                t.transaction_date,
                t.disclosure_date,
                t.ticker,
                t.asset_name,
                t.transaction_type,
                t.amount_low,
                t.amount_high,
                (t.amount_low + t.amount_high) / 2.0 AS amount_midpoint,
                t.comment,
                m.bioguide_id,
                m.full_name,
                m.party,
                m.state,
                m.chamber,
                -- Compliance metric
                t.disclosure_date - t.transaction_date AS disclosure_delay_days
            FROM read_parquet('s3://{S3_BUCKET}/gold/facts/fact_ptr_transactions/*.parquet') t
            JOIN read_parquet('s3://{S3_BUCKET}/gold/dimensions/dim_member/*.parquet') m
                ON t.member_key = m.member_key
            WHERE {where_sql}
            ORDER BY t.transaction_date DESC, t.disclosure_date DESC
            LIMIT {limit} OFFSET {offset}
        """

        logger.info(f"Querying trades: limit={limit}, offset={offset}, total={total_count}")
        result_df = conn.execute(query).fetchdf()

        trades = result_df.to_dict('records')

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

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=300'  # Cache for 5 minutes
            },
            'body': json.dumps(response, default=str)
        }

    except Exception as e:
        logger.error(f"Error retrieving trades: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Failed to retrieve trades',
                'details': str(e)
            })
        }
