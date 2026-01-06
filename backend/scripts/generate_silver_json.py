#!/usr/bin/env python3
"""Generate silver_documents.json from parquet files for testing.

This script reads the silver layer parquet files and generates the JSON
files needed for the website UI.
"""

import sys
from pathlib import Path

# Add lib paths
sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion"))
sys.path.insert(0, str(Path(__file__).parent))

import boto3
import pandas as pd
from lib.manifest_generator import (
    generate_silver_documents_json,
    update_manifest_incremental,
)
from lib.terraform_config import get_aws_config

# Get configuration from Terraform outputs (no hardcoded secrets!)
config = get_aws_config()
S3_BUCKET = config.get("s3_bucket_id")
S3_REGION = config.get("s3_region", "us-east-1")

if not S3_BUCKET:
    print("ERROR: Missing required configuration.")
    print("Please run 'terraform apply' or set S3_BUCKET_ID environment variable")
    sys.exit(1)


def main():
    """Generate silver_documents.json from parquet files."""
    s3_client = boto3.client("s3", region_name=S3_REGION)

    # Read documents parquet from S3
    documents_s3_key = (
        "silver/house/financial/documents/year=2025/part-0000.parquet"
    )

    print(f"Reading documents from s3://{S3_BUCKET}/{documents_s3_key}")

    try:
        # Download parquet file
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=documents_s3_key)
        # Read into memory first
        import io
        parquet_bytes = response["Body"].read()
        documents_df = pd.read_parquet(io.BytesIO(parquet_bytes))

        print(f"Found {len(documents_df)} documents")

        # Convert to list of dicts
        documents = documents_df.to_dict("records")

        # Generate silver_documents.json
        print("Generating silver_documents.json...")
        result = generate_silver_documents_json(
            documents=documents,
            s3_bucket=S3_BUCKET,
            s3_key="silver_documents.json",
        )

        print(f"✅ Silver documents JSON generated successfully!")
        print(f"   - Documents count: {result['documents_count']}")
        print(f"   - Size: {result['documents_size_bytes']:,} bytes")
        print(
            f"   - Compressed size: {result['documents_size_compressed']:,} bytes"
        )
        print(
            f"   - URL: https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/silver_documents.json"
        )

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
