#!/usr/bin/env python3
"""
Compute trading volume timeseries aggregations.

Creates daily, weekly, and monthly timeseries of:
- Total trading volume (buy + sell)
- Net flow (buy - sell)
- Trade counts
- Unique traders
- Party breakdown (D vs R)

Output: gold/aggregates/agg_trading_volume_timeseries/
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
import argparse

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
            logger.debug(f"  Reading {obj['Key']}")
            response_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
            df = pd.read_parquet(BytesIO(response_obj['Body'].read()))
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


def load_transactions_local() -> pd.DataFrame:
    """Load transactions from local gold layer."""
    fact_path = Path('data/gold/house/financial/facts/fact_ptr_transactions')
    
    if not fact_path.exists():
        logger.warning(f"Fact table not found at {fact_path}")
        return pd.DataFrame()
        
    files = list(fact_path.glob("**/*.parquet"))
    if not files:
        logger.warning("No transaction files found.")
        return pd.DataFrame()
        
    df = pd.concat([pd.read_parquet(f) for f in files])
    logger.info(f"Loaded {len(df)} transactions from local")
    return df


def load_dim_members_local() -> pd.DataFrame:
    """Load dim_members from local gold layer."""
    dim_path = Path('data/gold/dimensions/dim_members')
    if not dim_path.exists():
        logger.warning(f"Dim members not found at {dim_path}")
        return pd.DataFrame()
        
    files = list(dim_path.glob("*.parquet"))
    if not files:
        return pd.DataFrame()
        
    return pd.concat([pd.read_parquet(f) for f in files])


def compute_timeseries(transactions_df: pd.DataFrame, members_df: pd.DataFrame, 
                       granularity: str = 'daily') -> pd.DataFrame:
    """
    Compute trading volume timeseries at specified granularity.
    
    Args:
        transactions_df: Transaction data with transaction_date, amount, type
        members_df: Member data with party affiliation
        granularity: 'daily', 'weekly', or 'monthly'
    
    Returns:
        DataFrame with timeseries data
    """
    logger.info(f"Computing {granularity} timeseries...")
    
    if transactions_df.empty:
        logger.warning("No transactions found")
        return pd.DataFrame()
    
    # Ensure transaction_date exists
    if 'transaction_date' not in transactions_df.columns and 'transaction_date_key' in transactions_df.columns:
        transactions_df['transaction_date'] = pd.to_datetime(
            transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce'
        )
    else:
        transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'], errors='coerce')
    
    # Drop rows with invalid dates
    transactions_df = transactions_df.dropna(subset=['transaction_date'])
    
    # Ensure amount_midpoint exists
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    # Merge with members for party info
    if not members_df.empty and 'member_key' in transactions_df.columns:
        if 'party' in members_df.columns:
            transactions_df = transactions_df.merge(
                members_df[['member_key', 'party']],
                on='member_key',
                how='left'
            )
    
    # Create period column based on granularity
    if granularity == 'daily':
        transactions_df['period'] = transactions_df['transaction_date'].dt.date
    elif granularity == 'weekly':
        transactions_df['period'] = transactions_df['transaction_date'].dt.to_period('W').apply(lambda x: x.start_time.date())
    else:  # monthly
        transactions_df['period'] = transactions_df['transaction_date'].dt.to_period('M').apply(lambda x: x.start_time.date())
    
    # Calculate buy/sell volumes
    transactions_df['buy_volume'] = transactions_df.apply(
        lambda x: x['amount_midpoint'] if x.get('transaction_type') == 'Purchase' else 0, axis=1
    )
    transactions_df['sell_volume'] = transactions_df.apply(
        lambda x: x['amount_midpoint'] if x.get('transaction_type') in ['Sale', 'Sale (partial)', 'Sale (full)'] else 0, axis=1
    )
    transactions_df['is_buy'] = transactions_df['transaction_type'] == 'Purchase'
    transactions_df['is_sell'] = transactions_df['transaction_type'].isin(['Sale', 'Sale (partial)', 'Sale (full)'])
    
    # Aggregate by period
    agg_df = transactions_df.groupby('period').agg({
        'amount_midpoint': 'sum',
        'buy_volume': 'sum',
        'sell_volume': 'sum',
        'is_buy': 'sum',
        'is_sell': 'sum',
        'member_key': 'nunique',
    }).reset_index()
    
    agg_df.columns = ['period', 'total_volume', 'buy_volume', 'sell_volume', 
                      'buy_count', 'sell_count', 'unique_traders']
    
    # Calculate net flow and trade count
    agg_df['net_flow'] = agg_df['buy_volume'] - agg_df['sell_volume']
    agg_df['trade_count'] = agg_df['buy_count'] + agg_df['sell_count']
    
    # Party breakdown (if available)
    if 'party' in transactions_df.columns:
        party_agg = transactions_df.groupby(['period', 'party']).agg({
            'amount_midpoint': 'sum'
        }).reset_index()
        
        # Pivot to get D and R columns
        party_pivot = party_agg.pivot(index='period', columns='party', values='amount_midpoint').reset_index()
        party_pivot.columns = ['period'] + [f'volume_{col.lower()}' if col else 'volume_other' for col in party_pivot.columns[1:]]
        
        agg_df = agg_df.merge(party_pivot, on='period', how='left')
    
    # Add metadata
    agg_df['granularity'] = granularity
    agg_df['period'] = pd.to_datetime(agg_df['period'])
    agg_df['dt_computed'] = datetime.utcnow().isoformat()
    
    # Sort by period
    agg_df = agg_df.sort_values('period')
    
    logger.info(f"Computed {len(agg_df)} {granularity} periods")
    return agg_df


def write_to_s3(df: pd.DataFrame, granularity: str):
    """Write timeseries to S3."""
    if df.empty:
        logger.warning(f"No data to write for {granularity}")
        return
    
    s3 = boto3.client('s3')
    s3_key = f'gold/aggregates/agg_trading_volume_timeseries/granularity={granularity}/part-0000.parquet'
    
    buffer = BytesIO()
    df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
    buffer.seek(0)
    
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
    logger.info(f"Wrote {len(df)} records to s3://{BUCKET_NAME}/{s3_key}")


def write_to_local(df: pd.DataFrame, granularity: str):
    """Write timeseries to local gold layer."""
    if df.empty:
        logger.warning(f"No data to write for {granularity}")
        return
    
    output_dir = Path(f'data/gold/aggregates/agg_trading_volume_timeseries/granularity={granularity}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
    logger.info(f"Wrote {len(df)} records to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Compute trading volume timeseries')
    parser.add_argument('--granularity', choices=['daily', 'weekly', 'monthly', 'all'], 
                        default='all', help='Timeseries granularity')
    parser.add_argument('--local', action='store_true', help='Use local data instead of S3')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - do not write output')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Computing Trading Volume Timeseries")
    logger.info("=" * 80)
    
    # Load data
    if args.local:
        transactions_df = load_transactions_local()
        members_df = load_dim_members_local()
    else:
        s3 = boto3.client('s3')
        transactions_df = read_parquet_from_s3(s3, 'gold/house/financial/facts/fact_ptr_transactions/')
        members_df = read_parquet_from_s3(s3, 'gold/dimensions/dim_members/')
    
    if transactions_df.empty:
        logger.error("No transaction data available")
        return
    
    # Compute timeseries
    granularities = ['daily', 'weekly', 'monthly'] if args.granularity == 'all' else [args.granularity]
    
    for gran in granularities:
        ts_df = compute_timeseries(transactions_df.copy(), members_df, gran)
        
        if not ts_df.empty:
            logger.info(f"\n{gran.upper()} Summary:")
            logger.info(f"  Periods: {len(ts_df)}")
            logger.info(f"  Total volume: ${ts_df['total_volume'].sum():,.0f}")
            logger.info(f"  Avg daily volume: ${ts_df['total_volume'].mean():,.0f}")
            
            if not args.dry_run:
                if args.local:
                    write_to_local(ts_df, gran)
                else:
                    write_to_s3(ts_df, gran)
    
    logger.info("\n✅ Trading volume timeseries computation complete!")


if __name__ == '__main__':
    main()
