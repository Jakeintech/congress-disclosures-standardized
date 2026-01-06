#!/usr/bin/env python3
"""
Ingest Congress committees and rosters into Bronze S3.
Fetches master list and detail for each committee/subcommittee.
"""

import os
import sys
import json
import gzip
import logging
import boto3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load env from root
load_dotenv(Path(__file__).parent.parent / '.env')

# Add parent directory to path to allow importing from ingestion.lib
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set CONGRESS_API_KEY if not set but CONGRESS_GOV_API_KEY is
if 'CONGRESS_GOV_API_KEY' in os.environ and 'CONGRESS_API_KEY' not in os.environ:
    os.environ['CONGRESS_API_KEY'] = os.environ['CONGRESS_GOV_API_KEY']

from backend.lib.ingestion.congress_api_client import CongressAPIClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def upload_to_s3(s3_client, data: Dict[str, Any], s3_key: str):
    """Upload data to S3 as gzipped JSON."""
    json_bytes = json.dumps(data, indent=2).encode('utf-8')
    gzipped_bytes = gzip.compress(json_bytes)
    
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=gzipped_bytes,
        ContentType='application/json',
        ContentEncoding='gzip'
    )
    logger.info(f"  Uploaded to s3://{BUCKET_NAME}/{s3_key}")

def ingest_committees():
    """Main ingestion function."""
    client = CongressAPIClient()
    s3 = boto3.client('s3')
    ingest_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    logger.info("Fetching committee master list...")
    committees = list(client.list_committees())
    logger.info(f"Found {len(committees)} committees")
    
    # Save master list
    master_key = f"bronze/congress/committee/master_list/ingest_date={ingest_date}/committees.json.gz"
    upload_to_s3(s3, {"committees": committees, "ingest_date": ingest_date}, master_key)
    
    # Process each committee for detail (includes members/subcommittees)
    for i, c in enumerate(committees):
        code = c.get('systemCode')
        chamber = (c.get('chamber') or 'unknown').lower()
        
        if not code:
            continue
            
        logger.info(f"[{i+1}/{len(committees)}] Fetching detail for {code} ({chamber})...")
        try:
            detail = client.get_committee(chamber, code)
            
            # Save detail to Bronze
            detail_key = f"bronze/congress/committee/chamber={chamber}/ingest_date={ingest_date}/{code}.json.gz"
            upload_to_s3(s3, detail, detail_key)
            
            # If it's a parent committee, it might have subcommittees in the response
            # Note: The Congress API typically includes subcommittees in the main committee detail
            # but sometimes we might need to fetch them separately if they have their own codes.
            # In the list response, subcommittees are often included if they have distinct codes.
            
        except Exception as e:
            logger.error(f"  Failed to fetch {code}: {e}")
            continue

    logger.info("✅ Committee ingestion complete!")

if __name__ == '__main__':
    ingest_committees()
