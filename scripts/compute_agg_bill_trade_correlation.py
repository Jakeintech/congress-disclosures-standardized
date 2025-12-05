#!/usr/bin/env python3
"""
Compute bill-trade correlation scores.

Analyzes correlation between:
- Member stock trades
- Bill sponsorship/cosponsorship
- Industry overlap
- Time proximity
- Committee assignments

Output: gold/congress/agg_bill_trade_correlation/congress={congress}/
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
from io import BytesIO
from datetime import datetime, timedelta
from typing import List, Dict
import logging
import argparse

# Import our libraries
from ingestion.lib.ticker_industry_mapper import TickerIndustryMapper

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


def calculate_correlation_score(
    trade_date: pd.Timestamp,
    bill_action_date: pd.Timestamp,
    trade_ticker: str,
    bill_industries: List[str],
    bill_tickers: List[str],
    member_role: str,
    committee_overlap: bool,
    ticker_mapper: TickerIndustryMapper
) -> Dict[str, any]:
    """
    Calculate correlation score using the Epic 2 algorithm.

    Score breakdown:
    - Time proximity (0-50 points): How close trade was to bill action
    - Industry match (0-30 points): Ticker/industry overlap
    - Role weight (0-10 points): Sponsor vs cosponsor
    - Committee overlap (0-10 points): Member on bill committee

    Total: 0-100 points
    """
    score = 0
    score_breakdown = {}

    # 1. Time proximity (0-50 points)
    days_offset = abs((trade_date - bill_action_date).days)

    if days_offset <= 30:
        time_score = 50
    elif days_offset <= 60:
        time_score = 30
    elif days_offset <= 90:
        time_score = 15
    else:
        time_score = 0

    score += time_score
    score_breakdown['time_proximity'] = time_score
    score_breakdown['days_offset'] = days_offset

    # 2. Industry/ticker match (0-30 points)
    industry_score = 0

    # Direct ticker mention in bill
    if trade_ticker in bill_tickers:
        industry_score = 30
        score_breakdown['match_type'] = 'ticker_exact'
    else:
        # Industry overlap
        ticker_industries = ticker_mapper.get_all_industries(trade_ticker)
        industry_overlaps = set(ticker_industries) & set(bill_industries)

        if industry_overlaps:
            # Check if primary industry matches
            primary_industry = ticker_mapper.get_primary_industry(trade_ticker)
            if primary_industry in bill_industries:
                industry_score = 20
                score_breakdown['match_type'] = 'industry_primary'
            else:
                industry_score = 10
                score_breakdown['match_type'] = 'industry_secondary'

            score_breakdown['matched_industries'] = list(industry_overlaps)
        else:
            score_breakdown['match_type'] = 'none'

    score += industry_score
    score_breakdown['industry_match'] = industry_score

    # 3. Role weight (0-10 points)
    if member_role == 'sponsor':
        role_score = 10
    elif member_role == 'cosponsor':
        role_score = 5
    else:
        role_score = 0

    score += role_score
    score_breakdown['role_weight'] = role_score

    # 4. Committee overlap (0-10 points)
    committee_score = 10 if committee_overlap else 0
    score += committee_score
    score_breakdown['committee_overlap'] = committee_score

    score_breakdown['total_score'] = score

    return score_breakdown


def load_committee_assignments(s3_client) -> pd.DataFrame:
    """
    Load bill committee assignments from Bronze layer.

    Returns DataFrame with bill_id and committee_name.
    """
    try:
        logger.info("Loading bill committee assignments...")
        committees_df = read_parquet_from_s3(s3_client, 'bronze/congress/bill_committees/')

        if not committees_df.empty and 'committees' in committees_df.columns:
            # Expand committees (may be nested)
            expanded = []
            for _, row in committees_df.iterrows():
                bill_id = row.get('bill_id')
                committees = row.get('committees', [])

                if isinstance(committees, list):
                    for committee in committees:
                        if isinstance(committee, dict):
                            expanded.append({
                                'bill_id': bill_id,
                                'committee_name': committee.get('name', ''),
                                'activity_date': committee.get('activity_date')
                            })

            if expanded:
                return pd.DataFrame(expanded)

        logger.warning("No committee data found")
        return pd.DataFrame()

    except Exception as e:
        logger.warning(f"Could not load committee data: {e}")
        return pd.DataFrame()


def compute_correlations(congress_filter: int = None, min_score: int = 15) -> pd.DataFrame:
    """
    Compute bill-trade correlations.

    Args:
        congress_filter: Only process specific congress
        min_score: Minimum correlation score threshold

    Returns:
        DataFrame with correlation records
    """
    s3 = boto3.client('s3')
    ticker_mapper = TickerIndustryMapper()

    # 1. Load bill industry tags
    logger.info("Loading bill industry tags...")
    industry_tags_df = read_parquet_from_s3(s3, 'gold/congress/bill_industry_tags/')

    if industry_tags_df.empty:
        logger.error("No bill industry tags found. Run analyze_bill_industry_impact.py first.")
        return pd.DataFrame()

    logger.info(f"Loaded {len(industry_tags_df)} industry tags for {industry_tags_df['bill_id'].nunique()} bills")

    # 2. Load member-bill roles
    logger.info("Loading member-bill relationships...")
    member_bill_df = read_parquet_from_s3(s3, 'gold/congress/fact_member_bill_role/')

    if member_bill_df.empty:
        logger.error("No member-bill relationships found")
        return pd.DataFrame()

    logger.info(f"Loaded {len(member_bill_df)} member-bill relationships")

    # 3. Load bill actions for dates
    logger.info("Loading bill actions...")
    actions_df = read_parquet_from_s3(s3, 'silver/congress/bill_actions/')

    if actions_df.empty:
        logger.warning("No bill actions found, using introduced dates")
        actions_df = pd.DataFrame()
    else:
        logger.info(f"Loaded {len(actions_df)} bill actions")

    # 4. Load PTR transactions
    logger.info("Loading PTR transactions...")
    transactions_df = read_parquet_from_s3(s3, 'gold/house/financial/fact_ptr_transactions/')

    if transactions_df.empty:
        logger.error("No PTR transactions found")
        return pd.DataFrame()

    logger.info(f"Loaded {len(transactions_df)} transactions")

    # 5. Load committee assignments (optional)
    committees_df = load_committee_assignments(s3)

    # Filter by congress if specified
    if congress_filter:
        industry_tags_df = industry_tags_df[industry_tags_df['congress'] == congress_filter]
        member_bill_df = member_bill_df[member_bill_df['congress'] == congress_filter]
        actions_df = actions_df[actions_df['congress'] == congress_filter] if not actions_df.empty else actions_df
        logger.info(f"Filtered to congress {congress_filter}")

    # Prepare industry tags (aggregate by bill)
    logger.info("Aggregating industry tags by bill...")
    bill_industries = industry_tags_df.groupby('bill_id').agg({
        'industry': lambda x: list(x),
        'tickers': lambda x: ','.join([t for t in x if pd.notna(t)]),
        'confidence_score': 'max'
    }).reset_index()

    # Split tickers into list
    bill_industries['ticker_list'] = bill_industries['tickers'].apply(
        lambda x: [t.strip() for t in x.split(',') if t.strip()] if x else []
    )

    # Get latest action date per bill
    logger.info("Finding latest action dates...")
    if not actions_df.empty:
        actions_df['action_date'] = pd.to_datetime(actions_df['action_date'], errors='coerce')
        latest_actions = actions_df.groupby('bill_id')['action_date'].max().reset_index()
        latest_actions.rename(columns={'action_date': 'latest_action_date'}, inplace=True)
    else:
        # Fallback to introduced date from member_bill
        latest_actions = member_bill_df[['bill_id', 'action_date']].drop_duplicates()
        latest_actions['action_date'] = pd.to_datetime(latest_actions['action_date'], errors='coerce')
        latest_actions = latest_actions.groupby('bill_id')['action_date'].max().reset_index()
        latest_actions.rename(columns={'action_date': 'latest_action_date'}, inplace=True)

    # Join member-bill with industry tags and action dates
    logger.info("Joining datasets...")
    correlations_base = member_bill_df.merge(
        bill_industries[['bill_id', 'industry', 'ticker_list']],
        on='bill_id',
        how='inner'
    )

    correlations_base = correlations_base.merge(
        latest_actions,
        on='bill_id',
        how='left'
    )

    # Join with transactions
    transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'], errors='coerce')

    correlations = correlations_base.merge(
        transactions_df[['bioguide_id', 'ticker', 'transaction_date', 'transaction_type', 'amount_description', 'doc_id']],
        on='bioguide_id',
        how='inner'
    )

    logger.info(f"Found {len(correlations)} potential correlations to score")

    # Calculate scores
    logger.info("Calculating correlation scores...")
    correlation_records = []

    for idx, row in correlations.iterrows():
        if idx % 1000 == 0:
            logger.info(f"  Scored {idx}/{len(correlations)} correlations...")

        # Check committee overlap (if data available)
        committee_overlap = False
        if not committees_df.empty:
            member_on_committee = False  # TODO: Need member committee assignments
            committee_overlap = member_on_committee

        # Calculate score
        score_result = calculate_correlation_score(
            trade_date=row['transaction_date'],
            bill_action_date=row['latest_action_date'],
            trade_ticker=row['ticker'],
            bill_industries=row['industry'],
            bill_tickers=row['ticker_list'],
            member_role=row['role'],
            committee_overlap=committee_overlap,
            ticker_mapper=ticker_mapper
        )

        # Filter by minimum score
        if score_result['total_score'] < min_score:
            continue

        # Build record
        record = {
            'bill_id': row['bill_id'],
            'congress': row['congress'],
            'bioguide_id': row['bioguide_id'],
            'ticker': row['ticker'],
            'trade_date': row['transaction_date'].strftime('%Y-%m-%d'),
            'trade_type': row['transaction_type'],
            'amount_range': row['amount_description'],
            'bill_action_date': row['latest_action_date'].strftime('%Y-%m-%d') if pd.notna(row['latest_action_date']) else None,
            'days_offset': score_result['days_offset'],
            'correlation_score': score_result['total_score'],
            'member_role': row['role'],
            'committee_overlap': committee_overlap,
            'match_type': score_result.get('match_type', 'none'),
            'matched_industries': ','.join(score_result.get('matched_industries', [])),
            'score_breakdown': str(score_result),
            'created_at': datetime.utcnow().isoformat()
        }

        correlation_records.append(record)

    if not correlation_records:
        logger.warning("No correlations met minimum score threshold")
        return pd.DataFrame()

    df = pd.DataFrame(correlation_records)
    logger.info(f"Generated {len(df)} correlations above threshold")

    return df


def write_gold_parquet_partitioned(df: pd.DataFrame, prefix: str, partition_col: str):
    """Write DataFrame to Gold layer partitioned by column."""
    s3 = boto3.client('s3')

    if partition_col not in df.columns:
        logger.error(f"Partition column '{partition_col}' not found")
        return

    for partition_value in sorted(df[partition_col].unique()):
        partition_df = df[df[partition_col] == partition_value].copy()
        s3_key = f"{prefix}/{partition_col}={partition_value}/part-0000.parquet"

        buffer = BytesIO()
        partition_df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
        buffer.seek(0)

        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
        logger.info(f"Wrote {len(partition_df)} records to s3://{BUCKET_NAME}/{s3_key}")


def main():
    parser = argparse.ArgumentParser(description='Compute bill-trade correlations')
    parser.add_argument(
        '--congress',
        type=int,
        help='Process specific congress only (e.g., 118, 119)'
    )
    parser.add_argument(
        '--min-score',
        type=int,
        default=15,
        help='Minimum correlation score threshold (default: 15)'
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("Bill-Trade Correlation Analysis")
    logger.info("=" * 80)

    # Compute correlations
    df = compute_correlations(
        congress_filter=args.congress,
        min_score=args.min_score
    )

    if df.empty:
        logger.error("No correlations to write")
        return

    # Summary statistics
    logger.info("\n" + "=" * 80)
    logger.info("Summary Statistics")
    logger.info("=" * 80)
    logger.info(f"Total correlations: {len(df)}")
    logger.info(f"Unique bills: {df['bill_id'].nunique()}")
    logger.info(f"Unique members: {df['bioguide_id'].nunique()}")
    logger.info(f"Unique tickers: {df['ticker'].nunique()}")

    logger.info(f"\nScore distribution:")
    logger.info(f"  High (70-100): {(df['correlation_score'] >= 70).sum()}")
    logger.info(f"  Medium (40-69): {((df['correlation_score'] >= 40) & (df['correlation_score'] < 70)).sum()}")
    logger.info(f"  Low (15-39): {(df['correlation_score'] < 40).sum()}")

    logger.info(f"\nTop 10 correlations by score:")
    top_10 = df.nlargest(10, 'correlation_score')[['bioguide_id', 'bill_id', 'ticker', 'correlation_score', 'days_offset']]
    for _, row in top_10.iterrows():
        logger.info(f"  {row['bioguide_id']} | {row['bill_id']} | {row['ticker']} | Score: {row['correlation_score']} | Days: {row['days_offset']}")

    # Write to Gold
    logger.info("\nWriting to Gold layer...")
    write_gold_parquet_partitioned(
        df,
        'gold/congress/agg_bill_trade_correlation',
        'congress'
    )

    logger.info("\n✅ Bill-trade correlation analysis complete!")
    logger.info(f"Output: s3://{BUCKET_NAME}/gold/congress/agg_bill_trade_correlation/")


if __name__ == '__main__':
    main()
