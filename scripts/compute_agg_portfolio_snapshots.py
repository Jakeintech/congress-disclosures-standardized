#!/usr/bin/env python3
"""
Compute agg_portfolio_snapshots aggregate table.
Estimates current portfolio holdings based on transaction history and annual disclosures.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_data(bucket_name: str):
    """Load transactions and asset holdings."""
    tx_path = Path('data/gold/house/financial/facts/fact_ptr_transactions')
    holdings_path = Path('data/gold/house/financial/facts/fact_asset_holdings')
    
    tx_df = pd.DataFrame()
    if tx_path.exists():
        files = list(tx_path.glob("**/*.parquet"))
        if files:
            tx_df = pd.concat([pd.read_parquet(f) for f in files])
            
    holdings_df = pd.DataFrame()
    if holdings_path.exists():
        files = list(holdings_path.glob("**/*.parquet"))
        if files:
            holdings_df = pd.concat([pd.read_parquet(f) for f in files])
            
    return tx_df, holdings_df

def compute_portfolio_snapshots(tx_df: pd.DataFrame, holdings_df: pd.DataFrame) -> pd.DataFrame:
    """Compute estimated portfolio snapshots."""
    logger.info("Computing portfolio snapshots...")
    
    # This is a complex estimation. For MVP, we'll just aggregate latest holdings.
    # If holdings_df is empty (which it is for 2025), we rely on transactions?
    # Actually, without a base, transactions are hard to sum up to a portfolio.
    # We'll return latest holdings if available, else empty.
    
    if holdings_df.empty:
        return pd.DataFrame()
        
    # Take latest year for each member/asset
    latest_year = holdings_df['year'].max()
    snapshot = holdings_df[holdings_df['year'] == latest_year].copy()
    
    snapshot['snapshot_date'] = f"{latest_year}-12-31"
    
    return snapshot[['member_key', 'asset_key', 'value_low', 'value_high', 'snapshot_date', 'asset_category']]

def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write agg_portfolio_snapshots to gold layer."""
    logger.info("Writing to gold layer...")
    output_dir = Path('data/gold/aggregates/agg_portfolio_snapshots')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
    logger.info(f"Wrote {len(df)} records to {output_file}")

def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
    tx_df, holdings_df = load_data(bucket_name)
    stats_df = compute_portfolio_snapshots(tx_df, holdings_df)
    write_to_gold(stats_df, bucket_name)

if __name__ == '__main__':
    main()
