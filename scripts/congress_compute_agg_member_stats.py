#!/usr/bin/env python3
"""
Compute Gold Aggregate: Member Legislative Stats

Aggregates member-level statistics combining legislative activity
(bills sponsored, votes) with financial disclosure data.

Output: gold/congress/aggregates/member_legislative_stats/
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion"))

import pandas as pd
import boto3
from io import BytesIO
from datetime import datetime
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def read_parquet_from_s3(s3_client, prefix: str) -> pd.DataFrame:
    """Read all Parquet files from an S3 prefix."""
    logger.info(f"Reading from s3://{BUCKET_NAME}/{prefix}")
    
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    if 'Contents' not in response:
        logger.warning(f"No files found in {prefix}")
        return pd.DataFrame()
    
    dfs = []
    for obj in response['Contents']:
        if obj['Key'].endswith('.parquet'):
            response_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
            df = pd.read_parquet(BytesIO(response_obj['Body'].read()))
            dfs.append(df)
    
    if not dfs:
        return pd.DataFrame()
    
    return pd.concat(dfs, ignore_index=True)


def compute_member_stats():
    """Compute member-level legislative + trading statistics."""
    s3 = boto3.client('s3')
    
    # 1. Read Congress dim_member
    logger.info("Loading member dimension...")
    members_df = read_parquet_from_s3(s3, 'gold/congress/dim_member/')
    if members_df.empty:
        logger.error("No members found")
        return pd.DataFrame()
    logger.info(f"Loaded {len(members_df)} members")
    
    # 2. Read member-bill relationships
    logger.info("Loading member-bill relationships...")
    member_bills_df = read_parquet_from_s3(s3, 'gold/congress/fact_member_bill_role/')
    bills_by_member = defaultdict(lambda: {'sponsored': 0, 'cosponsored': 0})
    
    if not member_bills_df.empty:
        for _, row in member_bills_df.iterrows():
            bioguide_id = row.get('bioguide_id')
            if pd.isna(bioguide_id):
                continue
            role = row.get('role', 'sponsor')
            if role == 'sponsor' or row.get('is_sponsor', False):
                bills_by_member[bioguide_id]['sponsored'] += 1
            if role == 'cosponsor' or row.get('is_cosponsor', False):
                bills_by_member[bioguide_id]['cosponsored'] += 1
        logger.info(f"Aggregated bills for {len(bills_by_member)} members")
    
    # 3. Read FD transactions
    logger.info("Loading FD transactions...")
    transactions_df = read_parquet_from_s3(s3, 'gold/house/financial/facts/fact_ptr_transactions/')
    trades_by_member = defaultdict(lambda: {'count': 0, 'tickers': set()})
    
    if not transactions_df.empty:
        # Group by filer_name
        for filer_name, group in transactions_df.groupby('filer_name'):
            if pd.isna(filer_name):
                continue
            filer_str = str(filer_name).lower()
            trades_by_member[filer_str]['count'] = len(group)
            if 'ticker' in group.columns:
                trades_by_member[filer_str]['tickers'] = set(group['ticker'].dropna().unique())
        logger.info(f"Aggregated trades for {len(trades_by_member)} filers")
    
    # 4. Build member stats records
    records = []
    for _, member in members_df.iterrows():
        bioguide_id = member.get('bioguide_id')
        first_name = member.get('first_name', '')
        last_name = member.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip()
        
        # Get legislative counts
        bill_stats = bills_by_member.get(bioguide_id, {'sponsored': 0, 'cosponsored': 0})
        
        # Try to match FD trades by last name
        trade_stats = {'count': 0, 'tickers': set()}
        if last_name:
            for filer, stats in trades_by_member.items():
                if last_name.lower() in filer:
                    trade_stats['count'] += stats['count']
                    trade_stats['tickers'].update(stats['tickers'])
        
        records.append({
            'bioguide_id': bioguide_id,
            'full_name': full_name,
            'party': member.get('party'),
            'state': member.get('state'),
            'chamber': member.get('chamber'),
            'bills_sponsored': bill_stats['sponsored'],
            'bills_cosponsored': bill_stats['cosponsored'],
            'total_bills': bill_stats['sponsored'] + bill_stats['cosponsored'],
            'fd_transaction_count': trade_stats['count'],
            'fd_unique_tickers': len(trade_stats['tickers']),
            'has_fd_disclosures': trade_stats['count'] > 0,
        })
    
    df = pd.DataFrame(records)
    df['gold_created_at'] = datetime.utcnow().isoformat()
    
    return df


def write_gold_parquet(df: pd.DataFrame, prefix: str):
    """Write DataFrame to Gold layer."""
    s3 = boto3.client('s3')
    
    s3_key = f"{prefix}/part-0000.parquet"
    buffer = BytesIO()
    df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
    buffer.seek(0)
    
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
    logger.info(f"Wrote {len(df)} records to s3://{BUCKET_NAME}/{s3_key}")


def main():
    logger.info("=" * 80)
    logger.info("Computing Gold Aggregate: Member Legislative Stats")
    logger.info("=" * 80)
    
    df = compute_member_stats()
    
    if df.empty:
        logger.error("No data to write")
        return
    
    logger.info(f"\nSummary:")
    logger.info(f"  Total members: {len(df)}")
    logger.info(f"  Members with bills: {(df['total_bills'] > 0).sum()}")
    logger.info(f"  Members with FD disclosures: {df['has_fd_disclosures'].sum()}")
    if 'bills_sponsored' in df.columns:
        logger.info(f"  Max bills sponsored: {df['bills_sponsored'].max()}")
    
    write_gold_parquet(df, 'gold/congress/aggregates/member_legislative_stats')
    
    logger.info("\n✅ Member legislative stats compute complete!")


if __name__ == '__main__':
    main()
