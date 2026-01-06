#!/usr/bin/env python3
"""
wipe_pipeline.py

Wipes all data from the pipeline to allow a clean rerun.
- Purges SQS queues (Extract, DLQ)
- Deletes all items from DynamoDB table (house_fd_documents)
- Deletes objects from S3 bucket (Silver, Gold layers)
- Optionally deletes Bronze layer (if --wipe-bronze is specified)

Usage:
    python3 scripts/wipe_pipeline.py [--wipe-bronze] [--yes]
"""

import boto3
import argparse
import sys
import time

# Configuration - Update these if they change in Terraform
SQS_QUEUE_NAME = "congress-disclosures-development-extract-queue"
SQS_DLQ_NAME = "congress-disclosures-development-extract-dlq"
DYNAMODB_TABLE_NAME = "house_fd_documents"
S3_BUCKET_NAME = "congress-disclosures-standardized"

def get_queue_url(sqs, queue_name):
    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        return response['QueueUrl']
    except sqs.exceptions.QueueDoesNotExist:
        print(f"Queue {queue_name} does not exist.")
        return None

def purge_sqs(sqs, queue_name):
    url = get_queue_url(sqs, queue_name)
    if url:
        print(f"Purging queue: {queue_name}...")
        try:
            sqs.purge_queue(QueueUrl=url)
            print(f"✓ Purged {queue_name}")
        except Exception as e:
            print(f"Error purging {queue_name}: {e}")

def wipe_dynamodb(dynamodb, table_name):
    print(f"Wiping DynamoDB table: {table_name}...")
    table = dynamodb.Table(table_name)
    
    # Scan and delete is slow but simple for this scale
    try:
        scan = table.scan()
        items = scan.get('Items', [])
        
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(
                    Key={
                        'doc_id': item['doc_id'],
                        'year': item['year']
                    }
                )
        
        while 'LastEvaluatedKey' in scan:
            scan = table.scan(ExclusiveStartKey=scan['LastEvaluatedKey'])
            items = scan.get('Items', [])
            with table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(
                        Key={
                            'doc_id': item['doc_id'],
                            'year': item['year']
                        }
                    )
        print(f"✓ Wiped {table_name}")
    except Exception as e:
        print(f"Error wiping DynamoDB table {table_name}: {e}")

def wipe_s3(s3, bucket_name, prefixes):
    print(f"Wiping S3 bucket: {bucket_name} prefixes: {prefixes}...")
    bucket = s3.Bucket(bucket_name)
    
    for prefix in prefixes:
        print(f"  Deleting objects with prefix: {prefix}...")
        try:
            bucket.objects.filter(Prefix=prefix).delete()
            print(f"  ✓ Deleted {prefix}")
        except Exception as e:
            print(f"  Error deleting {prefix}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Wipe pipeline data")
    parser.add_argument("--wipe-bronze", action="store_true", help="Also wipe Bronze layer (raw PDFs)")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation")
    args = parser.parse_args()

    if not args.yes:
        print("WARNING: This will DELETE ALL DATA in:")
        print(f"  - SQS: {SQS_QUEUE_NAME}, {SQS_DLQ_NAME}")
        print(f"  - DynamoDB: {DYNAMODB_TABLE_NAME}")
        print(f"  - S3: {S3_BUCKET_NAME} (Silver/Gold layers)")
        if args.wipe_bronze:
            print(f"  - S3: {S3_BUCKET_NAME} (Bronze layer - RAW PDFs!)")
        
        confirm = input("Are you sure? Type 'yes' to proceed: ")
        if confirm != "yes":
            print("Aborted.")
            sys.exit(1)

    session = boto3.Session()
    sqs = session.client('sqs')
    dynamodb = session.resource('dynamodb')
    s3 = session.resource('s3')

    # 1. Purge SQS
    purge_sqs(sqs, SQS_QUEUE_NAME)
    purge_sqs(sqs, SQS_DLQ_NAME)

    # 2. Wipe DynamoDB
    wipe_dynamodb(dynamodb, DYNAMODB_TABLE_NAME)

    # 3. Wipe S3
    prefixes = ['silver/', 'gold/', 'data/'] # data/ might be used for website json
    if args.wipe_bronze:
        prefixes.append('bronze/')
    
    wipe_s3(s3, S3_BUCKET_NAME, prefixes)

    print("\n✓ Pipeline wipe complete.")
    print("Next steps:")
    if args.wipe_bronze:
        print("  1. Run 'make ingest-current' to re-download PDFs")
    else:
        print("  1. Run 'make run-silver-pipeline' to re-process existing PDFs")

if __name__ == "__main__":
    main()
