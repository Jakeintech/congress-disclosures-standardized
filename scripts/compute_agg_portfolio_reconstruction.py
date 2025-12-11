#!/usr/bin/env python3
"""
Portfolio Reconstruction Engine.

Reconstructs estimated portfolio holdings from cumulative trade data.

Key features:
1. Cumulative position tracking from first trade to present
2. Sector allocation breakdown
3. Position sizing and concentration analysis
4. Confidence scoring based on data quality
5. Net worth estimation (within disclosure ranges)

Confidence Score factors:
- Trade history completeness (more trades = higher confidence)
- Recent activity (more recent = higher confidence)
- Range precision (narrower ranges = higher confidence)

Output: gold/aggregates/agg_portfolio_reconstruction/
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


def load_local_data(table_name: str) -> pd.DataFrame:
    """Load data from local gold layer."""
    paths = [
        Path('data/gold/house/financial/facts') / table_name,
        Path('data/gold/dimensions') / table_name,
        Path('data/gold/aggregates') / table_name,
    ]
    
    for path in paths:
        if path.exists():
            files = list(path.glob("**/*.parquet"))
            if files:
                return pd.concat([pd.read_parquet(f) for f in files])
    
    logger.warning(f"Table not found: {table_name}")
    return pd.DataFrame()


def classify_sector(asset_description: str) -> str:
    """Classify asset into sector."""
    if pd.isna(asset_description):
        return 'Other'
    
    desc = str(asset_description).upper()
    
    sectors = {
        'Technology': ['TECH', 'SOFTWARE', 'APPLE', 'MICROSOFT', 'GOOGLE', 'NVIDIA', 'META', 'AMAZON', 'SEMICONDUCTOR', 'INTEL', 'AMD'],
        'Healthcare': ['PHARMA', 'DRUG', 'BIOTECH', 'HEALTH', 'MEDICAL', 'PFIZER', 'JOHNSON', 'MERCK', 'MODERNA', 'UNITEDHEALTH'],
        'Financials': ['BANK', 'FINANCIAL', 'JPMORGAN', 'GOLDMAN', 'INSURANCE', 'CAPITAL', 'CREDIT', 'VISA', 'MASTERCARD'],
        'Energy': ['ENERGY', 'OIL', 'GAS', 'EXXON', 'CHEVRON', 'PETRO', 'SOLAR', 'WIND', 'SHELL'],
        'Defense': ['DEFENSE', 'AEROSPACE', 'BOEING', 'LOCKHEED', 'RAYTHEON', 'MILITARY', 'NORTHROP', 'GENERAL DYNAMICS'],
        'Consumer Discretionary': ['RETAIL', 'CONSUMER', 'WALMART', 'TARGET', 'HOME DEPOT', 'NIKE', 'STARBUCKS'],
        'Telecom': ['TELECOM', 'VERIZON', 'AT&T', 'T-MOBILE', 'WIRELESS', 'COMCAST'],
        'Real Estate': ['REAL ESTATE', 'REIT', 'PROPERTY', 'HOUSING'],
        'Industrials': ['INDUSTRIAL', 'CATERPILLAR', 'DEERE', 'HONEYWELL', '3M', 'GE'],
        'Materials': ['MINING', 'STEEL', 'CHEMICAL', 'GOLD', 'SILVER', 'COPPER'],
        'Utilities': ['UTILITY', 'ELECTRIC', 'WATER', 'POWER', 'DUKE ENERGY'],
    }
    
    for sector, keywords in sectors.items():
        if any(kw in desc for kw in keywords):
            return sector
    
    return 'Other'


def calculate_confidence_score(
    trade_count: int,
    last_trade_date: datetime,
    avg_range_precision: float,
    years_of_history: float
) -> Tuple[float, str]:
    """
    Calculate confidence score for portfolio reconstruction.
    
    Returns (score, explanation)
    """
    score = 0.0
    factors = []
    
    # Trade count factor (0-30 points)
    if trade_count >= 50:
        trade_score = 30
    elif trade_count >= 20:
        trade_score = 25
    elif trade_count >= 10:
        trade_score = 18
    elif trade_count >= 5:
        trade_score = 12
    else:
        trade_score = 5
    score += trade_score
    factors.append(f"Trade history: {trade_score}/30")
    
    # Recency factor (0-25 points)
    days_since_last = (datetime.now() - last_trade_date).days if last_trade_date else 365
    if days_since_last <= 30:
        recency_score = 25
    elif days_since_last <= 90:
        recency_score = 20
    elif days_since_last <= 180:
        recency_score = 15
    elif days_since_last <= 365:
        recency_score = 10
    else:
        recency_score = 5
    score += recency_score
    factors.append(f"Data recency: {recency_score}/25")
    
    # Range precision factor (0-25 points)
    # Lower ratio = more precise ranges
    if avg_range_precision <= 1.5:
        precision_score = 25
    elif avg_range_precision <= 2.0:
        precision_score = 20
    elif avg_range_precision <= 3.0:
        precision_score = 15
    else:
        precision_score = 10
    score += precision_score
    factors.append(f"Range precision: {precision_score}/25")
    
    # History depth factor (0-20 points)
    if years_of_history >= 4:
        history_score = 20
    elif years_of_history >= 2:
        history_score = 15
    elif years_of_history >= 1:
        history_score = 10
    else:
        history_score = 5
    score += history_score
    factors.append(f"History depth: {history_score}/20")
    
    return score, "; ".join(factors)


def reconstruct_portfolio(
    transactions_df: pd.DataFrame,
    members_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Reconstruct estimated portfolios for all members.
    """
    logger.info("Reconstructing portfolios...")
    
    if transactions_df.empty:
        return pd.DataFrame()
    
    # Prepare data
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
    
    # Calculate range ratio for precision
    transactions_df['range_ratio'] = transactions_df.apply(
        lambda x: x.get('amount_high', 1) / x.get('amount_low', 1) if x.get('amount_low', 0) > 0 else 10,
        axis=1
    )
    
    # Classify sectors
    transactions_df['sector'] = transactions_df.get('asset_description', '').apply(classify_sector)
    
    # Get member key column
    member_col = None
    for col in ['member_key', 'member_bioguide_id', 'bioguide_id']:
        if col in transactions_df.columns:
            member_col = col
            break
    
    if not member_col:
        logger.warning("No member key column found")
        return pd.DataFrame()
    
    portfolios = []
    holdings_details = []
    
    for member_id in transactions_df[member_col].unique():
        member_txs = transactions_df[transactions_df[member_col] == member_id].copy()
        member_txs = member_txs.sort_values('transaction_date')
        
        # Calculate cumulative positions by ticker
        positions = {}
        
        for _, tx in member_txs.iterrows():
            ticker = tx.get('ticker', tx.get('asset_description', 'UNKNOWN')[:20])
            amount = tx['amount_midpoint']
            tx_type = tx.get('transaction_type', '')
            
            if ticker not in positions:
                positions[ticker] = {
                    'total_bought': 0,
                    'total_sold': 0,
                    'net_position': 0,
                    'last_trade_date': None,
                    'trade_count': 0,
                    'sector': tx['sector'],
                    'asset_description': tx.get('asset_description', '')[:100],
                }
            
            positions[ticker]['trade_count'] += 1
            positions[ticker]['last_trade_date'] = tx['transaction_date']
            
            if tx_type == 'Purchase':
                positions[ticker]['total_bought'] += amount
                positions[ticker]['net_position'] += amount
            elif tx_type in ['Sale', 'Sale (partial)', 'Sale (full)']:
                positions[ticker]['total_sold'] += amount
                positions[ticker]['net_position'] -= amount
                
                # Full sale = position closed
                if tx_type == 'Sale (full)':
                    positions[ticker]['net_position'] = 0
        
        # Filter to active positions (net > 0)
        active_positions = {k: v for k, v in positions.items() if v['net_position'] > 0}
        
        if not active_positions:
            continue
        
        # Calculate portfolio metrics
        total_portfolio_value = sum(p['net_position'] for p in active_positions.values())
        
        # Sector allocation
        sector_values = {}
        for ticker, pos in active_positions.items():
            sector = pos['sector']
            sector_values[sector] = sector_values.get(sector, 0) + pos['net_position']
        
        sector_allocation = {
            sector: round(value / total_portfolio_value * 100, 1) 
            for sector, value in sorted(sector_values.items(), key=lambda x: -x[1])
        }
        
        # Top holdings
        top_holdings = sorted(
            active_positions.items(),
            key=lambda x: -x[1]['net_position']
        )[:10]
        
        # Concentration metrics
        top_5_concentration = sum(h[1]['net_position'] for h in top_holdings[:5]) / total_portfolio_value * 100
        position_count = len(active_positions)
        
        # Calculate confidence
        total_trades = member_txs.shape[0]
        last_trade = member_txs['transaction_date'].max()
        avg_range_precision = member_txs['range_ratio'].mean()
        first_trade = member_txs['transaction_date'].min()
        years_history = (datetime.now() - first_trade).days / 365 if not pd.isna(first_trade) else 0
        
        confidence_score, confidence_factors = calculate_confidence_score(
            total_trades, last_trade, avg_range_precision, years_history
        )
        
        # Build portfolio record
        portfolio = {
            'member_key': member_id,
            'estimated_portfolio_value': total_portfolio_value,
            'portfolio_value_low': total_portfolio_value * 0.7,  # Conservative estimate
            'portfolio_value_high': total_portfolio_value * 1.5,  # Aggressive estimate
            'position_count': position_count,
            'top_5_concentration': round(top_5_concentration, 1),
            'largest_position_ticker': top_holdings[0][0] if top_holdings else '',
            'largest_position_value': top_holdings[0][1]['net_position'] if top_holdings else 0,
            'sector_allocation': sector_allocation,
            'top_sector': list(sector_allocation.keys())[0] if sector_allocation else 'Other',
            'top_sector_pct': list(sector_allocation.values())[0] if sector_allocation else 0,
            'total_trades': total_trades,
            'total_bought': sum(p['total_bought'] for p in positions.values()),
            'total_sold': sum(p['total_sold'] for p in positions.values()),
            'first_trade_date': first_trade.strftime('%Y-%m-%d') if not pd.isna(first_trade) else None,
            'last_trade_date': last_trade.strftime('%Y-%m-%d') if not pd.isna(last_trade) else None,
            'confidence_score': round(confidence_score, 1),
            'confidence_factors': confidence_factors,
        }
        
        portfolio['top_holdings'] = [
            {'ticker': t, 'value': h['net_position'], 'sector': h['sector']}
            for t, h in top_holdings[:5]
        ]
        
        portfolios.append(portfolio)
        
        # Store individual holdings
        for ticker, pos in active_positions.items():
            holdings_details.append({
                'member_key': member_id,
                'ticker': ticker,
                'asset_description': pos['asset_description'],
                'estimated_value': pos['net_position'],
                'sector': pos['sector'],
                'pct_of_portfolio': round(pos['net_position'] / total_portfolio_value * 100, 2),
                'trade_count': pos['trade_count'],
                'last_trade_date': pos['last_trade_date'].strftime('%Y-%m-%d') if pos['last_trade_date'] else None,
            })
    
    portfolios_df = pd.DataFrame(portfolios)
    holdings_df = pd.DataFrame(holdings_details)
    
    if not portfolios_df.empty:
        # Add member names
        if not members_df.empty:
            name_col = None
            for col in ['member_key', 'bioguide_id', 'member_bioguide_id']:
                if col in members_df.columns:
                    name_col = col
                    break
            
            if name_col:
                # Ensure both keys are the same type (string)
                portfolios_df['member_key'] = portfolios_df['member_key'].astype(str)
                members_df[name_col] = members_df[name_col].astype(str)
                
                name_fields = [name_col]
                for col in ['full_name', 'name', 'first_name', 'last_name', 'party', 'state']:
                    if col in members_df.columns:
                        name_fields.append(col)
                
                portfolios_df = portfolios_df.merge(
                    members_df[name_fields].drop_duplicates(),
                    on='member_key',
                    how='left'
                )
                
                if 'full_name' in portfolios_df.columns:
                    portfolios_df['name'] = portfolios_df['full_name']
                elif 'name' not in portfolios_df.columns:
                    portfolios_df['name'] = portfolios_df['member_key']
        
        portfolios_df['dt_computed'] = datetime.utcnow().isoformat()
        portfolios_df = portfolios_df.sort_values('estimated_portfolio_value', ascending=False)
    
    if not holdings_df.empty:
        holdings_df['dt_computed'] = datetime.utcnow().isoformat()
    
    logger.info(f"Reconstructed {len(portfolios_df)} portfolio snapshots")
    return portfolios_df, holdings_df


def write_to_s3(df: pd.DataFrame, table_name: str):
    """Write to S3."""
    if df.empty:
        return
    
    s3 = boto3.client('s3')
    s3_key = f'gold/aggregates/{table_name}/part-0000.parquet'
    
    buffer = BytesIO()
    df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
    buffer.seek(0)
    
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
    logger.info(f"Wrote {len(df)} records to s3://{BUCKET_NAME}/{s3_key}")


def write_to_local(df: pd.DataFrame, table_name: str):
    """Write to local gold layer."""
    if df.empty:
        return
    
    output_dir = Path(f'data/gold/aggregates/{table_name}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
    logger.info(f"Wrote {len(df)} records to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Reconstruct Congressional Portfolios')
    parser.add_argument('--local', action='store_true', help='Use local data instead of S3')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - do not write output')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Portfolio Reconstruction Engine")
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
    
    # Reconstruct portfolios
    portfolios_df, holdings_df = reconstruct_portfolio(transactions_df, members_df)
    
    if not portfolios_df.empty:
        logger.info(f"\nPORTFOLIO RECONSTRUCTION Summary:")
        logger.info(f"  Total portfolios: {len(portfolios_df)}")
        logger.info(f"  Total estimated value: ${portfolios_df['estimated_portfolio_value'].sum():,.0f}")
        logger.info(f"  Avg portfolio value: ${portfolios_df['estimated_portfolio_value'].mean():,.0f}")
        logger.info(f"  Avg confidence score: {portfolios_df['confidence_score'].mean():.1f}/100")
        
        logger.info(f"\n  Top 5 Largest Portfolios:")
        for _, row in portfolios_df.head(5).iterrows():
            name = row.get('name', row['member_key'])
            logger.info(f"    {name}: ${row['estimated_portfolio_value']:,.0f} ({row['position_count']} positions)")
        
        if not args.dry_run:
            if args.local:
                write_to_local(portfolios_df, 'agg_portfolio_reconstruction')
                write_to_local(holdings_df, 'agg_portfolio_holdings')
            else:
                write_to_s3(portfolios_df, 'agg_portfolio_reconstruction')
                write_to_s3(holdings_df, 'agg_portfolio_holdings')
    
    logger.info("\n✅ Portfolio reconstruction complete!")


if __name__ == '__main__':
    main()
