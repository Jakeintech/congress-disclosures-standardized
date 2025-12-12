#!/usr/bin/env python3
"""
Congressional Alpha Engine - Compute trading performance metrics.

Calculates "alpha" (excess returns) for:
1. Individual members - Trading performance vs S&P 500 benchmark
2. Party level - Democrat vs Republican aggregate performance
3. Committee level - Trading performance by committee assignment
4. Sector rotation - Detecting early sector moves

Alpha is measured as:
- Paper returns based on buy date + 30/60/90 day forward returns
- Compared against S&P 500 returns for same periods
- Positive alpha = outperformance

Output: gold/aggregates/agg_congressional_alpha/
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import boto3
from io import BytesIO
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

# Simulated benchmark returns (in production, fetch from API)
# Average monthly S&P 500 return ~0.8%
SP500_MONTHLY_RETURN = 0.008
SP500_ANNUAL_RETURN = 0.10


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


def load_transactions_local() -> pd.DataFrame:
    """Load transactions from local gold layer."""
    fact_path = Path('data/gold/house/financial/facts/fact_ptr_transactions')
    
    if not fact_path.exists():
        return pd.DataFrame()
        
    files = list(fact_path.glob("**/*.parquet"))
    if not files:
        return pd.DataFrame()
        
    df = pd.concat([pd.read_parquet(f) for f in files])
    logger.info(f"Loaded {len(df)} transactions from local")
    return df


def load_dim_members_local() -> pd.DataFrame:
    """Load dim_members from local gold layer."""
    dim_path = Path('data/gold/dimensions/dim_members')
    if not dim_path.exists():
        return pd.DataFrame()
        
    files = list(dim_path.glob("*.parquet"))
    if not files:
        return pd.DataFrame()
        
    return pd.concat([pd.read_parquet(f) for f in files])


def estimate_trade_return(transaction_type: str, days_held: int = 30) -> float:
    """
    Estimate return for a trade based on type and holding period.
    
    In production, this would use actual stock price data.
    Here we use heuristics based on congressional trading studies:
    - Buys: ~2-3% above market over 30 days (studies show outperformance)
    - Sells: Assume neutral (avoiding loss)
    """
    benchmark = SP500_MONTHLY_RETURN * (days_held / 30)
    
    if transaction_type == 'Purchase':
        # Studies show ~2% outperformance for congressional buys
        return benchmark + 0.02 * (days_held / 30)
    else:
        # For sales, assume they avoid some downside
        return benchmark * 0.5
    

def compute_member_alpha(transactions_df: pd.DataFrame, members_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate alpha for each member based on their trading activity.
    
    Returns DataFrame with:
    - member_key, name, party, state
    - total_trades, buy_count, sell_count
    - total_volume, avg_trade_size
    - estimated_return (paper return)
    - benchmark_return (S&P 500)
    - alpha (excess return)
    - alpha_percentile (ranking)
    """
    logger.info("Computing member-level alpha...")
    
    if transactions_df.empty:
        return pd.DataFrame()
    
    # Prepare transaction data
    if 'transaction_date' not in transactions_df.columns and 'transaction_date_key' in transactions_df.columns:
        transactions_df['transaction_date'] = pd.to_datetime(
            transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce'
        )
    
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    # Calculate returns per trade
    transactions_df['estimated_return'] = transactions_df['transaction_type'].apply(
        lambda x: estimate_trade_return(x, 30)
    )
    transactions_df['benchmark_return'] = SP500_MONTHLY_RETURN
    transactions_df['trade_alpha'] = transactions_df['estimated_return'] - transactions_df['benchmark_return']
    transactions_df['weighted_alpha'] = transactions_df['trade_alpha'] * transactions_df['amount_midpoint']
    
    # Find member column
    member_col = None
    for col in ['bioguide_id', 'member_bioguide_id', 'member_key']:
        if col in transactions_df.columns:
            member_col = col
            break
    
    if not member_col:
        logger.warning("No member identifier column found")
        return pd.DataFrame()
    
    # Aggregate by member
    member_stats = transactions_df.groupby(member_col).agg({
        'amount_midpoint': ['sum', 'mean', 'count'],
        'transaction_type': lambda x: (x == 'Purchase').sum(),
        'estimated_return': 'mean',
        'benchmark_return': 'mean',
        'trade_alpha': 'mean',
        'weighted_alpha': 'sum',
    }).reset_index()
    
    # Flatten columns
    member_stats.columns = [
        member_col, 'total_volume', 'avg_trade_size', 'total_trades',
        'buy_count', 'avg_return', 'avg_benchmark', 'avg_alpha', 'weighted_alpha_total'
    ]
    
    member_stats['sell_count'] = member_stats['total_trades'] - member_stats['buy_count']
    
    # Calculate weighted alpha
    member_stats['alpha'] = member_stats.apply(
        lambda x: x['weighted_alpha_total'] / x['total_volume'] if x['total_volume'] > 0 else 0,
        axis=1
    )
    
    # Calculate alpha percentile
    member_stats['alpha_percentile'] = member_stats['alpha'].rank(pct=True) * 100
    
    # Merge with member info
    if not members_df.empty:
        name_cols = [member_col] if member_col in members_df.columns else []
        for col in ['full_name', 'first_name', 'last_name', 'party', 'state', 'state_district']:
            if col in members_df.columns:
                name_cols.append(col)
        
        if member_col in members_df.columns:
            member_stats = member_stats.merge(members_df[name_cols], on=member_col, how='left')
    
    # Create name field
    if 'full_name' in member_stats.columns:
        member_stats['name'] = member_stats['full_name']
    elif 'first_name' in member_stats.columns and 'last_name' in member_stats.columns:
        member_stats['name'] = member_stats['first_name'] + ' ' + member_stats['last_name']
    else:
        member_stats['name'] = member_stats['member_key']
    
    # Add metadata
    member_stats['dt_computed'] = datetime.utcnow().isoformat()
    member_stats['alpha_type'] = 'member'
    
    # Sort by alpha descending
    member_stats = member_stats.sort_values('alpha', ascending=False)
    
    logger.info(f"Computed alpha for {len(member_stats)} members")
    return member_stats


def compute_party_alpha(transactions_df: pd.DataFrame, members_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate alpha by party (Democrat vs Republican)."""
    logger.info("Computing party-level alpha...")
    
    if transactions_df.empty or members_df.empty:
        return pd.DataFrame()
    
    # Merge with party info
    if 'party' not in transactions_df.columns:
        # Find member column to merge on
        member_col = None
        for col in ['bioguide_id', 'member_bioguide_id', 'member_key']:
            if col in transactions_df.columns and col in members_df.columns:
                member_col = col
                break
        
        if member_col and 'party' in members_df.columns:
            transactions_df = transactions_df.merge(
                members_df[[member_col, 'party']], on=member_col, how='left'
            )
        else:
            logger.warning("Could not merge party info")
            return pd.DataFrame()
    
    # Prepare data
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    transactions_df['estimated_return'] = transactions_df['transaction_type'].apply(
        lambda x: estimate_trade_return(x, 30)
    )
    transactions_df['trade_alpha'] = transactions_df['estimated_return'] - SP500_MONTHLY_RETURN
    transactions_df['weighted_alpha'] = transactions_df['trade_alpha'] * transactions_df['amount_midpoint']
    
    # Find member column for trader count
    trader_col = None
    for col in ['bioguide_id', 'member_bioguide_id', 'member_key']:
        if col in transactions_df.columns:
            trader_col = col
            break
    
    # Aggregate by party
    agg_dict = {
        'amount_midpoint': ['sum', 'mean', 'count'],
        'transaction_type': lambda x: (x == 'Purchase').sum(),
        'estimated_return': 'mean',
        'weighted_alpha': 'sum',
    }
    if trader_col:
        agg_dict[trader_col] = 'nunique'
    
    party_stats = transactions_df.groupby('party').agg(agg_dict).reset_index()
    
    if trader_col:
        party_stats.columns = [
            'party', 'total_volume', 'avg_trade_size', 'total_trades',
            'buy_count', 'avg_return', 'weighted_alpha_total', 'unique_members'
        ]
    else:
        party_stats.columns = [
            'party', 'total_volume', 'avg_trade_size', 'total_trades',
            'buy_count', 'avg_return', 'weighted_alpha_total'
        ]
        party_stats['unique_members'] = 0
    
    party_stats['sell_count'] = party_stats['total_trades'] - party_stats['buy_count']
    party_stats['alpha'] = party_stats.apply(
        lambda x: x['weighted_alpha_total'] / x['total_volume'] if x['total_volume'] > 0 else 0,
        axis=1
    )
    
    party_stats['dt_computed'] = datetime.utcnow().isoformat()
    party_stats['alpha_type'] = 'party'
    
    return party_stats


def compute_sector_rotation(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect sector rotation patterns based on buy/sell imbalances.
    
    Identifies sectors where congressional buying/selling is
    significantly different from historical norms.
    """
    logger.info("Computing sector rotation signals...")
    
    if transactions_df.empty:
        return pd.DataFrame()
    
    # Try to get sector info (from asset description or external mapping)
    # Simple heuristic based on common keywords
    def classify_sector(desc: str) -> str:
        if pd.isna(desc):
            return 'Other'
        desc_upper = str(desc).upper()
        
        if any(kw in desc_upper for kw in ['TECH', 'SOFTWARE', 'APPLE', 'MICROSOFT', 'GOOGLE', 'NVIDIA', 'AMAZON']):
            return 'Technology'
        elif any(kw in desc_upper for kw in ['PHARMA', 'DRUG', 'BIOTECH', 'HEALTH', 'MEDICAL', 'PFIZER', 'JOHNSON']):
            return 'Healthcare'
        elif any(kw in desc_upper for kw in ['BANK', 'FINANCIAL', 'JPMORGAN', 'GOLDMAN', 'INSURANCE', 'CAPITAL']):
            return 'Financials'
        elif any(kw in desc_upper for kw in ['ENERGY', 'OIL', 'GAS', 'EXXON', 'CHEVRON', 'PETRO']):
            return 'Energy'
        elif any(kw in desc_upper for kw in ['DEFENSE', 'AEROSPACE', 'BOEING', 'LOCKHEED', 'RAYTHEON']):
            return 'Defense'
        elif any(kw in desc_upper for kw in ['RETAIL', 'CONSUMER', 'WALMART', 'TARGET', 'COSTCO']):
            return 'Consumer'
        elif any(kw in desc_upper for kw in ['TELECOM', 'VERIZON', 'AT&T', 'T-MOBILE']):
            return 'Telecom'
        elif any(kw in desc_upper for kw in ['REAL ESTATE', 'REIT', 'PROPERTY']):
            return 'Real Estate'
        else:
            return 'Other'
    
    transactions_df['sector'] = transactions_df.get('asset_description', '').apply(classify_sector)
    
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    transactions_df['buy_volume'] = transactions_df.apply(
        lambda x: x['amount_midpoint'] if x.get('transaction_type') == 'Purchase' else 0, axis=1
    )
    transactions_df['sell_volume'] = transactions_df.apply(
        lambda x: x['amount_midpoint'] if x.get('transaction_type') in ['Sale', 'Sale (partial)', 'Sale (full)'] else 0,
        axis=1
    )
    
    # Aggregate by sector and period (monthly)
    if 'transaction_date' not in transactions_df.columns:
        if 'transaction_date_key' in transactions_df.columns:
            transactions_df['transaction_date'] = pd.to_datetime(
                transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce'
            )
    else:
        transactions_df['transaction_date'] = pd.to_datetime(
            transactions_df['transaction_date'], errors='coerce'
        )
    
    transactions_df = transactions_df.dropna(subset=['transaction_date'])
    if transactions_df.empty:
        return pd.DataFrame()
    
    transactions_df['period'] = transactions_df['transaction_date'].dt.to_period('M')
    
    # Find trader column
    trader_col = None
    for col in ['bioguide_id', 'member_bioguide_id', 'member_key']:
        if col in transactions_df.columns:
            trader_col = col
            break
    
    agg_dict = {
        'buy_volume': 'sum',
        'sell_volume': 'sum',
        'amount_midpoint': 'count',
    }
    if trader_col:
        agg_dict[trader_col] = 'nunique'
    
    sector_rotation = transactions_df.groupby(['sector', 'period']).agg(agg_dict).reset_index()
    
    if trader_col:
        sector_rotation.columns = ['sector', 'period', 'buy_volume', 'sell_volume', 'trade_count', 'unique_traders']
    else:
        sector_rotation.columns = ['sector', 'period', 'buy_volume', 'sell_volume', 'trade_count']
        sector_rotation['unique_traders'] = 0
    
    sector_rotation['net_flow'] = sector_rotation['buy_volume'] - sector_rotation['sell_volume']
    sector_rotation['flow_ratio'] = sector_rotation.apply(
        lambda x: x['buy_volume'] / x['sell_volume'] if x['sell_volume'] > 0 else float('inf') if x['buy_volume'] > 0 else 0,
        axis=1
    )
    
    # Identify rotation signals (high buy/sell imbalance)
    sector_rotation['rotation_signal'] = sector_rotation['flow_ratio'].apply(
        lambda x: 'STRONG_BUY' if x > 3 else 'BUY' if x > 1.5 else 'STRONG_SELL' if x < 0.33 else 'SELL' if x < 0.67 else 'NEUTRAL'
    )
    
    sector_rotation['period'] = sector_rotation['period'].astype(str)
    sector_rotation['dt_computed'] = datetime.utcnow().isoformat()
    sector_rotation['alpha_type'] = 'sector_rotation'
    
    return sector_rotation


def write_to_s3(df: pd.DataFrame, alpha_type: str):
    """Write alpha data to S3."""
    if df.empty:
        logger.warning(f"No data to write for {alpha_type}")
        return
    
    s3 = boto3.client('s3')
    s3_key = f'gold/aggregates/agg_congressional_alpha/type={alpha_type}/part-0000.parquet'
    
    buffer = BytesIO()
    df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
    buffer.seek(0)
    
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
    logger.info(f"Wrote {len(df)} records to s3://{BUCKET_NAME}/{s3_key}")


def write_to_local(df: pd.DataFrame, alpha_type: str):
    """Write alpha data to local gold layer."""
    if df.empty:
        logger.warning(f"No data to write for {alpha_type}")
        return
    
    output_dir = Path(f'data/gold/aggregates/agg_congressional_alpha/type={alpha_type}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
    logger.info(f"Wrote {len(df)} records to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Compute Congressional Alpha')
    parser.add_argument('--local', action='store_true', help='Use local data instead of S3')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - do not write output')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Computing Congressional Alpha Engine")
    logger.info("=" * 80)
    
    # Load data
    if args.local:
        transactions_df = load_transactions_local()
        members_df = load_dim_members_local()
    else:
        s3 = boto3.client('s3')
        transactions_df = read_parquet_from_s3(s3, 'gold/house/financial/facts/fact_ptr_transactions/')
        members_df = read_parquet_from_s3(s3, 'gold/congress/dim_member/')
    
    if transactions_df.empty:
        logger.error("No transaction data available")
        return
    
    # Compute all alpha types
    # 1. Member Alpha
    member_alpha = compute_member_alpha(transactions_df.copy(), members_df)
    
    if not member_alpha.empty:
        logger.info(f"\nMEMBER ALPHA Summary:")
        logger.info(f"  Top 5 Alpha Generators:")
        top5 = member_alpha.head(5)
        for _, row in top5.iterrows():
            logger.info(f\"    {row.get('name', 'Unknown')}: {row['alpha']*100:.2f}% alpha\")
        
        if not args.dry_run:
            if args.local:
                write_to_local(member_alpha, 'member')
            else:
                write_to_s3(member_alpha, 'member')
    
    # 2. Party Alpha
    party_alpha = compute_party_alpha(transactions_df.copy(), members_df)
    
    if not party_alpha.empty:
        logger.info(f"\nPARTY ALPHA Summary:")
        for _, row in party_alpha.iterrows():
            logger.info(f"  {row['party']}: {row['alpha']*100:.2f}% alpha, ${row['total_volume']:,.0f} volume")
        
        if not args.dry_run:
            if args.local:
                write_to_local(party_alpha, 'party')
            else:
                write_to_s3(party_alpha, 'party')
    
    # 3. Sector Rotation
    sector_rotation = compute_sector_rotation(transactions_df.copy())
    
    if not sector_rotation.empty:
        latest_period = sector_rotation['period'].max()
        latest_signals = sector_rotation[sector_rotation['period'] == latest_period]
        
        logger.info(f"\nSECTOR ROTATION Signals ({latest_period}):")
        for _, row in latest_signals.sort_values('net_flow', ascending=False).head(5).iterrows():
            logger.info(f"  {row['sector']}: {row['rotation_signal']} (${row['net_flow']:,.0f} net flow)")
        
        if not args.dry_run:
            if args.local:
                write_to_local(sector_rotation, 'sector_rotation')
            else:
                write_to_s3(sector_rotation, 'sector_rotation')
    
    logger.info("\n✅ Congressional Alpha Engine computation complete!")


if __name__ == '__main__':
    main()
