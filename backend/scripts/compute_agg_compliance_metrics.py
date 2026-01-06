#!/usr/bin/env python3
"""
Compute agg_compliance_metrics aggregate table.
Analyzes filing timeliness, amendments, and potential conflicts.
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

def compute_compliance_metrics(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Compute compliance metrics."""
    logger.info("Computing compliance metrics...")
    
    if transactions_df.empty:
        return pd.DataFrame()
        
    # Convert keys to dates
    if 'transaction_date' not in transactions_df.columns and 'transaction_date_key' in transactions_df.columns:
        transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date_key'].astype(str), format='%Y%m%d', errors='coerce')
    
    if 'notification_date' not in transactions_df.columns and 'notification_date_key' in transactions_df.columns:
        transactions_df['notification_date'] = pd.to_datetime(transactions_df['notification_date_key'].astype(str), format='%Y%m%d', errors='coerce')
        
    if 'filing_date' not in transactions_df.columns and 'filing_date_key' in transactions_df.columns:
        transactions_df['filing_date'] = pd.to_datetime(transactions_df['filing_date_key'].astype(str), format='%Y%m%d', errors='coerce')

    stats = []
    
    for member_key, group in transactions_df.groupby('member_key'):
        total_tx = len(group)
        
        # Calculate days to file
        # STOCK Act requires filing within 45 days of transaction or 30 days of notification
        # We'll use transaction date for simplicity if notification missing
        
        valid_dates = group.dropna(subset=['transaction_date', 'filing_date'])
        if valid_dates.empty:
            continue
            
        valid_dates['days_to_file'] = (valid_dates['filing_date'] - valid_dates['transaction_date']).dt.days
        
        avg_days = valid_dates['days_to_file'].mean()
        max_days = valid_dates['days_to_file'].max()
        late_filings = len(valid_dates[valid_dates['days_to_file'] > 45])
        
        record = {
            'member_key': member_key,
            'total_transactions': total_tx,
            'avg_days_to_file': avg_days,
            'max_days_to_file': max_days,
            'late_filings_count': late_filings,
            'late_filing_rate': late_filings / total_tx if total_tx > 0 else 0
        }
        stats.append(record)
        
    return pd.DataFrame(stats)

def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write agg_compliance_metrics to gold layer."""
    logger.info("Writing to gold layer...")
    output_dir = Path('data/gold/aggregates/agg_compliance_metrics')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
    logger.info(f"Wrote {len(df)} records to {output_file}")

def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
    transactions_df = load_transactions(bucket_name)
    stats_df = compute_compliance_metrics(transactions_df)
    write_to_gold(stats_df, bucket_name)

if __name__ == '__main__':
    main()
