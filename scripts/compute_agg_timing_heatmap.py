#!/usr/bin/env python3
"""
Trading Timing Heatmap Aggregation.

Analyzes trading patterns by:
1. Day of week distribution
2. Month of year patterns
3. Proximity to bill actions (before/after)
4. Market events correlation

Detects anomalies in timing (e.g., unusual trading before events).

Output: gold/aggregates/agg_timing_heatmap/
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import boto3
from io import BytesIO
from datetime import datetime
import logging
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def read_parquet_from_s3(s3_client, prefix: str) -> pd.DataFrame:
    """Read all Parquet files from an S3 prefix."""
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    if 'Contents' not in response:
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


def load_local_data(table_name: str) -> pd.DataFrame:
    """Load data from local gold layer."""
    paths = [
        Path('data/gold/house/financial/facts') / table_name,
        Path('data/gold/congress') / table_name,
        Path('data/gold/dimensions') / table_name,
    ]
    
    for path in paths:
        if path.exists():
            files = list(path.glob("**/*.parquet"))
            if files:
                return pd.concat([pd.read_parquet(f) for f in files])
    
    return pd.DataFrame()


def compute_day_of_week_heatmap(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Compute trading activity by day of week."""
    logger.info("Computing day of week heatmap...")
    
    # Ensure transaction_date is datetime
    if 'transaction_date' not in transactions_df.columns:
        if 'transaction_date_key' in transactions_df.columns:
            transactions_df['transaction_date'] = pd.to_datetime(
                transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce'
            )
    else:
        # Convert string dates to datetime
        transactions_df['transaction_date'] = pd.to_datetime(
            transactions_df['transaction_date'], errors='coerce'
        )
    
    # Drop rows with invalid dates
    transactions_df = transactions_df.dropna(subset=['transaction_date'])
    if transactions_df.empty:
        logger.warning("No valid transaction dates found")
        return pd.DataFrame()
    
    transactions_df['day_of_week'] = transactions_df['transaction_date'].dt.dayofweek
    transactions_df['day_name'] = transactions_df['day_of_week'].map(lambda x: DAY_NAMES[x] if 0 <= x <= 6 else 'Unknown')
    
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    # Use bioguide_id instead of member_key
    trader_col = None
    for col in ['bioguide_id', 'member_bioguide_id', 'member_key']:
        if col in transactions_df.columns:
            trader_col = col
            break
    
    if trader_col:
        day_stats = transactions_df.groupby(['day_of_week', 'day_name']).agg({
            'amount_midpoint': ['sum', 'count', 'mean'],
            trader_col: 'nunique'
        }).reset_index()
        day_stats.columns = ['day_of_week', 'day_name', 'total_volume', 'trade_count', 'avg_trade_size', 'unique_traders']
    else:
        day_stats = transactions_df.groupby(['day_of_week', 'day_name']).agg({
            'amount_midpoint': ['sum', 'count', 'mean']
        }).reset_index()
        day_stats.columns = ['day_of_week', 'day_name', 'total_volume', 'trade_count', 'avg_trade_size']
        day_stats['unique_traders'] = 0
    
    
    # Calculate percentage of weekly volume
    total_volume = day_stats['total_volume'].sum()
    day_stats['pct_of_volume'] = (day_stats['total_volume'] / total_volume * 100).round(2)
    
    # Expected distribution (uniform = ~14.3% per day for weekdays)
    day_stats['expected_pct'] = day_stats.apply(
        lambda x: 20.0 if x['day_of_week'] < 5 else 0.0,  # Weekdays only for trading
        axis=1
    )
    
    # Deviation from expected
    day_stats['deviation'] = day_stats['pct_of_volume'] - day_stats['expected_pct']
    
    day_stats['heatmap_type'] = 'day_of_week'
    day_stats['dt_computed'] = datetime.utcnow().isoformat()
    
    return day_stats.sort_values('day_of_week')


def compute_month_of_year_heatmap(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Compute trading activity by month."""
    logger.info("Computing month of year heatmap...")
    
    # Ensure transaction_date is datetime
    if 'transaction_date' not in transactions_df.columns:
        if 'transaction_date_key' in transactions_df.columns:
            transactions_df['transaction_date'] = pd.to_datetime(
                transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce'
            )
    else:
        transactions_df['transaction_date'] = pd.to_datetime(
            transactions_df['transaction_date'], errors='coerce'
        )
    
    transactions_df = transactions_df.dropna(subset=['transaction_date'])
    if transactions_df.empty:
        return pd.DataFrame()
    
    transactions_df['month'] = transactions_df['transaction_date'].dt.month
    transactions_df['month_name'] = transactions_df['month'].map(lambda x: MONTH_NAMES[x-1] if 1 <= x <= 12 else 'Unknown')
    
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    # Use bioguide_id instead of member_key
    trader_col = None
    for col in ['bioguide_id', 'member_bioguide_id', 'member_key']:
        if col in transactions_df.columns:
            trader_col = col
            break
    
    if trader_col:
        month_stats = transactions_df.groupby(['month', 'month_name']).agg({
            'amount_midpoint': ['sum', 'count', 'mean'],
            trader_col: 'nunique'
        }).reset_index()
        month_stats.columns = ['month', 'month_name', 'total_volume', 'trade_count', 'avg_trade_size', 'unique_traders']
    else:
        month_stats = transactions_df.groupby(['month', 'month_name']).agg({
            'amount_midpoint': ['sum', 'count', 'mean']
        }).reset_index()
        month_stats.columns = ['month', 'month_name', 'total_volume', 'trade_count', 'avg_trade_size']
        month_stats['unique_traders'] = 0
    
    total_volume = month_stats['total_volume'].sum()
    month_stats['pct_of_volume'] = (month_stats['total_volume'] / total_volume * 100).round(2)
    month_stats['expected_pct'] = 100 / 12  # ~8.33% per month
    month_stats['deviation'] = month_stats['pct_of_volume'] - month_stats['expected_pct']
    
    month_stats['heatmap_type'] = 'month_of_year'
    month_stats['dt_computed'] = datetime.utcnow().isoformat()
    
    return month_stats.sort_values('month')


def compute_bill_proximity_heatmap(
    transactions_df: pd.DataFrame,
    bill_actions_df: pd.DataFrame,
    member_bill_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute trading activity relative to bill actions.
    
    Buckets: -90 to -61, -60 to -31, -30 to -8, -7 to -1, 0 (day of), 
             1-7, 8-30, 31-60, 61-90 days
    """
    logger.info("Computing bill proximity heatmap...")
    
    if transactions_df.empty or bill_actions_df.empty or member_bill_df.empty:
        logger.warning("Missing data for bill proximity analysis")
        return pd.DataFrame()
    
    # Prepare transaction dates - ensure datetime
    if 'transaction_date' not in transactions_df.columns:
        if 'transaction_date_key' in transactions_df.columns:
            transactions_df['transaction_date'] = pd.to_datetime(
                transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce'
            )
    else:
        transactions_df['transaction_date'] = pd.to_datetime(
            transactions_df['transaction_date'], errors='coerce'
        )
    
    transactions_df = transactions_df.dropna(subset=['transaction_date'])
    
    # Get bill action dates
    date_col = 'latest_action_date' if 'latest_action_date' in bill_actions_df.columns else 'action_date'
    if date_col in bill_actions_df.columns:
        bill_actions_df[date_col] = pd.to_datetime(bill_actions_df[date_col], errors='coerce')
    
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    # Find matching trades and bill actions for the same member
    proximity_data = []
    
    bioguide_col = None
    for col in ['member_bioguide_id', 'bioguide_id', 'bioguide']:
        if col in transactions_df.columns:
            bioguide_col = col
            break
    
    bill_bioguide_col = None
    for col in ['member_bioguide_id', 'bioguide_id', 'bioguide']:
        if col in member_bill_df.columns:
            bill_bioguide_col = col
            break
    
    if not bioguide_col or not bill_bioguide_col:
        logger.warning("No bioguide column found")
        return pd.DataFrame()
    
    for member_id in transactions_df[bioguide_col].unique():
        member_trades = transactions_df[transactions_df[bioguide_col] == member_id]
        member_bills = member_bill_df[member_bill_df[bill_bioguide_col] == member_id]
        
        for _, trade in member_trades.iterrows():
            trade_date = trade['transaction_date']
            if pd.isna(trade_date):
                continue
            
            # Find closest bill action
            for _, bill in member_bills.iterrows():
                bill_id = bill.get('bill_id', '')
                
                # Get action date
                bill_action = bill_actions_df[bill_actions_df['bill_id'] == bill_id]
                if bill_action.empty:
                    continue
                
                action_date = bill_action.iloc[0][date_col]
                if pd.isna(action_date):
                    continue
                
                days_offset = (trade_date - action_date).days
                
                # Only consider within ±90 days
                if abs(days_offset) > 90:
                    continue
                
                proximity_data.append({
                    'days_offset': days_offset,
                    'amount': trade['amount_midpoint'],
                    'transaction_type': trade.get('transaction_type', ''),
                    'member_id': member_id,
                })
    
    if not proximity_data:
        return pd.DataFrame()
    
    prox_df = pd.DataFrame(proximity_data)
    
    # Define buckets
    def bucket_days(days: int) -> str:
        if days <= -61:
            return '90-61 before'
        elif days <= -31:
            return '60-31 before'
        elif days <= -8:
            return '30-8 before'
        elif days <= -1:
            return '7-1 before'
        elif days == 0:
            return 'Same day'
        elif days <= 7:
            return '1-7 after'
        elif days <= 30:
            return '8-30 after'
        elif days <= 60:
            return '31-60 after'
        else:
            return '61-90 after'
    
    bucket_order = [
        '90-61 before', '60-31 before', '30-8 before', '7-1 before', 
        'Same day', 
        '1-7 after', '8-30 after', '31-60 after', '61-90 after'
    ]
    
    prox_df['bucket'] = prox_df['days_offset'].apply(bucket_days)
    
    bucket_stats = prox_df.groupby('bucket').agg({
        'amount': ['sum', 'count', 'mean'],
        'member_id': 'nunique'
    }).reset_index()
    
    bucket_stats.columns = ['bucket', 'total_volume', 'trade_count', 'avg_trade_size', 'unique_traders']
    
    # Add bucket order for sorting
    bucket_stats['bucket_order'] = bucket_stats['bucket'].map(lambda x: bucket_order.index(x) if x in bucket_order else 99)
    bucket_stats = bucket_stats.sort_values('bucket_order')
    
    total_volume = bucket_stats['total_volume'].sum()
    bucket_stats['pct_of_volume'] = (bucket_stats['total_volume'] / total_volume * 100).round(2)
    
    bucket_stats['heatmap_type'] = 'bill_proximity'
    bucket_stats['dt_computed'] = datetime.utcnow().isoformat()
    
    return bucket_stats


def compute_year_over_year(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Compute year-over-year trading patterns."""
    logger.info("Computing year-over-year patterns...")
    
    # Ensure transaction_date is datetime
    if 'transaction_date' not in transactions_df.columns:
        if 'transaction_date_key' in transactions_df.columns:
            transactions_df['transaction_date'] = pd.to_datetime(
                transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce'
            )
    else:
        transactions_df['transaction_date'] = pd.to_datetime(
            transactions_df['transaction_date'], errors='coerce'
        )
    
    transactions_df = transactions_df.dropna(subset=['transaction_date'])
    if transactions_df.empty:
        return pd.DataFrame()
    
    transactions_df['year'] = transactions_df['transaction_date'].dt.year
    
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    # Use bioguide_id instead of member_key
    trader_col = None
    for col in ['bioguide_id', 'member_bioguide_id', 'member_key']:
        if col in transactions_df.columns:
            trader_col = col
            break
    
    if trader_col:
        year_stats = transactions_df.groupby('year').agg({
            'amount_midpoint': ['sum', 'count', 'mean'],
            trader_col: 'nunique'
        }).reset_index()
        year_stats.columns = ['year', 'total_volume', 'trade_count', 'avg_trade_size', 'unique_traders']
    else:
        year_stats = transactions_df.groupby('year').agg({
            'amount_midpoint': ['sum', 'count', 'mean']
        }).reset_index()
        year_stats.columns = ['year', 'total_volume', 'trade_count', 'avg_trade_size']
        year_stats['unique_traders'] = 0
    
    # Calculate YoY growth
    year_stats = year_stats.sort_values('year')
    year_stats['yoy_volume_growth'] = year_stats['total_volume'].pct_change() * 100
    year_stats['yoy_count_growth'] = year_stats['trade_count'].pct_change() * 100
    
    year_stats['heatmap_type'] = 'year_over_year'
    year_stats['dt_computed'] = datetime.utcnow().isoformat()
    
    return year_stats


def write_to_s3(df: pd.DataFrame, heatmap_type: str):
    """Write heatmap to S3."""
    if df.empty:
        return
    
    s3 = boto3.client('s3')
    s3_key = f'gold/aggregates/agg_timing_heatmap/type={heatmap_type}/part-0000.parquet'
    
    buffer = BytesIO()
    df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
    buffer.seek(0)
    
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
    logger.info(f"Wrote {len(df)} records to s3://{BUCKET_NAME}/{s3_key}")


def write_to_local(df: pd.DataFrame, heatmap_type: str):
    """Write heatmap to local gold layer."""
    if df.empty:
        return
    
    output_dir = Path(f'data/gold/aggregates/agg_timing_heatmap/type={heatmap_type}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
    logger.info(f"Wrote {len(df)} records to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Compute Trading Timing Heatmaps')
    parser.add_argument('--local', action='store_true', help='Use local data')
    parser.add_argument('--dry-run', action='store_true', help='Dry run')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Computing Trading Timing Heatmaps")
    logger.info("=" * 80)
    
    # Load data
    if args.local:
        transactions_df = load_local_data('fact_ptr_transactions')
        bill_actions_df = load_local_data('agg_bill_latest_action')
        member_bill_df = load_local_data('fact_member_bill_role')
    else:
        s3 = boto3.client('s3')
        transactions_df = read_parquet_from_s3(s3, 'gold/house/financial/facts/fact_ptr_transactions/')
        bill_actions_df = read_parquet_from_s3(s3, 'gold/congress/agg_bill_latest_action/')
        member_bill_df = read_parquet_from_s3(s3, 'gold/congress/fact_member_bill_role/')
    
    if transactions_df.empty:
        logger.error("No transaction data available")
        return
    
    # Compute heatmaps
    heatmaps = {}
    
    # 1. Day of week
    day_heatmap = compute_day_of_week_heatmap(transactions_df.copy())
    if not day_heatmap.empty:
        heatmaps['day_of_week'] = day_heatmap
        logger.info(f"\nDAY OF WEEK Trading Pattern:")
        for _, row in day_heatmap.iterrows():
            logger.info(f"  {row['day_name']}: {row['pct_of_volume']:.1f}% (deviation: {row['deviation']:+.1f}%)")
    
    # 2. Month of year
    month_heatmap = compute_month_of_year_heatmap(transactions_df.copy())
    if not month_heatmap.empty:
        heatmaps['month_of_year'] = month_heatmap
        logger.info(f"\nMONTH OF YEAR Trading Pattern:")
        for _, row in month_heatmap.iterrows():
            logger.info(f"  {row['month_name']}: {row['pct_of_volume']:.1f}%")
    
    # 3. Bill proximity
    prox_heatmap = compute_bill_proximity_heatmap(transactions_df.copy(), bill_actions_df, member_bill_df)
    if not prox_heatmap.empty:
        heatmaps['bill_proximity'] = prox_heatmap
        logger.info(f"\nBILL PROXIMITY Trading Pattern:")
        for _, row in prox_heatmap.iterrows():
            logger.info(f"  {row['bucket']}: {row['pct_of_volume']:.1f}% ({row['trade_count']} trades)")
    
    # 4. Year over year
    yoy_heatmap = compute_year_over_year(transactions_df.copy())
    if not yoy_heatmap.empty:
        heatmaps['year_over_year'] = yoy_heatmap
        logger.info(f"\nYEAR OVER YEAR Pattern:")
        for _, row in yoy_heatmap.iterrows():
            growth = f"{row['yoy_volume_growth']:+.1f}%" if not pd.isna(row['yoy_volume_growth']) else "N/A"
            logger.info(f"  {int(row['year'])}: ${row['total_volume']:,.0f} ({growth} YoY)")
    
    # Write outputs
    if not args.dry_run:
        for hm_type, hm_df in heatmaps.items():
            if args.local:
                write_to_local(hm_df, hm_type)
            else:
                write_to_s3(hm_df, hm_type)
    
    logger.info("\n✅ Timing heatmap computation complete!")


if __name__ == '__main__':
    main()
