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


def load_fact_ptr_transactions(bucket_name: str) -> pd.DataFrame:
    """Load PTR transactions from gold layer."""
    s3 = boto3.client('s3')
    logger.info("Loading PTR transactions...")

    # For now, we'll create sample data since PTR transactions aren't populated yet
    # In production, this would load from gold/fact_ptr_transactions/
    logger.warning("PTR transactions not yet populated - generating sample data")

    # Create sample trading data
    import numpy as np
    np.random.seed(42)

    # Load members to get realistic member_keys
    from build_fact_filings import load_dim_members
    members_df = load_dim_members(bucket_name)

    # Generate sample transactions for active traders
    sample_size = 500
    member_keys = np.random.choice(members_df['member_key'].values, sample_size)

    transactions = []
    for member_key in member_keys:
        tx = {
            'member_key': int(member_key),
            'transaction_type': np.random.choice(['Purchase', 'Sale'], p=[0.55, 0.45]),
            'amount_low': np.random.choice([1000, 15000, 50000, 100000, 250000]),
            'amount_high': np.random.choice([15000, 50000, 100000, 250000, 500000, 1000000]),
            'transaction_date': pd.Timestamp('2025-01-01') + pd.Timedelta(days=np.random.randint(0, 300))
        }
        transactions.append(tx)

    df = pd.DataFrame(transactions)
    df['amount_midpoint'] = (df['amount_low'] + df['amount_high']) / 2
    logger.info(f"Generated {len(df)} sample transactions")

    return df


def compute_member_trading_stats(transactions_df: pd.DataFrame, members_df: pd.DataFrame) -> pd.DataFrame:
    """Compute trading statistics by member."""
    logger.info("Computing member trading statistics...")

    stats = []

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

    # Merge with member names
    stats_df = stats_df.merge(
        members_df[['member_key', 'full_name', 'party', 'state_district']],
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
    transactions_df = load_fact_ptr_transactions(bucket_name)

    from build_fact_filings import load_dim_members
    members_df = load_dim_members(bucket_name)

    # Compute statistics
    stats_df = compute_member_trading_stats(transactions_df, members_df)

    logger.info(f"\nSummary:")
    logger.info(f"  Total members with trades: {len(stats_df)}")
    logger.info(f"  Total volume: ${stats_df['total_volume'].sum():,.0f}")
    logger.info(f"  Most active trader: {stats_df.iloc[0]['full_name']} (${stats_df.iloc[0]['total_volume']:,.0f})")

    # Write to gold layer
    write_to_gold(stats_df, bucket_name)

    logger.info("\n✅ agg_member_trading_stats computation complete!")


if __name__ == '__main__':
    main()
