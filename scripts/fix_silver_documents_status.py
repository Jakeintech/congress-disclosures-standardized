#!/usr/bin/env python3
"""Fix silver documents table by updating extraction status based on S3 reality.

This script:
1. Reads silver/house/financial/documents parquet table
2. Checks which documents have extracted text and structured JSON
3. Updates extraction_status, extraction_method, pages, etc. based on reality
4. Writes corrected parquet back to S3
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any
import tempfile
import os
import gzip

# Add lib paths
sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion"))
sys.path.insert(0, str(Path(__file__).parent))

import boto3
import pandas as pd
from lib.terraform_config import get_aws_config

# Get configuration
config = get_aws_config()
S3_BUCKET = config.get("s3_bucket_id")
S3_REGION = config.get("s3_region", "us-east-1")

if not S3_BUCKET:
    print("ERROR: Missing required configuration.")
    sys.exit(1)


def check_extraction_exists(s3_client, doc_id: str, year: int) -> Dict[str, Any]:
    """Check what extraction artifacts exist for a document.

    Returns:
        Dict with: has_text, has_structured, extraction_method, pages, char_count
    """
    result = {
        "has_text": False,
        "has_structured": False,
        "extraction_method": "pending",
        "pages": 0,
        "char_count": 0,
        "text_s3_key": None,
        "json_s3_key": None,
    }

    # Check for text extraction (try different extraction methods)
    extraction_methods = ["pypdf", "textract", "textract-async"]

    for method in extraction_methods:
        text_key = f"silver/house/financial/text/extraction_method={method}/year={year}/doc_id={doc_id}/raw_text.txt.gz"

        try:
            response = s3_client.head_object(Bucket=S3_BUCKET, Key=text_key)
            result["has_text"] = True
            result["extraction_method"] = method
            result["text_s3_key"] = text_key

            # Try to read and count chars
            try:
                obj = s3_client.get_object(Bucket=S3_BUCKET, Key=text_key)
                text = gzip.decompress(obj["Body"].read()).decode("utf-8")
                result["char_count"] = len(text)
            except Exception:
                pass

            break
        except s3_client.exceptions.NoSuchKey:
            continue
        except Exception:
            continue

    # Check for structured JSON
    structured_key = f"silver/house/financial/structured/year={year}/doc_id={doc_id}/structured.json"

    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=structured_key)
        result["has_structured"] = True
        result["json_s3_key"] = structured_key

        # Parse JSON to get pages count if available
        try:
            data = json.loads(response["Body"].read())
            # Try to get pages from extraction metadata
            if "extraction_metadata" in data:
                if "pages" in data["extraction_metadata"]:
                    result["pages"] = data["extraction_metadata"]["pages"]
        except Exception:
            pass

    except s3_client.exceptions.NoSuchKey:
        pass
    except Exception:
        pass

    return result


def main():
    """Fix silver documents table."""
    s3_client = boto3.client("s3", region_name=S3_REGION)

    year = 2025  # Focus on 2025 for now

    print(f"Fixing silver documents table for year={year}")
    print()

    # Step 1: Download current documents parquet
    documents_key = f"silver/house/financial/documents/year={year}/part-0000.parquet"

    print(f"Downloading {documents_key}...")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
        tmp_path = tmp.name
        s3_client.download_file(S3_BUCKET, documents_key, tmp_path)

    # Read parquet
    df = pd.read_parquet(tmp_path)
    os.unlink(tmp_path)

    print(f"Loaded {len(df)} documents")
    print(f"  Current status breakdown:")
    print(df['extraction_status'].value_counts().to_string())
    print()

    # Step 2: Check S3 for each document
    print("Checking S3 for extraction artifacts...")
    print()

    updated_count = 0
    checked_count = 0

    for idx, row in df.iterrows():
        doc_id = row['doc_id']
        year_val = row['year']

        checked_count += 1

        # Check every 100 docs
        if checked_count % 100 == 0:
            print(f"  Checked {checked_count}/{len(df)} documents, updated {updated_count}")

        # Check what exists
        extraction = check_extraction_exists(s3_client, doc_id, year_val)

        # Update row if extraction found
        if extraction["has_text"] or extraction["has_structured"]:
            df.at[idx, 'extraction_status'] = 'success'
            df.at[idx, 'extraction_method'] = extraction['extraction_method']

            if extraction['pages'] > 0:
                df.at[idx, 'pages'] = extraction['pages']

            if extraction['char_count'] > 0:
                df.at[idx, 'char_count'] = extraction['char_count']

            if extraction['text_s3_key']:
                df.at[idx, 'text_s3_key'] = extraction['text_s3_key']

            if extraction['json_s3_key']:
                df.at[idx, 'json_s3_key'] = extraction['json_s3_key']

            updated_count += 1

    print()
    print(f"Checked {checked_count} documents")
    print(f"Updated {updated_count} with extraction artifacts found")
    print()

    # Show new status breakdown
    print("New status breakdown:")
    print(df['extraction_status'].value_counts().to_string())
    print()

    # Step 3: Write updated parquet back to S3
    print(f"Writing updated parquet to {documents_key}...")

    # Write to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
        tmp_path = tmp.name
        df.to_parquet(tmp_path, index=False, engine='pyarrow')

    # Upload to S3
    s3_client.upload_file(
        tmp_path,
        S3_BUCKET,
        documents_key,
        ExtraArgs={'ContentType': 'application/x-parquet'}
    )

    os.unlink(tmp_path)

    print("✅ Updated silver documents table")
    print()

    # Step 4: Regenerate silver_documents.json for website
    print("Regenerating silver_documents.json for website...")

    # Create manifest
    documents_list = df.to_dict('records')

    # Convert non-serializable types
    for doc in documents_list:
        for key, value in doc.items():
            if pd.isna(value):
                doc[key] = None
            elif isinstance(value, (pd.Timestamp, pd.Timestamp)):
                doc[key] = value.isoformat() if value is not None else None

    manifest = {
        "generated_at": pd.Timestamp.now(tz='UTC').isoformat(),
        "total_documents": len(df),
        "by_status": df['extraction_status'].value_counts().to_dict(),
        "by_method": df['extraction_method'].value_counts().to_dict(),
        "documents": documents_list
    }

    # Upload JSON
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key="silver_documents.json",
        Body=json.dumps(manifest, indent=2, default=str),
        ContentType="application/json"
    )

    print("✅ Regenerated silver_documents.json")
    print()
    print(f"Status: {updated_count} documents now show as 'success'")

    return 0


if __name__ == "__main__":
    sys.exit(main())
