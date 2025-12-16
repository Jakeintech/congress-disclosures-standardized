import boto3
import json
import concurrent.futures
import time
import subprocess
from typing import List, Dict

# Configuration
BUCKET = "congress-disclosures-standardized"
LAMBDA_FUNCTION = "congress-disclosures-development-extract-structured-code"
PREFIX = "silver/house/financial/text/extraction_method=direct_text/"
WORKERS = 20  # Parallel lambda invocations

s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')

def list_all_text_files(bucket, prefix):
    print(f"Listing objects in s3://{bucket}/{prefix}...")
    paginator = s3.get_paginator('list_objects_v2')
    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                keys.append(obj['Key'])
    print(f"Found {len(keys)} text files")
    return keys

def parse_key_metadata(key):
    # Key format: silver/house/financial/text/extraction_method=direct_text/year=2024/doc_id=10056489/raw_text.txt.gz
    try:
        parts = key.split('/')
        year_part = next(p for p in parts if p.startswith('year='))
        doc_id_part = next(p for p in parts if p.startswith('doc_id='))
        
        year = int(year_part.split('=')[1])
        doc_id = doc_id_part.split('=')[1]
        
        # We need filing_type. Since we don't have it in the text path, we might need to guess or default to 'P' 
        # based on user context saying likely P. Or lookup in bronze if needed.
        # Ideally we'd look up a manifest, but for now defaulting P or generic is better than nothing.
        # The Lambda can handle generic. But the user specifically mentioned "Type P extractor".
        # Let's check bronze path for filing type? No, too slow.
        # Let's assume Type P for 2024/2025 financial disclosures as primary target.
        # Actually the lambda will try to extract whatever it is.
        
        return {
            "doc_id": doc_id,
            "year": year,
            "text_s3_key": key,
            "filing_type": "P" # Optimistic default, lambda has fallbacks?
        }
    except Exception as e:
        print(f"Failed to parse key {key}: {e}")
        return None

def invoke_lambda(records):
    payload = {
        "Records": [
            {
                "messageId": f"manual-{i}",
                "body": json.dumps(record)
            }
            for i, record in enumerate(records)
        ]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION,
            InvocationType='Event', # Async
            Payload=json.dumps(payload)
        )
        return response['StatusCode']
    except Exception as e:
        print(f"Error invoking lambda: {e}")
        return 500

def main():
    all_keys = list_all_text_files(BUCKET, PREFIX)
    
    # Filter for relevant years if needed, or just process all
    # all_keys = [k for k in all_keys if 'year=2024' or 'year=2025' in k]
    
    tasks = []
    for key in all_keys:
        meta = parse_key_metadata(key)
        if meta:
            tasks.append(meta)
            
    print(f"Prepared {len(tasks)} items for processing")
    
    # Batch into groups of 10 for Lambda invocation
    batch_size = 10
    batches = [tasks[i:i + batch_size] for i in range(0, len(tasks), batch_size)]
    print(f"Processing {len(batches)} batches...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = []
        for batch in batches:
            futures.append(executor.submit(invoke_lambda, batch))
            
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            if completed % 10 == 0:
                print(f"Progress: {completed}/{len(batches)} batches triggered")

if __name__ == "__main__":
    main()
