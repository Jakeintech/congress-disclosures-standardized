"""
Lambda handler: GET /v1/trending-stocks
OPTIMIZED: DuckDB with connection pooling and pre-computed aggregates
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
    """GET /v1/trending-stocks - Get trending stocks with activity metrics."""
    try:
        query_params = event.get('queryStringParameters') or {}

        # Parameters
        time_window = query_params.get('window', '30d')  # 7d, 30d, or 90d
        limit = min(int(query_params.get('limit', 50)), 200)
        sort_by = query_params.get('sort_by', 'total_volume')  # total_volume, sentiment_score, total_transactions

        # Validate time_window
        if time_window not in ['7d', '30d', '90d']:
            time_window = '30d'

        conn = get_duckdb_connection()

        # Query pre-computed aggregates from Gold layer
        query = f"""
            SELECT
                ticker,
                time_window,
                total_transactions,
                total_volume,
                buy_volume,
                sell_volume,
                net_volume,
                sentiment_score,
                dem_transactions,
                rep_transactions,
                unique_members
            FROM read_parquet('s3://{S3_BUCKET}/gold/aggregates/trending_stocks/*.parquet')
            WHERE time_window = '{time_window}'
            ORDER BY {sort_by} DESC
            LIMIT {limit}
        """

        logger.info(f"Querying trending stocks: window={time_window}, limit={limit}, sort={sort_by}")
        result_df = conn.execute(query).fetchdf()

        # Get top movers (biggest sentiment change)
        movers_query = f"""
            WITH current AS (
                SELECT ticker, sentiment_score
                FROM read_parquet('s3://{S3_BUCKET}/gold/aggregates/trending_stocks/*.parquet')
                WHERE time_window = '{time_window}'
            ),
            previous AS (
                SELECT ticker, sentiment_score AS prev_score
                FROM read_parquet('s3://{S3_BUCKET}/gold/aggregates/trending_stocks/*.parquet')
                WHERE time_window = '{time_window}_prev'
            )
            SELECT
                c.ticker,
                c.sentiment_score,
                COALESCE(p.prev_score, 0) AS prev_score,
                (c.sentiment_score - COALESCE(p.prev_score, 0)) AS sentiment_change
            FROM current c
            LEFT JOIN previous p ON c.ticker = p.ticker
            ORDER BY ABS(sentiment_change) DESC
            LIMIT 10
        """

        try:
            movers_df = conn.execute(movers_query).fetchdf()
            top_movers = movers_df.to_dict('records')
        except:
            # Fallback if previous window doesn't exist
            top_movers = []

        stocks = result_df.to_dict('records')

        response = {
            'time_window': time_window,
            'total_stocks': len(stocks),
            'stocks': stocks,
            'top_movers': top_movers,
            'sort_by': sort_by
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
        logger.error(f"Error retrieving trending stocks: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to retrieve trending stocks',
                'details': str(e)
            })
        }
