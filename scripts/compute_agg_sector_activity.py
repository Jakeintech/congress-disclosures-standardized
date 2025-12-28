#!/usr/bin/env python3
"""
Compute agg_sector_activity aggregate table.
Analyzes trading activity by sector (derived from asset descriptions or external enrichment).
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
    """Load transactions from gold layer (fact_ptr_transactions)."""
    logger.info("Loading transactions from gold layer...")
    fact_path = Path('data/gold/house/financial/facts/fact_ptr_transactions')
    if not fact_path.exists():
        return pd.DataFrame()
    files = list(fact_path.glob("**/*.parquet"))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(f) for f in files])

def derive_sector(row):
    """Simple heuristic to derive sector from asset description."""
    desc = str(row.get('asset_description', '')).lower()
    if 'tech' in desc or 'software' in desc or 'apple' in desc or 'microsoft' in desc:
        return 'Technology'
    if 'pharm' in desc or 'health' in desc or 'pfizer' in desc:
        return 'Healthcare'
    if 'bank' in desc or 'financial' in desc or 'chase' in desc:
        return 'Financials'
    if 'energy' in desc or 'oil' in desc or 'gas' in desc:
        return 'Energy'
    if 'real estate' in desc or 'reit' in desc:
        return 'Real Estate'
    return 'Other'

def compute_sector_activity(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Compute trading statistics by sector."""
    logger.info("Computing sector activity statistics...")
    
    if transactions_df.empty:
        return pd.DataFrame()
        
    if 'amount_midpoint' not in transactions_df.columns:
        transactions_df['amount_midpoint'] = (
            transactions_df.get('amount_low', 0) + transactions_df.get('amount_high', 0)
        ) / 2
        
    # Enrich with sector
    transactions_df['sector'] = transactions_df.apply(derive_sector, axis=1)

    stats = []
    
    for sector, group in transactions_df.groupby('sector'):
        total_volume = group['amount_midpoint'].sum()
        buy_volume = group[group['transaction_type'] == 'Purchase']['amount_midpoint'].sum()
        sell_volume = group[group['transaction_type'] == 'Sale']['amount_midpoint'].sum()
        
        unique_traders = group['member_key'].nunique()
        unique_assets = group['asset_key'].nunique()
        
        record = {
            'sector': sector,
            'total_trades': len(group),
            'total_volume': total_volume,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'net_flow': buy_volume - sell_volume,
            'unique_traders': unique_traders,
            'unique_assets': unique_assets,
            'last_traded': group['transaction_date_key'].max()
        }
        stats.append(record)
        
    return pd.DataFrame(stats)

def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write agg_sector_activity to gold layer."""
    logger.info("Writing to gold layer...")
    output_dir = Path('data/gold/aggregates/agg_sector_activity')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
    logger.info(f"Wrote {len(df)} records to {output_file}")

def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
    transactions_df = load_transactions(bucket_name)
    stats_df = compute_sector_activity(transactions_df)
    write_to_gold(stats_df, bucket_name)

if __name__ == '__main__':
    main()
