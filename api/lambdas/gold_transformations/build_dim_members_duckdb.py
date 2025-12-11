"""
Lambda handler: Build dim_member table using DuckDB with SCD Type 2

Implements Slowly Changing Dimensions (Type 2) to track historical changes:
- Party changes (Democrat → Republican, etc.)
- District changes (CA-12 → CA-11, etc.)
- Committee assignments
- Leadership roles

Each change creates a new row with valid_from/valid_to dates.
"""

import os
import logging
import duckdb
import boto3
from datetime import datetime, date
from typing import Dict, Any, List

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


def get_dynamodb_client():
    """Get or create DynamoDB client."""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    return _dynamodb


def get_watermark(table_name: str, watermark_type: str) -> str:
    """Get last processed watermark value from DynamoDB."""
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
            value = response['Item'].get('last_processed_value', '1900-01-01')
            logger.info(f"Retrieved watermark for {table_name}.{watermark_type}: {value}")
            return value
        else:
            logger.info(f"No watermark found for {table_name}.{watermark_type}, starting from 1900-01-01")
            return '1900-01-01'

    except Exception as e:
        logger.warning(f"Failed to get watermark: {e}. Using default '1900-01-01'")
        return '1900-01-01'


def update_watermark(table_name: str, watermark_type: str, value: str, rows_processed: int):
    """Update watermark in DynamoDB."""
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


def build_dim_member_scd2(conn, last_update_date: str) -> Dict[str, Any]:
    """
    Build dim_member table with SCD Type 2 logic.

    Strategy:
    1. Load current dimension (all active records)
    2. Load new/updated members from Silver
    3. Detect changes in key attributes (party, district, committees)
    4. Expire old records (set valid_to date)
    5. Insert new records with updated values

    Args:
        conn: DuckDB connection
        last_update_date: Last processed date (watermark)

    Returns:
        Dict with stats (rows_inserted, rows_expired, output_path)
    """
    logger.info(f"Starting SCD Type 2 build from date > {last_update_date}")

    # Paths
    silver_filings_path = f"s3://{S3_BUCKET}/silver/house/financial/filings/*.parquet"
    silver_members_path = f"s3://{S3_BUCKET}/silver/congress_gov/members/*.parquet"
    gold_dim_member_path = f"s3://{S3_BUCKET}/gold/dimensions/dim_member/*.parquet"

    # Step 1: Load existing dimension (current records only)
    logger.info("Loading existing dimension...")
    try:
        conn.execute(f"""
            CREATE TABLE existing_members AS
            SELECT *
            FROM '{gold_dim_member_path}'
            WHERE is_current = true
        """)
        existing_count = conn.execute("SELECT COUNT(*) FROM existing_members").fetchone()[0]
        logger.info(f"Loaded {existing_count} existing members")
    except Exception as e:
        logger.info(f"No existing dimension found (first run?): {e}")
        conn.execute("""
            CREATE TABLE existing_members (
                member_key BIGINT,
                bioguide_id VARCHAR,
                full_name VARCHAR,
                first_name VARCHAR,
                last_name VARCHAR,
                party VARCHAR,
                state VARCHAR,
                district VARCHAR,
                chamber VARCHAR,
                office VARCHAR,
                phone VARCHAR,
                twitter_handle VARCHAR,
                official_website VARCHAR,
                leadership_role VARCHAR,
                committees VARCHAR,
                subcommittees VARCHAR,
                valid_from DATE,
                valid_to DATE,
                is_current BOOLEAN,
                gold_ingest_ts TIMESTAMP
            )
        """)
        existing_count = 0

    # Step 2: Load new/updated members from Silver
    logger.info("Loading new members from Silver...")
    conn.execute(f"""
        CREATE TABLE new_members AS
        SELECT DISTINCT
            f.bioguide_id,
            COALESCE(m.full_name, f.first_name || ' ' || f.last_name) AS full_name,
            f.first_name,
            f.last_name,
            CASE
                WHEN m.party IN ('D', 'Democrat', 'Democratic') THEN 'Democrat'
                WHEN m.party IN ('R', 'Republican') THEN 'Republican'
                WHEN m.party IN ('I', 'Independent') THEN 'Independent'
                ELSE COALESCE(m.party, 'Unknown')
            END AS party,
            COALESCE(m.state, SUBSTRING(f.state_district, 1, 2)) AS state,
            COALESCE(m.district, SUBSTRING(f.state_district, 4)) AS district,
            COALESCE(m.chamber, 'House') AS chamber,
            f.office,
            m.phone,
            m.twitter_handle,
            m.official_website,
            m.leadership_role,
            m.committees,
            m.subcommittees,
            MAX(f.filing_date) AS last_filing_date
        FROM '{silver_filings_path}' f
        LEFT JOIN '{silver_members_path}' m
            ON f.bioguide_id = m.bioguide_id
        WHERE f.filing_date > DATE '{last_update_date}'
        GROUP BY ALL
    """)

    new_count = conn.execute("SELECT COUNT(*) FROM new_members").fetchone()[0]
    logger.info(f"Loaded {new_count} new/updated members")

    if new_count == 0:
        logger.info("No new members to process")
        return {
            'rows_inserted': 0,
            'rows_expired': 0,
            'output_path': None
        }

    # Step 3: Detect changes (party, district, or committees changed)
    logger.info("Detecting changes...")
    conn.execute("""
        CREATE TABLE changed_members AS
        SELECT
            e.member_key,
            e.bioguide_id,
            n.party AS new_party,
            e.party AS old_party,
            n.district AS new_district,
            e.district AS old_district,
            n.committees AS new_committees,
            e.committees AS old_committees,
            n.last_filing_date AS change_date
        FROM new_members n
        INNER JOIN existing_members e
            ON n.bioguide_id = e.bioguide_id
        WHERE n.party != e.party
           OR n.district != e.district
           OR COALESCE(n.committees, '') != COALESCE(e.committees, '')
    """)

    changed_count = conn.execute("SELECT COUNT(*) FROM changed_members").fetchone()[0]
    logger.info(f"Detected {changed_count} members with changes")

    # Step 4: Get next member_key
    try:
        max_key = conn.execute("SELECT MAX(member_key) FROM existing_members").fetchone()[0] or 0
    except:
        max_key = 0
    next_key = max_key + 1
    logger.info(f"Next member_key: {next_key}")

    # Step 5: Build final dimension
    logger.info("Building final dimension...")
    conn.execute(f"""
        CREATE TABLE final_dim_member AS
        -- Expired records (unchanged, just copy)
        SELECT
            e.member_key,
            e.bioguide_id,
            e.full_name,
            e.first_name,
            e.last_name,
            e.party,
            e.state,
            e.district,
            e.chamber,
            e.office,
            e.phone,
            e.twitter_handle,
            e.official_website,
            e.leadership_role,
            e.committees,
            e.subcommittees,
            e.valid_from,
            COALESCE(c.change_date - INTERVAL '1 day', e.valid_to) AS valid_to,
            CASE WHEN c.bioguide_id IS NOT NULL THEN false ELSE e.is_current END AS is_current,
            e.gold_ingest_ts
        FROM existing_members e
        LEFT JOIN changed_members c
            ON e.bioguide_id = c.bioguide_id

        UNION ALL

        -- New records for changed members
        SELECT
            ROW_NUMBER() OVER (ORDER BY n.bioguide_id) + {next_key} - 1 AS member_key,
            n.bioguide_id,
            n.full_name,
            n.first_name,
            n.last_name,
            n.party,
            n.state,
            n.district,
            n.chamber,
            n.office,
            n.phone,
            n.twitter_handle,
            n.official_website,
            n.leadership_role,
            n.committees,
            n.subcommittees,
            n.last_filing_date AS valid_from,
            DATE '9999-12-31' AS valid_to,
            true AS is_current,
            CURRENT_TIMESTAMP AS gold_ingest_ts
        FROM new_members n
        WHERE n.bioguide_id IN (
            SELECT bioguide_id FROM changed_members
            UNION
            SELECT bioguide_id FROM new_members
            WHERE bioguide_id NOT IN (SELECT bioguide_id FROM existing_members)
        )
    """)

    final_count = conn.execute("SELECT COUNT(*) FROM final_dim_member").fetchone()[0]
    logger.info(f"Final dimension has {final_count} rows")

    # Step 6: Export to S3
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    output_path = f"s3://{S3_BUCKET}/gold/dimensions/dim_member/dim_member_{timestamp}.parquet"

    logger.info(f"Exporting to {output_path}...")
    conn.execute(f"""
        COPY final_dim_member
        TO '{output_path}'
        (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    # Get max date for watermark
    max_date = conn.execute("SELECT MAX(valid_from) FROM final_dim_member WHERE is_current = true").fetchone()[0]

    return {
        'rows_inserted': new_count,
        'rows_expired': changed_count,
        'total_rows': final_count,
        'output_path': output_path,
        'max_date': str(max_date)
    }


def lambda_handler(event, context):
    """
    Lambda handler for building dim_member with SCD Type 2.

    Event parameters (optional):
        - force_full_rebuild: bool - If true, rebuild all data (default: false)

    Returns:
        Dict with processing stats and status
    """
    try:
        logger.info(f"Starting dim_member build (SCD Type 2). Event: {event}")

        # Get parameters
        force_full_rebuild = event.get('force_full_rebuild', False)

        # Get DuckDB connection
        conn = get_duckdb_connection()

        # Get watermark (unless full rebuild)
        if force_full_rebuild:
            logger.info("Force full rebuild requested")
            last_update_date = '1900-01-01'
        else:
            last_update_date = get_watermark('gold.dim_member', 'max_valid_from_date')

        # Build dimension with SCD Type 2
        result = build_dim_member_scd2(conn, last_update_date)

        # Update watermark if rows were processed
        if result['rows_inserted'] > 0:
            update_watermark(
                'gold.dim_member',
                'max_valid_from_date',
                result['max_date'],
                result['rows_inserted']
            )

        # Return success response
        response = {
            'statusCode': 200,
            'status': 'success',
            'table': 'gold.dim_member',
            'scd_type': 2,
            'rows_inserted': result['rows_inserted'],
            'rows_expired': result['rows_expired'],
            'total_rows': result['total_rows'],
            'output_path': result['output_path'],
            'watermark': {
                'previous': last_update_date,
                'current': result['max_date']
            },
            'execution_id': context.request_id if context else 'local'
        }

        logger.info(f"Build completed successfully: {result['rows_inserted']} inserted, {result['rows_expired']} expired")
        return response

    except Exception as e:
        logger.error(f"Error building dim_member: {e}", exc_info=True)

        return {
            'statusCode': 500,
            'status': 'error',
            'error': str(e),
            'table': 'gold.dim_member'
        }


# For local testing
if __name__ == '__main__':
    import json

    # Mock event
    test_event = {
        'force_full_rebuild': False
    }

    # Mock context
    class MockContext:
        request_id = 'local-test-123'

    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2, default=str))
