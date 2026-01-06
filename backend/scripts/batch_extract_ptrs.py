#!/usr/bin/env python3
"""Batch extract PTRs locally (mimics Lambda pipeline).

This script processes PTRs through the complete pipeline:
1. Download PDF from House website → bronze
2. Extract text → silver/text
3. Extract structured data → silver/structured
"""

import sys
import os
from pathlib import Path

# Add lib paths
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "ingestion"))
sys.path.insert(0, str(repo_root / "scripts"))

# Change to ingestion directory for imports
original_dir = os.getcwd()
os.chdir(repo_root / "ingestion")

import json
import io
import boto3
import pandas as pd
import requests
import tempfile

# Now imports should work
from lib.extractors.ptr_extractor import PTRExtractor

# Import terraform config from scripts
os.chdir(original_dir)
sys.path.insert(0, str(repo_root / "scripts"))
from lib.terraform_config import get_aws_config

# Change back to original directory
os.chdir(original_dir)

# Get configuration
config = get_aws_config()
S3_BUCKET = config.get("s3_bucket_id")
S3_REGION = config.get("s3_region", "us-east-1")

if not S3_BUCKET:
    print("ERROR: Missing required configuration.")
    sys.exit(1)


def process_ptr(doc_id: str, year: int, s3_client) -> dict:
    """Process a single PTR through the pipeline.

    Returns:
        dict with status and transaction count
    """
    print(f"\n{'='*80}")
    print(f"Processing PTR {doc_id}")
    print(f"{'='*80}")

    # Construct S3 keys
    pdf_key = f"bronze/house/financial/disclosures/year={year}/doc_id={doc_id}/{doc_id}.pdf"
    structured_key = f"silver/house/financial/structured/year={year}/doc_id={doc_id}/structured.json"

    # Download PDF
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        pdf_path = Path(tmp_pdf.name)

        try:
            # Try to download from bronze first
            try:
                print(f"  Checking bronze: s3://{S3_BUCKET}/{pdf_key}")
                s3_client.download_file(S3_BUCKET, pdf_key, str(pdf_path))
                print(f"  ✅ Found in bronze ({pdf_path.stat().st_size:,} bytes)")
            except:
                # Download from House website
                house_url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}/{doc_id}.pdf"
                print(f"  Downloading from House: {house_url}")

                response = requests.get(house_url, timeout=30)
                response.raise_for_status()

                pdf_path.write_bytes(response.content)
                print(f"  ✅ Downloaded ({len(response.content):,} bytes)")

                # Upload to bronze
                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=pdf_key,
                    Body=response.content,
                    ContentType="application/pdf"
                )
                print(f"  ✅ Uploaded to bronze")

            # Extract structured data
            print(f"  Extracting structured data...")
            extractor = PTRExtractor(pdf_path=str(pdf_path))
            structured_data = extractor.extract_with_fallback()
            structured_data["filing_id"] = doc_id

            trans_count = len(structured_data.get("transactions", []))
            confidence = structured_data["extraction_metadata"]["confidence_score"]
            completeness = structured_data["extraction_metadata"]["data_completeness"]["completeness_percentage"]

            print(f"  ✅ Extracted {trans_count} transactions")
            print(f"     Confidence: {confidence:.2%}, Completeness: {completeness:.1f}%")

            # Upload structured.json
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=structured_key,
                Body=json.dumps(structured_data, indent=2),
                ContentType="application/json"
            )
            print(f"  ✅ Uploaded structured.json")

            return {
                "status": "success",
                "doc_id": doc_id,
                "transactions": trans_count,
                "confidence": confidence,
                "completeness": completeness
            }

        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "doc_id": doc_id,
                "error": str(e)
            }
        finally:
            # Clean up
            if pdf_path.exists():
                pdf_path.unlink()


def main(limit=None):
    """Batch process PTRs."""
    s3_client = boto3.client("s3", region_name=S3_REGION)

    # Load bronze CSV to get PTR info
    csv_path = "/Users/jake/Downloads/congress-disclosures-2025-11-25.csv"
    bronze_df = pd.read_csv(csv_path)
    ptrs_df = bronze_df[bronze_df["Filing Type"] == "P"].copy()
    ptrs_df["doc_id"] = ptrs_df["Document ID"].astype(str)

    # Load silver documents
    documents_s3_key = "silver/house/financial/documents/year=2025/part-0000.parquet"
    response = s3_client.get_object(Bucket=S3_BUCKET, Key=documents_s3_key)
    documents_df = pd.read_parquet(io.BytesIO(response["Body"].read()))
    documents_df["doc_id"] = documents_df["doc_id"].astype(str)

    # Get pending PTRs
    ptr_docs = documents_df[
        (documents_df["doc_id"].isin(ptrs_df["doc_id"])) &
        (documents_df["extraction_status"] == "pending")
    ]

    if limit:
        ptr_docs = ptr_docs.head(limit)

    print(f"Processing {len(ptr_docs)} PTRs...")

    results = []
    for idx, row in ptr_docs.iterrows():
        result = process_ptr(row["doc_id"], int(row["year"]), s3_client)
        results.append(result)

    # Summary
    print(f"\n{'='*80}")
    print("PROCESSING SUMMARY")
    print(f"{'='*80}")

    success = [r for r in results if r["status"] == "success"]
    errors = [r for r in results if r["status"] == "error"]

    total_transactions = sum(r.get("transactions", 0) for r in success)
    avg_confidence = sum(r.get("confidence", 0) for r in success) / len(success) if success else 0

    print(f"Total processed: {len(results)}")
    print(f"  ✅ Success: {len(success)}")
    print(f"  ❌ Errors: {len(errors)}")
    print(f"  📊 Total transactions: {total_transactions}")
    print(f"  🎯 Average confidence: {avg_confidence:.2%}")

    if errors:
        print(f"\nErrors:")
        for r in errors:
            print(f"  {r['doc_id']}: {r['error']}")

    return 0


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    sys.exit(main(limit=limit))
