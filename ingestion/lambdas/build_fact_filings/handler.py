#!/usr/bin/env python3
"""
Lambda handler for building fact_filings fact table.

Transforms Silver layer filings metadata into a queryable fact table.
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any

import boto3
import pandas as pd

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')


def load_filings_from_silver(bucket_name: str) -> pd.DataFrame:
    """Load filings metadata from Silver layer."""
    logger.info("Loading filings from silver/house/financial/filings/...")

    prefix = 'silver/house/financial/filings/'
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

    if 'Contents' not in response:
        logger.warning("No filings found in Silver layer")
        return pd.DataFrame()

    dfs = []
    for obj in response['Contents']:
        if obj['Key'].endswith('.parquet'):
            logger.info(f"  Reading {obj['Key']}")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                s3_client.download_file(bucket_name, obj['Key'], tmp.name)
                df = pd.read_parquet(tmp.name)
                dfs.append(df)
                os.unlink(tmp.name)

    if not dfs:
        logger.warning("No Parquet files found")
        return pd.DataFrame()

    all_filings = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(all_filings):,} filings")
    return all_filings


def build_fact_filings(filings_df: pd.DataFrame) -> pd.DataFrame:
    """Transform filings into fact table format."""
    if filings_df.empty:
        logger.warning("No filings to process")
        return pd.DataFrame()

    logger.info("Building fact_filings...")

    # Select and rename columns
    fact_filings = filings_df.copy()

    # Create filer_name from first_name + last_name if not present
    if 'filer_name' not in fact_filings.columns or fact_filings['filer_name'].isna().all():
        if 'first_name' in fact_filings.columns and 'last_name' in fact_filings.columns:
            fact_filings['filer_name'] = (
                fact_filings['first_name'].fillna('') + ' ' +
                fact_filings['last_name'].fillna('')
            ).str.strip()
            logger.info("Created filer_name from first_name + last_name")

    # Ensure required columns exist
    required_cols = ['doc_id', 'filing_date', 'filing_type', 'filer_name', 'state_district', 'year']
    for col in required_cols:
        if col not in fact_filings.columns:
            logger.warning(f"Missing column: {col}")
            fact_filings[col] = None

    # Add derived fields
    if 'state_district' in fact_filings.columns:
        fact_filings['state'] = fact_filings['state_district'].str[:2]
        fact_filings['district'] = fact_filings['state_district'].str[3:].replace('', None)

    # Add load metadata
    fact_filings['load_timestamp'] = datetime.utcnow().isoformat()

    logger.info(f"Built {len(fact_filings)} filing records")
    return fact_filings


def write_to_gold(df: pd.DataFrame, bucket_name: str) -> Dict[str, Any]:
    """Write fact_filings to gold layer S3."""
    if df.empty:
        logger.warning("Empty dataframe - no files to write")
        return {'files_written': [], 'total_records': 0, 'years': []}

    logger.info("Writing to gold layer...")

    # Partition by year
    files_written = []
    for year in df['year'].dropna().unique():
        year_df = df[df['year'] == year]

        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            year_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)
            s3_key = f'gold/house/financial/facts/fact_filings/year={int(year)}/part-0000.parquet'
            s3_client.upload_file(tmp.name, bucket_name, s3_key)
            logger.info(f"  Uploaded {len(year_df)} records to s3://{bucket_name}/{s3_key}")
            files_written.append(s3_key)
            os.unlink(tmp.name)

    return {
        'files_written': files_written,
        'total_records': len(df),
        'years': sorted([int(y) for y in df['year'].dropna().unique()])
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for building fact_filings.

    Args:
        event: Event data
        context: Lambda context

    Returns:
        Dict with status, records_processed, files_written
    """
    try:
        logger.info("=" * 80)
        logger.info("Lambda: build_fact_filings")
        logger.info("=" * 80)
        logger.info(f"Event: {json.dumps(event)}")

        # Get bucket name
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
        if 'bucket_name' in event:
            bucket_name = event['bucket_name']

        # Step 1: Load filings from Silver
        filings_df = load_filings_from_silver(bucket_name)

        # Step 2: Build fact table
        fact_filings = build_fact_filings(filings_df)

        # Step 3: Write to gold layer
        result = write_to_gold(fact_filings, bucket_name)

        logger.info("✅ fact_filings build complete!")

        return {
            'statusCode': 200,
            'status': 'success',
            'fact_table': 'fact_filings',
            'records_processed': result['total_records'],
            'files_written': result['files_written'],
            'years': result['years'],
            'execution_time_ms': context.get_remaining_time_in_millis() if context else None
        }

    except Exception as e:
        logger.error(f"❌ Error building fact_filings: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'status': 'error',
            'fact_table': 'fact_filings',
            'error': str(e),
            'error_type': type(e).__name__
        }
