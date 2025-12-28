#!/usr/bin/env python3
"""
Lambda handler for building dim_bills dimension table.

Extracts bill metadata from Congress.gov Bronze/Silver data.
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


def load_bills_from_bronze(bucket_name: str) -> pd.DataFrame:
    """Load bill metadata from Bronze layer Congress.gov data."""
    logger.info("Loading bills from bronze/congress/bills/...")

    prefix = 'bronze/congress/bills/'
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    bills = []
    processed_count = 0

    for page in pages:
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            if not obj['Key'].endswith('.json'):
                continue

            try:
                response = s3_client.get_object(Bucket=bucket_name, Key=obj['Key'])
                data = json.loads(response['Body'].read().decode('utf-8'))

                # Extract bill metadata
                bill = {
                    'bill_number': data.get('number'),
                    'bill_type': data.get('type'),
                    'congress': data.get('congress'),
                    'title': data.get('title', '')[:500],  # Truncate for storage
                    'introduced_date': data.get('introducedDate'),
                    'sponsor_bioguide_id': data.get('sponsors', [{}])[0].get('bioguideId') if data.get('sponsors') else None,
                    'sponsor_name': data.get('sponsors', [{}])[0].get('fullName') if data.get('sponsors') else None,
                    'policy_area': data.get('policyArea', {}).get('name'),
                    'latest_action_date': data.get('latestAction', {}).get('actionDate'),
                    'latest_action_text': data.get('latestAction', {}).get('text', '')[:200],
                }
                bills.append(bill)

                processed_count += 1
                if processed_count % 1000 == 0:
                    logger.info(f"  Processed {processed_count} bills...")

            except Exception as e:
                logger.warning(f"Error processing {obj['Key']}: {e}")
                continue

    logger.info(f"Loaded {len(bills):,} bills from {processed_count} files")

    if not bills:
        logger.warning("No bills found in Bronze layer - returning empty dataframe")
        return pd.DataFrame()

    return pd.DataFrame(bills)


def build_dim_bills(bills_df: pd.DataFrame) -> pd.DataFrame:
    """Build dim_bills dimension table."""
    if bills_df.empty:
        logger.warning("No bills to process - returning empty dimension")
        return pd.DataFrame()

    logger.info("Building dim_bills records...")

    # Add metadata
    bills_df['effective_from'] = datetime.utcnow().isoformat()
    bills_df['effective_to'] = None
    bills_df['version'] = 1

    # Create bill_id (e.g., "119-hr-1234")
    bills_df['bill_id'] = bills_df.apply(
        lambda row: f"{row['congress']}-{row['bill_type'].lower()}-{row['bill_number']}"
        if pd.notna(row['congress']) and pd.notna(row['bill_type']) and pd.notna(row['bill_number'])
        else None,
        axis=1
    )

    # Assign surrogate keys
    bills_df = bills_df.sort_values(['congress', 'bill_type', 'bill_number']).reset_index(drop=True)
    bills_df['bill_key'] = bills_df.index + 1

    logger.info(f"Built {len(bills_df)} bill records")
    return bills_df


def write_to_gold(df: pd.DataFrame, bucket_name: str) -> Dict[str, Any]:
    """Write dim_bills to gold layer S3."""
    if df.empty:
        logger.warning("Empty dataframe - no files to write")
        return {'files_written': [], 'total_records': 0, 'congresses': []}

    logger.info("Writing to gold layer...")

    # Partition by congress
    files_written = []
    for congress in df['congress'].dropna().unique():
        congress_df = df[df['congress'] == congress]

        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            congress_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)
            s3_key = f'gold/congress/dimensions/dim_bills/congress={int(congress)}/part-0000.parquet'
            s3_client.upload_file(tmp.name, bucket_name, s3_key)
            logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")
            files_written.append(s3_key)
            os.unlink(tmp.name)

    return {
        'files_written': files_written,
        'total_records': len(df),
        'congresses': sorted([int(c) for c in df['congress'].dropna().unique()])
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for building dim_bills.

    Args:
        event: Event data (optional parameters)
        context: Lambda context

    Returns:
        Dict with status, records_processed, files_written
    """
    try:
        logger.info("=" * 80)
        logger.info("Lambda: build_dim_bills")
        logger.info("=" * 80)
        logger.info(f"Event: {json.dumps(event)}")

        # Get bucket name
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
        if 'bucket_name' in event:
            bucket_name = event['bucket_name']

        # Step 1: Load bills from Bronze
        bills_df = load_bills_from_bronze(bucket_name)

        # Step 2: Build dimension table
        dim_bills = build_dim_bills(bills_df)

        # Step 3: Write to gold layer
        result = write_to_gold(dim_bills, bucket_name)

        logger.info("✅ dim_bills build complete!")

        return {
            'statusCode': 200,
            'status': 'success',
            'dimension': 'dim_bills',
            'records_processed': result['total_records'],
            'files_written': result['files_written'],
            'congresses': result.get('congresses', []),
            'execution_time_ms': context.get_remaining_time_in_millis() if context else None
        }

    except Exception as e:
        logger.error(f"❌ Error building dim_bills: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'status': 'error',
            'dimension': 'dim_bills',
            'error': str(e),
            'error_type': type(e).__name__
        }
