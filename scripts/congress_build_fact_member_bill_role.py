#!/usr/bin/env python3
"""
Build Gold fact_member_bill_role from Silver Congress layer.

Creates one row per member-bill relationship (sponsor/cosponsor).
Writes to gold/congress/fact_member_bill_role/ partitioned by congress.
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


def build_fact_member_bill_role() -> pd.DataFrame:
    """Build fact table for member-bill relationships."""
    s3 = boto3.client('s3')
    
    # 1. Read Silver dim_bill for sponsor relationships
    bills_df = read_silver_parquet(s3, 'silver/congress/dim_bill/')
    if bills_df.empty:
        logger.error("No bills found in Silver layer")
        return pd.DataFrame()
    
    logger.info(f"Loaded {len(bills_df)} bills from Silver")
    
    # 2. Build sponsor records
    sponsor_records = []
    for _, bill in bills_df.iterrows():
        if pd.notna(bill.get('sponsor_bioguide_id')):
            sponsor_records.append({
                'bioguide_id': bill['sponsor_bioguide_id'],
                'bill_id': bill.get('bill_id', f"{bill.get('congress', 118)}-{bill.get('bill_type', 'hr')}-{bill.get('bill_number', 0)}"),
                'congress': bill.get('congress', 118),
                'bill_type': bill.get('bill_type', 'hr'),
                'bill_number': bill.get('bill_number'),
                'role': 'sponsor',
                'is_sponsor': True,
                'is_cosponsor': False,
                'action_date': bill.get('introduced_date'),
            })
    
    logger.info(f"Created {len(sponsor_records)} sponsor records")
    
    # 3. Read Silver bill_cosponsors if available (may not exist yet)
    cosponsors_df = read_silver_parquet(s3, 'silver/congress/bill_cosponsors/')
    
    cosponsor_records = []
    if not cosponsors_df.empty:
        for _, cosponsor in cosponsors_df.iterrows():
            if pd.notna(cosponsor.get('bioguide_id')):
                cosponsor_records.append({
                    'bioguide_id': cosponsor['bioguide_id'],
                    'bill_id': cosponsor.get('bill_id'),
                    'congress': cosponsor.get('congress', 118),
                    'bill_type': cosponsor.get('bill_type', 'hr'),
                    'bill_number': cosponsor.get('bill_number'),
                    'role': 'cosponsor',
                    'is_sponsor': False,
                    'is_cosponsor': True,
                    'action_date': cosponsor.get('sponsorship_date'),  # Fixed field name
                })
        logger.info(f"Created {len(cosponsor_records)} cosponsor records")
    else:
        logger.info("No cosponsors found (subresources may not be ingested yet)")
    
    # 4. Combine all records
    all_records = sponsor_records + cosponsor_records
    if not all_records:
        logger.warning("No member-bill relationships found")
        return pd.DataFrame()
    
    df = pd.DataFrame(all_records)
    
    # 5. Normalize action_date column to string (handle mixed types from different sources)
    if 'action_date' in df.columns:
        df['action_date'] = pd.to_datetime(df['action_date'], errors='coerce').dt.strftime('%Y-%m-%d')

    # 6. Add metadata
    df['gold_created_at'] = datetime.utcnow().isoformat()
    df['gold_version'] = 1

    return df


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
    logger.info("Building Gold fact_member_bill_role from Silver Congress data")
    logger.info("=" * 80)
    
    df = build_fact_member_bill_role()
    
    if df.empty:
        logger.error("No data to write")
        return
    
    logger.info(f"\nSummary:")
    logger.info(f"  Total relationships: {len(df)}")
    logger.info(f"  Sponsors: {df['is_sponsor'].sum()}")
    logger.info(f"  Cosponsors: {df['is_cosponsor'].sum()}")
    if 'congress' in df.columns:
        logger.info(f"  By congress: {df['congress'].value_counts().to_dict()}")
    
    write_gold_parquet_partitioned(df, 'gold/congress/fact_member_bill_role', 'congress')
    
    logger.info("\n✅ Gold fact_member_bill_role build complete!")


if __name__ == '__main__':
    main()
