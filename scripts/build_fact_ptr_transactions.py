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

def process_year(year):
    """Process all Type P filings for a specific year."""
    logger.info(f"Processing year {year}...")
    
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
                    
                    # Get bronze metadata
                    bronze_meta = data.get('bronze_metadata', {})
                    filer_name = bronze_meta.get('filer_name') or data.get('document_header', {}).get('filer_name')
                    state_district = bronze_meta.get('state_district')
                    
                    # Enrich with bioguide_id if available
                    bioguide_id = None
                    party = None
                    state = None
                    chamber = None
                    first = None
                    last = None
                    
                    if member_lookup and filer_name:
                         # Clean name
                        import re
                        # Remove trailing state code
                        clean_name = re.sub(r'\s+[A-Z]{2}$', '', str(filer_name)).strip()
                        # Remove prefixes
                        clean_name = re.sub(r'^(Hon\.|Rep\.|Mr\.|Mrs\.|Ms\.|Dr\.)\s+', '', clean_name, flags=re.IGNORECASE)
                        
                        state_hint = state_district[:2] if state_district else None
                        
                        # Try to parse name parts
                        first = None
                        last = clean_name
                        if ',' in clean_name:
                            parts = clean_name.split(',', 1)
                            last = parts[0].strip()
                            first = parts[1].strip()
                        elif ' ' in clean_name:
                            parts = clean_name.split(' ')
                            first = parts[0]
                            last = ' '.join(parts[1:])
                            
                        enriched = member_lookup.enrich_member(
                            first_name=first,
                            last_name=last,
                            state=state_hint
                        )
                        bioguide_id = enriched.get('bioguide_id')
                        party = enriched.get('party')
                        state = enriched.get('state') or state_hint
                        chamber = enriched.get('chamber')
                        
                        if bioguide_id:
                            # Use full name from enrichment if matched
                             pass # we keep logic simple for now

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
                            'ticker': tx.get('ticker'),
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

