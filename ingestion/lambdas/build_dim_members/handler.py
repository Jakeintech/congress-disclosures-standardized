#!/usr/bin/env python3
"""
Lambda handler for building dim_members dimension table.

Wraps the existing build_dim_members_simple.py script for Step Functions orchestration.
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


def load_unique_members_from_filings(bucket_name: str) -> pd.DataFrame:
    """Load unique members from Silver layer filings."""
    logger.info("Loading filings from silver/house/financial/filings...")

    prefix = 'silver/house/financial/filings/'
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

    if 'Contents' not in response:
        raise ValueError(f"No filings found in s3://{bucket_name}/{prefix}")

    dfs = []
    for obj in response['Contents']:
        if obj['Key'].endswith('.parquet'):
            logger.info(f"  Reading {obj['Key']}")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                s3_client.download_file(bucket_name, obj['Key'], tmp.name)
                df = pd.read_parquet(tmp.name)
                dfs.append(df)
                os.unlink(tmp.name)

    all_filings = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(all_filings):,} filings")

    # Silver layer already has first_name, last_name, state_district
    required_cols = ['first_name', 'last_name', 'state_district']
    if not all(col in all_filings.columns for col in required_cols):
        raise ValueError(f"Missing required columns. Found: {list(all_filings.columns)}")

    # Extract unique members
    unique_members = all_filings[required_cols].drop_duplicates()

    # Parse state and district
    unique_members['state'] = unique_members['state_district'].str[:2]
    # Handle cases where district might be empty (e.g., "CA" vs "CA01")
    district_str = unique_members['state_district'].str[2:]
    unique_members['district'] = district_str.replace('', None).astype('Int64')

    logger.info(f"Found {len(unique_members)} unique members")
    return unique_members


def build_dim_members(members_df: pd.DataFrame) -> pd.DataFrame:
    """Build dim_members dimension table (SCD Type 2)."""
    logger.info("Building dim_members records...")

    records = []
    for idx, row in members_df.iterrows():
        record = {
            'bioguide_id': None,  # Future: Congress API enrichment
            'first_name': row['first_name'],
            'last_name': row['last_name'],
            'full_name': f"{row['first_name']} {row['last_name']}",
            'party': None,  # Future: Congress API enrichment
            'state': row['state'],
            'district': row['district'],
            'state_district': row['state_district'],
            'chamber': 'House',
            'member_type': 'Member',
            'start_date': None,
            'end_date': None,
            'is_current': True,
            'effective_from': datetime.utcnow().isoformat(),
            'effective_to': None,
            'version': 1
        }
        records.append(record)

    df = pd.DataFrame(records)

    # Assign surrogate keys
    df = df.sort_values(['last_name', 'first_name', 'state']).reset_index(drop=True)
    df['member_key'] = df.index + 1

    logger.info(f"Built {len(df)} member records")
    return df


def write_to_gold(df: pd.DataFrame, bucket_name: str) -> Dict[str, Any]:
    """Write dim_members to gold layer S3."""
    logger.info("Writing to gold layer...")

    df['year'] = pd.to_datetime(df['effective_from']).dt.year

    files_written = []
    for year in df['year'].unique():
        year_df = df[df['year'] == year].drop(columns=['year'])

        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            year_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)
            s3_key = f'gold/house/financial/dimensions/dim_members/year={year}/part-0000.parquet'
            s3_client.upload_file(tmp.name, bucket_name, s3_key)
            logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")
            files_written.append(s3_key)
            os.unlink(tmp.name)

    return {
        'files_written': files_written,
        'total_records': len(df),
        'years': sorted([int(y) for y in df['year'].unique()])
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for building dim_members.

    Args:
        event: Event data (optional parameters)
        context: Lambda context

    Returns:
        Dict with status, records_processed, files_written
    """
    try:
        logger.info("=" * 80)
        logger.info("Lambda: build_dim_members")
        logger.info("=" * 80)
        logger.info(f"Event: {json.dumps(event)}")

        # Get bucket name from environment or event
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
        if 'bucket_name' in event:
            bucket_name = event['bucket_name']

        # Step 1: Load unique members from filings
        members_df = load_unique_members_from_filings(bucket_name)

        # Step 2: Build dimension table
        dim_members = build_dim_members(members_df)

        # Step 3: Write to gold layer
        result = write_to_gold(dim_members, bucket_name)

        logger.info("✅ dim_members build complete!")

        return {
            'statusCode': 200,
            'status': 'success',
            'dimension': 'dim_members',
            'records_processed': result['total_records'],
            'files_written': result['files_written'],
            'years': result['years'],
            'execution_time_ms': context.get_remaining_time_in_millis() if context else None
        }

    except Exception as e:
        logger.error(f"❌ Error building dim_members: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'status': 'error',
            'dimension': 'dim_members',
            'error': str(e),
            'error_type': type(e).__name__
        }
