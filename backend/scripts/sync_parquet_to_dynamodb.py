#!/usr/bin/env python3
"""
Sync Silver Parquet to DynamoDB.

Reads the corrected Silver documents parquet file and updates the DynamoDB table.
This ensures that rebuild_silver_manifest.py (which reads DynamoDB) has the latest data.
"""

import sys
import os
from pathlib import Path
import boto3
import pandas as pd
import logging
from decimal import Decimal

# Add lib paths
sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion"))
sys.path.insert(0, str(Path(__file__).parent))

from lib.terraform_config import get_aws_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    config = get_aws_config()
    S3_BUCKET = config.get("s3_bucket_id")
    S3_REGION = config.get("s3_region", "us-east-1")
    TABLE_NAME = "house_fd_documents"

    if not S3_BUCKET:
        logger.error("Missing S3_BUCKET_ID")
        sys.exit(1)

    s3 = boto3.client("s3", region_name=S3_REGION)
    dynamodb = boto3.resource("dynamodb", region_name=S3_REGION)
    table = dynamodb.Table(TABLE_NAME)

    year = 2025
    parquet_key = f"silver/house/financial/documents/year={year}/part-0000.parquet"

    logger.info(f"Reading {parquet_key}...")
    
    # Download parquet
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
        s3.download_file(S3_BUCKET, parquet_key, tmp.name)
        df = pd.read_parquet(tmp.name)
        os.unlink(tmp.name)

    logger.info(f"Loaded {len(df)} records")

    # Convert to records for DynamoDB
    # Handle NaN/None and float to Decimal
    records = df.to_dict('records')
    
    logger.info("Writing to DynamoDB...")
    
    with table.batch_writer() as batch:
        count = 0
        for record in records:
            # Clean up record for DynamoDB
            item = {}
            for k, v in record.items():
                if pd.isna(v):
                    continue
                if isinstance(v, float):
                    item[k] = Decimal(str(v))
                elif isinstance(v, pd.Timestamp):
                    item[k] = v.isoformat()
                else:
                    item[k] = v
            
            # Ensure keys exist
            if 'doc_id' not in item or 'year' not in item:
                continue
                
            batch.put_item(Item=item)
            count += 1
            
            if count % 100 == 0:
                logger.info(f"  Synced {count} records...")

    logger.info(f"✅ Synced {count} records to DynamoDB")

if __name__ == "__main__":
    main()
