#!/usr/bin/env python3
"""Queue pending documents for extraction.

This script reads the silver layer documents table and queues any pending
documents for PDF extraction.
"""

import sys
import json
import io
from pathlib import Path

# Add lib paths
sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion"))
sys.path.insert(0, str(Path(__file__).parent))

import boto3
import pandas as pd
from lib.terraform_config import get_aws_config

# Get configuration from Terraform outputs (no hardcoded secrets!)
config = get_aws_config()
S3_BUCKET = config.get("s3_bucket_id")
S3_REGION = config.get("s3_region", "us-east-1")
SQS_QUEUE_URL = config.get("sqs_extraction_queue_url")

if not S3_BUCKET or not SQS_QUEUE_URL:
    print("ERROR: Missing required configuration.")
    print("Please run 'terraform apply' or set environment variables:")
    print("  S3_BUCKET_ID, SQS_EXTRACTION_QUEUE_URL")
    sys.exit(1)


def main(limit=None):
    """Queue pending documents for extraction.

    Args:
        limit: Optional limit on number of documents to queue
    """
    s3_client = boto3.client("s3", region_name=S3_REGION)
    sqs_client = boto3.client("sqs", region_name=S3_REGION)

    # Read documents parquet from S3
    documents_s3_key = "silver/house/financial/documents/year=2025/part-0000.parquet"

    print(f"Reading documents from s3://{S3_BUCKET}/{documents_s3_key}")

    # Download parquet file
    response = s3_client.get_object(Bucket=S3_BUCKET, Key=documents_s3_key)
    parquet_bytes = response["Body"].read()
    documents_df = pd.read_parquet(io.BytesIO(parquet_bytes))

    print(f"Found {len(documents_df)} total documents")

    # Filter to pending documents
    pending_df = documents_df[documents_df["extraction_status"] == "pending"]

    print(f"Found {len(pending_df)} pending documents")

    if limit:
        pending_df = pending_df.head(limit)
        print(f"Limiting to {len(pending_df)} documents")

    # Send SQS messages in batches of 10
    batch = []
    queued_count = 0

    for idx, row in pending_df.iterrows():
        message = {
            "Id": str(idx),
            "MessageBody": json.dumps({
                "doc_id": row["doc_id"],
                "year": int(row["year"]),
                "s3_pdf_key": row["pdf_s3_key"],
            }),
        }
        batch.append(message)

        if len(batch) >= 10:
            # Send batch
            response = sqs_client.send_message_batch(
                QueueUrl=SQS_QUEUE_URL,
                Entries=batch,
            )
            queued_count += len(batch)
            print(f"Queued {queued_count} documents...")
            batch = []

    # Send remaining messages
    if batch:
        response = sqs_client.send_message_batch(
            QueueUrl=SQS_QUEUE_URL,
            Entries=batch,
        )
        queued_count += len(batch)

    print(f"✅ Queued {queued_count} documents for extraction")

    return 0


if __name__ == "__main__":
    # Get limit from command line if provided
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    sys.exit(main(limit))
