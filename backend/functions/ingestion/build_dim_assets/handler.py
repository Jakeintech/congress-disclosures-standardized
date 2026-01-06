#!/usr/bin/env python3
"""
Lambda handler for building dim_assets dimension table.

Extracts unique assets from PTR transactions and creates a normalized dimension table.
"""

import json
import logging
import os
import tempfile
from collections import Counter
from datetime import datetime
from typing import Dict, Any

import boto3
import pandas as pd

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')


def load_unique_assets_from_silver(bucket_name: str) -> pd.DataFrame:
    """Load unique assets from Silver layer structured PTR data."""
    logger.info("Loading assets from silver/house/financial/objects/filing_type=type_p/...")

    prefix = 'silver/house/financial/objects/filing_type=type_p/'
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    assets = []
    asset_occurrences = Counter()
    asset_first_seen = {}
    asset_last_seen = {}
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

                # Extract transactions from Type P filings
                transactions = data.get('transactions', [])

                for txn in transactions:
                    asset_name = txn.get('asset_name', '').strip()
                    if not asset_name:
                        continue

                    # Track occurrences
                    asset_occurrences[asset_name] += 1

                    # Track first/last seen
                    txn_date = txn.get('transaction_date')
                    if txn_date:
                        if asset_name not in asset_first_seen or txn_date < asset_first_seen[asset_name]:
                            asset_first_seen[asset_name] = txn_date
                        if asset_name not in asset_last_seen or txn_date > asset_last_seen[asset_name]:
                            asset_last_seen[asset_name] = txn_date

                    assets.append(asset_name)

                processed_count += 1
                if processed_count % 100 == 0:
                    logger.info(f"  Processed {processed_count} files...")

            except Exception as e:
                logger.warning(f"Error processing {obj['Key']}: {e}")
                continue

    logger.info(f"Loaded {len(assets):,} total asset transactions from {processed_count} files")

    # Create unique assets dataframe
    unique_assets = pd.DataFrame({
        'asset_name': list(set(assets))
    })

    # Add occurrence counts and dates
    unique_assets['occurrence_count'] = unique_assets['asset_name'].map(asset_occurrences)
    unique_assets['first_seen_date'] = unique_assets['asset_name'].map(asset_first_seen)
    unique_assets['last_seen_date'] = unique_assets['asset_name'].map(asset_last_seen)

    logger.info(f"Found {len(unique_assets)} unique assets")
    return unique_assets


def build_dim_assets(assets_df: pd.DataFrame) -> pd.DataFrame:
    """Build dim_assets dimension table."""
    logger.info("Building dim_assets records...")

    records = []
    for idx, row in assets_df.iterrows():
        record = {
            'asset_name': row['asset_name'],
            'asset_type': 'Stock',  # Default - can be enhanced with classification logic
            'ticker_symbol': None,  # Future: Extract from asset_name with regex
            'sector': None,         # Future: API enrichment
            'industry': None,       # Future: API enrichment
            'market_cap': None,     # Future: API enrichment
            'occurrence_count': row['occurrence_count'],
            'first_seen_date': row.get('first_seen_date'),
            'last_seen_date': row.get('last_seen_date'),
            'effective_from': datetime.utcnow().isoformat(),
            'effective_to': None,
            'version': 1
        }
        records.append(record)

    df = pd.DataFrame(records)

    # Assign surrogate keys
    df = df.sort_values(['asset_name']).reset_index(drop=True)
    df['asset_key'] = df.index + 1

    logger.info(f"Built {len(df)} asset records")
    return df


def write_to_gold(df: pd.DataFrame, bucket_name: str) -> Dict[str, Any]:
    """Write dim_assets to gold layer S3."""
    logger.info("Writing to gold layer...")

    # Partition by year (use current year for initial load)
    df['year'] = datetime.utcnow().year

    files_written = []
    for year in df['year'].unique():
        year_df = df[df['year'] == year].drop(columns=['year'])

        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            year_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)
            s3_key = f'gold/house/financial/dimensions/dim_assets/year={year}/part-0000.parquet'
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
    Lambda handler for building dim_assets.

    Args:
        event: Event data (optional parameters)
        context: Lambda context

    Returns:
        Dict with status, records_processed, files_written
    """
    try:
        logger.info("=" * 80)
        logger.info("Lambda: build_dim_assets")
        logger.info("=" * 80)
        logger.info(f"Event: {json.dumps(event)}")

        # Get bucket name
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
        if 'bucket_name' in event:
            bucket_name = event['bucket_name']

        # Step 1: Load unique assets from Silver
        assets_df = load_unique_assets_from_silver(bucket_name)

        # Step 2: Build dimension table
        dim_assets = build_dim_assets(assets_df)

        # Step 3: Write to gold layer
        result = write_to_gold(dim_assets, bucket_name)

        logger.info("✅ dim_assets build complete!")

        return {
            'statusCode': 200,
            'status': 'success',
            'dimension': 'dim_assets',
            'records_processed': result['total_records'],
            'files_written': result['files_written'],
            'years': result['years'],
            'execution_time_ms': context.get_remaining_time_in_millis() if context else None
        }

    except Exception as e:
        logger.error(f"❌ Error building dim_assets: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'status': 'error',
            'dimension': 'dim_assets',
            'error': str(e),
            'error_type': type(e).__name__
        }
