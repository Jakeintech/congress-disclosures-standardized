#!/usr/bin/env python3
"""
Deep Sector Analysis Aggregation.

Provides comprehensive sector-level analytics:
1. Volume and trade count by sector
2. Sector rotation signals (buy/sell flow)
3. Party preferences by sector
4. Committee correlation with sector trading
5. Concentration metrics
6. Trend analysis over time

Output: gold/aggregates/agg_sector_analysis/
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
import logging
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

# Sector classification mapping
SECTOR_KEYWORDS = {
    'Technology': ['TECH', 'SOFTWARE', 'APPLE', 'MICROSOFT', 'GOOGLE', 'NVIDIA', 'META', 'AMAZON', 
                   'SEMICONDUCTOR', 'INTEL', 'AMD', 'CISCO', 'ORACLE', 'SALESFORCE', 'ADOBE'],
    'Healthcare': ['PHARMA', 'DRUG', 'BIOTECH', 'HEALTH', 'MEDICAL', 'PFIZER', 'JOHNSON', 'MERCK', 
                   'MODERNA', 'UNITEDHEALTH', 'ELI LILLY', 'ABBVIE', 'BRISTOL'],
    'Financials': ['BANK', 'FINANCIAL', 'JPMORGAN', 'GOLDMAN', 'INSURANCE', 'CAPITAL', 'CREDIT',
                   'VISA', 'MASTERCARD', 'BERKSHIRE', 'MORGAN STANLEY', 'WELLS FARGO'],
    'Energy': ['ENERGY', 'OIL', 'GAS', 'EXXON', 'CHEVRON', 'PETRO', 'SHELL', 'CONOCOPHILLIPS'],
    'Defense & Aerospace': ['DEFENSE', 'AEROSPACE', 'BOEING', 'LOCKHEED', 'RAYTHEON', 'MILITARY', 
                            'NORTHROP', 'GENERAL DYNAMICS', 'L3HARRIS'],
    'Consumer Discretionary': ['RETAIL', 'CONSUMER', 'WALMART', 'TARGET', 'HOME DEPOT', 'NIKE',
                               'STARBUCKS', 'MCDONALD', 'DISNEY', 'TESLA'],
    'Telecommunications': ['TELECOM', 'VERIZON', 'AT&T', 'T-MOBILE', 'WIRELESS', 'COMCAST'],
    'Real Estate': ['REAL ESTATE', 'REIT', 'PROPERTY', 'HOUSING'],
    'Industrials': ['INDUSTRIAL', 'CATERPILLAR', 'DEERE', 'HONEYWELL', '3M', 'GE', 'UNITED PARCEL'],
    'Materials': ['MINING', 'STEEL', 'CHEMICAL', 'GOLD', 'SILVER', 'COPPER', 'DOW', 'DUPONT'],
    'Utilities': ['UTILITY', 'ELECTRIC', 'WATER', 'POWER', 'DUKE ENERGY', 'SOUTHERN'],
    'Consumer Staples': ['COCA COLA', 'PEPSI', 'PROCTER', 'COSTCO', 'KROGER', 'COLGATE'],
}


def classify_sector(asset_description: str) -> str:
    """Classify asset into sector using keywords."""
    if pd.isna(asset_description):
        return 'Other'
    
    desc = str(asset_description).upper()
    
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in desc for kw in keywords):
            return sector
    
    return 'Other'


def read_parquet_from_s3(s3_client, prefix: str) -> pd.DataFrame:
    """Read all Parquet files from S3."""
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    if 'Contents' not in response:
        return pd.DataFrame()

    dfs = []
    for obj in response['Contents']:
        if obj['Key'].endswith('.parquet'):
            response_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
            df = pd.read_parquet(BytesIO(response_obj['Body'].read()))
            dfs.append(df)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def load_local_data(table_name: str) -> pd.DataFrame:
    """Load data from local gold layer."""
    paths = [
        Path('data/gold/house/financial/facts') / table_name,
        Path('data/gold/dimensions') / table_name,
    ]
    
    for path in paths:
        if path.exists():
            files = list(path.glob("**/*.parquet"))
            if files:
                return pd.concat([pd.read_parquet(f) for f in files])
    
    return pd.DataFrame()


def compute_sector_summary(transactions_df: pd.DataFrame, members_df: pd.DataFrame) -> pd.DataFrame:
    """Compute overall sector summary statistics."""
    logger.info("Computing sector summary...")
    
    if transactions_df.empty:
        return pd.DataFrame()
    
    # Prepare data
    if 'transaction_date' not in transactions_df.columns:
        if 'transaction_date_key' in transactions_df.columns:
            transactions_df['transaction_date'] = pd.to_datetime(
                transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce'
            )
    
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    # Classify sectors
    transactions_df['sector'] = transactions_df.get('asset_description', '').apply(classify_sector)
    
    # Calculate buy/sell volumes
    transactions_df['buy_volume'] = transactions_df.apply(
        lambda x: x['amount_midpoint'] if x.get('transaction_type') == 'Purchase' else 0, axis=1
    )
    transactions_df['sell_volume'] = transactions_df.apply(
        lambda x: x['amount_midpoint'] if x.get('transaction_type') in ['Sale', 'Sale (partial)', 'Sale (full)'] else 0,
        axis=1
    )
    
    # Aggregate by sector
    sector_stats = transactions_df.groupby('sector').agg({
        'amount_midpoint': ['sum', 'count', 'mean', 'std'],
        'buy_volume': 'sum',
        'sell_volume': 'sum',
        'member_key': 'nunique' if 'member_key' in transactions_df.columns else lambda x: 0,
        'ticker': 'nunique' if 'ticker' in transactions_df.columns else lambda x: 0,
    }).reset_index()
    
    sector_stats.columns = [
        'sector', 'total_volume', 'trade_count', 'avg_trade_size', 'std_trade_size',
        'buy_volume', 'sell_volume', 'unique_traders', 'unique_tickers'
    ]
    
    # Calculate derived metrics
    total_volume = sector_stats['total_volume'].sum()
    sector_stats['pct_of_total'] = (sector_stats['total_volume'] / total_volume * 100).round(2)
    sector_stats['net_flow'] = sector_stats['buy_volume'] - sector_stats['sell_volume']
    sector_stats['flow_ratio'] = sector_stats.apply(
        lambda x: x['buy_volume'] / x['sell_volume'] if x['sell_volume'] > 0 else float('inf') if x['buy_volume'] > 0 else 0,
        axis=1
    )
    
    # Flow signal
    sector_stats['flow_signal'] = sector_stats['flow_ratio'].apply(
        lambda x: 'STRONG_BUY' if x > 3 else 'BUY' if x > 1.5 else 'STRONG_SELL' if x < 0.33 else 'SELL' if x < 0.67 else 'NEUTRAL'
    )
    
    # Concentration (HHI proxy)
    sector_stats['concentration'] = sector_stats.apply(
        lambda x: 'HIGH' if x['unique_tickers'] < 3 else 'MEDIUM' if x['unique_tickers'] < 10 else 'LOW',
        axis=1
    )
    
    sector_stats['analysis_type'] = 'summary'
    sector_stats['dt_computed'] = datetime.utcnow().isoformat()
    
    return sector_stats.sort_values('total_volume', ascending=False)


def compute_sector_by_party(transactions_df: pd.DataFrame, members_df: pd.DataFrame) -> pd.DataFrame:
    """Compute sector preferences by party."""
    logger.info("Computing sector by party...")
    
    if transactions_df.empty or members_df.empty:
        return pd.DataFrame()
    
    # Merge with members
    if 'party' not in transactions_df.columns:
        member_col = None
        for col in ['member_key', 'member_bioguide_id', 'bioguide_id']:
            if col in transactions_df.columns and col in members_df.columns:
                member_col = col
                break
        
        if member_col and 'party' in members_df.columns:
            # Ensure both keys are the same type (string)
            transactions_df[member_col] = transactions_df[member_col].astype(str)
            members_df[member_col] = members_df[member_col].astype(str)
            
            transactions_df = transactions_df.merge(
                members_df[[member_col, 'party']].drop_duplicates(),
                on=member_col,
                how='left'
            )
    
    if 'party' not in transactions_df.columns:
        return pd.DataFrame()
    
    # Prepare data
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    transactions_df['sector'] = transactions_df.get('asset_description', '').apply(classify_sector)
    
    # Aggregate by sector and party
    party_sector = transactions_df.groupby(['sector', 'party']).agg({
        'amount_midpoint': ['sum', 'count'],
        'member_key': 'nunique' if 'member_key' in transactions_df.columns else lambda x: 0
    }).reset_index()
    
    party_sector.columns = ['sector', 'party', 'total_volume', 'trade_count', 'unique_traders']
    
    # Calculate party preference index
    # Positive = D preference, Negative = R preference
    pivot = party_sector.pivot_table(
        index='sector', 
        columns='party', 
        values='total_volume', 
        aggfunc='sum'
    ).reset_index()
    
    pivot['d_volume'] = pivot['D'].fillna(0) if 'D' in pivot.columns else 0
    pivot['r_volume'] = pivot['R'].fillna(0) if 'R' in pivot.columns else 0
    pivot['total_volume'] = pivot['d_volume'] + pivot['r_volume']
    pivot['d_pct'] = (pivot['d_volume'] / pivot['total_volume'] * 100).round(1)
    pivot['r_pct'] = (pivot['r_volume'] / pivot['total_volume'] * 100).round(1)
    pivot['party_lean'] = pivot.apply(
        lambda x: 'DEMOCRAT' if x['d_pct'] > 60 else 'REPUBLICAN' if x['r_pct'] > 60 else 'BIPARTISAN',
        axis=1
    )
    
    pivot['analysis_type'] = 'party_breakdown'
    pivot['dt_computed'] = datetime.utcnow().isoformat()
    
    return pivot.sort_values('total_volume', ascending=False)


def compute_sector_timeseries(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Compute monthly sector trends."""
    logger.info("Computing sector timeseries...")
    
    if transactions_df.empty:
        return pd.DataFrame()
    
    # Prepare data
    if 'transaction_date' not in transactions_df.columns:
        if 'transaction_date_key' in transactions_df.columns:
            transactions_df['transaction_date'] = pd.to_datetime(
                transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce'
            )
    
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    transactions_df['sector'] = transactions_df.get('asset_description', '').apply(classify_sector)
    transactions_df['month'] = transactions_df['transaction_date'].dt.to_period('M')
    
    transactions_df['buy_volume'] = transactions_df.apply(
        lambda x: x['amount_midpoint'] if x.get('transaction_type') == 'Purchase' else 0, axis=1
    )
    transactions_df['sell_volume'] = transactions_df.apply(
        lambda x: x['amount_midpoint'] if x.get('transaction_type') in ['Sale', 'Sale (partial)', 'Sale (full)'] else 0,
        axis=1
    )
    
    # Aggregate by sector and month
    ts = transactions_df.groupby(['sector', 'month']).agg({
        'amount_midpoint': 'sum',
        'buy_volume': 'sum',
        'sell_volume': 'sum',
        'transaction_type': 'count'
    }).reset_index()
    
    ts.columns = ['sector', 'month', 'total_volume', 'buy_volume', 'sell_volume', 'trade_count']
    ts['net_flow'] = ts['buy_volume'] - ts['sell_volume']
    ts['month'] = ts['month'].astype(str)
    
    ts['analysis_type'] = 'timeseries'
    ts['dt_computed'] = datetime.utcnow().isoformat()
    
    return ts.sort_values(['sector', 'month'])


def compute_top_stocks_by_sector(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Identify top traded stocks in each sector."""
    logger.info("Computing top stocks by sector...")
    
    if transactions_df.empty:
        return pd.DataFrame()
    
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0).fillna(0) + 
            transactions_df.get('amount_high', 0).fillna(0)
        ) / 2
    
    transactions_df['sector'] = transactions_df.get('asset_description', '').apply(classify_sector)
    
    # Get ticker if available
    ticker_col = 'ticker' if 'ticker' in transactions_df.columns else 'asset_description'
    
    # Aggregate by sector and ticker
    stock_stats = transactions_df.groupby(['sector', ticker_col]).agg({
        'amount_midpoint': ['sum', 'count'],
        'member_key': 'nunique' if 'member_key' in transactions_df.columns else lambda x: 0
    }).reset_index()
    
    stock_stats.columns = ['sector', 'ticker', 'total_volume', 'trade_count', 'unique_traders']
    
    # Rank within sector
    stock_stats['sector_rank'] = stock_stats.groupby('sector')['total_volume'].rank(ascending=False)
    
    # Keep top 10 per sector
    top_stocks = stock_stats[stock_stats['sector_rank'] <= 10].copy()
    
    top_stocks['analysis_type'] = 'top_stocks'
    top_stocks['dt_computed'] = datetime.utcnow().isoformat()
    
    return top_stocks.sort_values(['sector', 'sector_rank'])


def write_to_s3(df: pd.DataFrame, analysis_type: str):
    """Write to S3."""
    if df.empty:
        return
    
    s3 = boto3.client('s3')
    s3_key = f'gold/aggregates/agg_sector_analysis/type={analysis_type}/part-0000.parquet'
    
    buffer = BytesIO()
    df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
    buffer.seek(0)
    
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
    logger.info(f"Wrote {len(df)} records to s3://{BUCKET_NAME}/{s3_key}")


def write_to_local(df: pd.DataFrame, analysis_type: str):
    """Write to local gold layer."""
    if df.empty:
        return
    
    output_dir = Path(f'data/gold/aggregates/agg_sector_analysis/type={analysis_type}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
    logger.info(f"Wrote {len(df)} records to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Compute Deep Sector Analysis')
    parser.add_argument('--local', action='store_true', help='Use local data')
    parser.add_argument('--dry-run', action='store_true', help='Dry run')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Computing Deep Sector Analysis")
    logger.info("=" * 80)
    
    # Load data
    if args.local:
        transactions_df = load_local_data('fact_ptr_transactions')
        members_df = load_local_data('dim_members')
    else:
        s3 = boto3.client('s3')
        transactions_df = read_parquet_from_s3(s3, 'gold/house/financial/facts/fact_ptr_transactions/')
        members_df = read_parquet_from_s3(s3, 'gold/dimensions/dim_members/')
    
    if transactions_df.empty:
        logger.error("No transaction data available")
        return
    
    analyses = {}
    
    # 1. Sector Summary
    summary = compute_sector_summary(transactions_df.copy(), members_df)
    if not summary.empty:
        analyses['summary'] = summary
        logger.info(f"\nSECTOR SUMMARY:")
        for _, row in summary.head(5).iterrows():
            logger.info(f"  {row['sector']}: ${row['total_volume']:,.0f} ({row['pct_of_total']:.1f}%) [{row['flow_signal']}]")
    
    # 2. Party Breakdown
    party = compute_sector_by_party(transactions_df.copy(), members_df)
    if not party.empty:
        analyses['party'] = party
        logger.info(f"\nPARTY PREFERENCES:")
        for _, row in party.head(5).iterrows():
            logger.info(f"  {row['sector']}: D={row['d_pct']:.0f}% R={row['r_pct']:.0f}% [{row['party_lean']}]")
    
    # 3. Timeseries
    ts = compute_sector_timeseries(transactions_df.copy())
    if not ts.empty:
        analyses['timeseries'] = ts
        logger.info(f"\nTIMESERIES: {len(ts)} sector-month records")
    
    # 4. Top Stocks
    top_stocks = compute_top_stocks_by_sector(transactions_df.copy())
    if not top_stocks.empty:
        analyses['top_stocks'] = top_stocks
        logger.info(f"\nTOP STOCKS: {len(top_stocks)} records")
    
    # Write outputs
    if not args.dry_run:
        for analysis_type, df in analyses.items():
            if args.local:
                write_to_local(df, analysis_type)
            else:
                write_to_s3(df, analysis_type)
    
    logger.info("\n✅ Deep sector analysis complete!")


if __name__ == '__main__':
    main()
