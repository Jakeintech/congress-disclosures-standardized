"""
Build Gold Layer: Fact Positions (Schedule E)

This script reads Silver layer data (Type A/B/C filings) and creates the
fact_positions table in the Gold layer.

Schema:
- doc_id: string
- filing_year: int
- filer_name: string
- state_district: string
- position_title: string
- position_key: string (unique hash)
"""

import os
import json
import logging
import argparse
import hashlib
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

def generate_position_key(doc_id, position_title, index):
    """Generate a unique key for each position."""
    raw = f"{doc_id}|{position_title}|{index}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def process_year(year):
    """Process all Type A/B/C filings for a given year."""
    s3 = get_s3_client()
    
    filing_types = ['type_a', 'type_b', 'type_c']
    
    positions_list = []
    processed_count = 0
    
    for ftype in filing_types:
        prefix = f"silver/house/financial/objects/year={year}/filing_type={ftype}/"
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
                    
                    # Extract Schedule E (Positions)
                    positions = data.get('schedule_e') or data.get('positions', [])
                    
                    if not positions:
                        continue
                        
                    for idx, pos in enumerate(positions):
                        # Clean up fields
                        position_title = pos.get('position_title', '').strip()
                        if not position_title:
                            continue
                            
                        record = {
                            'doc_id': doc_id,
                            'filing_year': year,
                            'filer_name': filer_name,
                            'state_district': state_district,
                            'filing_type': ftype,
                            
                            'position_title': position_title,
                            
                            'position_key': generate_position_key(doc_id, position_title, idx)
                        }
                        positions_list.append(record)
                    
                    processed_count += 1
                    if processed_count % 100 == 0:
                        logger.info(f"Processed {processed_count} filings...")
                        
                except Exception as e:
                    logger.error(f"Error processing {key}: {e}")

    if not positions_list:
        logger.warning(f"No positions found for year {year}")
        return

    # Create DataFrame
    df = pd.DataFrame(positions_list)
    
    # Write to S3 (Hive partitioned by year)
    output_key = f"gold/house/financial/facts/fact_positions/year={year}/part-0000.parquet"
    
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=output_key,
        Body=buffer.getvalue(),
        ContentType="application/x-parquet"
    )
    
    logger.info(f"Processed {processed_count} filings, wrote {len(df)} positions to s3://{S3_BUCKET}/{output_key}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, required=True, help='Process specific year')
    args = parser.parse_args()
    
    process_year(args.year)

if __name__ == '__main__':
    main()
