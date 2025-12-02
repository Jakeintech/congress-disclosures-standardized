#!/usr/bin/env python3
"""Generate Type A/N (Annual/New Filer) assets table from structured.json files.

This script is SPECIFIC to Filing Type A (Annual) and N (New Filer).
These filing types contain asset/income disclosures (Schedule A), not transactions.

This script:
1. Reads bronze manifest from S3 to get Type A/N metadata
2. Reads structured.json files from silver/structured_code layer (Type A/N only)
3. Flattens assets and income (one row per asset)
4. Generates parquet table: silver/house/financial/type_a_assets/
5. Generates JSON for website: website/api/v1/assets.json
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
OUTPUT_JSON_KEY = "website/api/v1/assets.json"


def load_manifest_metadata(s3_client) -> pd.DataFrame:
    """Load bronze manifest with Type A/N metadata from S3."""
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
        
        # Filter to Type A and N (Annual and New Filer)
        annual_filings = df[df["filing_type"].isin(["A", "N"])].copy()
        
        print(f"Found {len(annual_filings)} Annual/New Filer reports (Type A/N)")
        
        return annual_filings
        
    except s3_client.exceptions.NoSuchKey:
        print(f"❌ Manifest not found at {MANIFEST_KEY}")
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error loading manifest: {e}")
        return pd.DataFrame()


def load_structured_json(s3_client, doc_id: str, year: int, filing_type: str) -> Dict[str, Any]:
    """Load structured.json for a document from S3."""
    # Ensure filing_type starts with 'type_' if it's a single letter code
    if len(filing_type) == 1:
        filing_type_folder = f"type_{filing_type.lower()}"
    else:
        filing_type_folder = filing_type.lower()
        
    s3_key = f"silver/objects/{filing_type_folder}/{year}/{doc_id}/extraction.json"

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


def flatten_assets(filing_metadata: pd.Series, structured_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten structured Annual/New Filer data into asset rows."""
    assets = []

    filer_info = structured_data.get("filer_info", {})
    extraction_metadata = structured_data.get("extraction_metadata", {})
    
    # Get assets from structured data
    extracted_assets = structured_data.get("assets_and_income", [])

    for idx, asset in enumerate(extracted_assets, 1):
        asset_row = {
            # From bronze metadata
            "doc_id": str(filing_metadata["doc_id"]),
            "year": int(filing_metadata["year"]) if pd.notna(filing_metadata["year"]) else None,
            "filing_date": filing_metadata["filing_date"],
            "filing_type": filing_metadata["filing_type"],
            "first_name": filing_metadata["first_name"],
            "last_name": filing_metadata["last_name"],
            "state_district": filing_metadata["state_district"],
            "pdf_url": convert_to_s3_url(filing_metadata["doc_id"], filing_metadata["year"]),

            # From structured.json filer_info
            "filer_full_name": filer_info.get("full_name"),
            "filer_type": filer_info.get("filer_type"),

            # From asset
            "asset_id": idx,
            "asset_name": asset.get("asset_name"),
            "owner_code": asset.get("owner_code"),

            # From extraction_metadata
            "extraction_confidence": extraction_metadata.get("confidence_score"),
            "extraction_method": extraction_metadata.get("method"),
        }

        assets.append(asset_row)

    return assets


def main():
    """Generate Type A/N assets table."""
    s3_client = boto3.client("s3", region_name=S3_REGION)

    # Load bronze metadata
    bronze_df = load_manifest_metadata(s3_client)
    
    if bronze_df.empty:
        print("❌ No Annual/New Filer reports found to process.")
        return 1

    # Process each Annual/New Filer report
    all_assets = []
    success_count = 0
    no_data_count = 0

    print()
    print("Processing Annual/New Filer reports...")
    print()

    for idx, row in bronze_df.iterrows():
        doc_id = str(row["doc_id"])
        filing_type = row["filing_type"]
        try:
            year = int(row["year"])
        except (ValueError, TypeError):
            continue

        # Load structured.json
        structured_data = load_structured_json(s3_client, doc_id, year, filing_type)

        if not structured_data:
            no_data_count += 1
            continue

        # Flatten assets
        assets = flatten_assets(row, structured_data)

        if assets:
            all_assets.extend(assets)
            success_count += 1
            if success_count <= 10:  # Show first 10
                print(f"  ✅ {doc_id}: {len(assets)} assets ({row['first_name']} {row['last_name']})")

    print()
    print(f"Total Annual/New Filer reports processed: {len(bronze_df)}")
    print(f"  ✅ With structured data: {success_count}")
    print(f"  ⚠️  Missing structured data: {no_data_count}")
    print(f"  📊 Total assets: {len(all_assets)}")
    print()

    if not all_assets:
        print("⚠️ No assets to save.")
        # Upload empty JSON
        json_data = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_reports": success_count,
            "total_assets": 0,
            "assets_included": 0,
            "assets": []
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
    assets_df = pd.DataFrame(all_assets)

    # Show sample
    print("Sample assets:")
    print(assets_df.head(3)[["first_name", "last_name", "asset_name", "owner_code"]].to_string(index=False))
    print()

    # Save to parquet
    parquet_key = f"silver/tables/assets/year={year}/part-0000.parquet"
    print(f"Saving to s3://{S3_BUCKET}/{parquet_key}...")

    parquet_buffer = io.BytesIO()
    assets_df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
    parquet_buffer.seek(0)

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=parquet_key,
        Body=parquet_buffer.getvalue(),
        ContentType="application/x-parquet"
    )

    print(f"✅ Saved {len(assets_df)} assets to parquet")

    # Generate JSON for website
    print(f"Generating {OUTPUT_JSON_KEY} for website...")

    # Limit to recent assets for website (last 1000)
    recent_assets = assets_df.sort_values("filing_date", ascending=False).head(1000)
    assets_list = recent_assets.to_dict("records")
    included_count = len(recent_assets)

    json_data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_reports": success_count,
        "total_assets": len(all_assets),
        "assets_included": included_count,
        "assets": assets_list
    }

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=OUTPUT_JSON_KEY,
        Body=json.dumps(json_data, indent=2, default=str),
        ContentType="application/json",
        CacheControl="max-age=300"
    )

    print(f"✅ Saved {included_count} assets to JSON")
    print()
    print(f"🌐 Website URL: https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{OUTPUT_JSON_KEY}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
