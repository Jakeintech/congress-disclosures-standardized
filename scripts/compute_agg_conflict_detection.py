#!/usr/bin/env python3
"""
Conflict of Interest Detection Engine.

Automated detection and scoring of potential conflicts between:
1. Member trading activity
2. Bill sponsorship/cosponsorship
3. Committee assignments
4. Industry overlap

Conflict Score (0-100):
- Time proximity (0-40): Trade within 30/60/90 days of bill action
- Industry match (0-25): Direct ticker or sector overlap
- Role weight (0-20): Sponsor > Cosponsor > Committee member
- Trade size (0-15): Larger trades = higher concern

Output: gold/aggregates/agg_conflict_detection/
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
from typing import Dict, List, Optional, Tuple
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
            response_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
            df = pd.read_parquet(BytesIO(response_obj['Body'].read()))
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


def load_local_data(table_name: str, base_path: str = 'data/gold') -> pd.DataFrame:
    """Load data from local gold layer."""
    path = Path(base_path) / table_name
    if not path.exists():
        # Try alternative paths
        alt_paths = [
            Path('data/gold/house/financial/facts') / table_name,
            Path('data/gold/congress') / table_name,
            Path('data/gold/dimensions') / table_name,
            Path('data/gold/aggregates') / table_name,
        ]
        for alt_path in alt_paths:
            if alt_path.exists():
                path = alt_path
                break
        else:
            logger.warning(f"Table not found: {table_name}")
            return pd.DataFrame()
    
    files = list(path.glob("**/*.parquet"))
    if not files:
        return pd.DataFrame()
    
    return pd.concat([pd.read_parquet(f) for f in files])


def classify_industry(asset_description: str) -> str:
    """Classify asset into industry sector."""
    if pd.isna(asset_description):
        return 'Other'
    
    desc = str(asset_description).upper()
    
    industry_keywords = {
        'Technology': ['TECH', 'SOFTWARE', 'APPLE', 'MICROSOFT', 'GOOGLE', 'NVIDIA', 'META', 'AMAZON', 'SEMICONDUCTOR'],
        'Healthcare': ['PHARMA', 'DRUG', 'BIOTECH', 'HEALTH', 'MEDICAL', 'PFIZER', 'JOHNSON', 'MERCK', 'MODERNA'],
        'Financials': ['BANK', 'FINANCIAL', 'JPMORGAN', 'GOLDMAN', 'INSURANCE', 'CAPITAL', 'CREDIT'],
        'Energy': ['ENERGY', 'OIL', 'GAS', 'EXXON', 'CHEVRON', 'PETRO', 'SOLAR', 'WIND'],
        'Defense': ['DEFENSE', 'AEROSPACE', 'BOEING', 'LOCKHEED', 'RAYTHEON', 'MILITARY', 'NORTHROP'],
        'Telecom': ['TELECOM', 'VERIZON', 'AT&T', 'T-MOBILE', 'WIRELESS'],
        'Consumer': ['RETAIL', 'CONSUMER', 'WALMART', 'TARGET', 'AMAZON', 'FOOD'],
        'Real Estate': ['REAL ESTATE', 'REIT', 'PROPERTY', 'HOUSING'],
        'Transportation': ['AIRLINE', 'TRANSPORT', 'RAIL', 'SHIPPING', 'LOGISTICS'],
        'Utilities': ['UTILITY', 'ELECTRIC', 'WATER', 'POWER'],
    }
    
    for industry, keywords in industry_keywords.items():
        if any(kw in desc for kw in keywords):
            return industry
    
    return 'Other'


def calculate_conflict_score(
    trade_date: datetime,
    bill_action_date: datetime,
    trade_industry: str,
    bill_industries: List[str],
    member_role: str,
    trade_amount: float,
    is_committee_member: bool = False
) -> Dict:
    """
    Calculate conflict of interest score.
    
    Returns dict with:
    - total_score (0-100)
    - time_score (0-40)
    - industry_score (0-25)
    - role_score (0-20)
    - size_score (0-15)
    - severity: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    """
    score = 0
    breakdown = {}
    
    # 1. Time Proximity (0-40 points)
    days_offset = abs((trade_date - bill_action_date).days )
    
    if days_offset <= 7:
        time_score = 40
    elif days_offset <= 14:
        time_score = 35
    elif days_offset <= 30:
        time_score = 25
    elif days_offset <= 60:
        time_score = 15
    elif days_offset <= 90:
        time_score = 8
    else:
        time_score = 0
    
    score += time_score
    breakdown['time_score'] = time_score
    breakdown['days_offset'] = days_offset
    
    # 2. Industry Match (0-25 points)
    industry_score = 0
    matched_industry = None
    
    if trade_industry in bill_industries:
        industry_score = 25
        matched_industry = trade_industry
    elif trade_industry != 'Other':
        # Check for related industries
        related_mappings = {
            'Technology': ['Telecom'],
            'Healthcare': ['Biotech'],
            'Energy': ['Utilities'],
            'Defense': ['Aerospace'],
        }
        for ind in bill_industries:
            if trade_industry in related_mappings.get(ind, []) or ind in related_mappings.get(trade_industry, []):
                industry_score = 15
                matched_industry = ind
                break
    
    score += industry_score
    breakdown['industry_score'] = industry_score
    breakdown['matched_industry'] = matched_industry
    
    # 3. Role Weight (0-20 points)
    role_scores = {
        'sponsor': 20,
        'cosponsor': 12,
        'committee': 8,
        'subcommittee': 6,
        'other': 2,
    }
    role_score = role_scores.get(str(member_role).lower(), 2)
    
    if is_committee_member:
        role_score = max(role_score, 8)
    
    score += role_score
    breakdown['role_score'] = role_score
    
    # 4. Trade Size (0-15 points)
    if trade_amount >= 500000:
        size_score = 15
    elif trade_amount >= 250000:
        size_score = 12
    elif trade_amount >= 100000:
        size_score = 9
    elif trade_amount >= 50000:
        size_score = 6
    elif trade_amount >= 15000:
        size_score = 3
    else:
        size_score = 1
    
    score += size_score
    breakdown['size_score'] = size_score
    
    # Determine severity
    if score >= 80:
        severity = 'CRITICAL'
    elif score >= 60:
        severity = 'HIGH'
    elif score >= 40:
        severity = 'MEDIUM'
    else:
        severity = 'LOW'
    
    breakdown['total_score'] = score
    breakdown['severity'] = severity
    
    return breakdown


def compute_conflict_detection(
    transactions_df: pd.DataFrame,
    member_bill_df: pd.DataFrame,
    bill_actions_df: pd.DataFrame,
    members_df: pd.DataFrame,
    min_score: int = 30
) -> pd.DataFrame:
    """
    Compute conflicts between trades and bills.
    """
    logger.info("Computing conflict detection...")
    
    if transactions_df.empty or member_bill_df.empty:
        logger.warning("Missing required data")
        return pd.DataFrame()
    
    # Prepare transaction data
    if 'transaction_date' not in transactions_df.columns:
        if 'transaction_date_key' in transactions_df.columns:
            transactions_df['transaction_date'] = pd.to_datetime(
                transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce'
            )
    else:
        transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'], errors='coerce')
    
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    # Classify industries
    transactions_df['trade_industry'] = transactions_df.get('asset_description', '').apply(classify_industry)
    
    # Get member bioguide mapping
    bioguide_col = None
    for col in ['member_bioguide_id', 'bioguide_id', 'bioguide']:
        if col in transactions_df.columns:
            bioguide_col = col
            break
    
    if not bioguide_col:
        logger.warning("No bioguide ID column found in transactions")
        return pd.DataFrame()
    
    conflicts = []
    
    # For each member with trades
    for member_id in transactions_df[bioguide_col].unique():
        member_trades = transactions_df[transactions_df[bioguide_col] == member_id]
        
        # Get bills this member is associated with
        bill_col = None
        for col in ['member_bioguide_id', 'bioguide_id', 'bioguide']:
            if col in member_bill_df.columns:
                bill_col = col
                break
        
        if not bill_col:
            continue
        
        member_bills = member_bill_df[member_bill_df[bill_col] == member_id]
        
        if member_bills.empty:
            continue
        
        for _, trade in member_trades.iterrows():
            trade_date = trade['transaction_date']
            
            if pd.isna(trade_date):
                continue
            
            for _, bill in member_bills.iterrows():
                bill_id = bill.get('bill_id', '')
                
                # Get bill action date
                bill_date = None
                if not bill_actions_df.empty:
                    bill_actions = bill_actions_df[bill_actions_df['bill_id'] == bill_id]
                    if not bill_actions.empty:
                        date_col = 'latest_action_date' if 'latest_action_date' in bill_actions.columns else 'action_date'
                        if date_col in bill_actions.columns:
                            bill_date = pd.to_datetime(bill_actions.iloc[0][date_col], errors='coerce')
                
                if bill_date is None:
                    bill_date = pd.to_datetime(bill.get('action_date', bill.get('introduced_date', '')), errors='coerce')
                
                if pd.isna(bill_date):
                    continue
                
                # Check if within 90 day window
                days_diff = abs((trade_date - bill_date).days)
                if days_diff > 90:
                    continue
                
                # Infer bill industries from title/subject
                bill_title = str(bill.get('bill_title', bill.get('title', '')))
                bill_industries = [classify_industry(bill_title)]
                
                # Calculate conflict score
                score_result = calculate_conflict_score(
                    trade_date=trade_date,
                    bill_action_date=bill_date,
                    trade_industry=trade['trade_industry'],
                    bill_industries=bill_industries,
                    member_role=bill.get('role_type', bill.get('role', 'other')),
                    trade_amount=trade['amount_midpoint'],
                )
                
                if score_result['total_score'] < min_score:
                    continue
                
                # Build conflict record
                conflict = {
                    'member_bioguide_id': member_id,
                    'bill_id': bill_id,
                    'bill_title': bill_title[:200] if bill_title else '',
                    'ticker': trade.get('ticker', ''),
                    'asset_description': trade.get('asset_description', '')[:100],
                    'transaction_type': trade.get('transaction_type', ''),
                    'trade_date': trade_date.strftime('%Y-%m-%d'),
                    'bill_action_date': bill_date.strftime('%Y-%m-%d'),
                    'amount_display': trade.get('amount_description', trade.get('amount_display', '')),
                    'amount_midpoint': trade['amount_midpoint'],
                    'trade_industry': trade['trade_industry'],
                    'member_role': bill.get('role_type', bill.get('role', '')),
                    'conflict_score': score_result['total_score'],
                    'severity': score_result['severity'],
                    'days_offset': score_result['days_offset'],
                    'time_score': score_result['time_score'],
                    'industry_score': score_result['industry_score'],
                    'role_score': score_result['role_score'],
                    'size_score': score_result['size_score'],
                    'matched_industry': score_result.get('matched_industry', ''),
                }
                
                conflicts.append(conflict)
    
    if not conflicts:
        logger.warning("No conflicts detected above threshold")
        return pd.DataFrame()
    
    conflicts_df = pd.DataFrame(conflicts)
    
    # Add member names
    if not members_df.empty:
        name_col = None
        for col in ['bioguide_id', 'member_bioguide_id', 'member_key']:
            if col in members_df.columns:
                name_col = col
                break
        
        if name_col:
            name_fields = [name_col]
            for col in ['full_name', 'name', 'first_name', 'last_name', 'party', 'state']:
                if col in members_df.columns:
                    name_fields.append(col)
            
            conflicts_df = conflicts_df.merge(
                members_df[name_fields].drop_duplicates(),
                left_on='member_bioguide_id',
                right_on=name_col,
                how='left'
            )
            
            # Create name field
            if 'full_name' in conflicts_df.columns:
                conflicts_df['member_name'] = conflicts_df['full_name']
            elif 'name' in conflicts_df.columns:
                conflicts_df['member_name'] = conflicts_df['name']
            else:
                conflicts_df['member_name'] = conflicts_df['member_bioguide_id']
    
    # Add metadata
    conflicts_df['dt_computed'] = datetime.utcnow().isoformat()
    
    # Sort by score
    conflicts_df = conflicts_df.sort_values('conflict_score', ascending=False)
    
    logger.info(f"Detected {len(conflicts_df)} conflicts above threshold {min_score}")
    return conflicts_df


def write_to_s3(df: pd.DataFrame, severity: str = 'all'):
    """Write conflicts to S3."""
    if df.empty:
        logger.warning(f"No data to write")
        return
    
    s3 = boto3.client('s3')
    s3_key = f'gold/aggregates/agg_conflict_detection/severity={severity}/part-0000.parquet'
    
    buffer = BytesIO()
    df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
    buffer.seek(0)
    
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
    logger.info(f"Wrote {len(df)} records to s3://{BUCKET_NAME}/{s3_key}")


def write_to_local(df: pd.DataFrame, severity: str = 'all'):
    """Write conflicts to local gold layer."""
    if df.empty:
        logger.warning(f"No data to write")
        return
    
    output_dir = Path(f'data/gold/aggregates/agg_conflict_detection/severity={severity}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
    logger.info(f"Wrote {len(df)} records to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Compute Conflict of Interest Detection')
    parser.add_argument('--min-score', type=int, default=30, help='Minimum conflict score threshold')
    parser.add_argument('--local', action='store_true', help='Use local data instead of S3')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - do not write output')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Computing Conflict of Interest Detection")
    logger.info("=" * 80)
    
    # Load data
    if args.local:
        transactions_df = load_local_data('fact_ptr_transactions')
        member_bill_df = load_local_data('fact_member_bill_role')
        bill_actions_df = load_local_data('agg_bill_latest_action')
        members_df = load_local_data('dim_members')
    else:
        s3 = boto3.client('s3')
        transactions_df = read_parquet_from_s3(s3, 'gold/house/financial/facts/fact_ptr_transactions/')
        member_bill_df = read_parquet_from_s3(s3, 'gold/congress/fact_member_bill_role/')
        bill_actions_df = read_parquet_from_s3(s3, 'gold/congress/agg_bill_latest_action/')
        members_df = read_parquet_from_s3(s3, 'gold/dimensions/dim_members/')
    
    logger.info(f"Transactions: {len(transactions_df)}")
    logger.info(f"Member-Bill relations: {len(member_bill_df)}")
    logger.info(f"Bill actions: {len(bill_actions_df)}")
    logger.info(f"Members: {len(members_df)}")
    
    # Compute conflicts
    conflicts_df = compute_conflict_detection(
        transactions_df, member_bill_df, bill_actions_df, members_df,
        min_score=args.min_score
    )
    
    if not conflicts_df.empty:
        # Summary
        logger.info(f"\nCONFLICT DETECTION Summary:")
        logger.info(f"  Total conflicts: {len(conflicts_df)}")
        logger.info(f"  CRITICAL: {(conflicts_df['severity'] == 'CRITICAL').sum()}")
        logger.info(f"  HIGH: {(conflicts_df['severity'] == 'HIGH').sum()}")
        logger.info(f"  MEDIUM: {(conflicts_df['severity'] == 'MEDIUM').sum()}")
        logger.info(f"  LOW: {(conflicts_df['severity'] == 'LOW').sum()}")
        
        logger.info(f"\n  Top 5 Conflicts:")
        for idx, row in conflicts_df.head(5).iterrows():
            member = row.get('member_name', row['member_bioguide_id'])
            logger.info(f"    [{row['severity']}] {member} - {row['ticker']} - Score: {row['conflict_score']}")
        
        if not args.dry_run:
            # Write all conflicts
            if args.local:
                write_to_local(conflicts_df, 'all')
                # Also write by severity
                for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                    sev_df = conflicts_df[conflicts_df['severity'] == sev]
                    if not sev_df.empty:
                        write_to_local(sev_df, sev.lower())
            else:
                write_to_s3(conflicts_df, 'all')
                for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                    sev_df = conflicts_df[conflicts_df['severity'] == sev]
                    if not sev_df.empty:
                        write_to_s3(sev_df, sev.lower())
    
    logger.info("\n✅ Conflict detection computation complete!")


if __name__ == '__main__':
    main()
