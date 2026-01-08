#!/usr/bin/env python3
"""
Compute cryptocurrency transactions aggregate for analytics.

Identifies and aggregates all crypto-related transactions:
- Bitcoin (BTC, Grayscale Bitcoin Trust)
- Ethereum (ETH, Grayscale Ethereum Trust)
- Crypto exchange stocks (Coinbase, Robinhood)
- Blockchain ETFs and crypto-related equities

Output:
- Transaction-level crypto data (filtered Parquet)
- Monthly aggregates by category
"""

import pandas as pd
from datetime import datetime
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.lib.ingestion.s3_utils import upload_file_to_s3
from backend.lib.ingestion.s3_path_registry import S3Paths

BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

# Cryptocurrency classification keywords (factual, data-driven)
CRYPTO_KEYWORDS = {
    'bitcoin': [
        'bitcoin', 'btc', 'grayscale bitcoin', 'gbtc',
        'proshares bitcoin', 'bito', 'bitcoin trust'
    ],
    'ethereum': [
        'ethereum', 'eth', 'grayscale ethereum', 'ethe',
        'ethereum trust'
    ],
    'crypto_exchanges': [
        'coinbase', 'coin', 'robinhood', 'hood', 'binance',
        'kraken', 'gemini', 'crypto.com'
    ],
    'blockchain_funds': [
        'blockchain', 'crypto', 'digital currency', 'digital asset',
        'amplify transformational data sharing', 'blok',
        'siren nasdaq nexgen economy', 'blcn'
    ]
}


def load_transactions() -> pd.DataFrame:
    """Load all PTR transactions from Gold fact table."""
    try:
        s3_path = f"s3://{BUCKET}/data/gold/facts/fact_transactions/"
        print(f"Loading transactions from {s3_path}")
        df = pd.read_parquet(s3_path)
        print(f"Loaded {len(df):,} transactions")
        return df
    except Exception as e:
        print(f"Error loading transactions: {e}")
        return pd.DataFrame()


def identify_crypto_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Identify all cryptocurrency-related transactions."""

    if len(df) == 0:
        print("No transactions to process")
        return pd.DataFrame()

    df = df.copy()
    df['asset_name_lower'] = df['asset_name'].str.lower()

    # Tag crypto categories
    for category, keywords in CRYPTO_KEYWORDS.items():
        pattern = '|'.join(keywords)
        df[f'is_{category}'] = df['asset_name_lower'].str.contains(pattern, na=False, regex=True)

    # Overall crypto flag (any category match)
    df['is_crypto'] = (
        df['is_bitcoin'] |
        df['is_ethereum'] |
        df['is_crypto_exchanges'] |
        df['is_blockchain_funds']
    )

    # Filter to crypto only
    df_crypto = df[df['is_crypto']].copy()

    if len(df_crypto) == 0:
        print("No crypto transactions found")
        return pd.DataFrame()

    # Add time dimensions
    df_crypto['transaction_date'] = pd.to_datetime(df_crypto['transaction_date'])
    df_crypto['year'] = df_crypto['transaction_date'].dt.year
    df_crypto['month'] = df_crypto['transaction_date'].dt.month
    df_crypto['quarter'] = df_crypto['transaction_date'].dt.quarter
    df_crypto['year_month'] = df_crypto['transaction_date'].dt.to_period('M').astype(str)

    # Determine primary category
    def get_primary_category(row):
        if row['is_bitcoin']:
            return 'bitcoin'
        elif row['is_ethereum']:
            return 'ethereum'
        elif row['is_crypto_exchanges']:
            return 'crypto_exchanges'
        elif row['is_blockchain_funds']:
            return 'blockchain_funds'
        else:
            return 'other'

    df_crypto['crypto_category'] = df_crypto.apply(get_primary_category, axis=1)

    # Add metadata
    df_crypto['computed_at'] = datetime.utcnow().isoformat()

    return df_crypto


def compute_crypto_aggregates(df_crypto: pd.DataFrame) -> pd.DataFrame:
    """Compute aggregated crypto metrics by month and category."""

    if len(df_crypto) == 0:
        print("No crypto transactions to aggregate")
        return pd.DataFrame()

    aggs = []

    # Overall crypto activity by month
    monthly_all = df_crypto.groupby(['year', 'month', 'year_month']).agg({
        'bioguide_id': 'nunique',
        'transaction_type': 'count',
        'amount_low': 'sum'
    }).reset_index()
    monthly_all.columns = ['year', 'month', 'year_month', 'unique_members', 'transaction_count', 'total_amount']
    monthly_all['crypto_category'] = 'all_crypto'
    aggs.append(monthly_all)

    # By category
    for category in ['bitcoin', 'ethereum', 'crypto_exchanges', 'blockchain_funds']:
        df_cat = df_crypto[df_crypto['crypto_category'] == category]

        if len(df_cat) > 0:
            monthly_cat = df_cat.groupby(['year', 'month', 'year_month']).agg({
                'bioguide_id': 'nunique',
                'transaction_type': 'count',
                'amount_low': 'sum'
            }).reset_index()
            monthly_cat.columns = ['year', 'month', 'year_month', 'unique_members', 'transaction_count', 'total_amount']
            monthly_cat['crypto_category'] = category
            aggs.append(monthly_cat)

    # Combine
    df_agg = pd.concat(aggs, ignore_index=True)
    df_agg['computed_at'] = datetime.utcnow().isoformat()

    # Sort by year, month, category
    df_agg = df_agg.sort_values(['year', 'month', 'crypto_category'], ascending=[False, False, True])

    return df_agg


def main():
    """Main execution."""
    print("=" * 80)
    print("Cryptocurrency Transactions Aggregate")
    print("=" * 80)

    print("\n1. Loading transaction data...")
    df_trans = load_transactions()

    if len(df_trans) == 0:
        print("ERROR: No transaction data available")
        return 1

    print(f"\n2. Identifying crypto transactions...")
    df_crypto = identify_crypto_transactions(df_trans)

    if len(df_crypto) == 0:
        print("WARNING: No crypto transactions found")
        # Still create empty files for consistency
        empty_trans = pd.DataFrame(columns=[
            'bioguide_id', 'transaction_date', 'asset_name', 'ticker',
            'transaction_type', 'amount_low', 'amount_high',
            'crypto_category', 'is_bitcoin', 'is_ethereum',
            'is_crypto_exchanges', 'is_blockchain_funds', 'year', 'month', 'computed_at'
        ])
        empty_agg = pd.DataFrame(columns=[
            'year', 'month', 'year_month', 'crypto_category',
            'unique_members', 'transaction_count', 'total_amount', 'computed_at'
        ])

        # Upload empty files
        trans_path = "data/gold/aggregates/crypto_transactions/crypto_transactions.parquet"
        agg_path = "data/gold/aggregates/crypto_transactions/monthly_aggregates.parquet"

        empty_trans.to_parquet("/tmp/crypto_transactions.parquet", index=False)
        empty_agg.to_parquet("/tmp/crypto_monthly_agg.parquet", index=False)

        upload_file_to_s3("/tmp/crypto_transactions.parquet", BUCKET, trans_path)
        upload_file_to_s3("/tmp/crypto_monthly_agg.parquet", BUCKET, agg_path)

        print(f"✓ Created empty crypto transaction files")
        return 0

    print(f"\n3. Found {len(df_crypto):,} crypto transactions")
    print(f"   - Bitcoin:          {df_crypto['is_bitcoin'].sum():,}")
    print(f"   - Ethereum:         {df_crypto['is_ethereum'].sum():,}")
    print(f"   - Crypto Exchanges: {df_crypto['is_crypto_exchanges'].sum():,}")
    print(f"   - Blockchain Funds: {df_crypto['is_blockchain_funds'].sum():,}")

    # Compute aggregates
    print(f"\n4. Computing monthly aggregates...")
    df_agg = compute_crypto_aggregates(df_crypto)

    print(f"   Generated {len(df_agg):,} aggregate records")

    # Upload transaction-level data
    print("\n5. Uploading to S3...")
    trans_path = "data/gold/aggregates/crypto_transactions/crypto_transactions.parquet"
    local_trans = "/tmp/crypto_transactions.parquet"

    # Select output columns for transaction-level data
    trans_cols = [
        'bioguide_id', 'transaction_date', 'filing_date',
        'asset_name', 'ticker', 'transaction_type',
        'amount_low', 'amount_high', 'crypto_category',
        'is_bitcoin', 'is_ethereum', 'is_crypto_exchanges', 'is_blockchain_funds',
        'year', 'month', 'quarter', 'year_month', 'computed_at'
    ]
    trans_cols = [col for col in trans_cols if col in df_crypto.columns]

    df_crypto[trans_cols].to_parquet(local_trans, index=False, compression='snappy')
    upload_file_to_s3(local_trans, BUCKET, trans_path)
    print(f"   ✓ Uploaded transaction-level data to s3://{BUCKET}/{trans_path}")

    # Upload aggregates
    agg_path = "data/gold/aggregates/crypto_transactions/monthly_aggregates.parquet"
    local_agg = "/tmp/crypto_monthly_agg.parquet"

    df_agg.to_parquet(local_agg, index=False, compression='snappy')
    upload_file_to_s3(local_agg, BUCKET, agg_path)
    print(f"   ✓ Uploaded monthly aggregates to s3://{BUCKET}/{agg_path}")

    # Summary statistics
    print("\n6. Monthly Activity Summary (last 6 months):")
    recent_agg = df_agg[df_agg['crypto_category'] == 'all_crypto'].head(6)

    for _, row in recent_agg.iterrows():
        print(f"   {row['year_month']}: {row['transaction_count']:3d} transactions, "
              f"{row['unique_members']:2d} members, ${row['total_amount']:,.0f} total")

    print("\n" + "=" * 80)
    print("✓ Cryptocurrency transactions aggregate complete")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
