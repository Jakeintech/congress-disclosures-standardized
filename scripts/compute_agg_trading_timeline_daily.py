#!/usr/bin/env python3
"""
Compute agg_trading_timeline_daily aggregate table.
Aggregates trading volume and counts by day.
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

def load_transactions(bucket_name: str) -> pd.DataFrame:
    """Load transactions from gold layer."""
    fact_path = Path('data/gold/house/financial/facts/fact_ptr_transactions')
    if not fact_path.exists(): return pd.DataFrame()
    files = list(fact_path.glob("**/*.parquet"))
    if not files: return pd.DataFrame()
    return pd.concat([pd.read_parquet(f) for f in files])

def compute_timeline(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Compute daily trading timeline."""
    logger.info("Computing trading timeline...")
    
    if transactions_df.empty:
        return pd.DataFrame()
        
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0) + transactions_df.get('amount_high', 0)
        ) / 2
        
    if 'transaction_date' not in transactions_df.columns and 'transaction_date_key' in transactions_df.columns:
        transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce')

    # Group by date
    timeline = transactions_df.groupby('transaction_date').agg({
        'amount_midpoint': 'sum',
        'transaction_key': 'count',
        'member_key': 'nunique'
    }).reset_index()
    
    timeline.columns = ['date', 'total_volume', 'transaction_count', 'unique_traders']
    
    # Add rolling averages
    timeline = timeline.sort_values('date')
    timeline['volume_7d_avg'] = timeline['total_volume'].rolling(window=7).mean()
    timeline['count_7d_avg'] = timeline['transaction_count'].rolling(window=7).mean()
    
    return timeline

def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write agg_trading_timeline_daily to gold layer."""
    logger.info("Writing to gold layer...")
    output_dir = Path('data/gold/aggregates/agg_trading_timeline_daily')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
    logger.info(f"Wrote {len(df)} records to {output_file}")

def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
    transactions_df = load_transactions(bucket_name)
    stats_df = compute_timeline(transactions_df)
    write_to_gold(stats_df, bucket_name)

if __name__ == '__main__':
    main()
