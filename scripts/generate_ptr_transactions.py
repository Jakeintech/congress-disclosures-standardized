#!/usr/bin/env python3
"""Generate ptr_transactions table from structured.json files.

This script:
1. Reads bronze CSV to get PTR metadata (name, state, filing date)
2. Reads structured.json files from silver/structured layer
3. Flattens transactions (one row per transaction, not per filing)
4. Generates parquet table: silver/house/financial/ptr_transactions/
5. Generates JSON for website: ptr_transactions.json
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

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


def load_bronze_metadata(s3_client, year: int = 2025) -> pd.DataFrame:
    """Load bronze CSV with PTR metadata.

    Args:
        s3_client: Boto3 S3 client
        year: Filing year

    Returns:
        DataFrame with columns: doc_id, filing_date, first_name, last_name, state_district, filing_type
    """
    # Try to load from S3 (if uploaded) or local file
    csv_path = f"/Users/jake/Downloads/congress-disclosures-{year}-11-25.csv"

    print(f"Loading bronze metadata from {csv_path}...")
    df = pd.read_csv(csv_path)

    # Rename columns to match our schema
    df = df.rename(columns={
        "Year": "year",
        "Filing Date": "filing_date",
        "First Name": "first_name",
        "Last Name": "last_name",
        "State/District": "state_district",
        "Filing Type": "filing_type",
        "Document ID": "doc_id",
        "PDF URL": "pdf_url"
    })

    # Filter to PTRs only
    ptrs = df[df["filing_type"] == "P"].copy()

    print(f"Found {len(ptrs)} PTRs in bronze metadata")

    return ptrs


def load_structured_json(s3_client, doc_id: str, year: int) -> Dict[str, Any]:
    """Load structured.json for a document from S3.

    Args:
        s3_client: Boto3 S3 client
        doc_id: Document ID
        year: Filing year

    Returns:
        Structured data dict or None if not found
    """
    s3_key = f"silver/house/financial/structured/year={year}/doc_id={doc_id}/structured.json"

    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        data = json.loads(response["Body"].read())
        return data
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        print(f"  ⚠️  Error loading {doc_id}: {e}")
        return None


def convert_to_s3_url(doc_id: int, year: int) -> str:
    """Convert external PDF URL to S3 URL.

    Args:
        doc_id: Document ID
        year: Filing year

    Returns:
        S3 URL for the PDF
    """
    return f"https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/bronze/house/financial/disclosures/year={year}/doc_id={doc_id}/{doc_id}.pdf"


def flatten_transactions(ptr_metadata: pd.Series, structured_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten structured PTR data into transaction rows.

    Args:
        ptr_metadata: Bronze metadata row (name, state, filing date)
        structured_data: Structured.json data with transactions

    Returns:
        List of transaction dicts (one per transaction)
    """
    transactions = []

    filer_info = structured_data.get("filer_info", {})
    extraction_metadata = structured_data.get("extraction_metadata", {})

    for idx, trans in enumerate(structured_data.get("transactions", []), 1):
        transaction_row = {
            # From bronze CSV
            "doc_id": ptr_metadata["doc_id"],
            "year": ptr_metadata["year"],
            "filing_date": ptr_metadata["filing_date"],
            "first_name": ptr_metadata["first_name"],
            "last_name": ptr_metadata["last_name"],
            "state_district": ptr_metadata["state_district"],
            "pdf_url": convert_to_s3_url(ptr_metadata["doc_id"], ptr_metadata["year"]),  # Use S3 URL instead of external URL

            # From structured.json filer_info
            "filer_full_name": filer_info.get("full_name"),
            "filer_type": filer_info.get("filer_type"),

            # From transaction
            "transaction_id": idx,
            "asset_name": trans.get("asset_name"),
            "transaction_type": trans.get("transaction_type"),
            "transaction_date": trans.get("transaction_date"),
            "notification_date": trans.get("notification_date"),
            "amount_range": trans.get("amount_range"),
            "amount_low": trans.get("amount_low"),
            "amount_high": trans.get("amount_high"),
            "amount_column": trans.get("amount_column"),
            "owner_code": trans.get("owner_code"),

            # From extraction_metadata
            "extraction_confidence": extraction_metadata.get("confidence_score"),
            "extraction_method": extraction_metadata.get("extraction_method"),
            "pdf_type": extraction_metadata.get("pdf_type"),
            "data_completeness_pct": extraction_metadata.get("data_completeness", {}).get("completeness_percentage"),
        }

        transactions.append(transaction_row)

    return transactions


def main():
    """Generate PTR transactions table."""
    s3_client = boto3.client("s3", region_name=S3_REGION)

    # Load bronze metadata
    bronze_df = load_bronze_metadata(s3_client)

    # Process each PTR
    all_transactions = []
    success_count = 0
    no_data_count = 0

    print()
    print("Processing PTRs...")
    print()

    for idx, row in bronze_df.iterrows():
        doc_id = row["doc_id"]
        year = row["year"]

        # Load structured.json
        structured_data = load_structured_json(s3_client, doc_id, year)

        if not structured_data:
            no_data_count += 1
            if no_data_count <= 5:  # Only show first few
                print(f"  ⚠️  {doc_id}: No structured.json found")
            continue

        # Flatten transactions
        transactions = flatten_transactions(row, structured_data)

        if transactions:
            all_transactions.extend(transactions)
            success_count += 1
            if success_count <= 10:  # Show first 10
                print(f"  ✅ {doc_id}: {len(transactions)} transactions ({row['first_name']} {row['last_name']})")
        else:
            if no_data_count <= 5:
                print(f"  ⚠️  {doc_id}: 0 transactions extracted")

    if no_data_count > 5:
        print(f"  ... {no_data_count - 5} more without data")

    print()
    print(f"Total PTRs processed: {len(bronze_df)}")
    print(f"  ✅ With structured data: {success_count}")
    print(f"  ⚠️  Missing structured data: {no_data_count}")
    print(f"  📊 Total transactions: {len(all_transactions)}")
    print()

    if not all_transactions:
        print("❌ No transactions to save. Process some PTRs first.")
        return 1

    # Convert to DataFrame
    transactions_df = pd.DataFrame(all_transactions)

    # Show sample
    print("Sample transactions:")
    print(transactions_df.head(3)[["first_name", "last_name", "asset_name", "transaction_type", "transaction_date", "amount_range"]].to_string(index=False))
    print()

    # Save to parquet
    parquet_key = "silver/house/financial/ptr_transactions/year=2025/part-0000.parquet"
    print(f"Saving to s3://{S3_BUCKET}/{parquet_key}...")

    # Convert to parquet bytes
    import io
    parquet_buffer = io.BytesIO()
    transactions_df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
    parquet_buffer.seek(0)

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=parquet_key,
        Body=parquet_buffer.getvalue(),
        ContentType="application/x-parquet"
    )

    print(f"✅ Saved {len(transactions_df)} transactions to parquet")

    # Generate JSON for website
    json_key = "ptr_transactions.json"
    print(f"Generating {json_key} for website...")

    # Limit to recent transactions for website (last 1000)
    recent_transactions = transactions_df.sort_values("filing_date", ascending=False).head(1000)

    json_data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_ptrs": success_count,
        "total_transactions": len(all_transactions),
        "transactions_included": len(recent_transactions),
        "transactions": recent_transactions.to_dict("records")
    }

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=json_key,
        Body=json.dumps(json_data, indent=2),
        ContentType="application/json"
    )

    print(f"✅ Saved {len(recent_transactions)} transactions to JSON")
    print()
    print(f"🌐 Website URL: https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{json_key}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
