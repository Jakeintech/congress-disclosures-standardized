#!/usr/bin/env python3
"""
Reprocess Type P filings by sending messages to the extraction queue.
"""
import boto3
import json
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
S3_BUCKET = "congress-disclosures-standardized"
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-code-extraction-queue"

s3 = boto3.client('s3')
sqs = boto3.client('sqs')

def main():
    logger.info("Listing Type P filings for 2025...")
    
    prefix = "silver/objects/filing_type=type_p/year=2025/"
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
    
    count = 0
    
    for page in pages:
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            key = obj['Key']
            if not key.endswith("extraction.json"):
                continue
                
            # Parse doc_id
            # Key: silver/objects/filing_type=type_p/year=2025/doc_id=12345/extraction.json
            try:
                parts = key.split('/')
                doc_id_part = next(p for p in parts if p.startswith('doc_id='))
                doc_id = doc_id_part.split('=')[1]
                
                # Construct text key
                text_key = f"silver/house/financial/text/extraction_method=direct_text/year=2025/doc_id={doc_id}/raw_text.txt.gz"
                
                # Construct message
                message = {
                    "doc_id": doc_id,
                    "year": 2025,
                    "text_s3_key": text_key,
                    "filing_type": "P"
                }
                
                # Send to SQS
                sqs.send_message(
                    QueueUrl=QUEUE_URL,
                    MessageBody=json.dumps(message)
                )
                
                count += 1
                if count % 100 == 0:
                    logger.info(f"Sent {count} messages...")
                    
            except Exception as e:
                logger.error(f"Error processing {key}: {e}")
                
    logger.info(f"Successfully sent {count} reprocessing messages.")

if __name__ == "__main__":
    main()
