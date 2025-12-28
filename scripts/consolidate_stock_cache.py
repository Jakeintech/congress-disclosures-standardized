#!/usr/bin/env python3
"""
Cache Consolidation Script
Consolidates individual ticker enrichment JSOns from S3 into a single Parquet file
to enable vectorized lookups in the Gold build scripts.
"""

import sys
import os
import json
import logging
import io
import pandas as pd
import boto3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.terraform_config import get_aws_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
config = get_aws_config()
S3_BUCKET = config.get("s3_bucket_id")
S3_REGION = config.get("s3_region", "us-east-1")
s3 = boto3.client('s3', region_name=S3_REGION)

def consolidate_stock_cache():
    """Consolidate individual stock JSON cache files into a single Parquet."""
    prefix = "gold/house/financial/cache/stock_api/"
    logger.info(f"Scanning s3://{S3_BUCKET}/{prefix} for cache files...")
    
    paginator = s3.get_paginator('list_objects_v2')
    all_keys = []
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        if 'Contents' not in page:
            continue
        for obj in page['Contents']:
            if obj['Key'].endswith('.json'):
                all_keys.append(obj['Key'])
    
    if not all_keys:
        logger.warning("No cache files found.")
        return

    logger.info(f"Found {len(all_keys):,} cache files to consolidate.")

    records = []

    def process_key(key):
        try:
            s3_client = boto3.client('s3', region_name=S3_REGION)
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            data_wrapper = json.loads(response['Body'].read())
            
            # The structure is {"cached_at": ..., "data": {...}}
            data = data_wrapper.get('data', {})
            data['cached_at'] = data_wrapper.get('cached_at')
            data['source_key'] = key
            return data, None
        except Exception as e:
            return None, e

    # Parallel read
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(process_key, key): key for key in all_keys}
        
        completed = 0
        for future in as_completed(futures):
            record, error = future.result()
            if error:
                logger.error(f"Error reading {futures[future]}: {error}")
            elif record:
                records.append(record)
            
            completed += 1
            if completed % 1000 == 0:
                logger.info(f"  [{completed}/{len(all_keys)}] Files read...")

    if not records:
        return

    # Write to Tabular
    df = pd.DataFrame(records)
    output_key = "silver/house/financial/tabular/cache/stock_enrichment.parquet"
    
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    s3.put_object(Bucket=S3_BUCKET, Key=output_key, Body=buffer.getvalue())
    logger.info(f"Successfully wrote {len(df):,} cache entries to {output_key}")

if __name__ == "__main__":
    consolidate_stock_cache()
