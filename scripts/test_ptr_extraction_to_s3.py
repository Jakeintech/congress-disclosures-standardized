#!/usr/bin/env python3
"""Test PTR extraction and upload structured.json to S3 silver layer."""

import sys
from pathlib import Path

# Add lib paths
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "ingestion"))
sys.path.insert(0, str(repo_root / "scripts"))

import json
import boto3

# Now import from ingestion
from lib.extractors.ptr_extractor import PTRExtractor

# Import from scripts
from lib.terraform_config import get_aws_config

# Get configuration
config = get_aws_config()
S3_BUCKET = config.get("s3_bucket_id")
S3_REGION = config.get("s3_region", "us-east-1")

if not S3_BUCKET:
    print("ERROR: Missing required configuration.")
    print("Please run 'terraform apply' or set S3_BUCKET_ID environment variable")
    sys.exit(1)


def main():
    """Extract Nancy Pelosi PTR and upload to S3."""

    # Test document ID (Nancy Pelosi PTR)
    doc_id = "20026590"
    pdf_path = "analysis/sample_pdfs/P_20026590_real.pdf"

    print(f"Extracting PTR {doc_id}...")
    print(f"  PDF: {pdf_path}")
    print()

    # Extract structured data
    extractor = PTRExtractor(pdf_path=pdf_path)
    result = extractor.extract_with_fallback()

    # Add filing_id to match bronze data
    result["filing_id"] = doc_id

    # Show summary
    print("✅ Extraction complete!")
    print(f"  Filer: {result['filer_info']['full_name']}")
    print(f"  Transactions: {len(result['transactions'])}")
    print(f"  Confidence: {result['extraction_metadata']['confidence_score']:.2f}")
    print(f"  Completeness: {result['extraction_metadata']['data_completeness']['completeness_percentage']}%")
    print()

    # Save locally for inspection
    output_path = f"/tmp/ptr_{doc_id}_structured.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"💾 Saved locally: {output_path}")

    # Upload to S3 silver layer
    s3_key = f"silver/house/financial/structured/year=2025/doc_id={doc_id}/structured.json"

    print(f"📤 Uploading to S3...")
    print(f"  Bucket: {S3_BUCKET}")
    print(f"  Key: {s3_key}")

    s3_client = boto3.client("s3", region_name=S3_REGION)

    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(result, indent=2),
            ContentType="application/json",
            ACL="public-read"  # Make publicly accessible for website
        )

        print()
        print("✅ Upload successful!")
        print(f"📊 URL: https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}")
        print()
        print("Sample transaction:")
        trans = result['transactions'][0]
        print(f"  {trans['asset_name']}")
        print(f"  {trans['transaction_type']} on {trans['transaction_date']}")
        print(f"  Amount: {trans['amount_range']}")
        print()

    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
