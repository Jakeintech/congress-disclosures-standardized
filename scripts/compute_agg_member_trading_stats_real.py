#!/usr/bin/env python3
"""
Compute agg_member_trading_stats using REAL silver data.

Reads from silver_ptr_transactions and builds actual trading statistics
for the 38 Congress members with PTR filings.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
import logging
import tempfile

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_ptr_transactions(bucket_name: str) -> pd.DataFrame:
    """Load all PTR transactions from silver layer."""
    s3 = boto3.client('s3')
    prefix = 'silver/house/financial/ptr_transactions/'

    logger.info(f"Loading PTR transactions from s3://{bucket_name}/{prefix}")

    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    if 'Contents' not in response:
        raise ValueError(f"No PTR transactions found")

    dfs = []
    for obj in response['Contents']:
        if obj['Key'].endswith('.parquet'):
            logger.info(f"  Reading {obj['Key']}")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                s3.download_file(bucket_name, obj['Key'], tmp.name)
                df = pd.read_parquet(tmp.name)
                dfs.append(df)
                os.unlink(tmp.name)

    all_transactions = pd.concat(dfs, ignore_index=True)
    logger.info(f"✅ Loaded {len(all_transactions):,} transactions")

    return all_transactions


def compute_member_trading_stats(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Compute trading statistics by member."""
    logger.info("Computing member trading statistics...")

    # Only include actual members (filer_type = 'Member')
    member_transactions = transactions_df[transactions_df['filer_type'] == 'Member'].copy()

    logger.info(f"  Analyzing {len(member_transactions):,} transactions from members")

    # Group by member
    member_stats = []

    for (first_name, last_name, state_district), group in member_transactions.groupby(['first_name', 'last_name', 'state_district']):

        # Calculate amount midpoint for volume calculations
        group['amount_midpoint'] = (group['amount_low'] + group['amount_high']) / 2

        # Count transaction types
        buy_count = len(group[group['transaction_type'].str.contains('Purchase', case=False, na=False)])
        sell_count = len(group[group['transaction_type'].str.contains('Sale', case=False, na=False)])

        # Calculate buy/sell ratio (avoid division by zero)
        if sell_count > 0:
            buy_sell_ratio = round(buy_count / sell_count, 2)
        else:
            buy_sell_ratio = buy_count if buy_count > 0 else 0

        stats = {
            'first_name': first_name,
            'last_name': last_name,
            'full_name': f"{first_name} {last_name}",
            'state_district': state_district,
            'state': state_district[:2] if pd.notna(state_district) else None,
            'district': state_district[2:] if pd.notna(state_district) and len(state_district) > 2 else None,
            'party': None,  # Will be enriched later
            'total_trades': len(group),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'buy_sell_ratio': buy_sell_ratio,
            'total_volume': group['amount_midpoint'].sum(),
            'avg_transaction_size': group['amount_midpoint'].mean(),
            'unique_stocks': group['asset_name'].nunique(),
            'period_start': group['transaction_date'].min(),
            'period_end': group['transaction_date'].max()
        }

        member_stats.append(stats)

    stats_df = pd.DataFrame(member_stats)

    # Sort by total trades descending
    stats_df = stats_df.sort_values('total_trades', ascending=False).reset_index(drop=True)

    logger.info(f"✅ Computed stats for {len(stats_df)} members")
    logger.info(f"\nTop 5 most active traders:")
    for _, row in stats_df.head(5).iterrows():
        logger.info(f"  {row['full_name']} ({row['state_district']}): {row['total_trades']} trades, ${row['total_volume']/1000:.0f}K volume")

    return stats_df


def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write to gold layer."""
    logger.info("\nWriting to gold layer...")

    # Save locally
    output_dir = Path('data/gold/aggregates/agg_member_trading_stats')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Partition by year of period_end
    df['year'] = pd.to_datetime(df['period_end']).dt.year

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

        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            year_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)
            s3_key = f'gold/house/financial/aggregates/agg_member_trading_stats/year={year}/part-0000.parquet'
            s3.upload_file(tmp.name, bucket_name, s3_key)
            logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")
            os.unlink(tmp.name)


def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    logger.info("=" * 80)
    logger.info("Computing agg_member_trading_stats (REAL DATA)")
    logger.info("=" * 80)

    # Load PTR transactions
    transactions_df = load_ptr_transactions(bucket_name)

    # Compute stats
    stats_df = compute_member_trading_stats(transactions_df)

    # Write to gold layer
    write_to_gold(stats_df, bucket_name)

    logger.info("\n" + "=" * 80)
    logger.info("✅ agg_member_trading_stats computation complete!")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
