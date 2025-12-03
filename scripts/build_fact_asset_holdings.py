"""
Build Gold Layer: Fact Asset Holdings (Schedule A)

This script reads Silver layer data (Type A/B/C filings) and creates the
fact_asset_holdings table in the Gold layer.

Schema:
- doc_id: string
- filing_year: int
- filer_name: string
- state_district: string
- asset_name: string
- ticker: string
- asset_type: string
- owner: string (SP, DC, JT)
- value_range: string
- income_type: string
- income_amount: string
- tx_over_1000: boolean
- holding_key: string (unique hash)
"""

import os
import json
import logging
import argparse
import hashlib
from datetime import datetime
import pandas as pd
import boto3
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def get_s3_client():
    return boto3.client('s3')

def generate_holding_key(doc_id, asset_name, value_range, index):
    """Generate a unique key for each holding."""
    raw = f"{doc_id}|{asset_name}|{value_range}|{index}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def process_year(year):
    """Process all Type A/B/C filings for a given year."""
    s3 = get_s3_client()
    
    # Scan silver/objects/ for relevant filing types
    # We need to check type_a, type_b, type_c
    filing_types = ['type_a', 'type_b', 'type_c']
    
    holdings = []
    processed_count = 0
    
    for ftype in filing_types:
        prefix = f"silver/objects/filing_type={ftype}/year={year}/"
        logger.info(f"Scanning {prefix}...")
        
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                key = obj['Key']
                if not key.endswith("extraction.json"):
                    continue
                    
                try:
                    response = s3.get_object(Bucket=S3_BUCKET, Key=key)
                    data = json.loads(response['Body'].read())
                    
                    doc_id = data.get('doc_id')
                    
                    # Get metadata
                    bronze_meta = data.get('bronze_metadata', {})
                    filer_name = bronze_meta.get('filer_name') or data.get('document_header', {}).get('filer_name')
                    state_district = bronze_meta.get('state_district')
                    
                    # Extract Schedule A (Assets and Unearned Income)
                    # The field name is 'schedule_a' in the new extractor
                    assets = data.get('schedule_a') or data.get('assets_and_income', [])
                    
                    if not assets:
                        continue
                        
                    for idx, asset in enumerate(assets):
                        # Clean up fields
                        asset_name = asset.get('asset_name', '').strip()
                        if not asset_name:
                            continue
                            
                        record = {
                            'doc_id': doc_id,
                            'filing_year': year,
                            'filer_name': filer_name,
                            'state_district': state_district,
                            'filing_type': ftype,
                            
                            'asset_name': asset_name,
                            'ticker': asset.get('ticker_symbol') or asset.get('ticker'),
                            'asset_type': asset.get('asset_type'),
                            'owner': asset.get('owner_code') or asset.get('owner'),
                            'value_range': asset.get('value_category') or asset.get('value'),
                            'income_type': asset.get('income_type'),
                            'income_amount': asset.get('income_category') or asset.get('income'),
                            'tx_over_1000': asset.get('tx_over_1000', False),
                            
                            'holding_key': generate_holding_key(doc_id, asset_name, asset.get('value_category') or asset.get('value'), idx)
                        }
                        holdings.append(record)
                    
                    processed_count += 1
                    if processed_count % 100 == 0:
                        logger.info(f"Processed {processed_count} filings...")
                        
                except Exception as e:
                    logger.error(f"Error processing {key}: {e}")

    if not holdings:
        logger.warning(f"No holdings found for year {year}")
        return

    # Create DataFrame
    df = pd.DataFrame(holdings)
    
    # Write to S3 (Hive partitioned by year)
    # Note: We do NOT include 'year' column in the file to avoid schema conflict with partition
    output_key = f"gold/house/financial/facts/fact_asset_holdings/year={year}/part-0000.parquet"
    
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=output_key,
        Body=buffer.getvalue(),
        ContentType="application/x-parquet"
    )
    
    logger.info(f"Processed {processed_count} filings, wrote {len(df)} holdings to s3://{S3_BUCKET}/{output_key}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, required=True, help='Process specific year')
    args = parser.parse_args()
    
    process_year(args.year)

if __name__ == '__main__':
    main()
