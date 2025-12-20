"""
Lambda handler: GET /v1/top-traders
OPTIMIZED: DuckDB with complex aggregations and window functions
"""

import json
import logging
import os
import duckdb
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
        _conn.execute("SET home_directory='/tmp';")
        _conn.execute("INSTALL httpfs; LOAD httpfs;")
        _conn.execute("SET enable_http_metadata_cache=true;")
        _conn.execute("SET s3_region='us-east-1';")
        _conn.execute("SET s3_use_ssl=true;")
    return _conn


def handler(event, context):
    """GET /v1/top-traders - Get members with most trading activity."""
    try:
        query_params = event.get('queryStringParameters') or {}

        # Parameters
        days = int(query_params.get('days', 365))  # Last N days
        limit = min(int(query_params.get('limit', 50)), 100)
        party = query_params.get('party')  # Optional: 'D', 'R', or 'I'
        metric = query_params.get('metric', 'volume')  # 'volume' or 'transactions'

        conn = get_duckdb_connection()

        # Build WHERE clause
        where_clauses = []
        if days > 0:
            where_clauses.append(f"CAST(transaction_date AS DATE) >= CURRENT_DATE - INTERVAL '{days} days'")

        if party:
            where_clauses.append(f"party = '{party}'")

        # Explicitly check for NaN-prone columns
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Sort column based on metric
        sort_col = 'total_volume' if metric == 'volume' else 'total_transactions'

        # Complex aggregation query with window functions
        query = f"""
            WITH member_stats AS (
                SELECT
                    bioguide_id,
                    filer_name AS full_name,
                    party,
                    state,
                    chamber,
                    COUNT(*) AS total_transactions,
                    COALESCE(SUM((amount_low + amount_high) / 2.0), 0) AS total_volume,
                    SUM(CASE WHEN transaction_type = 'Purchase' THEN 1 ELSE 0 END) AS purchases,
                    SUM(CASE WHEN transaction_type = 'Sale' THEN 1 ELSE 0 END) AS sales,
                    COALESCE(SUM(CASE WHEN transaction_type = 'Purchase' THEN (amount_low + amount_high) / 2.0 ELSE 0 END), 0) AS buy_volume,
                    COALESCE(SUM(CASE WHEN transaction_type = 'Sale' THEN (amount_low + amount_high) / 2.0 ELSE 0 END), 0) AS sell_volume,
                    COUNT(DISTINCT ticker) AS unique_stocks,
                    MIN(transaction_date) AS first_trade_date,
                    MAX(transaction_date) AS last_trade_date,
                    -- Compliance metrics
                    COALESCE(AVG(CASE WHEN CAST((CAST(filing_date AS DATE) - CAST(transaction_date AS DATE)) AS INTEGER) <= 45 THEN 1.0 ELSE 0.0 END), 0) AS compliance_rate
                FROM read_parquet('s3://{S3_BUCKET}/gold/house/financial/facts/fact_ptr_transactions/**/*.parquet')
                WHERE {where_sql}
                    AND bioguide_id IS NOT NULL
                GROUP BY bioguide_id, filer_name, party, state, chamber
            ),
            ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (ORDER BY {sort_col} DESC) AS rank,
                    COALESCE(buy_volume - sell_volume, 0) AS net_volume,
                    CASE
                        WHEN total_volume > 0 THEN (buy_volume - sell_volume) / total_volume
                        ELSE 0
                    END AS sentiment_score
                FROM member_stats
            )
            SELECT * FROM ranked
            ORDER BY rank
            LIMIT {limit}
        """

        logger.info(f"Querying top traders: days={days}, limit={limit}, metric={metric}")
        result_df = conn.execute(query).fetchdf()

        # Clean NaN values before serialization
        traders = clean_nan_values(result_df.to_dict('records'))

        # Get party breakdown
        party_query = f"""
            SELECT
                party,
                COUNT(DISTINCT bioguide_id) AS member_count,
                COALESCE(SUM((amount_low + amount_high) / 2.0), 0) AS total_volume
            FROM read_parquet('s3://{S3_BUCKET}/gold/house/financial/facts/fact_ptr_transactions/**/*.parquet')
            WHERE {where_sql}
                AND bioguide_id IS NOT NULL
            GROUP BY party
            ORDER BY total_volume DESC
        """

        party_stats = clean_nan_values(conn.execute(party_query).fetchdf().to_dict('records'))

        response = {
            'days': days,
            'metric': metric,
            'total_traders': len(traders),
            'traders': traders,
            'party_breakdown': party_stats
        }

        return success_response(response)

    except Exception as e:
        logger.error(f"Error retrieving top traders: {str(e)}", exc_info=True)
        return error_response(
            message="Failed to retrieve top traders",
            status_code=500,
            details=str(e)
        )
