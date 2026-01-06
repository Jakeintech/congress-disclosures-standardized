#!/usr/bin/env python3
"""
Build Gold Layer: Fact Liabilities
Reads Silver layer structured JSONs (Schedule D), joins with dimensions, and writes Parquet.
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
SILVER_DIR = DATA_DIR / "silver" / "objects"
GOLD_DIR = DATA_DIR / "gold" / "house" / "financial" / "facts" / "fact_liabilities"
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
    """Parse value range string into low/high values."""
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

def generate_liability_key(row):
    """Generate unique key for liability."""
    raw = f"{row['doc_id']}_{row['creditor_name']}_{row['value_code']}"
    return hashlib.md5(raw.encode()).hexdigest()

def process_year(year):
    """Process all filings for a specific year."""
    logger.info(f"Processing year {year}...")
    
    year_path = SILVER_DIR / f"year={year}"
    if not year_path.exists():
        logger.warning(f"No silver data found for year {year} at {year_path}")
        return
        
    # We need to look recursively because structured_code has filing_type=X/doc_id.json
    files = list(year_path.glob("**/*.json"))
    logger.info(f"Found {len(files)} files")
    
    liabilities = []
    
    for json_file in files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            doc_id = data.get('doc_id')
            filing_date = data.get('filing_date')
            member_id = data.get('bioguide_id', 'UNKNOWN')
            
            # Process Schedule D (Liabilities)
            if 'aggs' in data and 'schedule_d' in data['aggs']:
                for item in data['aggs']['schedule_d']:
                    val_low, val_high = parse_range(item.get('amount'))
                    
                    record = {
                        'doc_id': doc_id,
                        'year': year,
                        'member_key': member_id,
                        'filing_date_key': get_date_key(filing_date),
                        'creditor_name': item.get('creditor'),
                        'description': item.get('liability_type'), # Mapping 'liability_type' to description
                        'month_incurred': None, # Need to parse date incurred
                        'year_incurred': None,
                        'value_code': item.get('amount'),
                        'value_low': val_low,
                        'value_high': val_high,
                        'interest_rate': item.get('rate'), # Assuming 'rate' field exists
                        'confidence_score': 1.0
                    }
                    
                    # Try to parse year/month from date
                    date_incurred = item.get('date')
                    if date_incurred:
                        try:
                            # Assuming date string like "2023" or "June 2023"
                            if len(date_incurred) == 4 and date_incurred.isdigit():
                                record['year_incurred'] = int(date_incurred)
                            else:
                                # Try parsing
                                pass
                        except:
                            pass

                    record['liability_key'] = generate_liability_key(record)
                    liabilities.append(record)
                    
        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
            
    if not liabilities:
        logger.warning("No liabilities found")
        return

    df = pd.DataFrame(liabilities)
    df['year'] = df['year'].astype(int)
    
    output_path = GOLD_DIR / f"year={year}"
    output_path.mkdir(parents=True, exist_ok=True)
    
    table = pa.Table.from_pandas(df)
    pq.write_table(table, output_path / "part-0000.parquet")
    
    logger.info(f"Wrote {len(df)} liabilities to {output_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, help='Process specific year')
    args = parser.parse_args()
    
    if args.year:
        process_year(args.year)
    else:
        if SILVER_DIR.exists():
            years = [int(p.name.split('=')[1]) for p in SILVER_DIR.glob("year=*")]
            for year in sorted(years):
                process_year(year)

if __name__ == "__main__":
    main()
