#!/usr/bin/env python3
"""
Build Gold Analytics: Member Bill Trade Windows

Analyzes member trades within ±30 days of bill actions they sponsored/cosponsored.
Identifies potential conflicts of interest by correlating legislative activity with trading.

Output: gold/analytics/fact_member_bill_trade_window/
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion"))

import pandas as pd
import boto3
from io import BytesIO
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
WINDOW_DAYS = 30  # Days before/after bill action to check for trades


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


def parse_date(date_val) -> pd.Timestamp:
    """Parse various date formats to pandas Timestamp."""
    if pd.isna(date_val):
        return pd.NaT
    if isinstance(date_val, pd.Timestamp):
        return date_val
    if isinstance(date_val, datetime):
        return pd.Timestamp(date_val)
    try:
        return pd.to_datetime(str(date_val)[:10])
    except:
        return pd.NaT


def build_trade_windows():
    """Build fact table for member-bill trade windows."""
    s3 = boto3.client('s3')
    
    # 1. Read member-bill relationships (sponsors/cosponsors)
    logger.info("Loading member-bill relationships...")
    member_bills_df = read_parquet_from_s3(s3, 'gold/congress/fact_member_bill_role/')
    if member_bills_df.empty:
        logger.error("No member-bill relationships found")
        return pd.DataFrame()
    logger.info(f"Loaded {len(member_bills_df)} member-bill relationships")
    
    # 2. Read Silver dim_bill for bill dates and policy areas
    logger.info("Loading bill metadata...")
    bills_df = read_parquet_from_s3(s3, 'silver/congress/dim_bill/')
    if bills_df.empty:
        logger.error("No bills found")
        return pd.DataFrame()
    logger.info(f"Loaded {len(bills_df)} bills")
    
    # 3. Read FD transactions
    logger.info("Loading FD transactions...")
    transactions_df = read_parquet_from_s3(s3, 'gold/house/financial/facts/fact_ptr_transactions/')
    if transactions_df.empty:
        logger.warning("No FD transactions found - proceeding with empty analysis")
        transactions_df = pd.DataFrame(columns=['filer_name', 'transaction_date', 'ticker', 'amount', 'transaction_type'])
    else:
        logger.info(f"Loaded {len(transactions_df)} FD transactions")
    
    # 4. Load dim_members to link bioguide_id to filer_name
    logger.info("Loading member dimension...")
    members_df = read_parquet_from_s3(s3, 'silver/congress/dim_member/')
    if not members_df.empty:
        logger.info(f"Loaded {len(members_df)} members")
    
    # 5. Parse dates
    if 'introduced_date' in bills_df.columns:
        bills_df['action_date'] = bills_df['introduced_date'].apply(parse_date)
    elif 'update_date' in bills_df.columns:
        bills_df['action_date'] = bills_df['update_date'].apply(parse_date)
    else:
        bills_df['action_date'] = pd.NaT
    
    if not transactions_df.empty and 'transaction_date' in transactions_df.columns:
        transactions_df['tx_date'] = transactions_df['transaction_date'].apply(parse_date)
    
    # 6. Merge member-bills with bill metadata
    # Build bill_id for joining
    if 'bill_id' not in member_bills_df.columns:
        if all(c in member_bills_df.columns for c in ['congress', 'bill_type', 'bill_number']):
            member_bills_df['bill_id'] = member_bills_df['congress'].astype(str) + '-' + member_bills_df['bill_type'] + '-' + member_bills_df['bill_number'].astype(str)
    
    if 'bill_id' not in bills_df.columns:
        if all(c in bills_df.columns for c in ['congress', 'bill_type', 'bill_number']):
            bills_df['bill_id'] = bills_df['congress'].astype(str) + '-' + bills_df['bill_type'] + '-' + bills_df['bill_number'].astype(str)
    
    # Join to get action dates
    member_bills_with_dates = member_bills_df.merge(
        bills_df[['bill_id', 'action_date', 'policy_area', 'title']].drop_duplicates(),
        on='bill_id',
        how='left'
    )
    
    logger.info(f"Member-bills with dates: {len(member_bills_with_dates)}")
    
    # 7. Create member name mapping from dim_member
    member_name_map = {}
    if not members_df.empty and 'bioguide_id' in members_df.columns:
        for _, row in members_df.iterrows():
            name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
            if name and pd.notna(row.get('bioguide_id')):
                member_name_map[row['bioguide_id']] = name
    
    # 8. Analyze trade windows
    window_records = []
    
    for _, mb_row in member_bills_with_dates.iterrows():
        bioguide_id = mb_row.get('bioguide_id')
        bill_id = mb_row.get('bill_id')
        action_date = mb_row.get('action_date')
        role = mb_row.get('role', 'sponsor')
        policy_area = mb_row.get('policy_area', 'General')
        
        if pd.isna(action_date) or pd.isna(bioguide_id):
            continue
        
        # Get member name for matching with FD transactions
        member_name = member_name_map.get(bioguide_id, '')
        
        # Skip if no transactions or no member name
        if transactions_df.empty or not member_name:
            # Still create record with 0 trades
            window_records.append({
                'bioguide_id': bioguide_id,
                'member_name': member_name,
                'bill_id': bill_id,
                'bill_title': mb_row.get('title', '')[:100] if pd.notna(mb_row.get('title')) else '',
                'role': role,
                'action_date': action_date,
                'policy_area': policy_area,
                'window_type': 'no_fd_data',
                'transaction_count': 0,
                'tickers_traded': '',
                'total_transactions_in_window': 0,
            })
            continue
        
        # Find trades by this member
        # Match on filer_name containing member last name (fuzzy)
        member_last = member_name.split()[-1].lower() if member_name else ''
        if member_last:
            member_trades = transactions_df[
                transactions_df['filer_name'].str.lower().str.contains(member_last, na=False)
            ]
        else:
            member_trades = pd.DataFrame()
        
        if member_trades.empty:
            window_records.append({
                'bioguide_id': bioguide_id,
                'member_name': member_name,
                'bill_id': bill_id,
                'bill_title': mb_row.get('title', '')[:100] if pd.notna(mb_row.get('title')) else '',
                'role': role,
                'action_date': action_date,
                'policy_area': policy_area,
                'window_type': 'no_trades',
                'transaction_count': 0,
                'tickers_traded': '',
                'total_transactions_in_window': 0,
            })
            continue
        
        # Check 30-day windows
        window_start = action_date - timedelta(days=WINDOW_DAYS)
        window_end = action_date + timedelta(days=WINDOW_DAYS)
        
        trades_in_window = member_trades[
            (member_trades['tx_date'] >= window_start) &
            (member_trades['tx_date'] <= window_end)
        ]
        
        trades_before = trades_in_window[trades_in_window['tx_date'] < action_date]
        trades_after = trades_in_window[trades_in_window['tx_date'] >= action_date]
        
        # Record before window
        if len(trades_before) > 0:
            tickers = trades_before['ticker'].dropna().unique()
            window_records.append({
                'bioguide_id': bioguide_id,
                'member_name': member_name,
                'bill_id': bill_id,
                'bill_title': mb_row.get('title', '')[:100] if pd.notna(mb_row.get('title')) else '',
                'role': role,
                'action_date': action_date,
                'policy_area': policy_area,
                'window_type': f'before_{WINDOW_DAYS}d',
                'transaction_count': len(trades_before),
                'tickers_traded': ','.join(str(t) for t in tickers[:10]),
                'total_transactions_in_window': len(trades_in_window),
            })
        
        # Record after window
        if len(trades_after) > 0:
            tickers = trades_after['ticker'].dropna().unique()
            window_records.append({
                'bioguide_id': bioguide_id,
                'member_name': member_name,
                'bill_id': bill_id,
                'bill_title': mb_row.get('title', '')[:100] if pd.notna(mb_row.get('title')) else '',
                'role': role,
                'action_date': action_date,
                'policy_area': policy_area,
                'window_type': f'after_{WINDOW_DAYS}d',
                'transaction_count': len(trades_after),
                'tickers_traded': ','.join(str(t) for t in tickers[:10]),
                'total_transactions_in_window': len(trades_in_window),
            })
        
        # Record if no trades in window
        if len(trades_in_window) == 0:
            window_records.append({
                'bioguide_id': bioguide_id,
                'member_name': member_name,
                'bill_id': bill_id,
                'bill_title': mb_row.get('title', '')[:100] if pd.notna(mb_row.get('title')) else '',
                'role': role,
                'action_date': action_date,
                'policy_area': policy_area,
                'window_type': 'no_trades_in_window',
                'transaction_count': 0,
                'tickers_traded': '',
                'total_transactions_in_window': 0,
            })
    
    if not window_records:
        logger.warning("No trade window records generated")
        return pd.DataFrame()
    
    df = pd.DataFrame(window_records)
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
    logger.info("Building Gold Analytics: Member Bill Trade Windows")
    logger.info("=" * 80)
    
    df = build_trade_windows()
    
    if df.empty:
        logger.error("No data to write")
        return
    
    logger.info(f"\nSummary:")
    logger.info(f"  Total records: {len(df)}")
    if 'window_type' in df.columns:
        logger.info(f"  By window_type: {df['window_type'].value_counts().to_dict()}")
    if 'transaction_count' in df.columns:
        trades_found = df[df['transaction_count'] > 0]
        logger.info(f"  Records with trades: {len(trades_found)}")
    
    write_gold_parquet(df, 'gold/analytics/fact_member_bill_trade_window')
    
    logger.info("\n✅ Trade window analysis complete!")


if __name__ == '__main__':
    main()
