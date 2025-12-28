#!/usr/bin/env python3
"""
Build Gold Layer: Fact Filings (Enhanced)
Reads Silver layer structured JSONs from S3, extracts metadata and schedule counts, and writes Parquet to S3.
"""

import os
import sys
import json
import logging
import io
from datetime import datetime
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import boto3

# Add lib paths
sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion"))
sys.path.insert(0, str(Path(__file__).parent))

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

def process_year(year):
    """Process all filings for a specific year."""
    logger.info(f"Processing year {year}...")
    
    # Scan BOTH old and new structures for backward compatibility
    # New: silver/house/financial/objects/year={year}/filing_type={type}/doc_id={doc_id}/extraction.json
    # Old: silver/objects/filing_type={type}/year={year}/doc_id={doc_id}/extraction.json
    prefixes = [
        f'silver/house/financial/objects/',  # New standardized structure
        f'silver/objects/',                   # Old structure (backward compat)
    ]
    
    filings = []
    filing_type_counts = {}
    
    for prefix in prefixes:
        logger.info(f"Scanning {prefix}...")
        
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                key = obj['Key']
                
                # Only process files for this year
                if f"/year={year}/" not in key or not key.endswith("extraction.json"):
                    continue
                    
                try:
                    import re
                    
                    response = s3.get_object(Bucket=S3_BUCKET, Key=key)
                    data = json.loads(response['Body'].read())
                    
                    # Try to extract from new format first: year=2025/filing_type=type_p/doc_id=12345
                    match_new = re.search(r'year=(\d+)/filing_type=([^/]+)/doc_id=([^/]+)/', key)
                    # Try old format: filing_type=type_p/year=2025/doc_id=12345
                    match_old = re.search(r'filing_type=([^/]+)/year=(\d+)/doc_id=([^/]+)/', key)
                    
                    filing_type = None
                    doc_id = None
                    
                    if match_new:
                        # New format: year first
                        year_from_path = int(match_new.group(1))
                        filing_type = match_new.group(2)
                        doc_id = match_new.group(3)
                    elif match_old:
                        # Old format: filing_type first
                        filing_type = match_old.group(1)
                        year_from_path = int(match_old.group(2))
                        doc_id = match_old.group(3)
                    
                    # Fallback to data if path parsing failed
                    if not filing_type:
                        filing_type = data.get('filing_type', 'Unknown')
                    if not doc_id:
                        doc_id = data.get('doc_id')
                    
                    if not doc_id:
                        logger.warning(f"Skipping {key}: no doc_id found")
                        continue
                    
                    filing_date = data.get('filing_date')
                    
                    # Track counts
                    filing_type_counts[filing_type] = filing_type_counts.get(filing_type, 0) + 1
                    
                    # Get bronze metadata if available
                    bronze_meta = data.get('bronze_metadata', {})
                    filer_name = bronze_meta.get('filer_name') or data.get('document_header', {}).get('filer_name')
                    state_district = bronze_meta.get('state_district')
                    
                    # Count items in schedules
                    schedule_a_count = len(data.get('assets_and_income', []))
                    schedule_b_count = len(data.get('transactions', []))
                    
                    record = {
                        'doc_id': doc_id,
                        'year': year,
                        'filing_year': year,  # Add explicit filing_year column
                        'filing_date_key': get_date_key(filing_date),
                        'filing_date': filing_date,  # Keep original date too
                        'filing_type': filing_type,
                        'filer_name': filer_name,
                        'state_district': state_district,
                        'is_extension': data.get('extension_details', {}).get('is_extension_request', False),
                        'schedule_a_count': schedule_a_count,
                        'schedule_b_count': schedule_b_count,
                        'confidence_score': data.get('extraction_metadata', {}).get('confidence_score', 1.0),
                        'bronze_pdf_s3_key': data.get('bronze_pdf_s3_key')
                    }
                    
                    filings.append(record)
                    
                except Exception as e:
                    logger.error(f"Error processing {key}: {e}")

    logger.info(f"Filing type counts: {filing_type_counts}")

    if not filings:
        logger.warning(f"No filings found for year {year}")
        return

    df = pd.DataFrame(filings)
    # df['year'] = df['year'].astype(int) # Year is in partition, don't include in file
    
    # Drop year column as it's the partition key
    if 'year' in df.columns:
        df = df.drop(columns=['year'])
    
    # Write to S3
    output_key = f"gold/house/financial/facts/fact_filings/year={year}/part-0000.parquet"
    
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    buffer.seek(0)
    
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=output_key,
        Body=buffer.getvalue(),
        ContentType="application/x-parquet"
    )
    
    logger.info(f"Wrote {len(df)} filings to s3://{S3_BUCKET}/{output_key}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, help='Process specific year')
    args = parser.parse_args()
    
    if args.year:
        process_year(args.year)
    else:
        # Default to current year + next year (for testing)
        current_year = datetime.now().year
        process_year(current_year)
        process_year(current_year + 1)

if __name__ == "__main__":
    main()
