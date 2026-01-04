#!/usr/bin/env python3
"""
Reprocess Type A/B/C filings by sending messages to the extraction queue.
"""
import boto3
import json
import logging
import argparse
import os
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'congress-disclosures')

# Validate required environment variables
if not AWS_ACCOUNT_ID:
    logger.error("AWS_ACCOUNT_ID environment variable is required")
    sys.exit(1)

# Config
S3_BUCKET = "congress-disclosures-standardized"
QUEUE_URL = f"https://sqs.{AWS_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/{PROJECT_NAME}-{ENVIRONMENT}-code-extraction-queue"

s3 = boto3.client('s3')
sqs = boto3.client('sqs')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0, help='Limit number of messages (0 for all)')
    args = parser.parse_args()

    filing_types = {
        'type_a': 'A',
        'type_b': 'B',
        'type_c': 'C'
    }
    
    total_sent = 0
    
    for ftype_folder, ftype_code in filing_types.items():
        logger.info(f"Listing {ftype_folder} filings for 2025...")
        
        prefix = f"silver/objects/filing_type={ftype_folder}/year=2025/"
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
        
        count = 0
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                if args.limit > 0 and total_sent >= args.limit:
                    break
                
                key = obj['Key']
                if not key.endswith("extraction.json"):
                    continue
                    
                # Parse doc_id
                try:
                    parts = key.split('/')
                    doc_id_part = next(p for p in parts if p.startswith('doc_id='))
                    doc_id = doc_id_part.split('=')[1]
                    
                    # Construct text key
                    # Note: text is stored in silver/house/financial/text/...
                    # We assume it exists.
                    text_key = f"silver/house/financial/text/extraction_method=direct_text/year=2025/doc_id={doc_id}/raw_text.txt.gz"
                    
                    # Construct message
                    message = {
                        "doc_id": doc_id,
                        "year": 2025,
                        "text_s3_key": text_key,
                        "filing_type": ftype_code
                    }
                    
                    # Send to SQS
                    sqs.send_message(
                        QueueUrl=QUEUE_URL,
                        MessageBody=json.dumps(message)
                    )
                    
                    count += 1
                    total_sent += 1
                    if count % 10 == 0:
                        logger.info(f"Sent {count} messages for {ftype_folder}...")
                        
                except Exception as e:
                    logger.error(f"Error processing {key}: {e}")
            
            if args.limit > 0 and total_sent >= args.limit:
                break
                
        logger.info(f"Sent {count} messages for {ftype_folder}.")
        if args.limit > 0 and total_sent >= args.limit:
            break
            
    logger.info(f"Total messages sent: {total_sent}")

if __name__ == "__main__":
    main()
