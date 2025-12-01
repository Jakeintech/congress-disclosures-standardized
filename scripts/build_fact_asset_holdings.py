#!/usr/bin/env python3
"""
Build Gold Layer: Fact Asset Holdings
Reads Silver layer structured JSONs (Schedule A), joins with dimensions, and writes Parquet.
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
# Assuming structured JSONs for Schedule A are in 'structured_code'
SILVER_DIR = DATA_DIR / "silver" / "house" / "financial" / "structured_code" 
GOLD_DIR = DATA_DIR / "gold" / "house" / "financial" / "facts" / "fact_asset_holdings"
DIM_MEMBERS_PATH = DATA_DIR / "gold" / "dimensions" / "dim_members"

def get_date_key(date_str):
    """Convert YYYY-MM-DD to YYYYMMDD integer key."""
    if not date_str or date_str == 'None':
        return None
    try:
        if isinstance(date_str, (int, float)):
             return None
        if len(str(date_str)) >= 10:
            dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            return int(dt.strftime("%Y%m%d"))
        return None
    except ValueError:
        return None

def parse_range(range_str):
    """Parse value/income range string into low/high values."""
    if not range_str:
        return 0.0, 0.0
    
    clean = str(range_str).replace('$', '').replace(',', '').strip()
    
    if ' - ' in clean:
        parts = clean.split(' - ')
        try:
            low = float(parts[0])
            high = float(parts[1])
            return low, high
        except:
            pass
            
    if 'Over' in clean:
        try:
            val = float(clean.replace('Over', '').strip())
            return val, val * 2
        except:
            pass
            
    return 0.0, 0.0

def categorize_asset(description):
    """Categorize asset based on description keywords."""
    if not description:
        return "Other"
    
    desc = description.lower()
    if any(x in desc for x in ['stock', 'corp', 'inc', 'company', 'common']):
        return "Stock"
    if any(x in desc for x in ['fund', 'etf', 'ishares', 'vanguard', 'spdr']):
        return "Fund"
    if any(x in desc for x in ['bond', 'note', 'treasury', 'municipal']):
        return "Bond"
    if any(x in desc for x in ['bank', 'cash', 'checking', 'savings']):
        return "Cash"
    if any(x in desc for x in ['real estate', 'property', 'land', 'residential', 'commercial']):
        return "Real Estate"
    if any(x in desc for x in ['llc', 'lp', 'partnership']):
        return "Business Entity"
    if any(x in desc for x in ['trust']):
        return "Trust"
        
    return "Other"

def generate_holding_key(row):
    """Generate unique key for holding."""
    raw = f"{row['doc_id']}_{row['asset_description']}_{row['value_code']}"
    return hashlib.md5(raw.encode()).hexdigest()

def process_year(year):
    """Process all filings for a specific year."""
    logger.info(f"Processing year {year}...")
    
    # Check if we have structured JSONs or Parquet for Schedule A
    # Based on previous steps, 'structured' dir was missing, but 'ptr_transactions' existed.
    # We might need to sync 'structured' from S3 if it exists there, or 'asset_holdings' if that exists.
    # For now, I'll assume we need to sync 'structured' or find the right path.
    # I'll use a placeholder path and let the user/agent fix it after listing dirs.
    
    year_path = SILVER_DIR / f"year={year}"
    if not year_path.exists():
        logger.warning(f"No silver data found for year {year} at {year_path}")
        return
        
    # We need to look recursively because structured_code has filing_type=X/doc_id.json
    files = list(year_path.glob("**/*.json"))
    logger.info(f"Found {len(files)} files")
    
    holdings = []
    
    for json_file in files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            doc_id = data.get('doc_id')
            filing_date = data.get('filing_date')
            member_id = data.get('bioguide_id', 'UNKNOWN')
            
            # Process Schedule A (Assets)
            if 'aggs' in data and 'schedule_a' in data['aggs']:
                for asset in data['aggs']['schedule_a']:
                    val_low, val_high = parse_range(asset.get('value'))
                    inc_low, inc_high = parse_range(asset.get('income'))
                    
                    record = {
                        'doc_id': doc_id,
                        'year': year,
                        'member_key': member_id,
                        'asset_key': asset.get('asset_name', 'UNKNOWN'), # Use name as key for now
                        'filing_date_key': get_date_key(filing_date),
                        'asset_description': asset.get('asset_name'),
                        'asset_category': categorize_asset(asset.get('asset_name')),
                        'location_city': asset.get('city'),
                        'location_state': asset.get('state'),
                        'value_code': asset.get('value'),
                        'value_low': val_low,
                        'value_high': val_high,
                        'income_type': asset.get('income_type'),
                        'income_amount_code': asset.get('income'),
                        'income_low': inc_low,
                        'income_high': inc_high,
                        'confidence_score': 1.0
                    }
                    
                    record['holding_key'] = generate_holding_key(record)
                    holdings.append(record)
                    
        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
            
    if not holdings:
        logger.warning("No holdings found")
        return

    df = pd.DataFrame(holdings)
    df['year'] = df['year'].astype(int)
    
    output_path = GOLD_DIR / f"year={year}"
    output_path.mkdir(parents=True, exist_ok=True)
    
    table = pa.Table.from_pandas(df)
    pq.write_table(table, output_path / "part-0000.parquet")
    
    logger.info(f"Wrote {len(df)} holdings to {output_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, help='Process specific year')
    args = parser.parse_args()
    
    if args.year:
        process_year(args.year)
    else:
        # Process all years found
        if SILVER_DIR.exists():
            years = [int(p.name.split('=')[1]) for p in SILVER_DIR.glob("year=*")]
            for year in sorted(years):
                process_year(year)

if __name__ == "__main__":
    main()
