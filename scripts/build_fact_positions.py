#!/usr/bin/env python3
"""
Build Gold Layer: Fact Positions
Reads Silver layer structured JSONs (Schedule E), joins with dimensions, and writes Parquet.
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
SILVER_DIR = DATA_DIR / "silver" / "house" / "financial" / "structured_code"
GOLD_DIR = DATA_DIR / "gold" / "house" / "financial" / "facts" / "fact_positions"
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

def generate_position_key(row):
    """Generate unique key for position."""
    raw = f"{row['doc_id']}_{row['organization']}_{row['position_title']}"
    return hashlib.md5(raw.encode()).hexdigest()

def process_year(year):
    """Process all filings for a specific year."""
    logger.info(f"Processing year {year}...")
    
    year_path = SILVER_DIR / f"year={year}"
    if not year_path.exists():
        logger.warning(f"No silver data found for year {year} at {year_path}")
        return
        
    files = list(year_path.glob("**/*.json"))
    logger.info(f"Found {len(files)} files")
    
    positions = []
    
    for json_file in files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            doc_id = data.get('doc_id')
            filing_date = data.get('filing_date')
            member_id = data.get('bioguide_id', 'UNKNOWN')
            
            # Process Schedule E (Positions)
            if 'aggs' in data and 'schedule_e' in data['aggs']:
                for item in data['aggs']['schedule_e']:
                    record = {
                        'doc_id': doc_id,
                        'year': year,
                        'member_key': member_id,
                        'filing_date_key': get_date_key(filing_date),
                        'organization': item.get('organization'),
                        'position_title': item.get('position'),
                        'confidence_score': 1.0
                    }
                    
                    record['position_key'] = generate_position_key(record)
                    positions.append(record)
                    
        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
            
    if not positions:
        logger.warning("No positions found")
        return

    df = pd.DataFrame(positions)
    df['year'] = df['year'].astype(int)
    
    output_path = GOLD_DIR / f"year={year}"
    output_path.mkdir(parents=True, exist_ok=True)
    
    table = pa.Table.from_pandas(df)
    pq.write_table(table, output_path / "part-0000.parquet")
    
    logger.info(f"Wrote {len(df)} positions to {output_path}")

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
