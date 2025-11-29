#!/usr/bin/env python3
"""Generate Type T (Termination) reports table from structured.json files.

This script is SPECIFIC to Filing Type T (Termination Reports).
These are filed when a Member/Employee leaves office or employment.

This script:
1. Reads bronze manifest from S3 to get Type T metadata
2. Reads structured.json files from silver/structured_code layer (Type T only)
3. Flattens termination reports (one row per report)
4. Generates parquet table: silver/house/financial/type_t_terminations/
5. Generates JSON for website: website/api/v1/terminations.json
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import io

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

MANIFEST_KEY = "website/api/v1/documents/manifest.json"
OUTPUT_JSON_KEY = "website/api/v1/terminations.json"


def load_manifest_metadata(s3_client) -> pd.DataFrame:
    """Load bronze manifest with Type T metadata from S3."""
    print(f"Loading bronze metadata from s3://{S3_BUCKET}/{MANIFEST_KEY}...")
    
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=MANIFEST_KEY)
        data = json.loads(response["Body"].read().decode("utf-8"))
        
        filings = data.get("filings", [])
        if not filings:
            print("⚠️  No filings found in manifest")
            return pd.DataFrame()
            
        df = pd.DataFrame(filings)
        
        # Ensure required columns exist
        required_cols = ["doc_id", "filing_date", "first_name", "last_name", "state_district", "filing_type", "year"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = None
        
        # Filter to Type T (Termination)
        terminations = df[df["filing_type"] == "T"].copy()
        
        print(f"Found {len(terminations)} Termination reports (Type T)")
        
        return terminations
        
    except s3_client.exceptions.NoSuchKey:
        print(f"❌ Manifest not found at {MANIFEST_KEY}")
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error loading manifest: {e}")
        return pd.DataFrame()


def load_structured_json(s3_client, doc_id: str, year: int) -> Dict[str, Any]:
    """Load structured.json for a document from S3."""
    s3_key = f"silver/house/financial/structured_code/year={year}/filing_type=T/doc_id={doc_id}.json"

    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        data = json.loads(response["Body"].read())
        return data
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        return None


def convert_to_s3_url(doc_id: str, year: int) -> str:
    """Convert to S3 URL for the PDF."""
    return f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com/bronze/house/financial/disclosures/year={year}/doc_id={doc_id}/{doc_id}.pdf"


def create_termination_row(filing_metadata: pd.Series, structured_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create termination report row."""
    
    filer_info = structured_data.get("filer_info", {})
    report_type = structured_data.get("report_type", {})
    extraction_metadata = structured_data.get("extraction_metadata", {})
    
    termination_row = {
        # From bronze metadata
        "doc_id": str(filing_metadata["doc_id"]),
        "year": int(filing_metadata["year"]) if pd.notna(filing_metadata["year"]) else None,
        "filing_date": filing_metadata["filing_date"],
        "first_name": filing_metadata["first_name"],
        "last_name": filing_metadata["last_name"],
        "state_district": filing_metadata["state_district"],
        "pdf_url": convert_to_s3_url(filing_metadata["doc_id"], filing_metadata["year"]),

        # From structured.json
        "filer_full_name": filer_info.get("full_name"),
        "filer_type": filer_info.get("filer_type"),
        "termination_date": report_type.get("termination_date"),

        # From extraction_metadata
        "extraction_confidence": extraction_metadata.get("confidence_score"),
        "extraction_method": extraction_metadata.get("method"),
    }

    return termination_row


def main():
    """Generate Type T terminations table."""
    s3_client = boto3.client("s3", region_name=S3_REGION)

    # Load bronze metadata
    bronze_df = load_manifest_metadata(s3_client)
    
    if bronze_df.empty:
        print("❌ No Termination reports found to process.")
        return 1

    # Process each termination report
    all_terminations = []
    success_count = 0
    no_data_count = 0

    print()
    print("Processing Termination reports...")
    print()

    for idx, row in bronze_df.iterrows():
        doc_id = str(row["doc_id"])
        try:
            year = int(row["year"])
        except (ValueError, TypeError):
            continue

        # Load structured.json
        structured_data = load_structured_json(s3_client, doc_id, year)

        if not structured_data:
            no_data_count += 1
            continue

        # Create termination row
        termination_row = create_termination_row(row, structured_data)
        all_terminations.append(termination_row)
        success_count += 1
        if success_count <= 10:  # Show first 10
            print(f"  ✅ {doc_id}: {row['first_name']} {row['last_name']}")

    print()
    print(f"Total Termination reports processed: {len(bronze_df)}")
    print(f"  ✅ With structured data: {success_count}")
    print(f"  ⚠️  Missing structured data: {no_data_count}")
    print()

    if not all_terminations:
        print("⚠️ No terminations to save.")
        # Upload empty JSON
        json_data = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_terminations": 0,
            "terminations": []
        }
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=OUTPUT_JSON_KEY,
            Body=json.dumps(json_data, indent=2, default=str),
            ContentType="application/json",
            CacheControl="max-age=300"
        )
        return 0
    
    # Convert to DataFrame
    terminations_df = pd.DataFrame(all_terminations)

    # Show sample
    print("Sample terminations:")
    print(terminations_df.head(5)[["first_name", "last_name", "termination_date", "filing_date"]].to_string(index=False))
    print()

    # Save to parquet
    parquet_key = "silver/house/financial/type_t_terminations/year=2025/part-0000.parquet"
    print(f"Saving to s3://{S3_BUCKET}/{parquet_key}...")

    parquet_buffer = io.BytesIO()
    terminations_df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
    parquet_buffer.seek(0)

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=parquet_key,
        Body=parquet_buffer.getvalue(),
        ContentType="application/x-parquet"
    )

    print(f"✅ Saved {len(terminations_df)} terminations to parquet")

    # Generate JSON for website
    print(f"Generating {OUTPUT_JSON_KEY} for website...")

    terminations_list = terminations_df.to_dict("records")

    json_data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_terminations": len(all_terminations),
        "terminations": terminations_list
    }

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=OUTPUT_JSON_KEY,
        Body=json.dumps(json_data, indent=2, default=str),
        ContentType="application/json",
        CacheControl="max-age=300"
    )

    print(f"✅ Saved {len(terminations_list)} terminations to JSON")
    print()
    print(f"🌐 Website URL: https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{OUTPUT_JSON_KEY}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
