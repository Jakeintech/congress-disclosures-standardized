#!/usr/bin/env python3
"""
Build Gold Layer: Fact PTR Transactions
Reads Silver layer structured JSONs (Type P), extracts transactions, and writes Parquet.
"""

import os
import sys
import json
import logging
import hashlib
import io
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import boto3

# Add lib paths
# Add lib paths
sys.path.insert(0, str(Path(__file__).parent.parent)) # Add Root
sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion")) # Add Ingestion
sys.path.insert(0, str(Path(__file__).parent)) # Add Scripts

from lib.terraform_config import get_aws_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
config = get_aws_config()
S3_BUCKET = config.get("s3_bucket_id")
S3_REGION = config.get("s3_region", "us-east-1")

if not S3_BUCKET:
    logger.error("Missing required configuration.")
    sys.exit(1)

s3 = boto3.client('s3', region_name=S3_REGION)

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

def generate_transaction_key(row):
    """Generate unique key for transaction."""
    raw = f"{row['doc_id']}_{row['transaction_date']}_{row['ticker']}_{row['amount']}_{row['transaction_type']}_{row['asset_description']}"
    return hashlib.md5(raw.encode()).hexdigest()

def parse_amount_string(amount_str):
    """Parse amount range string into low and high values."""
    if not amount_str:
        return None, None
    
    # Remove currency symbols, commas, and newlines
    clean = str(amount_str).replace('$', '').replace(',', '').replace('\n', ' ').strip()
    
    low = None
    high = None
    
    try:
        if ' - ' in clean:
            parts = clean.split(' - ')
            low = float(parts[0])
            if len(parts) > 1:
                high = float(parts[1])
        elif '-' in clean: # handling potential missing spaces
             parts = clean.split('-')
             low = float(parts[0])
             if len(parts) > 1:
                 high = float(parts[1])
        elif 'Over' in clean: # e.g. "Over 50000000"
            val = clean.replace('Over', '').strip()
            low = float(val)
        else:
            # Try to parse single number if possible
             try:
                 low = float(clean)
             except:
                 pass
    except:
        pass
        
    return low, high

def get_transaction_type(tx):
    """Map trans_type code to full name."""
    tt = tx.get('trans_type') or tx.get('transaction_type')
    if not tt:
        return None
    
    tt = tt.upper().strip()
    if tt == 'P':
        return 'Purchase'
    elif tt == 'S':
        return 'Sale'
    elif tt == 'E':
        return 'Exchange'
    return tt


def extract_ticker_from_description(asset_desc: str) -> str:
    """
    Extract stock ticker from asset description.
    
    Common patterns:
    - "AAPL - Apple Inc Common Stock"
    - "Apple Inc (AAPL)"
    - "Stock: MSFT"
    - "NVIDIA Corp Common Stock [NVDA]"
    """
    import re
    
    if not asset_desc:
        return None
    
    desc = str(asset_desc).strip()
    
    # Pattern 1: Ticker at start followed by dash (e.g., "AAPL - Apple Inc")
    match = re.match(r'^([A-Z]{1,5})\s*[-–—]', desc)
    if match:
        return match.group(1)
    
    # Pattern 2: Ticker in parentheses (e.g., "Apple Inc (AAPL)")
    match = re.search(r'\(([A-Z]{1,5})\)', desc)
    if match:
        return match.group(1)
    
    # Pattern 3: Ticker in brackets (e.g., "[AAPL]")
    match = re.search(r'\[([A-Z]{1,5})\]', desc)
    if match:
        return match.group(1)
    
    # Pattern 4: "Stock: TICKER" or "Ticker: TICKER"
    match = re.search(r'(?:Stock|Ticker):\s*([A-Z]{1,5})', desc, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Pattern 5: Standalone ticker at start (all caps 1-5 letters followed by space)
    match = re.match(r'^([A-Z]{1,5})\s+(?:[A-Z][a-z])', desc)
    if match:
        # Verify it's not a common word
        potential = match.group(1)
        common_words = {'NEW', 'THE', 'INC', 'LLC', 'LTD', 'CO', 'CORP', 'ETF', 'FUND', 'STOCK'}
        if potential not in common_words:
            return potential
    
    return None

import duckdb

def process_year(year):
    """Process consolidated Silver Tabular data for a specific year using DuckDB."""
    logger.info(f"Processing year {year} using DuckDB and Silver Tabular...")

    try:
        # 1. Setup DuckDB with S3 access
        con = duckdb.connect(database=':memory:')
        con.execute("INSTALL httpfs;")
        con.execute("LOAD httpfs;")
        con.execute(f"SET s3_region='{S3_REGION}';")
        
        # 2. Define source paths (Hive-partitioned)
        # Tabular transactions (Type P)
        tabular_path = f"s3://{S3_BUCKET}/silver/house/financial/tabular/year={year}/filing_type=P/transactions.parquet"
        
        # Check if file exists before DuckDB attempt to avoid 404
        s3_check = boto3.client('s3', region_name=S3_REGION)
        try:
            s3_check.head_object(Bucket=S3_BUCKET, Key=f"silver/house/financial/tabular/year={year}/filing_type=P/transactions.parquet")
        except:
            logger.warning(f"No tabular transactions found in S3 for year {year} at {tabular_path} - skipping.")
            return

        # Filings metadata (Silver)
        filings_path = f"s3://{S3_BUCKET}/silver/house/financial/filings/year={year}/*.parquet"

        # 3. Query and Join using DuckDB
        # We perform the enrichment (bioguide_id, party, etc.) via the filings join 
        # and then apply the same extraction logic for amounts/tickers.
        query = f"""
            SELECT 
                t.*,
                f.first_name,
                f.last_name,
                f.state_district,
                f.bioguide_id as filing_bioguide_id
            FROM read_parquet('{tabular_path}') t
            LEFT JOIN read_parquet('{filings_path}') f ON t.doc_id = f.doc_id
        """
        df = con.execute(query).df()
        
        if df.empty:
            logger.warning(f"No transactions found for year {year} in tabular layer")
            return

        logger.info(f"Loaded {len(df):,} transactions from Silver Tabular via DuckDB")

        # 4. Final processing (computational logic that's easier in Python)
        transactions = []
        
        # Load SimpleMemberLookup for additional enrichment if needed
        from lib.simple_member_lookup import SimpleMemberLookup
        member_lookup = SimpleMemberLookup()

        for _, row in df.iterrows():
            doc_id = row['doc_id']
            first = row['first_name']
            last = row['last_name']
            state_district = row['state_district']
            bioguide_id = row['filing_bioguide_id']
            
            # Additional enrichment if bioguide_id missing from filings join
            party = None
            state = None
            chamber = None
            
            if member_lookup and first and last:
                state_hint = state_district[:2] if state_district else None
                enriched = member_lookup.enrich_member(
                    first_name=first,
                    last_name=last,
                    state=state_hint
                )
                bioguide_id = bioguide_id or enriched.get('bioguide_id')
                party = enriched.get('party')
                state = enriched.get('state') or state_hint
                chamber = enriched.get('chamber')

            tx_date = row.get('transaction_date') or row.get('trans_date')
            notif_date = row.get('notification_date') or row.get('notif_date')
            amt_low, amt_high = parse_amount_string(row.get('amount'))
            
            asset_description = row.get('asset_name') or row.get('asset_description')
            owner_code = row.get('owner') or row.get('owner_code')
            
            record = {
                'doc_id': doc_id,
                'filing_year': year,
                'filing_date': row.get('filing_date'),
                'filing_date_key': get_date_key(row.get('filing_date')),
                'filer_name': f"{first} {last}" if first and last else None,
                'first_name': first,
                'last_name': last,
                'state_district': state_district,
                'bioguide_id': bioguide_id,
                'parent_bioguide_id': bioguide_id,
                'member_key': bioguide_id,
                'asset_key': abs(hash(str(asset_description))) % 1000000 + 1 if asset_description else None,
                'party': party,
                'state': state,
                'chamber': chamber,
                'transaction_date': tx_date,
                'transaction_date_key': get_date_key(tx_date),
                'notification_date': notif_date,
                'notification_date_key': get_date_key(notif_date),
                'owner_code': owner_code,
                'is_spouse_transaction': (owner_code == 'SP'),
                'is_dependent_child_transaction': (owner_code == 'DC'),
                'ticker': row.get('ticker') or extract_ticker_from_description(asset_description),
                'asset_description': asset_description,
                'asset_type': row.get('asset_type') or row.get('type_code'),
                'transaction_type': get_transaction_type({'transaction_type': row.get('transaction_type')}),
                'amount': row.get('amount'),
                'amount_low': amt_low,
                'amount_high': amt_high,
                'comment': row.get('comment'),
                'cap_gains_over_200': row.get('cap_gains_over_200', False)
            }
            record['transaction_key'] = generate_transaction_key(record)
            transactions.append(record)

        # 5. Write Gold
        df_gold = pd.DataFrame(transactions)
        output_key = f"gold/house/financial/facts/fact_ptr_transactions/year={year}/part-0000.parquet"
        
        buffer = io.BytesIO()
        df_gold.to_parquet(buffer, index=False, engine="pyarrow")
        s3.put_object(
            Bucket=S3_BUCKET, 
            Key=output_key, 
            Body=buffer.getvalue(),
            ContentType="application/x-parquet"
        )
        logger.info(f"Processed {len(df_gold)} transactions from Silver Tabular via DuckDB")

    except Exception as e:
        logger.error(f"DuckDB processing failed for year {year}: {e}")
        # Revert to non-duckdb fallback if necessary, but here we expect duckdb to be available
        raise

    if not transactions:
        logger.warning(f"No transactions found for year {year}")
        return

    df = pd.DataFrame(transactions)
    
    # Ensure types
    df['filing_year'] = df['filing_year'].astype(int)
    
    # Write to S3
    output_key = f"gold/house/financial/facts/fact_ptr_transactions/year={year}/part-0000.parquet"
    
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    buffer.seek(0)
    
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=output_key,
        Body=buffer.getvalue(),
        ContentType="application/x-parquet"
    )
    
    logger.info(f"Processed {filing_count} filings, wrote {len(df)} transactions to s3://{S3_BUCKET}/{output_key}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, help='Process specific year')
    args = parser.parse_args()
    
    if args.year:
        process_year(args.year)
    else:
        # Default to current year + next year
        current_year = datetime.now().year
        process_year(current_year)
        process_year(current_year + 1)

if __name__ == "__main__":
    main()

