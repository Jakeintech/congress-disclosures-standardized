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
        _conn.execute("SET home_directory='/tmp';")
        _conn.execute("INSTALL httpfs; LOAD httpfs;")
        _conn.execute("SET enable_http_metadata_cache=true;")
        _conn.execute("SET s3_region='us-east-1';")
        _conn.execute("SET s3_use_ssl=true;")
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
                name,
                trade_count AS total_transactions,
                total_volume_usd AS total_volume,
                buy_count,
                sell_count,
                net_sentiment AS sentiment_score,
                unique_members,
                period_start,
                period_end
            FROM read_parquet('s3://{S3_BUCKET}/gold/house/financial/aggregates/agg_trending_stocks/**/*.parquet')
            ORDER BY {sort_by.replace('total_volume', 'total_volume_usd').replace('total_transactions', 'trade_count')} DESC
            LIMIT {limit}
        """

        logger.info(f"Querying trending stocks: window={time_window}, limit={limit}, sort={sort_by}")
        result_df = conn.execute(query).fetchdf()

        # Note: top_movers feature requires historical window data which isn't currently stored
        # Returning empty until we implement proper time-window tracking
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
