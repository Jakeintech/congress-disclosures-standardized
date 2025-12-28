#!/usr/bin/env python3
"""
Lambda handler for building fact_lobbying fact table.

Transforms Bronze/Silver lobbying disclosure data into a queryable fact table.
"""

import gzip
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


def load_lobbying_from_bronze(bucket_name: str) -> pd.DataFrame:
    """Load lobbying disclosures from Bronze layer."""
    logger.info("Loading lobbying data from bronze/lobbying/...")

    prefix = 'bronze/lobbying/'
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    disclosures = []
    processed_count = 0

    for page in pages:
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            # Skip non-filing files (constants, etc.)
            if '/filings/' not in obj['Key']:
                continue

            # Handle both .json and .json.gz files
            if not (obj['Key'].endswith('.json') or obj['Key'].endswith('.json.gz')):
                continue

            try:
                response = s3_client.get_object(Bucket=bucket_name, Key=obj['Key'])
                body_bytes = response['Body'].read()

                # Decompress if gzipped
                if obj['Key'].endswith('.gz'):
                    body_bytes = gzip.decompress(body_bytes)

                data = json.loads(body_bytes.decode('utf-8'))

                # Extract lobbying disclosure data
                disclosure = {
                    'filing_uuid': data.get('filing_uuid'),
                    'filing_year': data.get('filing_year'),
                    'filing_period': data.get('filing_period'),
                    'filing_date': data.get('filing_date'),
                    'client_name': data.get('client_name'),
                    'registrant_name': data.get('registrant_name'),
                    'lobbyist_name': data.get('lobbyist_name'),
                    'amount': data.get('amount'),
                    'issue_code': data.get('issue_code'),
                    'issue_description': data.get('issue_description'),
                    'government_entity': data.get('government_entity'),
                }
                disclosures.append(disclosure)

                processed_count += 1
                if processed_count % 1000 == 0:
                    logger.info(f"  Processed {processed_count} disclosures...")

            except Exception as e:
                logger.warning(f"Error processing {obj['Key']}: {e}")
                continue

    logger.info(f"Loaded {len(disclosures):,} lobbying disclosures")

    if not disclosures:
        logger.warning("No lobbying data found")
        return pd.DataFrame()

    return pd.DataFrame(disclosures)


def build_fact_lobbying(lobbying_df: pd.DataFrame) -> pd.DataFrame:
    """Transform lobbying data into fact table format."""
    if lobbying_df.empty:
        logger.warning("No lobbying data to process")
        return pd.DataFrame()

    logger.info("Building fact_lobbying...")

    # Add load metadata
    lobbying_df['load_timestamp'] = datetime.utcnow().isoformat()

    # Parse amounts (handle string amounts like "$50,000")
    if 'amount' in lobbying_df.columns:
        lobbying_df['amount_numeric'] = lobbying_df['amount'].apply(
            lambda x: float(str(x).replace('$', '').replace(',', '')) if x and str(x).strip() else None
        )

    logger.info(f"Built {len(lobbying_df)} lobbying records")
    return lobbying_df


def write_to_gold(df: pd.DataFrame, bucket_name: str) -> Dict[str, Any]:
    """Write fact_lobbying to gold layer S3."""
    if df.empty:
        logger.warning("Empty dataframe - no files to write")
        return {'files_written': [], 'total_records': 0, 'years': []}

    logger.info("Writing to gold layer...")

    # Partition by year
    if 'filing_year' not in df.columns:
        df['filing_year'] = datetime.utcnow().year

    files_written = []
    for year in df['filing_year'].dropna().unique():
        year_df = df[df['filing_year'] == year]

        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            year_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)
            s3_key = f'gold/lobbying/facts/fact_lobbying/year={int(year)}/part-0000.parquet'
            s3_client.upload_file(tmp.name, bucket_name, s3_key)
            logger.info(f"  Uploaded {len(year_df)} records to s3://{bucket_name}/{s3_key}")
            files_written.append(s3_key)
            os.unlink(tmp.name)

    return {
        'files_written': files_written,
        'total_records': len(df),
        'years': sorted([int(y) for y in df['filing_year'].dropna().unique()])
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for building fact_lobbying.

    Args:
        event: Event data
        context: Lambda context

    Returns:
        Dict with status, records_processed, files_written
    """
    try:
        logger.info("=" * 80)
        logger.info("Lambda: build_fact_lobbying")
        logger.info("=" * 80)
        logger.info(f"Event: {json.dumps(event)}")

        # Get bucket name
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
        if 'bucket_name' in event:
            bucket_name = event['bucket_name']

        # Step 1: Load lobbying data from Bronze
        lobbying_df = load_lobbying_from_bronze(bucket_name)

        # Step 2: Build fact table
        fact_lobbying = build_fact_lobbying(lobbying_df)

        # Step 3: Write to gold layer
        result = write_to_gold(fact_lobbying, bucket_name)

        logger.info("✅ fact_lobbying build complete!")

        return {
            'statusCode': 200,
            'status': 'success',
            'fact_table': 'fact_lobbying',
            'records_processed': result['total_records'],
            'files_written': result['files_written'],
            'years': result['years'],
            'execution_time_ms': context.get_remaining_time_in_millis() if context else None
        }

    except Exception as e:
        logger.error(f"❌ Error building fact_lobbying: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'status': 'error',
            'fact_table': 'fact_lobbying',
            'error': str(e),
            'error_type': type(e).__name__
        }
