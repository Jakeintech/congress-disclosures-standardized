#!/usr/bin/env python3
"""Generate ptr_transactions table from structured.json files.

This script:
1. Reads bronze manifest from S3 to get PTR metadata (name, state, filing date)
2. Reads structured.json files from silver/structured layer
3. Flattens transactions (one row per transaction, not per filing)
4. Generates parquet table: silver/house/financial/ptr_transactions/
5. Generates JSON for website: website/api/v1/schedules/b/transactions.json
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
OUTPUT_JSON_KEY = "website/api/v1/schedules/b/transactions.json"


def load_manifest_metadata(s3_client) -> pd.DataFrame:
    """Load bronze manifest with PTR metadata from S3.

    Args:
        s3_client: Boto3 S3 client

    Returns:
        DataFrame with columns: doc_id, filing_date, first_name, last_name, state_district, filing_type
    """
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
        
        # Filter to PTRs only
        ptrs = df[df["filing_type"] == "P"].copy()
        

        
        return ptrs
        
    except s3_client.exceptions.NoSuchKey:
        print(f"❌ Manifest not found at {MANIFEST_KEY}")
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error loading manifest: {e}")
        return pd.DataFrame()


def load_structured_json(s3_client, doc_id: str, year: int) -> Dict[str, Any]:
    """Load structured.json for a document from S3.

    Args:
        s3_client: Boto3 S3 client
        doc_id: Document ID
        year: Filing year

    Returns:
        Structured data dict or None if not found
    """
    # Updated path structure to match new extractor output
    s3_key = f"silver/house/financial/structured_code/year={year}/filing_type=P/doc_id={doc_id}.json"

    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        data = json.loads(response["Body"].read())
        return data
    except s3_client.exceptions.NoSuchKey:
        # Try fallback to old path (backward compatibility)
        try:
            old_key = f"silver/house/financial/structured/year={year}/doc_id={doc_id}.json"
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=old_key)
            data = json.loads(response["Body"].read())
            return data
        except:
            return None
    except Exception as e:
        # print(f"  ⚠️  Error loading {doc_id}: {e}")
        return None


def convert_to_s3_url(doc_id: str, year: int) -> str:
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
    
    # Get transactions from top-level list (new format) or extract from schedules (old format)
    extracted_transactions = structured_data.get("transactions", [])
    
    # If no top-level transactions, try to extract from Schedule B tables
    if not extracted_transactions and "schedules" in structured_data:
        # This is a fallback for older extractions or different formats
        # For now, we'll rely on the extractor doing its job and populating "transactions"
        pass

    for idx, trans in enumerate(extracted_transactions, 1):
        transaction_row = {
            # From bronze metadata
            "doc_id": str(ptr_metadata["doc_id"]),
            "year": int(ptr_metadata["year"]) if pd.notna(ptr_metadata["year"]) else None,
            "filing_date": ptr_metadata["filing_date"],
            "first_name": ptr_metadata["first_name"],
            "last_name": ptr_metadata["last_name"],
            "state_district": ptr_metadata["state_district"],
            "pdf_url": convert_to_s3_url(ptr_metadata["doc_id"], ptr_metadata["year"]),

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
            "ticker": trans.get("ticker"),

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
    bronze_df = load_manifest_metadata(s3_client)
    
    if bronze_df.empty:
        print("❌ No PTRs found to process.")
        return 1

    # Process each PTR
    all_transactions = []
    success_count = 0
    no_data_count = 0

    print()
    print("Processing PTRs...")
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
            if no_data_count <= 5:  # Only show first few
                # print(f"  ⚠️  {doc_id}: No structured.json found")
                pass
            continue

        # Flatten transactions
        transactions = flatten_transactions(row, structured_data)

        if transactions:
            all_transactions.extend(transactions)
            success_count += 1
            if success_count <= 10:  # Show first 10
                print(f"  ✅ {doc_id}: {len(transactions)} transactions ({row['first_name']} {row['last_name']})")
        else:
            # print(f"  ⚠️  {doc_id}: 0 transactions extracted")
            pass

    print()
    print(f"Total PTRs processed: {len(bronze_df)}")
    print(f"  ✅ With structured data: {success_count}")
    print(f"  ⚠️  Missing structured data: {no_data_count}")
    print(f"  📊 Total transactions: {len(all_transactions)}")
    print()

    if not all_transactions:
        print("❌ No transactions to save. Process some PTRs first.")
        # We might want to upload an empty list instead of failing
        # return 1
    
    # Convert to DataFrame
    transactions_df = pd.DataFrame(all_transactions)

    # Show sample
    if not transactions_df.empty:
        print("Sample transactions:")
        print(transactions_df.head(3)[["first_name", "last_name", "asset_name", "transaction_type", "transaction_date", "amount_range"]].to_string(index=False))
        print()

        # Save to parquet
        parquet_key = "silver/house/financial/ptr_transactions/year=2025/part-0000.parquet"
        print(f"Saving to s3://{S3_BUCKET}/{parquet_key}...")

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
    else:
        print("⚠️ No transactions found, skipping parquet generation")

    # Generate JSON for website
    print(f"Generating {OUTPUT_JSON_KEY} for website...")

    # Limit to recent transactions for website (last 1000)
    if not transactions_df.empty:
        recent_transactions = transactions_df.sort_values("filing_date", ascending=False).head(1000)
        transactions_list = recent_transactions.to_dict("records")
        included_count = len(recent_transactions)
    else:
        transactions_list = []
        included_count = 0

    json_data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_ptrs": success_count,
        "total_transactions": len(all_transactions),
        "transactions_included": included_count,
        "transactions": transactions_list
    }

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=OUTPUT_JSON_KEY,
        Body=json.dumps(json_data, indent=2, default=str),
        ContentType="application/json",
        CacheControl="max-age=300"
    )

    print(f"✅ Saved {included_count} transactions to JSON")
    print()
    print(f"🌐 Website URL: https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{OUTPUT_JSON_KEY}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
