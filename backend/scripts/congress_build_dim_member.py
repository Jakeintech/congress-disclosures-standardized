#!/usr/bin/env python3
"""
Build Gold dim_member table from Silver Congress layer.

Reads Silver dim_member and aggregates bill/cosponsor counts from dim_bill.
Writes to gold/congress/dim_member/ partitioned by chamber.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import pyarrow.parquet as pq
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
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
            df = pd.read_parquet(BytesIO(response['Body'].read()))
            dfs.append(df)
    
    if not dfs:
        return pd.DataFrame()
    
    return pd.concat(dfs, ignore_index=True)


def build_gold_dim_member() -> pd.DataFrame:
    """Build enriched Gold member dimension."""
    s3 = boto3.client('s3')
    
    # 1. Read Silver dim_member (current members only)
    members_df = read_silver_parquet(s3, 'silver/congress/dim_member/')
    if members_df.empty:
        logger.error("No members found in Silver layer")
        return pd.DataFrame()
    
    logger.info(f"Loaded {len(members_df)} members from Silver")
    
    # Filter to current members if is_current column exists
    if 'is_current' in members_df.columns:
        members_df = members_df[members_df['is_current'] == True].copy()
        logger.info(f"Filtered to {len(members_df)} current members")
    
    # 2. Read Silver dim_bill to count sponsored bills
    bills_df = read_silver_parquet(s3, 'silver/congress/dim_bill/')
    
    if not bills_df.empty and 'sponsor_bioguide_id' in bills_df.columns:
        # Count bills sponsored per member
        bills_sponsored = bills_df.groupby('sponsor_bioguide_id').size().reset_index(name='bills_sponsored_count')
        members_df = members_df.merge(bills_sponsored, left_on='bioguide_id', right_on='sponsor_bioguide_id', how='left')
        members_df['bills_sponsored_count'] = members_df['bills_sponsored_count'].fillna(0).astype(int)
        if 'sponsor_bioguide_id' in members_df.columns:
            members_df = members_df.drop(columns=['sponsor_bioguide_id'])
        logger.info(f"Added bills_sponsored_count (max: {members_df['bills_sponsored_count'].max()})")
    else:
        members_df['bills_sponsored_count'] = 0
    
    # 3. Add metadata columns
    members_df['gold_created_at'] = datetime.utcnow().isoformat()
    members_df['gold_version'] = 1
    
    return members_df


def write_gold_parquet(df: pd.DataFrame, prefix: str, partition_col: str = None):
    """Write DataFrame to Gold layer as Parquet."""
    s3 = boto3.client('s3')
    
    if partition_col and partition_col in df.columns:
        for partition_value in df[partition_col].unique():
            partition_df = df[df[partition_col] == partition_value].copy()
            s3_key = f"{prefix}/{partition_col}={partition_value}/part-0000.parquet"
            
            buffer = BytesIO()
            partition_df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
            buffer.seek(0)
            
            s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
            logger.info(f"Wrote {len(partition_df)} records to s3://{BUCKET_NAME}/{s3_key}")
    else:
        s3_key = f"{prefix}/part-0000.parquet"
        buffer = BytesIO()
        df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
        buffer.seek(0)
        
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
        logger.info(f"Wrote {len(df)} records to s3://{BUCKET_NAME}/{s3_key}")


def main():
    logger.info("=" * 80)
    logger.info("Building Gold dim_member from Silver Congress data")
    logger.info("=" * 80)
    
    df = build_gold_dim_member()
    
    if df.empty:
        logger.error("No data to write")
        return
    
    logger.info(f"\nSummary:")
    logger.info(f"  Total members: {len(df)}")
    if 'chamber' in df.columns:
        logger.info(f"  By chamber: {df['chamber'].value_counts().to_dict()}")
    if 'bills_sponsored_count' in df.columns:
        logger.info(f"  Max bills sponsored: {df['bills_sponsored_count'].max()}")
    
    write_gold_parquet(df, 'gold/congress/dim_member', partition_col='chamber')
    
    logger.info("\n✅ Gold dim_member build complete!")


if __name__ == '__main__':
    main()
