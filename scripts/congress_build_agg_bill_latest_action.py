#!/usr/bin/env python3
"""
Build Gold aggregate for latest bill action per bill.

Reads Silver bill_actions and creates an aggregate table with each bill's
most recent action for sorting and display purposes.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
from io import BytesIO
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def read_silver_parquet(s3_client, prefix: str) -> pd.DataFrame:
    """Read all Parquet files from a Silver prefix."""
    logger.info(f"Reading from s3://{BUCKET_NAME}/{prefix}")

    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    if 'Contents' not in response:
        logger.warning(f"No files found in {prefix}")
        return pd.DataFrame()

    dfs = []
    for obj in response['Contents']:
        if obj['Key'].endswith('.parquet'):
            logger.info(f"  Reading {obj['Key']}")
            response_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
            df = pd.read_parquet(BytesIO(response_obj['Body'].read()))
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


def build_agg_bill_latest_action() -> pd.DataFrame:
    """Build aggregate table of latest action per bill."""
    s3 = boto3.client('s3')

    # 1. Read Silver bill_actions
    actions_df = read_silver_parquet(s3, 'silver/congress/bill_actions/')
    if actions_df.empty:
        logger.error("No bill actions found in Silver layer")
        return pd.DataFrame()

    logger.info(f"Loaded {len(actions_df)} actions from Silver")

    # 2. Ensure action_date is datetime
    if 'action_date' in actions_df.columns:
        actions_df['action_date'] = pd.to_datetime(actions_df['action_date'], errors='coerce')

    # 3. Find latest action per bill
    latest_actions = actions_df.sort_values('action_date', ascending=False).groupby('bill_id').first().reset_index()

    logger.info(f"Found latest actions for {len(latest_actions)} bills")

    # 4. Calculate days since action
    today = datetime.utcnow()
    latest_actions['days_since_action'] = (today - pd.to_datetime(latest_actions['action_date'])).dt.days

    # 5. Select relevant columns
    result_df = latest_actions[[
        'bill_id',
        'congress',
        'bill_type',
        'bill_number',
        'action_date',
        'action_text',
        'action_code',
        'chamber',
        'days_since_action'
    ]].copy()

    # 6. Rename for clarity
    result_df = result_df.rename(columns={
        'action_date': 'latest_action_date',
        'action_text': 'latest_action_text',
        'action_code': 'latest_action_code',
        'chamber': 'latest_action_chamber'
    })

    # 7. Add metadata
    result_df['gold_created_at'] = datetime.utcnow().isoformat()
    result_df['gold_version'] = 1

    return result_df


def write_gold_parquet_partitioned(df: pd.DataFrame, prefix: str, partition_col: str):
    """Write DataFrame to Gold layer partitioned by a column."""
    s3 = boto3.client('s3')

    if partition_col not in df.columns:
        logger.warning(f"Partition column {partition_col} not in DataFrame")
        # Write without partitioning
        s3_key = f"{prefix}/part-0000.parquet"
        buffer = BytesIO()
        df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
        buffer.seek(0)
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
        logger.info(f"Wrote {len(df)} records to s3://{BUCKET_NAME}/{s3_key}")
        return

    for partition_value in df[partition_col].unique():
        partition_df = df[df[partition_col] == partition_value].copy()
        s3_key = f"{prefix}/{partition_col}={partition_value}/part-0000.parquet"

        buffer = BytesIO()
        partition_df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
        buffer.seek(0)

        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
        logger.info(f"Wrote {len(partition_df)} records to s3://{BUCKET_NAME}/{s3_key}")


def main():
    logger.info("=" * 80)
    logger.info("Building Gold agg_bill_latest_action from Silver Congress data")
    logger.info("=" * 80)

    df = build_agg_bill_latest_action()

    if df.empty:
        logger.error("No data to write")
        return

    logger.info(f"\nSummary:")
    logger.info(f"  Total bills with actions: {len(df)}")
    if 'congress' in df.columns:
        logger.info(f"  By congress: {df['congress'].value_counts().to_dict()}")
    if 'days_since_action' in df.columns:
        logger.info(f"  Average days since action: {df['days_since_action'].mean():.1f}")
        logger.info(f"  Most recent action: {df['days_since_action'].min()} days ago")

    write_gold_parquet_partitioned(df, 'gold/congress/agg_bill_latest_action', 'congress')

    logger.info("\n✅ Gold agg_bill_latest_action build complete!")


if __name__ == '__main__':
    main()
