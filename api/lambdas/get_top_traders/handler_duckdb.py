"""
Lambda handler: GET /v1/top-traders
OPTIMIZED: DuckDB with complex aggregations and window functions
"""

import json
import logging
import os
import duckdb

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
        _conn.execute("INSTALL httpfs; LOAD httpfs;")
        _conn.execute("SET enable_http_metadata_cache=true;")
        _conn.execute("SET s3_region='us-east-1';")
    return _conn


def handler(event, context):
    """GET /v1/top-traders - Get members with most trading activity."""
    try:
        query_params = event.get('queryStringParameters') or {}

        # Parameters
        days = int(query_params.get('days', 30))  # Last N days
        limit = min(int(query_params.get('limit', 50)), 100)
        party = query_params.get('party')  # Optional: 'D', 'R', or 'I'
        metric = query_params.get('metric', 'volume')  # 'volume' or 'transactions'

        conn = get_duckdb_connection()

        # Build WHERE clause
        where_clauses = [f"t.transaction_date >= CURRENT_DATE - INTERVAL '{days} days'"]

        if party:
            where_clauses.append(f"m.party = '{party}'")

        where_sql = " AND ".join(where_clauses)

        # Sort column based on metric
        sort_col = 'total_volume' if metric == 'volume' else 'total_transactions'

        # Complex aggregation query with window functions
        query = f"""
            WITH member_stats AS (
                SELECT
                    m.bioguide_id,
                    m.full_name,
                    m.party,
                    m.state,
                    m.chamber,
                    COUNT(*) AS total_transactions,
                    SUM((t.amount_low + t.amount_high) / 2.0) AS total_volume,
                    SUM(CASE WHEN t.transaction_type = 'Purchase' THEN 1 ELSE 0 END) AS purchases,
                    SUM(CASE WHEN t.transaction_type = 'Sale' THEN 1 ELSE 0 END) AS sales,
                    SUM(CASE WHEN t.transaction_type = 'Purchase' THEN (t.amount_low + t.amount_high) / 2.0 ELSE 0 END) AS buy_volume,
                    SUM(CASE WHEN t.transaction_type = 'Sale' THEN (t.amount_low + t.amount_high) / 2.0 ELSE 0 END) AS sell_volume,
                    COUNT(DISTINCT t.ticker) AS unique_stocks,
                    MIN(t.transaction_date) AS first_trade_date,
                    MAX(t.transaction_date) AS last_trade_date,
                    -- Compliance metrics
                    AVG(CASE WHEN t.disclosure_date - t.transaction_date <= 45 THEN 1.0 ELSE 0.0 END) AS compliance_rate
                FROM read_parquet('s3://{S3_BUCKET}/gold/facts/fact_ptr_transactions/*.parquet') t
                JOIN read_parquet('s3://{S3_BUCKET}/gold/dimensions/dim_member/*.parquet') m
                    ON t.member_key = m.member_key
                WHERE {where_sql}
                    AND m.is_current = true
                GROUP BY m.bioguide_id, m.full_name, m.party, m.state, m.chamber
            ),
            ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (ORDER BY {sort_col} DESC) AS rank,
                    buy_volume - sell_volume AS net_volume,
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

        traders = result_df.to_dict('records')

        # Get party breakdown
        party_query = f"""
            SELECT
                m.party,
                COUNT(DISTINCT m.bioguide_id) AS member_count,
                SUM((t.amount_low + t.amount_high) / 2.0) AS total_volume
            FROM read_parquet('s3://{S3_BUCKET}/gold/facts/fact_ptr_transactions/*.parquet') t
            JOIN read_parquet('s3://{S3_BUCKET}/gold/dimensions/dim_member/*.parquet') m
                ON t.member_key = m.member_key
            WHERE {where_clauses[0]}
                AND m.is_current = true
            GROUP BY m.party
            ORDER BY total_volume DESC
        """

        party_stats = conn.execute(party_query).fetchdf().to_dict('records')

        response = {
            'days': days,
            'metric': metric,
            'total_traders': len(traders),
            'traders': traders,
            'party_breakdown': party_stats
        }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=1800'  # Cache for 30 minutes
            },
            'body': json.dumps(response, default=str)
        }

    except Exception as e:
        logger.error(f"Error retrieving top traders: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to retrieve top traders',
                'details': str(e)
            })
        }
