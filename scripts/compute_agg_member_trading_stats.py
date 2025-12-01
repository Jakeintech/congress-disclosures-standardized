#!/usr/bin/env python3
"""
Compute agg_member_trading_stats aggregate table.

Analyzes trading activity by member including:
- Total trades and volume
- Buy vs sell ratios
- Average transaction size
- Trading frequency
- Most active periods
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_transactions(bucket_name: str) -> pd.DataFrame:
    """Load transactions from gold layer (fact_ptr_transactions)."""
    logger.info("Loading transactions from gold layer...")
    
    # Path to Gold Fact Table
    fact_path = Path('data/gold/house/financial/facts/fact_ptr_transactions')
    
    if not fact_path.exists():
        logger.warning(f"Fact table not found at {fact_path}")
        return pd.DataFrame()
        
    # Read all parquet files
    files = list(fact_path.glob("**/*.parquet"))
    if not files:
        logger.warning("No transaction files found.")
        return pd.DataFrame()
        
    df = pd.concat([pd.read_parquet(f) for f in files])
    logger.info(f"Loaded {len(df)} transactions")
    return df

def load_dim_members(bucket_name: str) -> pd.DataFrame:
    """Load dim_members from gold layer."""
    dim_path = Path('data/gold/dimensions/dim_members')
    if not dim_path.exists():
        logger.warning(f"Dim members not found at {dim_path}")
        return pd.DataFrame()
        
    files = list(dim_path.glob("*.parquet"))
    if not files:
        return pd.DataFrame()
        
    return pd.concat([pd.read_parquet(f) for f in files])


def compute_member_trading_stats(transactions_df: pd.DataFrame, members_df: pd.DataFrame) -> pd.DataFrame:
    """Compute trading statistics by member."""
    logger.info("Computing member trading statistics...")

    stats = []

    if transactions_df.empty:
        logger.warning("No transactions found. Returning empty stats DataFrame.")
        return pd.DataFrame(columns=[
            'member_key', 'total_trades', 'buy_count', 'sell_count', 'buy_sell_ratio',
            'total_volume', 'avg_transaction_size', 'min_transaction_size',
            'max_transaction_size', 'avg_days_between_trades', 'most_active_month',
            'first_transaction_date', 'last_transaction_date', 'period_start', 'period_end',
            'full_name', 'party', 'state_district'
        ])

    # Ensure amount_midpoint exists
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0) + transactions_df.get('amount_high', 0)
        ) / 2
        
    # Ensure transaction_date exists (convert from key)
    if 'transaction_date' not in transactions_df.columns and 'transaction_date_key' in transactions_df.columns:
        transactions_df['transaction_date'] = pd.to_datetime(
            transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce'
        )

    for member_key, member_txs in transactions_df.groupby('member_key'):
        total_trades = len(member_txs)
        buy_count = len(member_txs[member_txs['transaction_type'] == 'Purchase'])
        sell_count = len(member_txs[member_txs['transaction_type'] == 'Sale'])

        total_volume = member_txs['amount_midpoint'].sum()
        avg_transaction_size = member_txs['amount_midpoint'].mean()

        # Calculate trading frequency (days between trades)
        sorted_dates = member_txs['transaction_date'].sort_values()
        if len(sorted_dates) > 1:
            date_diffs = sorted_dates.diff().dt.days.dropna()
            avg_days_between_trades = date_diffs.mean()
        else:
            avg_days_between_trades = None

        # Most active month
        member_txs['month'] = member_txs['transaction_date'].dt.to_period('M')
        most_active_month = member_txs.groupby('month').size().idxmax()

        record = {
            'member_key': member_key,
            'total_trades': total_trades,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'buy_sell_ratio': buy_count / sell_count if sell_count > 0 else None,
            'total_volume': total_volume,
            'avg_transaction_size': avg_transaction_size,
            'min_transaction_size': member_txs['amount_midpoint'].min(),
            'max_transaction_size': member_txs['amount_midpoint'].max(),
            'avg_days_between_trades': avg_days_between_trades,
            'most_active_month': str(most_active_month),
            'first_transaction_date': member_txs['transaction_date'].min().strftime('%Y-%m-%d'),
            'last_transaction_date': member_txs['transaction_date'].max().strftime('%Y-%m-day'),
            'period_start': '2025-01-01',
            'period_end': '2025-12-31'
        }

        stats.append(record)

    stats_df = pd.DataFrame(stats)

    # Merge with member names (use columns that actually exist)
    available_cols = ['member_key']
    for col in ['full_name', 'first_name', 'last_name', 'party', 'state', 'district', 'state_district']:
        if col in members_df.columns:
            available_cols.append(col)
    
    if len(available_cols) > 1:
        stats_df = stats_df.merge(
            members_df[available_cols],
            on='member_key',
            how='left'
        )

    # Sort by total volume descending
    stats_df = stats_df.sort_values('total_volume', ascending=False)

    logger.info(f"Computed stats for {len(stats_df)} members")
    return stats_df


def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write agg_member_trading_stats to gold layer."""
    logger.info("Writing to gold layer...")

    output_dir = Path('data/gold/aggregates/agg_member_trading_stats')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Partition by year
    df['year'] = 2025

    for year in df['year'].unique():
        year_df = df[df['year'] == year].drop(columns=['year'])
        year_output_dir = output_dir / f'year={year}'
        year_output_dir.mkdir(parents=True, exist_ok=True)

        output_file = year_output_dir / 'part-0000.parquet'
        year_df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
        logger.info(f"  Wrote {year}: {len(year_df)} records -> {output_file}")

    # Upload to S3
    s3 = boto3.client('s3')
    for year in df['year'].unique():
        year_df = df[df['year'] == year].drop(columns=['year'])

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            year_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)
            s3_key = f'gold/house/financial/aggregates/agg_member_trading_stats/year={year}/part-0000.parquet'
            s3.upload_file(tmp.name, bucket_name, s3_key)
            logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")
            os.unlink(tmp.name)


def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    logger.info("=" * 80)
    logger.info("Computing agg_member_trading_stats")
    logger.info("=" * 80)

    # Load data
    # Load data
    transactions_df = load_transactions(bucket_name)
    members_df = load_dim_members(bucket_name)

    # Compute statistics
    stats_df = compute_member_trading_stats(transactions_df, members_df)

    logger.info(f"\nSummary:")
    if not stats_df.empty:
        logger.info(f"  Total members with trades: {len(stats_df)}")
        logger.info(f"  Total volume: ${stats_df['total_volume'].sum():,.0f}")
        logger.info(f"  Most active trader: {stats_df.iloc[0]['full_name']} (${stats_df.iloc[0]['total_volume']:,.0f})")
    else:
        logger.info("  No trading data to summarize.")

    # Write to gold layer
    write_to_gold(stats_df, bucket_name)

    logger.info("\n✅ agg_member_trading_stats computation complete!")


if __name__ == '__main__':
    main()
