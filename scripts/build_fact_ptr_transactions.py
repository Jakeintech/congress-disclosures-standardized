#!/usr/bin/env python3
"""
Build Gold Layer: Fact PTR Transactions
Reads Silver layer structured JSONs (Schedule B), joins with dimensions, and writes Parquet.
"""

import os
import sys
import json
import glob
import logging
import hashlib
from datetime import datetime
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SILVER_DIR = DATA_DIR / "silver" / "house" / "financial" / "ptr_transactions"
GOLD_DIR = DATA_DIR / "gold" / "house" / "financial" / "facts" / "fact_ptr_transactions"
DIM_MEMBERS_PATH = DATA_DIR / "gold" / "dimensions" / "dim_members" # It's a directory of parquet files

def get_date_key(date_str):
    """Convert YYYY-MM-DD to YYYYMMDD integer key."""
    if not date_str or date_str == 'None':
        return None
    try:
        # Handle timestamp or date string
        if isinstance(date_str, (int, float)):
             return None
        # If it's already YYYY-MM-DD
        if len(str(date_str)) >= 10:
            dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            return int(dt.strftime("%Y%m%d"))
        return None
    except ValueError:
        return None

def parse_amount_range(range_str):
    """Parse amount range string into low/high values."""
    if not range_str:
        return 0.0, 0.0
    
    # Clean string
    clean = str(range_str).replace('$', '').replace(',', '').strip()
    
    if ' - ' in clean:
        parts = clean.split(' - ')
        try:
            low = float(parts[0])
            high = float(parts[1])
            return low, high
        except:
            pass
            
    # Handle "Over X" cases
    if 'Over' in clean:
        try:
            val = float(clean.replace('Over', '').strip())
            return val, val * 2 # Estimate high as 2x low for open ranges
        except:
            pass
            
    return 0.0, 0.0

def generate_transaction_key(row):
    """Generate unique key for transaction."""
    raw = f"{row['doc_id']}_{row['transaction_date']}_{row['ticker']}_{row['amount_range']}_{row['transaction_type']}"
    return hashlib.md5(raw.encode()).hexdigest()

def load_dimensions():
    """Load reference dimensions."""
    members = {}
    if DIM_MEMBERS_PATH.exists():
        # Read all parquet files in directory
        files = list(DIM_MEMBERS_PATH.glob("*.parquet"))
        if files:
            df = pd.concat([pd.read_parquet(f) for f in files])
            # Create lookup: bioguide_id -> key (or just verify existence)
            # For now just returning the dataframe or set of IDs
            return set(df['bioguide_id'].unique()) if 'bioguide_id' in df.columns else set()
    return set()

def process_year(year):
    """Process all filings for a specific year."""
    logger.info(f"Processing year {year}...")
    
    # Silver structure: silver/house/financial/ptr_transactions/year=YYYY/part-*.parquet
    year_path = SILVER_DIR / f"year={year}"
    if not year_path.exists():
        logger.warning(f"No silver data found for year {year} at {year_path}")
        return
        
    files = list(year_path.glob("*.parquet"))
    logger.info(f"Found {len(files)} files")
    
    if not files:
        return

    # Read Silver Parquet
    df_silver = pd.concat([pd.read_parquet(f) for f in files])
    
    if df_silver.empty:
        logger.warning("Silver data is empty")
        return

    transactions = []
    
    for _, row in df_silver.iterrows():
        try:
            # Silver columns: doc_id, date, ticker, asset_name, amount_low, amount_high, type, owner, bioguide_id, etc.
            # We need to map these to our Gold schema
            
            doc_id = row.get('doc_id')
            member_id = row.get('bioguide_id', 'UNKNOWN')
            
            # Parse amounts if they are strings, but Silver parquet likely has them as floats/ints or structured
            # Assuming Silver is already somewhat clean
            
            record = {
                'doc_id': doc_id,
                'year': year,
                'member_key': member_id,
                'asset_key': row.get('ticker', 'UNKNOWN'),
                'transaction_date_key': get_date_key(str(row.get('transaction_date'))),
                'notification_date_key': get_date_key(str(row.get('notification_date'))),
                'filing_date_key': get_date_key(str(row.get('filing_date'))),
                'transaction_type': row.get('transaction_type'),
                'owner_code': row.get('owner'),
                'amount_range': row.get('amount_range'), # Assuming this exists or we reconstruct
                'amount_low': row.get('amount_low'),
                'amount_high': row.get('amount_high'),
                'amount_column': 'amount', 
                'ticker': row.get('ticker'),
                'asset_description': row.get('asset_name'),
                'confidence_score': 1.0 
            }
            
            # Generate key
            record['transaction_key'] = generate_transaction_key({
                'doc_id': doc_id,
                'transaction_date': str(row.get('transaction_date')),
                'ticker': row.get('ticker'),
                'amount_range': str(record['amount_low']), # Use low amount for uniqueness if range missing
                'transaction_type': row.get('transaction_type')
            })
            
            transactions.append(record)
            
        except Exception as e:
            logger.error(f"Error processing row: {e}")
            
    if not transactions:
        logger.warning("No transactions processed")
        return

    # Create DataFrame
    df_gold = pd.DataFrame(transactions)
    
    # Ensure types
    df_gold['year'] = df_gold['year'].astype(int)
    
    # Write to Parquet partitioned by year
    output_path = GOLD_DIR / f"year={year}"
    output_path.mkdir(parents=True, exist_ok=True)
    
    table = pa.Table.from_pandas(df_gold)
    pq.write_table(table, output_path / "part-0000.parquet")
    
    logger.info(f"Wrote {len(df_gold)} transactions to {output_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, help='Process specific year')
    args = parser.parse_args()
    
    if args.year:
        process_year(args.year)
    else:
        # Process all years found in Silver
        years = [int(p.name.split('=')[1]) for p in SILVER_DIR.glob("year=*")]
        for year in sorted(years):
            process_year(year)

if __name__ == "__main__":
    main()
