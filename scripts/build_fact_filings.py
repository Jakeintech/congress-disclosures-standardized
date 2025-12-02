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
    
    # Scan silver/objects/ for all filing types for this year
    # Prefix: silver/objects/
    # Structure: silver/objects/{filing_type}/{year}/{doc_id}/extraction.json
    
    prefix = "silver/objects/"
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
    
    filings = []
    
    for page in pages:
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            key = obj['Key']
            # Check if it matches the year and is an extraction.json
            if f"/{year}/" in key and key.endswith("extraction.json"):
                try:
                    response = s3.get_object(Bucket=S3_BUCKET, Key=key)
                    data = json.loads(response['Body'].read())
                    
                    doc_id = data.get('doc_id')
                    filing_date = data.get('filing_date')
                    # member_id = data.get('bioguide_id', 'UNKNOWN') # Not usually in extraction.json yet
                    
                    # Count items in schedules
                    # aggs = data.get('aggs', {}) # Old format?
                    # New format has 'transactions', 'assets_and_income', etc.
                    
                    schedule_a_count = len(data.get('assets_and_income', []))
                    schedule_b_count = len(data.get('transactions', []))
                    # Other schedules might be in 'schedules' dict or top level depending on extractor
                    
                    record = {
                        'doc_id': doc_id,
                        'year': year,
                        # 'member_key': member_id,
                        'filing_date_key': get_date_key(filing_date),
                        'filing_type': data.get('filing_type'),
                        'is_extension': data.get('extension_details', {}).get('is_extension_request', False),
                        'schedule_a_count': schedule_a_count,
                        'schedule_b_count': schedule_b_count,
                        'confidence_score': data.get('extraction_metadata', {}).get('confidence_score', 1.0)
                    }
                    
                    filings.append(record)
                    
                except Exception as e:
                    logger.error(f"Error processing {key}: {e}")

    if not filings:
        logger.warning(f"No filings found for year {year}")
        return

    df = pd.DataFrame(filings)
    df['year'] = df['year'].astype(int)
    
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
