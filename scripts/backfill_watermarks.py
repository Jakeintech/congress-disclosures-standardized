#!/usr/bin/env python3
"""
Backfill Watermarks Script

This script scans the S3 Bronze layer for House FD raw ZIP files and backfills
the DynamoDB watermark table. This ensures that the 'check_house_fd_updates' Lambda
doesn't trigger a re-ingestion of data that is already present.

Usage:
    python scripts/backfill_watermarks.py --year 2024
"""

import boto3
import hashlib
import os
import argparse
import sys
from datetime import datetime

# Configuration
BUCKET_NAME = "congress-disclosures-standardized"
WATERMARK_TABLE = "congress-disclosures-pipeline-watermarks"
S3_BRONZE_PREFIX = "bronze"

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def backfill_house_fd_watermark(year):
    print(f"Checking S3 for {year}FD.zip...")
    
    # Path used by ingest_zip lambda
    raw_zip_key = f"{S3_BRONZE_PREFIX}/house/financial/year={year}/raw_zip/{year}FD.zip"
    
    try:
        # Get object from S3
        response = s3.get_object(Bucket=BUCKET_NAME, Key=raw_zip_key)
        
        # Read content to compute SHA256
        print("   Reading file to compute SHA256 (this may take a moment)...")
        content = response['Body'].read()
        sha256 = hashlib.sha256(content).hexdigest()
        content_length = len(content)
        
        # Extract metadata saved by ingest_zip
        metadata = response.get('Metadata', {})
        http_last_modified = metadata.get('http_last_modified', response['LastModified'].strftime('%a, %d %b %Y %H:%M:%S GMT'))
        
        print(f"   Found ZIP in S3:")
        print(f"   - Size: {content_length} bytes")
        print(f"   - SHA256: {sha256}")
        print(f"   - Last-Modified (Origin): {http_last_modified}")
        
        # Update DynamoDB
        table = dynamodb.Table(WATERMARK_TABLE)
        table.put_item(
            Item={
                'table_name': 'house_fd',
                'watermark_type': f'year_{year}',
                'sha256': sha256,
                'last_modified': http_last_modified,
                'content_length': content_length,
                'updated_at': datetime.utcnow().isoformat() + 'Z',
                'backfilled': True
            }
        )
        print(f"✅ Successfully backfilled watermark for {year}")
        
    except s3.exceptions.NoSuchKey:
        print(f"⚠️  No raw zip found at s3://{BUCKET_NAME}/{raw_zip_key}")
        print("   Skipping backfill for this year.")
    except Exception as e:
        print(f"❌ Error backfilling watermark: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Backfill watermarks from S3")
    parser.add_argument("--year", type=int, default=datetime.now().year, help="Year to backfill")
    args = parser.parse_args()
    
    print(f"🚀 Starting watermark backfill for {args.year}...")
    backfill_house_fd_watermark(args.year)

if __name__ == "__main__":
    main()
