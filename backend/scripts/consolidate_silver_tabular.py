#!/usr/bin/env python3
"""
Silver Layer: Tabular Consolidation
Consolidates individual extraction.json files (Silver Objects) into 
aggregated Parquet files (Silver Tabular) for high-performance Gold layer builds.
"""

import os
import sys
import json
import logging
import io
import pandas as pd
import boto3
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

# Add lib paths
sys.path.insert(0, str(Path(__file__).parent.parent))
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
s3 = boto3.client('s3', region_name=S3_REGION)

def consolidate_year(year):
    """Consolidate all Silver Objects for a year into Tabular Parquet."""
    logger.info(f"Consolidating Silver Tabular for year {year}...")
    
    prefix = f"silver/house/financial/objects/year={year}/"
    paginator = s3.get_paginator('list_objects_v2')
    
    all_keys = []
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        if 'Contents' not in page:
            continue
        for obj in page['Contents']:
            if obj['Key'].endswith('extraction.json'):
                all_keys.append(obj['Key'])
    
    if not all_keys:
        logger.warning(f"No Silver Objects found for year {year}")
        return

    logger.info(f"Found {len(all_keys):,} objects to consolidate")

    transactions = []
    holdings = []

    def process_file(key):
        try:
            s3_client = boto3.client('s3', region_name=S3_REGION)
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            data = json.loads(response['Body'].read())
            
            # Extract doc metadata from key
            key_parts = key.split('/')
            doc_id = None
            for part in key_parts:
                if part.startswith('doc_id='):
                    doc_id = part.replace('doc_id=', '')

            # Add source metadata
            t_list = data.get('transactions', [])
            for t in t_list:
                t['doc_id'] = t.get('doc_id') or doc_id
                t['source_s3_key'] = key
                t['filing_year'] = year
            
            h_list = data.get('schedule_a', [])
            for h in h_list:
                h['doc_id'] = h.get('doc_id') or doc_id
                h['source_s3_key'] = key
                h['filing_year'] = year
                
            return t_list, h_list, None
        except Exception as e:
            return None, None, e

    # Parallel read
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(process_file, key): key for key in all_keys}
        
        completed = 0
        for future in as_completed(futures):
            t, h, error = future.result()
            if error:
                logger.error(f"Error reading {futures[future]}: {error}")
            else:
                transactions.extend(t)
                holdings.extend(h)
            
            completed += 1
            if completed % 500 == 0:
                logger.info(f"  [{completed}/{len(all_keys)}] Objects read...")

    # Write Transactions Tabular
    if transactions:
        df_t = pd.DataFrame(transactions)
        output_key_t = f"silver/house/financial/tabular/year={year}/filing_type=P/transactions.parquet"
        buffer_t = io.BytesIO()
        df_t.to_parquet(buffer_t, index=False, engine="pyarrow")
        s3.put_object(Bucket=S3_BUCKET, Key=output_key_t, Body=buffer_t.getvalue())
        logger.info(f"Wrote {len(df_t):,} transactions to {output_key_t}")

    # Write Holdings Tabular
    if holdings:
        df_h = pd.DataFrame(holdings)
        output_key_h = f"silver/house/financial/tabular/year={year}/filing_type=A/holdings.parquet"
        buffer_h = io.BytesIO()
        df_h.to_parquet(buffer_h, index=False, engine="pyarrow")
        s3.put_object(Bucket=S3_BUCKET, Key=output_key_h, Body=buffer_h.getvalue())
        logger.info(f"Wrote {len(df_h):,} holdings to {output_key_h}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int)
    args = parser.parse_args()
    
    if args.year:
        consolidate_year(args.year)
    else:
        current_year = datetime.now().year
        for y in range(current_year - 1, current_year + 1):
            consolidate_year(y)

if __name__ == "__main__":
    main()
