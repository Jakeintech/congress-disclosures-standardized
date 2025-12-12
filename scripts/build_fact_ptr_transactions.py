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

def process_year(year):
    """Process all Type P filings for a specific year."""
    logger.info(f"Processing year {year}...")

    # Load Silver filings table to get member names
    try:
        filings_key = f"silver/house/financial/filings/year={year}/part-0000.parquet"
        response = s3.get_object(Bucket=S3_BUCKET, Key=filings_key)
        filings_df = pd.read_parquet(io.BytesIO(response['Body'].read()))
        filings_dict = filings_df.set_index('doc_id').to_dict('index')
        logger.info(f"Loaded {len(filings_df)} filings from Silver layer")
    except Exception as e:
        logger.error(f"Could not load filings table: {e}")
        filings_dict = {}

    # Scan silver/objects/filing_type=type_p/year={year}/
    prefix = f"silver/objects/filing_type=type_p/year={year}/"

    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)

    transactions = []
    filing_count = 0

    # Initialize member lookup for enrichment
    try:
        from lib.simple_member_lookup import SimpleMemberLookup
        member_lookup = SimpleMemberLookup()
        logger.info("Initialized SimpleMemberLookup for enrichment")
    except ImportError as e:
        # Try alternate import path just in case
        try:
             from ingestion.lib.simple_member_lookup import SimpleMemberLookup
             member_lookup = SimpleMemberLookup()
             logger.info("Initialized SimpleMemberLookup via fully qualified path")
        except ImportError:
             logger.warning(f"Could not import SimpleMemberLookup: {e}, skipping enrichment")
             member_lookup = None

    for page in pages:
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            key = obj['Key']
            if key.endswith("extraction.json"):
                try:
                    response = s3.get_object(Bucket=S3_BUCKET, Key=key)
                    data = json.loads(response['Body'].read())
                    
                    doc_id = data.get('doc_id')
                    filing_date = data.get('filing_date')

                    # Get member info from filings table
                    filing_info = filings_dict.get(doc_id, {})
                    first = filing_info.get('first_name')
                    last = filing_info.get('last_name')
                    state_district = filing_info.get('state_district')
                    filer_name = f"{first} {last}" if first and last else None

                    # Enrich with bioguide_id if available
                    bioguide_id = None
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
                        bioguide_id = enriched.get('bioguide_id')
                        party = enriched.get('party')
                        state = enriched.get('state') or state_hint
                        chamber = enriched.get('chamber')

                    # Get transactions list
                    # The extraction Lambda puts them in 'transactions' list for Type P
                    doc_transactions = data.get('transactions', [])
                    
                    if not doc_transactions:
                        continue
                        
                    filing_count += 1
                    
                    for tx in doc_transactions:
                        # Extract fields with defaults
                        tx_date = tx.get('transaction_date') or tx.get('trans_date')
                        
                        # Parse amount
                        amt_low, amt_high = parse_amount_string(tx.get('amount'))

                        record = {
                            'doc_id': doc_id,
                            'filing_year': year,
                            'filing_date': filing_date,
                            'filing_date_key': get_date_key(filing_date),
                            'filer_name': filer_name,
                            'first_name': first,
                            'last_name': last,
                            'state_district': state_district,
                            'bioguide_id': bioguide_id,
                            'party': party,
                            'state': state,
                            'chamber': chamber,
                            
                            'transaction_date': tx_date,
                            'transaction_date_key': get_date_key(tx_date),
                            'owner': tx.get('owner') or tx.get('owner_code'),
                            'ticker': tx.get('ticker') or extract_ticker_from_description(tx.get('asset_name') or tx.get('asset_description')),
                            'asset_description': tx.get('asset_name') or tx.get('asset_description'),
                            'asset_type': tx.get('asset_type') or tx.get('type_code'),
                            'transaction_type': get_transaction_type(tx),
                            'amount': tx.get('amount'), # Usually a range string like "$1,001 - $15,000"
                            'amount_low': amt_low,
                            'amount_high': amt_high,
                            'comment': tx.get('comment'),
                            'cap_gains_over_200': tx.get('cap_gains_over_200', False)
                        }
                        
                        # Generate unique key
                        record['transaction_key'] = generate_transaction_key(record)
                        
                        transactions.append(record)
                        
                except Exception as e:
                    logger.error(f"Error processing {key}: {e}")

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

