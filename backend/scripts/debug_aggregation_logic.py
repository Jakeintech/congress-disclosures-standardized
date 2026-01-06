import boto3
import json
import os
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
S3_BUCKET = "congress-disclosures-standardized"
S3_REGION = "us-east-1"

s3 = boto3.client("s3", region_name=S3_REGION)

DOC_ID = "10063228"
YEAR = 2025

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

def main():
    # Load the structured JSON directly
    structured_key = f"silver/house/financial/year={YEAR}/{DOC_ID}/structured.json"
    print(f"Loading {structured_key}...")

    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=structured_key)
        data = json.loads(response["Body"].read().decode("utf-8"))

        # Inspect Schedule B
        schedules = data.get("schedules", {})
        schedule_b = schedules.get("B", {})
        tables = schedule_b.get("tables", [])

        print(f"Found {len(tables)} tables in Schedule B")

        # Debug the first table
        if tables:
            table_data = tables[0]
            rows = table_data.get("rows", [])
            print(f"Table has {len(rows)} rows")
            
            if rows:
                header_row = rows[0]
                print("Header Row:", json.dumps(header_row, indent=2))
                
                col_map = get_column_mapping(header_row)
                print("Column Mapping:", col_map)
                
                if "asset" in col_map:
                    print("Asset column found! Extracting rows...")
                    start_idx = 1
                    for i, row in enumerate(rows[start_idx:]):
                        print(f"Row {i+1}:", json.dumps(row, indent=2))
                        
                        # Try extraction logic
                        def get_cell(field):
                            idx = col_map.get(field)
                            if idx:
                                return extract_cell_value(row.get(idx, ""))
                            return {"value": ""}

                        asset_cell = get_cell("asset")
                        print(f"  -> Asset: {asset_cell}")
                else:
                    print("ERROR: No Asset column found in mapping!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
