#!/usr/bin/env python3
"""
Compute agg_trending_stocks using REAL silver data.

Reads from silver_ptr_transactions and identifies most traded stocks.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
import logging
import tempfile
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_ticker_from_asset_name(asset_name: str) -> str:
    """Extract ticker symbol from asset name."""
    if pd.isna(asset_name):
        return None

    # Look for patterns like (AAPL), [AAPL], - AAPL, etc.
    patterns = [
        r'\(([A-Z]{1,5})\)',  # (AAPL)
        r'\[([A-Z]{1,5})\]',  # [AAPL]
        r'\s-\s([A-Z]{1,5})$',  # - AAPL at end
        r'\s-\s\(([A-Z]{1,5})\)',  # - (AAPL)
    ]

    for pattern in patterns:
        match = re.search(pattern, asset_name)
        if match:
            return match.group(1)

    return None


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


def compute_trending_stocks(transactions_df: pd.DataFrame, limit: int = 50) -> pd.DataFrame:
    """Compute trending stocks statistics."""
    logger.info(f"Computing trending stocks (top {limit})...")

    # Extract tickers from asset names
    transactions_df['ticker'] = transactions_df['asset_name'].apply(extract_ticker_from_asset_name)

    # Filter to only transactions with identifiable tickers
    with_tickers = transactions_df[transactions_df['ticker'].notna()].copy()

    logger.info(f"  Found {len(with_tickers):,} transactions with identifiable tickers")
    logger.info(f"  Unique tickers: {with_tickers['ticker'].nunique()}")

    # Calculate amount midpoint
    with_tickers['amount_midpoint'] = (with_tickers['amount_low'] + with_tickers['amount_high']) / 2

    # Group by ticker
    stock_stats = []

    for ticker, group in with_tickers.groupby('ticker'):
        # Get a representative asset name (most common)
        asset_name = group['asset_name'].mode()[0] if len(group['asset_name'].mode()) > 0 else group['asset_name'].iloc[0]

        # Count transaction types
        buy_count = len(group[group['transaction_type'].str.contains('Purchase', case=False, na=False)])
        sell_count = len(group[group['transaction_type'].str.contains('Sale', case=False, na=False)])

        # Determine sentiment
        net_position = buy_count - sell_count
        if net_position > 0:
            net_sentiment = 'Bullish'
        elif net_position < 0:
            net_sentiment = 'Bearish'
        else:
            net_sentiment = 'Neutral'

        stats = {
            'ticker': ticker,
            'name': asset_name,
            'trade_count': len(group),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'net_sentiment': net_sentiment,
            'total_volume_usd': group['amount_midpoint'].sum(),
            'avg_transaction_size': group['amount_midpoint'].mean(),
            'unique_members': group[['first_name', 'last_name']].drop_duplicates().shape[0],
            'period_start': group['transaction_date'].min(),
            'period_end': group['transaction_date'].max()
        }

        stock_stats.append(stats)

    stats_df = pd.DataFrame(stock_stats)

    # Sort by trade count and take top N
    stats_df = stats_df.sort_values('trade_count', ascending=False).head(limit).reset_index(drop=True)
    stats_df['rank'] = range(1, len(stats_df) + 1)

    logger.info(f"✅ Computed stats for top {len(stats_df)} stocks")
    logger.info(f"\nTop 10 most traded stocks:")
    for _, row in stats_df.head(10).iterrows():
        logger.info(f"  #{row['rank']} {row['ticker']}: {row['trade_count']} trades ({row['net_sentiment']})")

    return stats_df


def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write to gold layer."""
    logger.info("\nWriting to gold layer...")

    # Save locally
    output_dir = Path('data/gold/aggregates/agg_trending_stocks')
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
            s3_key = f'gold/house/financial/aggregates/agg_trending_stocks/year={year}/part-0000.parquet'
            s3.upload_file(tmp.name, bucket_name, s3_key)
            logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")
            os.unlink(tmp.name)


def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    logger.info("=" * 80)
    logger.info("Computing agg_trending_stocks (REAL DATA)")
    logger.info("=" * 80)

    # Load PTR transactions
    transactions_df = load_ptr_transactions(bucket_name)

    # Compute stats
    stats_df = compute_trending_stocks(transactions_df, limit=50)

    # Write to gold layer
    write_to_gold(stats_df, bucket_name)

    logger.info("\n" + "=" * 80)
    logger.info("✅ agg_trending_stocks computation complete!")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
