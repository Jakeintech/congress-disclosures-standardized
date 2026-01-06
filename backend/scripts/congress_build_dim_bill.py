#!/usr/bin/env python3
"""
Build Gold dim_bill table from Silver Congress layer.

Reads Silver dim_bill and denormalizes sponsor info.
Writes to gold/congress/dim_bill/ partitioned by congress and bill_type.
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


def build_gold_dim_bill() -> pd.DataFrame:
    """Build denormalized Gold bill dimension."""
    s3 = boto3.client('s3')
    
    # 1. Read Silver dim_bill
    bills_df = read_silver_parquet(s3, 'silver/congress/dim_bill/')
    if bills_df.empty:
        logger.error("No bills found in Silver layer")
        return pd.DataFrame()
    
    logger.info(f"Loaded {len(bills_df)} bills from Silver")
    
    # 2. Read Silver dim_member to get sponsor names
    members_df = read_silver_parquet(s3, 'silver/congress/dim_member/')
    
    if not members_df.empty and 'bioguide_id' in members_df.columns:
        # Create sponsor name lookup
        member_names = members_df[['bioguide_id', 'first_name', 'last_name']].drop_duplicates()
        member_names['sponsor_name'] = member_names['first_name'] + ' ' + member_names['last_name']
        member_names = member_names[['bioguide_id', 'sponsor_name']]
        
        # Join to get sponsor_name
        if 'sponsor_bioguide_id' in bills_df.columns:
            bills_df = bills_df.merge(
                member_names, 
                left_on='sponsor_bioguide_id', 
                right_on='bioguide_id', 
                how='left',
                suffixes=('', '_member')
            )
            if 'bioguide_id_member' in bills_df.columns:
                bills_df = bills_df.drop(columns=['bioguide_id_member'])
            logger.info(f"Added sponsor_name to {bills_df['sponsor_name'].notna().sum()} bills")
    else:
        bills_df['sponsor_name'] = None
    
    # 3. Add metadata columns
    bills_df['gold_created_at'] = datetime.utcnow().isoformat()
    bills_df['gold_version'] = 1
    
    # 4. Ensure partition columns exist
    if 'congress' not in bills_df.columns:
        bills_df['congress'] = 118  # Default
    if 'bill_type' not in bills_df.columns:
        bills_df['bill_type'] = 'hr'  # Default
    
    return bills_df


def write_gold_parquet_partitioned(df: pd.DataFrame, prefix: str, partition_cols: list):
    """Write DataFrame to Gold layer with multiple partition columns."""
    s3 = boto3.client('s3')
    
    for col in partition_cols:
        if col not in df.columns:
            logger.warning(f"Partition column {col} not in DataFrame")
            return
    
    # Group by partition columns
    groups = df.groupby(partition_cols)
    
    for partition_values, group_df in groups:
        if not isinstance(partition_values, tuple):
            partition_values = (partition_values,)
        
        partition_path = '/'.join([f"{col}={val}" for col, val in zip(partition_cols, partition_values)])
        s3_key = f"{prefix}/{partition_path}/part-0000.parquet"
        
        buffer = BytesIO()
        group_df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
        buffer.seek(0)
        
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
        logger.info(f"Wrote {len(group_df)} records to s3://{BUCKET_NAME}/{s3_key}")


def main():
    logger.info("=" * 80)
    logger.info("Building Gold dim_bill from Silver Congress data")
    logger.info("=" * 80)
    
    df = build_gold_dim_bill()
    
    if df.empty:
        logger.error("No data to write")
        return
    
    logger.info(f"\nSummary:")
    logger.info(f"  Total bills: {len(df)}")
    if 'congress' in df.columns:
        logger.info(f"  By congress: {df['congress'].value_counts().to_dict()}")
    if 'bill_type' in df.columns:
        logger.info(f"  By bill_type: {df['bill_type'].value_counts().to_dict()}")
    if 'sponsor_name' in df.columns:
        logger.info(f"  With sponsor_name: {df['sponsor_name'].notna().sum()}")
    
    write_gold_parquet_partitioned(df, 'gold/congress/dim_bill', ['congress', 'bill_type'])
    
    logger.info("\n✅ Gold dim_bill build complete!")


if __name__ == '__main__':
    main()
