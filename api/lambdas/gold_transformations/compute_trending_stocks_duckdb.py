"""
Lambda handler: Compute agg_trending_stocks using DuckDB

Rolling window aggregations for stock trading activity:
- 7-day, 30-day, 90-day windows
- Buy/sell volume and sentiment scores
- Party-specific metrics (Democrat vs Republican trading)
- Net volume (buy_volume - sell_volume)
"""

import os
import logging
import duckdb
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Global connection for warm container reuse
_conn = None


def get_duckdb_connection():
    """Get or create DuckDB connection with S3 support."""
    global _conn
    if _conn is None:
        logger.info("Creating new DuckDB connection")
        _conn = duckdb.connect(':memory:')
        _conn.execute("INSTALL httpfs;")
        _conn.execute("LOAD httpfs;")
        _conn.execute(f"SET s3_region='{AWS_REGION}';")
        _conn.execute("SET enable_progress_bar=false;")
        logger.info("DuckDB connection established")
    return _conn


def compute_trending_stocks(conn) -> Dict[str, Any]:
    """
    Compute trending stocks aggregations with rolling windows.

    Args:
        conn: DuckDB connection

    Returns:
        Dict with stats (rows_processed, output_paths)
    """
    logger.info("Starting trending stocks computation")

    # Paths
    gold_fact_transactions_path = f"s3://{S3_BUCKET}/gold/facts/fact_ptr_transactions/*.parquet"
    gold_dim_member_path = f"s3://{S3_BUCKET}/gold/dimensions/dim_member/*.parquet"

    # Load transactions with member party info
    logger.info("Loading transaction data with member info...")
    conn.execute(f"""
        CREATE TABLE transactions_with_party AS
        SELECT
            t.transaction_date,
            t.ticker,
            t.transaction_type,
            t.amount_midpoint,
            m.party
        FROM '{gold_fact_transactions_path}' t
        LEFT JOIN '{gold_dim_member_path}' m
            ON t.member_key = m.member_key
        WHERE t.ticker IS NOT NULL
          AND t.ticker != ''
          AND t.transaction_date >= CURRENT_DATE - INTERVAL '90 days'
    """)

    tx_count = conn.execute("SELECT COUNT(*) FROM transactions_with_party").fetchone()[0]
    logger.info(f"Loaded {tx_count} transactions from last 90 days")

    if tx_count == 0:
        logger.warning("No recent transactions found")
        return {
            'rows_processed': 0,
            'output_paths': []
        }

    # Compute aggregates for each time window
    output_paths = []
    rows_by_window = {}

    for window_days, window_label in [(7, '7d'), (30, '30d'), (90, '90d')]:
        logger.info(f"Computing {window_label} window...")

        window_query = f"""
            CREATE OR REPLACE TABLE trending_{window_label} AS
            SELECT
                ticker,
                '{window_label}' AS time_window,
                COUNT(*) AS total_transactions,
                SUM(amount_midpoint) AS total_volume,
                COUNT(DISTINCT CASE WHEN transaction_type = 'Purchase' THEN transaction_date END) AS num_buyers,
                COUNT(DISTINCT CASE WHEN transaction_type = 'Sale' THEN transaction_date END) AS num_sellers,
                SUM(CASE WHEN transaction_type = 'Purchase' THEN amount_midpoint ELSE 0 END) AS buy_volume,
                SUM(CASE WHEN transaction_type = 'Sale' THEN amount_midpoint ELSE 0 END) AS sell_volume,
                SUM(CASE WHEN transaction_type = 'Purchase' THEN amount_midpoint ELSE 0 END) -
                SUM(CASE WHEN transaction_type = 'Sale' THEN amount_midpoint ELSE 0 END) AS net_volume,
                COUNT(CASE WHEN party IN ('D', 'Democrat', 'Democratic') THEN 1 END) AS dem_transactions,
                COUNT(CASE WHEN party IN ('R', 'Republican') THEN 1 END) AS rep_transactions,
                SUM(CASE WHEN party IN ('D', 'Democrat', 'Democratic') AND transaction_type = 'Purchase' THEN amount_midpoint ELSE 0 END) AS dem_buy_volume,
                SUM(CASE WHEN party IN ('R', 'Republican') AND transaction_type = 'Purchase' THEN amount_midpoint ELSE 0 END) AS rep_buy_volume,
                MIN(transaction_date) AS first_trade_date,
                MAX(transaction_date) AS last_trade_date,
                CURRENT_TIMESTAMP AS computed_at
            FROM transactions_with_party
            WHERE transaction_date >= CURRENT_DATE - INTERVAL '{window_days} days'
            GROUP BY ticker
            HAVING COUNT(*) >= 2  -- At least 2 transactions to be "trending"
            ORDER BY total_transactions DESC, total_volume DESC
        """

        conn.execute(window_query)

        # Add sentiment score (net_volume / total_volume)
        conn.execute(f"""
            CREATE OR REPLACE TABLE trending_{window_label}_final AS
            SELECT
                *,
                CASE
                    WHEN total_volume > 0 THEN net_volume / total_volume
                    ELSE 0
                END AS sentiment_score
            FROM trending_{window_label}
        """)

        row_count = conn.execute(f"SELECT COUNT(*) FROM trending_{window_label}_final").fetchone()[0]
        logger.info(f"{window_label} window: {row_count} trending stocks")
        rows_by_window[window_label] = row_count

        # Export to S3
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_path = f"s3://{S3_BUCKET}/gold/aggregates/agg_trending_stocks/window={window_label}/data_{timestamp}.parquet"

        conn.execute(f"""
            COPY trending_{window_label}_final
            TO '{output_path}'
            (FORMAT PARQUET, COMPRESSION ZSTD)
        """)

        logger.info(f"Exported {window_label} to {output_path}")
        output_paths.append(output_path)

    # Also create a combined view for all windows
    logger.info("Creating combined trending stocks view...")
    conn.execute("""
        CREATE TABLE trending_all_windows AS
        SELECT * FROM trending_7d_final
        UNION ALL
        SELECT * FROM trending_30d_final
        UNION ALL
        SELECT * FROM trending_90d_final
    """)

    combined_path = f"s3://{S3_BUCKET}/gold/aggregates/agg_trending_stocks/trending_stocks_all.parquet"
    conn.execute(f"""
        COPY trending_all_windows
        TO '{combined_path}'
        (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    logger.info(f"Exported combined view to {combined_path}")
    output_paths.append(combined_path)

    return {
        'rows_processed': sum(rows_by_window.values()),
        'output_paths': output_paths,
        'rows_by_window': rows_by_window
    }


def lambda_handler(event, context):
    """
    Lambda handler for computing trending stocks aggregations.

    Event parameters (optional):
        - windows: list - Time windows to compute (default: ['7d', '30d', '90d'])

    Returns:
        Dict with processing stats and status
    """
    try:
        logger.info(f"Starting trending stocks computation. Event: {event}")

        # Get DuckDB connection
        conn = get_duckdb_connection()

        # Compute trending stocks
        result = compute_trending_stocks(conn)

        # Return success response
        response = {
            'statusCode': 200,
            'status': 'success',
            'table': 'gold.agg_trending_stocks',
            'rows_processed': result['rows_processed'],
            'output_paths': result['output_paths'],
            'rows_by_window': result['rows_by_window'],
            'execution_id': context.request_id if context else 'local'
        }

        logger.info(f"Computation completed successfully: {result['rows_processed']} rows")
        return response

    except Exception as e:
        logger.error(f"Error computing trending stocks: {e}", exc_info=True)

        return {
            'statusCode': 500,
            'status': 'error',
            'error': str(e),
            'table': 'gold.agg_trending_stocks'
        }


# For local testing
if __name__ == '__main__':
    import json

    # Mock event
    test_event = {}

    # Mock context
    class MockContext:
        request_id = 'local-test-123'

    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2, default=str))
