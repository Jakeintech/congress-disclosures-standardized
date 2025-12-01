#!/usr/bin/env python3
"""
Re-trigger extraction for Type A/B filings.
Uses Bronze manifest to get Type A doc_ids and sends them through extraction pipeline.
"""
import boto3
import json
from pathlib import Path

def main():
    # Load Bronze manifest
    manifest_path = Path('data/bronze/house/financial/year=2025/index/manifest.json')
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    type_a_docs = manifest.get('filing_types', {}).get('A', {}).get('doc_ids', [])
    print(f"Found {len(type_a_docs)} Type A filings to re-extract")
    
    if not type_a_docs:
        print("No Type A filings found in manifest")
        return
    
    # Send to extraction SQS queue
    sqs = boto3.client('sqs')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT/house-fd-extraction-queue'  # TODO: Get from env/config
    
    print(f"Sending {len(type_a_docs)} messages to extraction queue...")
    for doc_id in type_a_docs:
        message = {
            'doc_id': doc_id,
            'year': 2025,
            'filing_type': 'A',
            's3_bucket': 'congress-disclosures-standardized',
            's3_key': f'bronze/house/financial/year=2025/pdfs/2025/{doc_id}.pdf'
        }
        
        try:
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message)
            )
            print(f"  ✓ Queued doc_id={doc_id}")
        except Exception as e:
            print(f"  ✗ Error queueing {doc_id}: {e}")
    
    print(f"\n✅ Re-extraction triggered for {len(type_a_docs)} Type A filings")
    print("Monitor Lambda logs to see extraction progress")

if __name__ == '__main__':
    main()
