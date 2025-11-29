#!/usr/bin/env python3
"""
Reset Pipeline Script

This script clears all data from Silver and Gold layers in S3 and purges SQS queues
to allow for a clean re-run of the pipeline.

Usage:
    python scripts/reset_pipeline.py [--force]
"""

import argparse
import boto3
import sys
import os

# Configure AWS clients
s3 = boto3.client('s3')
sqs = boto3.client('sqs')

# Configuration
BUCKET_NAME = "congress-disclosures-standardized"
PREFIXES_TO_CLEAR = [
    "silver/",
    "gold/"
]
QUEUES_TO_PURGE = [
    "congress-disclosures-development-extract-queue",
    "congress-disclosures-development-extract-dlq",
    "congress-disclosures-development-code-extraction-queue",
    "congress-disclosures-development-code-extraction-dlq"
]

def get_queue_url(queue_name):
    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        return response['QueueUrl']
    except sqs.exceptions.QueueDoesNotExist:
        print(f"⚠️  Queue not found: {queue_name}")
        return None

def clear_s3_prefixes():
    print(f"🗑️  Clearing S3 data from {BUCKET_NAME}...")
    
    for prefix in PREFIXES_TO_CLEAR:
        print(f"   Scanning {prefix}...")
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix)
        
        objects_to_delete = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})
                    
        if objects_to_delete:
            print(f"   Deleting {len(objects_to_delete)} objects from {prefix}...")
            # Delete in batches of 1000 (S3 limit)
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i+1000]
                s3.delete_objects(
                    Bucket=BUCKET_NAME,
                    Delete={'Objects': batch}
                )
            print(f"   ✅ Cleared {prefix}")
        else:
            print(f"   ℹ️  No objects found in {prefix}")

def purge_queues():
    print("🗑️  Purging SQS queues...")
    
    for queue_name in QUEUES_TO_PURGE:
        queue_url = get_queue_url(queue_name)
        if queue_url:
            try:
                sqs.purge_queue(QueueUrl=queue_url)
                print(f"   ✅ Purged {queue_name}")
            except Exception as e:
                print(f"   ❌ Failed to purge {queue_name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Reset pipeline data")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if not args.force:
        print("⚠️  WARNING: This will DELETE ALL DATA in Silver and Gold layers and PURGE all queues!")
        print(f"   Bucket: {BUCKET_NAME}")
        print(f"   Prefixes: {', '.join(PREFIXES_TO_CLEAR)}")
        print(f"   Queues: {', '.join(QUEUES_TO_PURGE)}")
        response = input("\nAre you sure you want to continue? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(1)

    print("\n🚀 Starting pipeline reset...\n")
    
    try:
        clear_s3_prefixes()
        purge_queues()
        print("\n✨ Pipeline reset complete! You can now run 'make run-pipeline' to re-process data.")
    except Exception as e:
        print(f"\n❌ Error during reset: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
