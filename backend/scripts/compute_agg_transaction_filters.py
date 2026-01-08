#!/usr/bin/env python3
"""
Compute high-value transactions aggregate for analytics and alerts.

Filters and enriches transactions based on:
- Transaction amount thresholds ($50K, $100K, $250K, $500K, $1M)
- Committee assignments and policy area correlation
- Cryptocurrency exposure
- Recent activity windows (7, 14, 30 days)

Output: Parquet file with filtered transactions + metadata flags
"""

import pandas as pd
import pyarrow.parquet as pq
from datetime import datetime, timedelta
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.lib.ingestion.s3_utils import upload_file_to_s3, download_file_from_s3
from backend.lib.ingestion.s3_path_registry import S3Paths

BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

# Thresholds (factual, data-driven)
AMOUNT_THRESHOLDS = {
    'tier_1': 50000,   # $50K+
    'tier_2': 100000,  # $100K+
    'tier_3': 250000,  # $250K+
    'tier_4': 500000,  # $500K+
    'tier_5': 1000000  # $1M+
}

CRYPTO_KEYWORDS = ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'coinbase', 'binance', 'blockchain']
RECENT_DAYS_WINDOWS = [7, 14, 30]


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


def load_members() -> pd.DataFrame:
    """Load member dimension."""
    try:
        s3_path = f"s3://{BUCKET}/data/gold/dimensions/dim_members/"
        print(f"Loading members from {s3_path}")
        df = pd.read_parquet(s3_path)
        print(f"Loaded {len(df):,} member records")
        return df[['bioguide_id', 'full_name', 'party', 'state', 'chamber']]
    except Exception as e:
        print(f"Error loading members: {e}")
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=['bioguide_id', 'full_name', 'party', 'state', 'chamber'])


def load_committee_assignments() -> pd.DataFrame:
    """Load committee assignments from reference data."""
    # TODO: Build this from Congress.gov API data (STORY-XXX)
    # For now, return empty DataFrame
    print("⚠ Committee assignments not yet available (requires Congress API integration)")
    return pd.DataFrame(columns=['bioguide_id', 'committee_name', 'subcommittee_name'])


def classify_amount_tier(amount: int) -> str:
    """Classify transaction by amount tier."""
    if amount >= AMOUNT_THRESHOLDS['tier_5']:
        return 'tier_5_1m_plus'
    elif amount >= AMOUNT_THRESHOLDS['tier_4']:
        return 'tier_4_500k_plus'
    elif amount >= AMOUNT_THRESHOLDS['tier_3']:
        return 'tier_3_250k_plus'
    elif amount >= AMOUNT_THRESHOLDS['tier_2']:
        return 'tier_2_100k_plus'
    elif amount >= AMOUNT_THRESHOLDS['tier_1']:
        return 'tier_1_50k_plus'
    else:
        return 'below_threshold'


def identify_transaction_filters(df_trans: pd.DataFrame, df_members: pd.DataFrame, df_committees: pd.DataFrame) -> pd.DataFrame:
    """Identify and enrich high-value transactions."""

    if len(df_trans) == 0:
        print("No transactions to process")
        return pd.DataFrame()

    # Join with member data
    print("Joining with member data...")
    df = df_trans.merge(df_members, on='bioguide_id', how='left', suffixes=('', '_member'))

    # Join with committee data if available
    if len(df_committees) > 0:
        df = df.merge(df_committees, on='bioguide_id', how='left')
    else:
        df['committee_name'] = None
        df['subcommittee_name'] = None

    # Filter for high-value amounts (>=$50K)
    print(f"Filtering for amount_low >= ${AMOUNT_THRESHOLDS['tier_1']:,}")
    df = df[df['amount_low'] >= AMOUNT_THRESHOLDS['tier_1']].copy()
    print(f"Filtered to {len(df):,} high-value transactions")

    if len(df) == 0:
        print("No high-value transactions found")
        return pd.DataFrame()

    # Add amount tier classification
    df['amount_tier'] = df['amount_low'].apply(classify_amount_tier)

    # Add crypto flag
    df['is_crypto'] = df['asset_name'].str.lower().str.contains('|'.join(CRYPTO_KEYWORDS), na=False)

    # Add recent activity flags
    current_date = pd.Timestamp.now()
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])

    for days in RECENT_DAYS_WINDOWS:
        cutoff = current_date - timedelta(days=days)
        df[f'is_within_{days}d'] = df['transaction_date'] >= cutoff

    # Calculate committee correlation score
    # 0.0 = no committee data or no correlation
    # 0.5 = partial correlation (general committee relevance)
    # 1.0 = direct correlation (specific subcommittee match)
    df['committee_correlation_score'] = 0.0

    # Crypto + Digital Assets/Financial Services committee
    if df['committee_name'].notna().any():
        crypto_mask = df['is_crypto'] & df['committee_name'].str.contains('Digital Assets|Financial Services|Banking', na=False, case=False)
        df.loc[crypto_mask, 'committee_correlation_score'] = 1.0

        # Tech stocks + Science/Tech/Commerce committee
        tech_keywords = ['apple', 'microsoft', 'google', 'alphabet', 'meta', 'amazon', 'nvidia', 'tesla', 'intel', 'amd']
        tech_pattern = '|'.join(tech_keywords)
        tech_mask = df['asset_name'].str.lower().str.contains(tech_pattern, na=False) & \
                    df['committee_name'].str.contains('Science|Technology|Commerce', na=False, case=False)
        df.loc[tech_mask, 'committee_correlation_score'] = 0.8

        # Defense stocks + Armed Services committee
        defense_keywords = ['lockheed', 'raytheon', 'northrop', 'general dynamics', 'boeing', 'bae systems']
        defense_pattern = '|'.join(defense_keywords)
        defense_mask = df['asset_name'].str.lower().str.contains(defense_pattern, na=False) & \
                       df['committee_name'].str.contains('Armed Services|Defense', na=False, case=False)
        df.loc[defense_mask, 'committee_correlation_score'] = 0.8

        # Energy stocks + Energy committee
        energy_keywords = ['exxon', 'chevron', 'conocophillips', 'shell', 'bp', 'totalenergies', 'energy']
        energy_pattern = '|'.join(energy_keywords)
        energy_mask = df['asset_name'].str.lower().str.contains(energy_pattern, na=False) & \
                      df['committee_name'].str.contains('Energy|Natural Resources', na=False, case=False)
        df.loc[energy_mask, 'committee_correlation_score'] = 0.8

        # Healthcare stocks + Health committee
        health_keywords = ['pfizer', 'johnson & johnson', 'merck', 'unitedhealth', 'cvs', 'humana', 'healthcare']
        health_pattern = '|'.join(health_keywords)
        health_mask = df['asset_name'].str.lower().str.contains(health_pattern, na=False) & \
                      df['committee_name'].str.contains('Health|Medicare|Medicaid', na=False, case=False)
        df.loc[health_mask, 'committee_correlation_score'] = 0.8

    # Sort by relevance: recent, high committee correlation, high amount
    df = df.sort_values(
        ['is_within_7d', 'committee_correlation_score', 'amount_low'],
        ascending=[False, False, False]
    )

    # Add metadata
    df['computed_at'] = datetime.utcnow().isoformat()
    df['filter_criteria'] = f"amount >= ${AMOUNT_THRESHOLDS['tier_1']:,}"

    # Select output columns
    output_cols = [
        'bioguide_id', 'full_name', 'party', 'state', 'chamber',
        'transaction_date', 'filing_date', 'asset_name', 'ticker',
        'transaction_type', 'amount_low', 'amount_high', 'amount_tier',
        'committee_name', 'subcommittee_name', 'committee_correlation_score',
        'is_crypto', 'is_within_7d', 'is_within_14d', 'is_within_30d',
        'computed_at', 'filter_criteria'
    ]

    # Only include columns that exist
    output_cols = [col for col in output_cols if col in df.columns]

    return df[output_cols]


def main():
    """Main execution."""
    print("=" * 80)
    print("High-Value Transactions Aggregate")
    print("=" * 80)

    print("\n1. Loading data...")
    df_trans = load_transactions()
    df_members = load_members()
    df_committees = load_committee_assignments()

    if len(df_trans) == 0:
        print("ERROR: No transaction data available")
        return 1

    print(f"\n2. Processing {len(df_trans):,} transactions...")
    df_high_value = identify_transaction_filters(df_trans, df_members, df_committees)

    if len(df_high_value) == 0:
        print("WARNING: No high-value transactions found")
        return 0

    print(f"\n3. Identified {len(df_high_value):,} high-value transactions")

    # Summary statistics
    print("\n4. Summary Statistics:")
    print(f"   - Tier 1 ($50K+):   {len(df_high_value[df_high_value['amount_tier'] == 'tier_1_50k_plus']):,}")
    print(f"   - Tier 2 ($100K+):  {len(df_high_value[df_high_value['amount_tier'] == 'tier_2_100k_plus']):,}")
    print(f"   - Tier 3 ($250K+):  {len(df_high_value[df_high_value['amount_tier'] == 'tier_3_250k_plus']):,}")
    print(f"   - Tier 4 ($500K+):  {len(df_high_value[df_high_value['amount_tier'] == 'tier_4_500k_plus']):,}")
    print(f"   - Tier 5 ($1M+):    {len(df_high_value[df_high_value['amount_tier'] == 'tier_5_1m_plus']):,}")
    print(f"   - Crypto:           {df_high_value['is_crypto'].sum():,}")
    print(f"   - Within 7 days:    {df_high_value['is_within_7d'].sum():,}")
    print(f"   - Within 30 days:   {df_high_value['is_within_30d'].sum():,}")

    # Upload to S3
    print("\n5. Uploading to S3...")
    output_path = "data/gold/aggregates/transaction_filters/transaction_filters.parquet"
    local_path = "/tmp/transaction_filters.parquet"

    df_high_value.to_parquet(local_path, index=False, compression='snappy')
    upload_file_to_s3(local_path, BUCKET, output_path)

    print(f"✓ Uploaded {len(df_high_value):,} transactions to s3://{BUCKET}/{output_path}")

    # Sample output
    print("\n6. Sample High-Value Transactions (top 5):")
    for idx, row in df_high_value.head(5).iterrows():
        amount_range = f"${row['amount_low']:,}"
        if pd.notna(row.get('amount_high')):
            amount_range += f"-${row['amount_high']:,}"

        print(f"\n   {row['full_name']} ({row['party']}-{row['state']})")
        print(f"   {row['transaction_type']}: {amount_range} in {row['asset_name']}")
        if pd.notna(row.get('ticker')):
            print(f"   Ticker: ${row['ticker']}")
        print(f"   Date: {row['transaction_date']}")
        if row.get('committee_correlation_score', 0) > 0:
            print(f"   Committee Correlation: {row['committee_correlation_score']:.1f} ({row.get('committee_name', 'N/A')})")

    print("\n" + "=" * 80)
    print("✓ High-Value Transactions aggregate complete")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
