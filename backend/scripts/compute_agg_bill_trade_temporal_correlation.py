#!/usr/bin/env python3
"""
Compute bill-trade temporal correlation aggregate.

Analyzes temporal proximity between:
- Stock transactions (PTRs)
- Bill introductions, votes, and committee activity

Correlation Windows: ±7, ±14, ±30 days

Temporal Correlation Score (0.0-1.0):
- 0.0 = No correlation or data
- 0.3-0.5 = Weak correlation (30-day window, general policy area)
- 0.6-0.8 = Moderate correlation (14-day window, specific industry)
- 0.9-1.0 = Strong correlation (7-day window, direct asset-bill match)

Output: Parquet file with correlation records
"""

import pandas as pd
from datetime import datetime, timedelta
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.lib.ingestion.s3_utils import upload_file_to_s3
from backend.lib.ingestion.s3_path_registry import S3Paths

BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

# Temporal windows (days before/after bill event)
CORRELATION_WINDOWS = [7, 14, 30]


def load_transactions() -> pd.DataFrame:
    """Load all PTR transactions from Gold fact table."""
    try:
        s3_path = f"s3://{BUCKET}/data/gold/facts/fact_transactions/"
        print(f"Loading transactions from {s3_path}")
        df = pd.read_parquet(s3_path)
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        print(f"Loaded {len(df):,} transactions")
        return df
    except Exception as e:
        print(f"Error loading transactions: {e}")
        return pd.DataFrame()


def load_bills() -> pd.DataFrame:
    """Load Congress.gov bills data from Silver layer."""
    # TODO: Once Congress API is integrated, load from Silver
    # Path: s3://bucket/data/silver/congress_api/bills/
    print("⚠ Congress.gov bills data not yet available (requires Congress API integration)")

    # Return empty DataFrame with expected schema
    return pd.DataFrame(columns=[
        'bill_id', 'congress', 'bill_type', 'bill_number',
        'sponsor_bioguide_id', 'introduced_date', 'title', 'policy_area'
    ])


def load_bill_actions() -> pd.DataFrame:
    """Load bill actions (votes, committee activity) from Silver layer."""
    # TODO: Load from Silver congress_api/bill_actions/
    print("⚠ Bill actions data not yet available (requires Congress API integration)")

    return pd.DataFrame(columns=[
        'bill_id', 'action_date', 'action_type', 'description'
    ])


def find_temporal_correlations(
    df_trans: pd.DataFrame,
    df_bills: pd.DataFrame,
    df_actions: pd.DataFrame
) -> pd.DataFrame:
    """Find temporal correlations between trades and bill activity."""

    if len(df_trans) == 0 or len(df_bills) == 0:
        print("Insufficient data for correlation analysis")
        return pd.DataFrame()

    correlations = []

    # For each bill introduction
    for _, bill in df_bills.iterrows():
        bill_date = pd.to_datetime(bill['introduced_date'])
        sponsor = bill['sponsor_bioguide_id']

        # Check each correlation window
        for window_days in CORRELATION_WINDOWS:
            delta = timedelta(days=window_days)

            # Find trades by sponsor within window
            trades = df_trans[
                (df_trans['bioguide_id'] == sponsor) &
                (df_trans['transaction_date'] >= bill_date - delta) &
                (df_trans['transaction_date'] <= bill_date + delta)
            ]

            for _, trade in trades.iterrows():
                days_diff = (trade['transaction_date'] - bill_date).days

                # Calculate temporal correlation score
                temporal_score = calculate_temporal_score(
                    days_diff, window_days, 'introduction',
                    bill.get('policy_area'), trade.get('asset_name')
                )

                correlations.append({
                    'bioguide_id': sponsor,
                    'bill_id': bill['bill_id'],
                    'bill_title': bill['title'],
                    'bill_policy_area': bill.get('policy_area'),
                    'bill_event_type': 'introduction',
                    'bill_event_date': bill_date,
                    'transaction_date': trade['transaction_date'],
                    'transaction_type': trade['transaction_type'],
                    'asset_name': trade['asset_name'],
                    'ticker': trade.get('ticker'),
                    'amount_low': trade.get('amount_low'),
                    'amount_high': trade.get('amount_high'),
                    'days_difference': days_diff,
                    'correlation_window_days': window_days,
                    'is_before_event': days_diff < 0,
                    'is_after_event': days_diff > 0,
                    'temporal_correlation_score': temporal_score
                })

    # Repeat for bill actions (votes, committee activity)
    for _, action in df_actions.iterrows():
        action_date = pd.to_datetime(action['action_date'])

        # Find bill sponsor for this action
        bill = df_bills[df_bills['bill_id'] == action['bill_id']]
        if len(bill) == 0:
            continue
        bill = bill.iloc[0]
        sponsor = bill['sponsor_bioguide_id']

        for window_days in CORRELATION_WINDOWS:
            delta = timedelta(days=window_days)

            trades = df_trans[
                (df_trans['bioguide_id'] == sponsor) &
                (df_trans['transaction_date'] >= action_date - delta) &
                (df_trans['transaction_date'] <= action_date + delta)
            ]

            for _, trade in trades.iterrows():
                days_diff = (trade['transaction_date'] - action_date).days

                temporal_score = calculate_temporal_score(
                    days_diff, window_days, action['action_type'],
                    bill.get('policy_area'), trade.get('asset_name')
                )

                correlations.append({
                    'bioguide_id': sponsor,
                    'bill_id': bill['bill_id'],
                    'bill_title': bill['title'],
                    'bill_policy_area': bill.get('policy_area'),
                    'bill_event_type': action['action_type'],
                    'bill_event_date': action_date,
                    'transaction_date': trade['transaction_date'],
                    'transaction_type': trade['transaction_type'],
                    'asset_name': trade['asset_name'],
                    'ticker': trade.get('ticker'),
                    'amount_low': trade.get('amount_low'),
                    'amount_high': trade.get('amount_high'),
                    'days_difference': days_diff,
                    'correlation_window_days': window_days,
                    'is_before_event': days_diff < 0,
                    'is_after_event': days_diff > 0,
                    'temporal_correlation_score': temporal_score
                })

    if len(correlations) == 0:
        print("No temporal correlations found")
        return pd.DataFrame()

    df_corr = pd.DataFrame(correlations)
    df_corr = df_corr.sort_values('temporal_correlation_score', ascending=False)
    df_corr['computed_at'] = datetime.utcnow().isoformat()

    return df_corr


def calculate_temporal_score(
    days_diff: int,
    window_days: int,
    event_type: str,
    policy_area: str,
    asset_name: str
) -> float:
    """
    Calculate temporal correlation score (0.0-1.0).

    Factors:
    1. Temporal proximity (closer = higher score)
    2. Event timing (before vote = higher concern)
    3. Policy-asset relevance (industry match = higher score)
    """

    score = 0.0

    # Base score from temporal proximity
    abs_days = abs(days_diff)

    if window_days == 7:
        # 7-day window: 0.6-0.9 base score
        proximity_score = 0.9 - (abs_days / 7) * 0.3
    elif window_days == 14:
        # 14-day window: 0.4-0.7 base score
        proximity_score = 0.7 - (abs_days / 14) * 0.3
    else:  # 30-day window
        # 30-day window: 0.2-0.5 base score
        proximity_score = 0.5 - (abs_days / 30) * 0.3

    score += proximity_score

    # Bonus for trades BEFORE votes (potential insider trading indicator)
    if days_diff < 0 and event_type in ['vote', 'floor_action', 'committee_vote']:
        score += 0.2

    # Bonus for policy-asset relevance
    if policy_area and asset_name:
        relevance = calculate_policy_asset_relevance(policy_area, asset_name)
        score += relevance * 0.3

    # Normalize to 0.0-1.0
    return min(max(score, 0.0), 1.0)


def calculate_policy_asset_relevance(policy_area: str, asset_name: str) -> float:
    """Calculate relevance between bill policy area and traded asset (0.0-1.0)."""

    if not policy_area or not asset_name:
        return 0.0

    policy_lower = policy_area.lower()
    asset_lower = asset_name.lower()

    # Direct matches (1.0)
    direct_matches = {
        'health': ['pfizer', 'johnson', 'merck', 'unitedhealth', 'cvs', 'humana', 'healthcare'],
        'energy': ['exxon', 'chevron', 'conocophillips', 'shell', 'bp', 'energy'],
        'defense': ['lockheed', 'raytheon', 'northrop', 'general dynamics', 'boeing'],
        'technology': ['apple', 'microsoft', 'google', 'alphabet', 'meta', 'amazon', 'nvidia', 'intel'],
        'finance': ['jpmorgan', 'bank of america', 'wells fargo', 'citigroup', 'goldman sachs'],
        'telecommunications': ['verizon', 'at&t', 'comcast', 't-mobile']
    }

    for policy_key, asset_keywords in direct_matches.items():
        if policy_key in policy_lower:
            for keyword in asset_keywords:
                if keyword in asset_lower:
                    return 1.0

    # Partial matches (0.5)
    partial_matches = {
        'finance': ['financial', 'banking'],
        'health': ['pharmaceutical', 'medical', 'biotech'],
        'technology': ['tech', 'software', 'semiconductor'],
        'energy': ['oil', 'gas', 'renewable']
    }

    for policy_key, policy_keywords in partial_matches.items():
        if any(kw in policy_lower for kw in policy_keywords):
            if policy_key in ['finance', 'financial', 'banking'] and any(kw in asset_lower for kw in ['bank', 'financial', 'capital']):
                return 0.5
            elif policy_key in ['health', 'pharmaceutical'] and any(kw in asset_lower for kw in ['health', 'pharma', 'medical']):
                return 0.5
            elif policy_key in ['technology', 'tech'] and 'tech' in asset_lower:
                return 0.5
            elif policy_key in ['energy', 'oil'] and 'energy' in asset_lower:
                return 0.5

    return 0.0


def main():
    """Main execution."""
    print("=" * 80)
    print("Bill-Trade Temporal Correlation Aggregate")
    print("=" * 80)

    print("\n1. Loading data...")
    df_trans = load_transactions()
    df_bills = load_bills()
    df_actions = load_bill_actions()

    if len(df_trans) == 0:
        print("ERROR: No transaction data available")
        return 1

    if len(df_bills) == 0:
        print("⚠ No bill data available yet")
        print("  This analysis requires Congress.gov API integration")
        print("  Creating empty correlation file for consistency...")

        # Create empty output
        empty_df = pd.DataFrame(columns=[
            'bioguide_id', 'bill_id', 'bill_title', 'bill_policy_area',
            'bill_event_type', 'bill_event_date', 'transaction_date',
            'transaction_type', 'asset_name', 'ticker', 'amount_low', 'amount_high',
            'days_difference', 'correlation_window_days',
            'is_before_event', 'is_after_event', 'temporal_correlation_score',
            'computed_at'
        ])

        output_path = "data/gold/aggregates/bill_trade_correlation/temporal_correlations.parquet"
        local_path = "/tmp/bill_trade_correlations.parquet"

        empty_df.to_parquet(local_path, index=False, compression='snappy')
        upload_file_to_s3(local_path, BUCKET, output_path)

        print(f"✓ Created empty correlation file at s3://{BUCKET}/{output_path}")
        print("\nℹ To enable this analysis:")
        print("  1. Integrate Congress.gov API (see docs/plans/)")
        print("  2. Populate Silver layer with bills and actions")
        print("  3. Re-run this script")
        return 0

    print(f"\n2. Analyzing temporal correlations...")
    print(f"   - {len(df_trans):,} transactions")
    print(f"   - {len(df_bills):,} bills")
    print(f"   - {len(df_actions):,} bill actions")

    df_corr = find_temporal_correlations(df_trans, df_bills, df_actions)

    if len(df_corr) == 0:
        print("No correlations found")
        return 0

    print(f"\n3. Found {len(df_corr):,} temporal correlations")

    # Summary by window
    print("\n4. Correlations by Time Window:")
    for window in CORRELATION_WINDOWS:
        count = len(df_corr[df_corr['correlation_window_days'] == window])
        print(f"   ±{window} days: {count:,} correlations")

    # Summary by score
    high_score = len(df_corr[df_corr['temporal_correlation_score'] >= 0.7])
    med_score = len(df_corr[(df_corr['temporal_correlation_score'] >= 0.4) & (df_corr['temporal_correlation_score'] < 0.7)])
    low_score = len(df_corr[df_corr['temporal_correlation_score'] < 0.4])

    print("\n5. Correlations by Score:")
    print(f"   High (≥0.7):  {high_score:,}")
    print(f"   Medium (0.4-0.7): {med_score:,}")
    print(f"   Low (<0.4):   {low_score:,}")

    # Upload to S3
    print("\n6. Uploading to S3...")
    output_path = "data/gold/aggregates/bill_trade_correlation/temporal_correlations.parquet"
    local_path = "/tmp/bill_trade_correlations.parquet"

    df_corr.to_parquet(local_path, index=False, compression='snappy')
    upload_file_to_s3(local_path, BUCKET, output_path)

    print(f"   ✓ Uploaded to s3://{BUCKET}/{output_path}")

    # Top correlations
    print("\n7. Top 5 Temporal Correlations (by score):")
    for _, row in df_corr.head(5).iterrows():
        print(f"\n   Score: {row['temporal_correlation_score']:.2f}")
        print(f"   {row['bioguide_id']}: Traded {row['asset_name']}")
        print(f"   {row['days_difference']:+d} days from {row['bill_event_type']} on:")
        print(f"   {row['bill_title'][:80]}...")
        if row.get('bill_policy_area'):
            print(f"   Policy Area: {row['bill_policy_area']}")

    print("\n" + "=" * 80)
    print("✓ Bill-trade temporal correlation aggregate complete")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
