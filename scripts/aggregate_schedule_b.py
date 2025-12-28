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
DYNAMODB_TABLE = "house_fd_documents"
OUTPUT_KEY = "website/api/v1/schedules/b/transactions.json"
MANIFEST_KEY = "manifest.json"

s3 = boto3.client("s3", region_name=S3_REGION)
dynamodb = boto3.resource("dynamodb", region_name=S3_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

def load_member_manifest():
    """Load Bronze manifest to get member names and details."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=MANIFEST_KEY)
        manifest = json.loads(response["Body"].read().decode("utf-8"))
        # Index by doc_id for quick lookup
        return {str(f["doc_id"]): f for f in manifest.get("filings", [])}
    except Exception as e:
        logger.warning(f"Could not load manifest: {e}")
        return {}

def scan_dynamodb_documents():
    """Scan DynamoDB to get all document records."""
    documents = []
    scan_kwargs = {}
    done = False
    
    while not done:
        response = table.scan(**scan_kwargs)
        documents.extend(response.get('Items', []))
        start_key = response.get('LastEvaluatedKey')
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        else:
            done = True
            
    return documents

def extract_cell_value(cell_data: Any) -> Dict[str, str]:
    """Extract value and metadata from a cell that might be a string or dict."""
    if isinstance(cell_data, dict):
        return {
            "value": str(cell_data.get("value", "")),
            "asset_type_code": cell_data.get("asset_type_code"),
            "owner_code": cell_data.get("owner_code"),
            "transaction_type_code": cell_data.get("transaction_type_code"),
            "description": cell_data.get("description"),
            "location": cell_data.get("location")
        }
    return {"value": str(cell_data)}

def get_column_mapping(header_row: Dict[str, Dict]) -> Dict[str, str]:
    """Determine which column index corresponds to which field based on header text."""
    mapping = {}
    
    for col_idx, cell in header_row.items():
        val = cell.get("value", "").upper()
        
        if "ASSET" in val:
            mapping["asset"] = col_idx
        elif "OWNER" in val:
            mapping["owner"] = col_idx
        elif "TYPE" in val:
            mapping["type"] = col_idx
        elif "DATE" in val and "NOTIF" not in val:
            mapping["date"] = col_idx
        elif "NOTIF" in val:
            mapping["notif_date"] = col_idx
        elif "AMOUNT" in val:
            mapping["amount"] = col_idx
        elif "CAP" in val and "GAIN" in val:
            mapping["cap_gains"] = col_idx
            
    return mapping

def extract_transactions_from_document(doc_id: str, year: int, member_data: Dict, json_key: str = None) -> List[Dict[str, Any]]:
    """Extract Schedule B transactions from a Silver document."""
    transactions = []
    
    # Use provided key or fallback to standard pattern
    if json_key:
        structured_key = json_key
    else:
        structured_key = f"silver/house/financial/structured/year={year}/doc_id={doc_id}.json"
    
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=structured_key)
        data = json.loads(response["Body"].read().decode("utf-8"))
        
        # Extract Schedule B
        schedules = data.get("schedules", {})
        schedule_b = schedules.get("B", {})
        tables = schedule_b.get("tables", [])
        
        for table_data in tables:
            rows = table_data.get("rows", [])
            if not rows:
                continue
                
            # Determine column mapping from first row
            header_row = rows[0]
            col_map = get_column_mapping(header_row)
            
            # If we found at least an Asset column, assume it's a valid table
            if "asset" in col_map:
                start_idx = 1
                
                for row in rows[start_idx:]:
                    # Helper to safely get cell
                    def get_cell(field):
                        idx = col_map.get(field)
                        if idx:
                            return extract_cell_value(row.get(idx, ""))
                        return {"value": ""}

                    asset_cell = get_cell("asset")
                    owner_cell = get_cell("owner")
                    type_cell = get_cell("type")
                    date_cell = get_cell("date")
                    notif_cell = get_cell("notif_date")
                    amount_cell = get_cell("amount")
                    cap_gains_cell = get_cell("cap_gains")
                    
                    trans = {
                        "doc_id": doc_id,
                        "year": year,
                        "first_name": member_data.get("first_name", ""),
                        "last_name": member_data.get("last_name", ""),
                        "state_district": member_data.get("state_district", ""),
                        "filing_date": member_data.get("filing_date", ""),
                        "filing_type": member_data.get("filing_type", ""),
                        "pdf_url": f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}/{doc_id}.pdf",
                        
                        # Core fields
                        "owner": owner_cell["value"],
                        "asset_name": asset_cell["value"],
                        "transaction_type": type_cell["value"],
                        "transaction_date": date_cell["value"],
                        "notification_date": notif_cell["value"],
                        "amount_range": amount_cell["value"],
                        "cap_gains": cap_gains_cell["value"],
                        
                        # Rich metadata
                        "asset_type_code": asset_cell.get("asset_type_code"),
                        "owner_code": owner_cell.get("owner_code") or asset_cell.get("owner_code"),
                        "transaction_type_code": type_cell.get("transaction_type_code"),
                        "description": asset_cell.get("description"),
                        "location": asset_cell.get("location")
                    }
                    
                    # Basic validation
                    if trans["asset_name"] and trans["asset_name"].upper() not in ["", "ASSET"]:
                        transactions.append(trans)
                    
    except s3.exceptions.NoSuchKey:
        # Expected for documents that haven't been processed yet or failed
        pass
    except Exception as e:
        logger.error(f"Error extracting from {doc_id} (key: {structured_key}): {e}")
    
    return transactions

def main():
    logger.info("Loading member manifest...")
    member_lookup = load_member_manifest()
    logger.info(f"Loaded {len(member_lookup)} member records from Bronze manifest.")
    
    logger.info("Scanning DynamoDB for documents...")
    documents = scan_dynamodb_documents()
    logger.info(f"Found {len(documents)} documents in DynamoDB.")
    
    all_transactions = []
    count = 0
    
    for doc in documents:
        doc_id = str(doc["doc_id"]).strip()
        year = int(doc["year"])
        json_key = doc.get("json_s3_key")
        member_data = member_lookup.get(doc_id, {})
        
        trans = extract_transactions_from_document(doc_id, year, member_data, json_key)
        all_transactions.extend(trans)
        
        count += 1
        if count % 100 == 0:
            logger.info(f"Processed {count}/{len(documents)} documents, {len(all_transactions)} transactions so far...")
    
    logger.info(f"Extracted {len(all_transactions)} total transactions from {len(documents)} documents.")
    
    # Calculate stats (keys match what app.js expects)
    stats = {
        "total_transactions": len(all_transactions),
        "total_ptrs": len(set(t["doc_id"] for t in all_transactions)),  # Changed from total_documents
        "unique_members": len(set(f"{t['first_name']} {t['last_name']}" for t in all_transactions if t['first_name'])),
        "latest_date": max((t.get("filing_date", "") for t in all_transactions), default=""),  # Changed from latest_filing_date
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }
    
    output_data = {
        "stats": stats,
        "transactions": all_transactions
    }
    
    # Write to S3
    logger.info(f"Uploading to {S3_BUCKET}/{OUTPUT_KEY}...")
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=OUTPUT_KEY,
        Body=json.dumps(output_data, indent=2),
        ContentType="application/json",
        CacheControl="max-age=300"
    )
    logger.info("✅ Done! API endpoint created.")
    logger.info(f"📍 URL: https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{OUTPUT_KEY}")

if __name__ == "__main__":
    main()
