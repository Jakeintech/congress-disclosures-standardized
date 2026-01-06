#!/usr/bin/env python3
"""Queue PTRs (type P) for extraction through the pipeline.

This script:
1. Reads bronze CSV to identify PTRs
2. Cross-references with silver documents table
3. Queues pending PTRs to SQS for extraction
"""

import sys
import json
import io
from pathlib import Path

# Add lib paths
sys.path.insert(0, str(Path(__file__).parent))

import boto3
import pandas as pd
from lib.terraform_config import get_aws_config

# Get configuration
config = get_aws_config()
S3_BUCKET = config.get("s3_bucket_id")
S3_REGION = config.get("s3_region", "us-east-1")
SQS_QUEUE_URL = config.get("sqs_extraction_queue_url")

if not S3_BUCKET or not SQS_QUEUE_URL:
    print("ERROR: Missing required configuration.")
    sys.exit(1)


def main(limit=None):
    """Queue PTRs for extraction.

    Args:
        limit: Optional limit on number of PTRs to queue (for testing)
    """
    s3_client = boto3.client("s3", region_name=S3_REGION)
    sqs_client = boto3.client("sqs", region_name=S3_REGION)

    # Load bronze CSV to identify PTRs
    csv_path = "/Users/jake/Downloads/congress-disclosures-2025-11-25.csv"
    print(f"Loading bronze CSV from {csv_path}...")
    bronze_df = pd.read_csv(csv_path)

    # Filter to PTRs only
    ptrs_df = bronze_df[bronze_df["Filing Type"] == "P"].copy()
    ptrs_df["doc_id"] = ptrs_df["Document ID"].astype(str)

    print(f"Found {len(ptrs_df)} PTRs in bronze CSV")

    # Load silver documents table
    documents_s3_key = "silver/house/financial/documents/year=2025/part-0000.parquet"
    print(f"Loading silver documents from s3://{S3_BUCKET}/{documents_s3_key}...")

    response = s3_client.get_object(Bucket=S3_BUCKET, Key=documents_s3_key)
    documents_df = pd.read_parquet(io.BytesIO(response["Body"].read()))
    documents_df["doc_id"] = documents_df["doc_id"].astype(str)

    print(f"Found {len(documents_df)} documents in silver")

    # Cross-reference: PTRs that are pending in silver
    ptr_docs = documents_df[
        (documents_df["doc_id"].isin(ptrs_df["doc_id"])) &
        (documents_df["extraction_status"] == "pending")
    ]

    print(f"Found {len(ptr_docs)} PTRs pending extraction")

    if limit:
        ptr_docs = ptr_docs.head(limit)
        print(f"Limiting to {limit} PTRs for testing")

    if len(ptr_docs) == 0:
        print("No PTRs to queue!")
        return 0

    # Show sample
    print()
    print("Sample PTRs to queue:")
    for idx, row in ptr_docs.head(5).iterrows():
        doc_id = row["doc_id"]
        ptr_info = ptrs_df[ptrs_df["doc_id"] == doc_id].iloc[0]
        print(f"  {doc_id}: {ptr_info['First Name']} {ptr_info['Last Name']} - {ptr_info['State/District']}")
    print()

    # Queue to SQS in batches of 10
    batch = []
    queued_count = 0

    for idx, row in ptr_docs.iterrows():
        message = {
            "Id": f"ptr_{row['doc_id']}",
            "MessageBody": json.dumps({
                "doc_id": row["doc_id"],
                "year": int(row["year"]),
                "s3_pdf_key": row["pdf_s3_key"],
                "filing_type": "P"
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
            print(f"Queued {queued_count}/{len(ptr_docs)} PTRs...")
            batch = []

    # Send remaining messages
    if batch:
        response = sqs_client.send_message_batch(
            QueueUrl=SQS_QUEUE_URL,
            Entries=batch,
        )
        queued_count += len(batch)

    print()
    print(f"✅ Queued {queued_count} PTRs for extraction")
    print()
    print("Pipeline will:")
    print("  1. Download PDFs from House website (if not in bronze)")
    print("  2. Extract text → silver/house/financial/text/")
    print("  3. Update silver documents table")
    print()
    print("Next: Run structured extraction on processed PTRs")

    return 0


if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    sys.exit(main(limit=limit))
