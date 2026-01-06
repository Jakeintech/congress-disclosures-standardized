#!/usr/bin/env python3
"""
Test the Congressional disclosures pipeline end-to-end.

This script:
1. Uploads 2025FD files to bronze layer
2. Invokes index-to-silver Lambda
3. Verifies silver layer outputs
4. Checks for manifest.json

Usage:
    python3 test_pipeline.py --year 2025
"""

import argparse
import json
import sys
from pathlib import Path

import boto3

# Configuration
S3_BUCKET = "congress-disclosures-standardized"
LAMBDA_PREFIX = "congress-disclosures-development"
DOWNLOADS_DIR = Path("/Users/jake/Downloads")


def main():
    parser = argparse.ArgumentParser(description="Test Congressional disclosures pipeline")
    parser.add_argument("--year", type=int, default=2025, help="Year to process")
    parser.add_argument("--skip-upload", action="store_true", help="Skip file upload step")
    args = parser.parse_args()

    year = args.year
    print(f"{'='*60}")
    print(f"Congressional Disclosures Pipeline Test")
    print(f"Year: {year}")
    print(f"Bucket: {S3_BUCKET}")
    print(f"{'='*60}\n")

    s3_client = boto3.client("s3")
    lambda_client = boto3.client("lambda")

    # Step 1: Upload files to bronze layer
    if not args.skip_upload:
        print(f"[1/4] Uploading {year}FD files to S3...")
        year_dir = DOWNLOADS_DIR / f"{year}FD"

        if not year_dir.exists():
            print(f"✗ Directory not found: {year_dir}")
            print(f"  Please ensure {year}FD.xml and {year}FD.txt are in {DOWNLOADS_DIR}/{year}FD/")
            sys.exit(1)

        xml_file = year_dir / f"{year}FD.xml"
        txt_file = year_dir / f"{year}FD.txt"

        if not xml_file.exists() or not txt_file.exists():
            print(f"✗ Required files not found in {year_dir}")
            print(f"  Expected: {year}FD.xml and {year}FD.txt")
            sys.exit(1)

        # Upload XML
        xml_key = f"bronze/house/financial/year={year}/index/{year}FD.xml"
        s3_client.upload_file(str(xml_file), S3_BUCKET, xml_key)
        print(f"  ✓ Uploaded {xml_file.name} → s3://{S3_BUCKET}/{xml_key}")

        # Upload TXT
        txt_key = f"bronze/house/financial/year={year}/index/{year}FD.txt"
        s3_client.upload_file(str(txt_file), S3_BUCKET, txt_key)
        print(f"  ✓ Uploaded {txt_file.name} → s3://{S3_BUCKET}/{txt_key}")
        print()
    else:
        print("[1/4] Skipping file upload (--skip-upload flag)\n")

    # Step 2: Invoke index-to-silver Lambda
    print("[2/4] Invoking index-to-silver Lambda...")
    lambda_name = f"{LAMBDA_PREFIX}-index-to-silver"

    # IMPORTANT: Proper JSON payload to avoid UTF-8 errors
    payload = {"year": year}

    try:
        response = lambda_client.invoke(
            FunctionName=lambda_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )

        response_payload = json.loads(response["Payload"].read())

        if response_payload.get("status") == "success":
            print(f"  ✓ index-to-silver completed")
            print(f"  Filings written: {response_payload.get('filings_written', 'N/A')}")
            print(f"  Documents initialized: {response_payload.get('documents_initialized', 'N/A')}")
            print()
        else:
            print(f"  ✗ index-to-silver failed")
            print(f"  Full response: {json.dumps(response_payload, indent=2)}")
            sys.exit(1)

    except Exception as e:
        print(f"  ✗ Lambda invocation failed: {str(e)}")
        sys.exit(1)

    # Step 3: Check silver layer output
    print("[3/4] Checking silver layer Parquet files...")

    filings_prefix = f"silver/house/financial/filings/year={year}/"
    documents_prefix = f"silver/house/financial/documents/year={year}/"

    try:
        filings_objects = s3_client.list_objects_v2(
            Bucket=S3_BUCKET, Prefix=filings_prefix
        )
        if "Contents" in filings_objects:
            total_size = sum(obj["Size"] for obj in filings_objects["Contents"])
            print(f"  ✓ Filings: {len(filings_objects['Contents'])} files, {total_size:,} bytes")
        else:
            print(f"  ⚠ No filings found at {filings_prefix}")

        documents_objects = s3_client.list_objects_v2(
            Bucket=S3_BUCKET, Prefix=documents_prefix
        )
        if "Contents" in documents_objects:
            total_size = sum(obj["Size"] for obj in documents_objects["Contents"])
            print(f"  ✓ Documents: {len(documents_objects['Contents'])} files, {total_size:,} bytes")
        else:
            print(f"  ⚠ No documents found at {documents_prefix}")
        print()
    except Exception as e:
        print(f"  ✗ Error listing S3 objects: {str(e)}")
        print()

    # Step 4: Check for manifest.json
    print("[4/4] Checking for manifest.json...")
    try:
        manifest_obj = s3_client.get_object(Bucket=S3_BUCKET, Key="manifest.json")
        manifest_data = json.loads(manifest_obj["Body"].read())

        print(f"  ✓ manifest.json exists")
        print(f"  Total filings: {manifest_data['stats']['total_filings']:,}")
        print(f"  Total members: {manifest_data['stats']['total_members']:,}")
        print(f"  Latest year: {manifest_data['stats']['latest_year']}")
        print(f"  Last updated: {manifest_data['stats']['last_updated']}")
    except s3_client.exceptions.NoSuchKey:
        print(f"  ⚠ manifest.json not found (will be generated after adding manifest generator)")
    except Exception as e:
        print(f"  ✗ Error reading manifest: {str(e)}")
    print()

    print(f"{'='*60}")
    print("Pipeline test complete!")
    print(f"{'='*60}\n")

    print("Next steps:")
    print("1. Add manifest generation to Lambda")
    print("2. Deploy website to S3")
    print("3. Add cost protection")


if __name__ == "__main__":
    main()
