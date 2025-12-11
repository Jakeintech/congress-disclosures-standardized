"""
Lambda handler: Build fact_ptr_transactions table using DuckDB

Incremental transformation from Silver to Gold layer with:
- DuckDB for fast S3-native queries
- Watermark-based incremental processing
- Connection pooling for warm Lambda reuse
- Automatic dimension key lookups
"""

import os
import logging
import duckdb
import boto3
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
WATERMARK_TABLE = os.environ.get('WATERMARK_TABLE', 'congress-disclosures-pipeline-watermarks')

# Global connection for warm container reuse
_conn = None
_dynamodb = None


def get_duckdb_connection():
    """Get or create DuckDB connection with S3 support (connection pooling)."""
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


def get_dynamodb_client():
    """Get or create DynamoDB client."""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    return _dynamodb


def get_watermark(table_name: str, watermark_type: str) -> str:
    """
    Get last processed watermark value from DynamoDB.

    Args:
        table_name: Name of the table (e.g., 'gold.fact_ptr_transactions')
        watermark_type: Type of watermark (e.g., 'max_doc_id')

    Returns:
        Last processed value (e.g., '20026590') or '0' if not found
    """
    try:
        dynamodb = get_dynamodb_client()
        table = dynamodb.Table(WATERMARK_TABLE)

        response = table.get_item(
            Key={
                'table_name': table_name,
                'watermark_type': watermark_type
            }
        )

        if 'Item' in response:
            value = response['Item'].get('last_processed_value', '0')
            logger.info(f"Retrieved watermark for {table_name}.{watermark_type}: {value}")
            return value
        else:
            logger.info(f"No watermark found for {table_name}.{watermark_type}, starting from 0")
            return '0'

    except Exception as e:
        logger.warning(f"Failed to get watermark: {e}. Using default '0'")
        return '0'


def update_watermark(table_name: str, watermark_type: str, value: str, rows_processed: int):
    """
    Update watermark in DynamoDB.

    Args:
        table_name: Name of the table
        watermark_type: Type of watermark
        value: New watermark value
        rows_processed: Number of rows processed in this run
    """
    try:
        dynamodb = get_dynamodb_client()
        table = dynamodb.Table(WATERMARK_TABLE)

        table.put_item(Item={
            'table_name': table_name,
            'watermark_type': watermark_type,
            'last_processed_value': str(value),
            'last_processed_timestamp': datetime.utcnow().isoformat(),
            'last_run_status': 'success',
            'rows_processed': rows_processed
        })

        logger.info(f"Updated watermark for {table_name}.{watermark_type} to {value} ({rows_processed} rows)")

    except Exception as e:
        logger.error(f"Failed to update watermark: {e}")
        raise


def build_fact_transactions_incremental(conn, last_doc_id: str) -> Dict[str, Any]:
    """
    Build fact_ptr_transactions table incrementally using DuckDB.

    Args:
        conn: DuckDB connection
        last_doc_id: Last processed doc_id (watermark)

    Returns:
        Dict with stats (rows_processed, max_doc_id, output_path)
    """
    logger.info(f"Starting incremental build from doc_id > {last_doc_id}")

    # Paths
    silver_transactions_path = f"s3://{S3_BUCKET}/silver/house/financial/transactions/*.parquet"
    gold_dim_member_path = f"s3://{S3_BUCKET}/gold/dimensions/dim_member/*.parquet"
    gold_dim_asset_path = f"s3://{S3_BUCKET}/gold/dimensions/dim_asset/*.parquet"

    # Get next transaction_key (max existing key + 1)
    try:
        max_key_query = f"""
            SELECT COALESCE(MAX(transaction_key), 0) as max_key
            FROM 's3://{S3_BUCKET}/gold/facts/fact_ptr_transactions/*.parquet'
        """
        max_key = conn.execute(max_key_query).fetchone()[0]
        next_key = max_key + 1
        logger.info(f"Next transaction_key will start at: {next_key}")
    except Exception as e:
        logger.info(f"No existing fact table found (first run?): {e}")
        next_key = 1

    # Build incremental fact table with DuckDB SQL
    create_query = f"""
        CREATE TABLE new_transactions AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY t.transaction_date, t.doc_id) + {next_key} - 1 AS transaction_key,
            t.transaction_id,
            t.doc_id,
            COALESCE(m.member_key, -1) AS member_key,
            COALESCE(a.asset_key, -1) AS asset_key,
            CAST(REPLACE(CAST(t.transaction_date AS VARCHAR), '-', '') AS INTEGER) AS transaction_date_key,
            CAST(REPLACE(CAST(t.notification_date AS VARCHAR), '-', '') AS INTEGER) AS notification_date_key,
            t.bioguide_id,
            t.ticker,
            t.transaction_type,
            t.amount_low,
            t.amount_high,
            (CAST(t.amount_low AS DECIMAL) + CAST(t.amount_high AS DECIMAL)) / 2.0 AS amount_midpoint,
            t.capital_gains_over_200,
            DATE_DIFF('day', t.transaction_date, t.notification_date) AS days_to_notification,
            t.extraction_confidence,
            CURRENT_TIMESTAMP AS gold_ingest_ts
        FROM '{silver_transactions_path}' t
        LEFT JOIN '{gold_dim_member_path}' m
            ON t.bioguide_id = m.bioguide_id
            AND m.is_current = true
        LEFT JOIN '{gold_dim_asset_path}' a
            ON t.ticker = a.ticker
        WHERE t.doc_id > '{last_doc_id}'
          AND t.transaction_date IS NOT NULL
          AND t.transaction_date >= DATE '2008-01-01'
          AND t.transaction_date <= CURRENT_DATE
        ORDER BY t.transaction_date, t.doc_id
    """

    logger.info("Executing DuckDB query...")
    start_time = datetime.now()
    conn.execute(create_query)
    query_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Query executed in {query_time:.2f}s")

    # Get row count
    row_count = conn.execute("SELECT COUNT(*) FROM new_transactions").fetchone()[0]
    logger.info(f"Rows to process: {row_count}")

    if row_count == 0:
        logger.info("No new transactions to process")
        return {
            'rows_processed': 0,
            'max_doc_id': last_doc_id,
            'output_path': None,
            'query_time_seconds': query_time
        }

    # Get max doc_id for watermark update
    max_doc_id = conn.execute("SELECT MAX(doc_id) FROM new_transactions").fetchone()[0]
    logger.info(f"Max doc_id in batch: {max_doc_id}")

    # Export to S3 (append mode - new file with timestamp)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    output_path = f"s3://{S3_BUCKET}/gold/facts/fact_ptr_transactions/data_incremental_{timestamp}.parquet"

    export_query = f"""
        COPY new_transactions
        TO '{output_path}'
        (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)
    """

    logger.info(f"Exporting to {output_path}...")
    export_start = datetime.now()
    conn.execute(export_query)
    export_time = (datetime.now() - export_start).total_seconds()
    logger.info(f"Export completed in {export_time:.2f}s")

    return {
        'rows_processed': row_count,
        'max_doc_id': max_doc_id,
        'output_path': output_path,
        'query_time_seconds': query_time,
        'export_time_seconds': export_time
    }


def lambda_handler(event, context):
    """
    Lambda handler for building fact_ptr_transactions incrementally.

    Event parameters (optional):
        - force_full_rebuild: bool - If true, rebuild all data (default: false)
        - max_rows: int - Limit number of rows processed (for testing)

    Returns:
        Dict with processing stats and status
    """
    try:
        logger.info(f"Starting fact_ptr_transactions build. Event: {event}")

        # Get parameters
        force_full_rebuild = event.get('force_full_rebuild', False)
        max_rows = event.get('max_rows', None)

        # Get DuckDB connection
        conn = get_duckdb_connection()

        # Get watermark (unless full rebuild)
        if force_full_rebuild:
            logger.info("Force full rebuild requested")
            last_doc_id = '0'
        else:
            last_doc_id = get_watermark('gold.fact_ptr_transactions', 'max_doc_id')

        # Build fact table incrementally
        result = build_fact_transactions_incremental(conn, last_doc_id)

        # Update watermark if rows were processed
        if result['rows_processed'] > 0:
            update_watermark(
                'gold.fact_ptr_transactions',
                'max_doc_id',
                result['max_doc_id'],
                result['rows_processed']
            )

        # Return success response
        response = {
            'statusCode': 200,
            'status': 'success',
            'table': 'gold.fact_ptr_transactions',
            'rows_processed': result['rows_processed'],
            'output_path': result['output_path'],
            'performance': {
                'query_time_seconds': result.get('query_time_seconds', 0),
                'export_time_seconds': result.get('export_time_seconds', 0),
                'total_time_seconds': result.get('query_time_seconds', 0) + result.get('export_time_seconds', 0)
            },
            'watermark': {
                'previous': last_doc_id,
                'current': result['max_doc_id']
            },
            'execution_id': context.request_id if context else 'local'
        }

        logger.info(f"Build completed successfully: {result['rows_processed']} rows")
        return response

    except Exception as e:
        logger.error(f"Error building fact_ptr_transactions: {e}", exc_info=True)

        # Update watermark with failure status
        try:
            dynamodb = get_dynamodb_client()
            table = dynamodb.Table(WATERMARK_TABLE)
            table.update_item(
                Key={
                    'table_name': 'gold.fact_ptr_transactions',
                    'watermark_type': 'max_doc_id'
                },
                UpdateExpression='SET last_run_status = :status, last_error = :error',
                ExpressionAttributeValues={
                    ':status': 'failed',
                    ':error': str(e)
                }
            )
        except:
            pass

        return {
            'statusCode': 500,
            'status': 'error',
            'error': str(e),
            'table': 'gold.fact_ptr_transactions'
        }


# For local testing
if __name__ == '__main__':
    import json

    # Mock event
    test_event = {
        'force_full_rebuild': False,
        'max_rows': 1000
    }

    # Mock context
    class MockContext:
        request_id = 'local-test-123'

    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2, default=str))
