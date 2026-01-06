import boto3
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "congress-disclosures-standardized")
S3_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_SILVER_PREFIX = "silver/house/financial/structured"
OUTPUT_KEY = "website/data/ptr_transactions.json"

s3 = boto3.client("s3", region_name=S3_REGION)

def list_structured_documents() -> List[str]:
    """List all structured JSON files in the silver layer."""
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_SILVER_PREFIX)

    for page in page_iterator:
        if "Contents" in page:
            for obj in page["Contents"]:
                if obj["Key"].endswith(".json"):
                    keys.append(obj["Key"])
    return keys

def process_document(key: str) -> List[Dict[str, Any]]:
    """Download and extract transactions from a structured JSON file."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        data = json.loads(response["Body"].read().decode("utf-8"))
        
        doc_id = data.get("doc_id")
        year = data.get("year")
        
        # Look for Schedule B (Transactions)
        # Note: handler.py maps tables to schedules A-I sequentially as a heuristic.
        # We'll look for any table in 'B' or just all tables for now since the heuristic is weak.
        # But strictly speaking, PTRs are usually Schedule B.
        
        transactions = []
        
        # Access schedules safely
        schedules = data.get("schedules", {})
        schedule_b = schedules.get("B", {})
        tables = schedule_b.get("tables", [])
        
        for table in tables:
            rows = table.get("rows", [])
            # Skip header row if it looks like a header
            start_idx = 0
            if rows and "Asset" in str(rows[0]):
                start_idx = 1
                
            for i in range(start_idx, len(rows)):
                row = rows[i]
                # Row is a dict of col_index -> text
                # Standard PTR columns: 
                # 1: Owner, 2: Asset, 3: Type, 4: Date, 5: Notif Date, 6: Amount, 7: Cap Gains, 8: Comment
                # Indices in JSON are strings "0", "1", etc.
                
                # Heuristic mapping (adjust based on actual Textract output)
                # Textract table cells might be sparse.
                
                trans = {
                    "doc_id": doc_id,
                    "year": year,
                    # Placeholder names until we link to Member data
                    "first_name": "Unknown", 
                    "last_name": "Member",
                    "state_district": "US",
                    "pdf_url": f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}/{doc_id}.pdf",
                    
                    "owner_code": row.get("0", ""),
                    "asset_name": row.get("1", ""),
                    "transaction_type": row.get("2", ""),
                    "transaction_date": row.get("3", ""),
                    "amount_range": row.get("5", ""),
                    "comment": row.get("7", "")
                }
                
                # Basic validation to ensure it's a real row
                if trans["asset_name"] or trans["amount_range"]:
                    transactions.append(trans)
                    
        return transactions

    except Exception as e:
        logger.error(f"Error processing {key}: {e}")
        return []

def main():
    logger.info(f"Scanning {S3_BUCKET}/{S3_SILVER_PREFIX}...")
    keys = list_structured_documents()
    logger.info(f"Found {len(keys)} structured documents.")
    
    all_transactions = []
    
    for key in keys:
        trans = process_document(key)
        all_transactions.extend(trans)
        
    logger.info(f"Extracted {len(all_transactions)} transactions.")
    
    # Sort by date (descending)
    # all_transactions.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)
    
    output_data = {
        "transactions": all_transactions,
        "total_transactions": len(all_transactions),
        "total_ptrs": len(set(t["doc_id"] for t in all_transactions)),
        "latest_date": datetime.now().strftime("%Y-%m-%d") # Placeholder
    }
    
    # Upload to S3
    logger.info(f"Uploading to {S3_BUCKET}/{OUTPUT_KEY}...")
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=OUTPUT_KEY,
        Body=json.dumps(output_data, indent=2),
        ContentType="application/json",
        CacheControl="max-age=300"
    )
    logger.info("Done.")

if __name__ == "__main__":
    main()
