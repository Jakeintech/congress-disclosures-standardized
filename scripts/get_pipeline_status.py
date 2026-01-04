#!/usr/bin/env python3
"""
Get extraction pipeline status metrics for UI dashboard.

Returns JSON with:
- Total PDFs in Bronze
- Extracted count (text + structured)
- Queue status (waiting + processing)
- DLQ count
- Filing type breakdown
"""

import boto3
import json
import os
import sys
from collections import defaultdict

s3 = boto3.client('s3')
sqs = boto3.client('sqs')

# Environment variables
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'congress-disclosures')

# Validate required environment variables
if not AWS_ACCOUNT_ID:
    print("ERROR: AWS_ACCOUNT_ID environment variable is required", file=sys.stderr)
    sys.exit(1)

BUCKET = 'congress-disclosures-standardized'
QUEUE_URL = f'https://sqs.{AWS_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/{PROJECT_NAME}-{ENVIRONMENT}-extract-queue'
DLQ_URL = f'https://sqs.{AWS_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/{PROJECT_NAME}-{ENVIRONMENT}-extract-dlq'

def count_bronze_pdfs():
    """Count total PDFs in Bronze layer."""
    count = 0
    paginator = s3.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=BUCKET, Prefix='bronze/house/financial/'):
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.pdf'):
                count += 1

    return count

def count_text_extractions():
    """Count completed text extractions."""
    count = 0
    paginator = s3.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=BUCKET, Prefix='silver/house/financial/text/'):
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('raw_text.txt.gz'):
                count += 1

    return count

def count_structured_extractions_by_type():
    """Count structured extractions grouped by filing type."""
    by_type = defaultdict(int)

    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=BUCKET, Prefix='silver/house/financial/structured/'):
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.json'):
                # Extract filing type from path: .../filing_type=X/...
                parts = obj['Key'].split('/')
                for part in parts:
                    if part.startswith('filing_type='):
                        filing_type = part.split('=')[1]
                        by_type[filing_type] += 1
                        break

    return dict(by_type)

def get_queue_stats():
    """Get SQS queue statistics."""
    try:
        response = sqs.get_queue_attributes(
            QueueUrl=QUEUE_URL,
            AttributeNames=[
                'ApproximateNumberOfMessages',
                'ApproximateNumberOfMessagesNotVisible'
            ]
        )
        attrs = response.get('Attributes', {})

        return {
            'waiting': int(attrs.get('ApproximateNumberOfMessages', 0)),
            'processing': int(attrs.get('ApproximateNumberOfMessagesNotVisible', 0))
        }
    except Exception as e:
        print(f"Error getting queue stats: {e}", file=sys.stderr)
        return {'waiting': 0, 'processing': 0}

def get_dlq_count():
    """Get DLQ message count."""
    try:
        response = sqs.get_queue_attributes(
            QueueUrl=DLQ_URL,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        return int(response.get('Attributes', {}).get('ApproximateNumberOfMessages', 0))
    except Exception as e:
        print(f"Error getting DLQ count: {e}", file=sys.stderr)
        return 0

def main():
    """Generate pipeline status JSON."""
    print("Gathering pipeline status...", file=sys.stderr)

    # Get all metrics
    total_pdfs = count_bronze_pdfs()
    print(f"  Total PDFs: {total_pdfs}", file=sys.stderr)

    text_count = count_text_extractions()
    print(f"  Text extractions: {text_count}", file=sys.stderr)

    structured_by_type = count_structured_extractions_by_type()
    structured_count = sum(structured_by_type.values())
    print(f"  Structured extractions: {structured_count}", file=sys.stderr)

    queue_stats = get_queue_stats()
    print(f"  Queue: {queue_stats['waiting']} waiting, {queue_stats['processing']} processing", file=sys.stderr)

    dlq_count = get_dlq_count()
    print(f"  DLQ: {dlq_count}", file=sys.stderr)

    # Build response
    status = {
        'totalPdfs': total_pdfs,
        'textExtracted': text_count,
        'structuredExtracted': structured_count,
        'queueWaiting': queue_stats['waiting'],
        'queueProcessing': queue_stats['processing'],
        'dlqCount': dlq_count,
        'filingTypes': structured_by_type
    }

    # Output JSON to stdout
    print(json.dumps(status, indent=2))

if __name__ == '__main__':
    main()
