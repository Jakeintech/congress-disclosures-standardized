# -*- coding: utf-8 -*-
"""Lambda handler for structured extraction of House FD PDFs using async Textract.

This Lambda is triggered by the SQS queue `structured-extraction-queue`.
It uses Textract's asynchronous StartDocumentAnalysis API for multi-page PDFs,
with SNS notifications for job completion. The results are parsed and mapped to 
schedules A-I JSON schemas.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import boto3

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# Environment variables
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_BRONZE_PREFIX = os.getenv("S3_BRONZE_PREFIX", "bronze")
S3_SILVER_PREFIX = os.getenv("S3_SILVER_PREFIX", "silver")
SNS_TOPIC_ARN = os.getenv("TEXTRACT_SNS_TOPIC_ARN")
TEXTRACT_ROLE_ARN = os.getenv("TEXTRACT_ROLE_ARN")

s3 = boto3.client("s3")
textract = boto3.client("textract")
dynamodb = boto3.resource("dynamodb")
documents_table = dynamodb.Table("house_fd_documents")

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Entry point for SQS events.

    Expected message body (JSON):
    {
        "doc_id": "1234567",
        "year": 2025,
        "extraction_method": "pypdf" | "textract",
        "has_embedded_text": true/false
    }
    """
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            doc_id = body["doc_id"]
            year = int(body["year"])
            logger.info(f"Starting async Textract extraction for {doc_id} ({year})")
            result = process_document_async(doc_id, year)
            if result["status"] == "success":
                # Update documents table with json_s3_key
                update_document_record(doc_id, year, result["json_s3_key"])
                logger.info(f"✅ Structured JSON uploaded for {doc_id}")
            elif result["status"] == "started":
                logger.info(f"⏳ Async Textract job started for {doc_id}: {result['job_id']}")
            else:
                logger.warning(f"⚠️ Extraction incomplete for {doc_id}: {result['message']}")
        except Exception as e:
            logger.error(f"Error processing SQS record: {e}", exc_info=True)
    return {"statusCode": 200, "body": json.dumps({"message": "Processing complete"})}

def process_document_async(doc_id: str, year: int) -> Dict[str, Any]:
    """Start async Textract analysis and poll for results.

    For production, we'd use SNS callbacks. For simplicity now, we'll poll inline
    if the Lambda has time, otherwise return job_id for later processing.
    
    Returns a dict with keys:
        - status: "success", "started", or "partial"
        - data: the structured JSON (if success)
        - job_id: Textract job ID (if started)
        - message: error or partial‑extraction info
    """
    # 1️⃣ Construct PDF S3 key
    pdf_key = f"{S3_BRONZE_PREFIX}/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf"
    
    # Verify PDF exists
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=pdf_key)
    except Exception as e:
        return {"status": "partial", "message": f"Failed to find PDF: {e}"}

    # 2️⃣ Start async Textract job
    try:
        response = textract.start_document_analysis(
            DocumentLocation={
                "S3Object": {
                    "Bucket": S3_BUCKET,
                    "Name": pdf_key
                }
            },
            FeatureTypes=["FORMS", "TABLES"]
        )
        job_id = response["JobId"]
        logger.info(f"Started Textract job {job_id} for doc_id={doc_id}")
    except Exception as e:
        return {"status": "partial", "message": f"Failed to start Textract: {e}"}

    # 3️⃣ Poll for completion (with timeout)
    max_wait_time = 60  # seconds
    poll_interval = 2   # seconds
    elapsed = 0
    
    while elapsed < max_wait_time:
        time.sleep(poll_interval)
        elapsed += poll_interval
        
        try:
            status_response = textract.get_document_analysis(JobId=job_id)
            status = status_response["JobStatus"]
            
            if status == "SUCCEEDED":
                logger.info(f"Textract job {job_id} completed successfully")
                blocks = get_all_blocks(job_id)
                structured = parse_textract_blocks(doc_id, year, blocks)
                json_s3_key = upload_structured_json(doc_id, year, structured)
                return {"status": "success", "data": structured, "json_s3_key": json_s3_key}
            elif status == "FAILED":
                return {"status": "partial", "message": f"Textract job failed: {status_response.get('StatusMessage', 'Unknown error')}"}
            elif status in ["IN_PROGRESS", "QUEUED"]:
                logger.debug(f"Job {job_id} still {status}, waiting...")
                continue
        except Exception as e:
            logger.error(f"Error polling Textract job {job_id}: {e}")
            return {"status": "partial", "message": f"Error polling job: {e}"}
    
    # Timeout - job is still running
    logger.warning(f"Textract job {job_id} timeout, will need async completion handler")
    return {"status": "started", "job_id": job_id, "doc_id": doc_id, "year": year}

def get_all_blocks(job_id: str) -> List[Dict[str, Any]]:
    """Get all blocks from a Textract job, handling pagination."""
    blocks = []
    next_token = None
    
    while True:
        if next_token:
            response = textract.get_document_analysis(JobId=job_id, NextToken=next_token)
        else:
            response = textract.get_document_analysis(JobId=job_id)
        
        blocks.extend(response.get("Blocks", []))
        next_token = response.get("NextToken")
        
        if not next_token:
            break
    
    return blocks

def parse_textract_blocks(doc_id: str, year: int, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Parse Textract blocks into structured JSON with schedules A-I.
    
    This is a comprehensive parser that extracts:
    - Document header fields (Filing ID, Name, Status, etc.)
    - Checkboxes (using SELECTION_ELEMENT blocks)
    - Key-value pairs from FORMS
    - Table data from TABLES with enhanced parsing (codes, locations, descriptions)
    - Maps them to the appropriate schedules
    """
    # Build block map for relationship lookups
    block_map = {block["Id"]: block for block in blocks}
    
    # Extract key-value pairs
    kv_pairs = extract_key_value_pairs(blocks, block_map)
    
    # Extract document header
    header = extract_document_header(blocks, kv_pairs)
    
    # Extract checkboxes
    checkboxes = extract_checkboxes(blocks, block_map)
    
    # Extract tables with enhanced parsing
    tables = extract_tables_enhanced(blocks, block_map)
    
    # Classify document type
    filing_type = classify_document_type(blocks, kv_pairs)
    
    # Map to schedules using content-based classification
    structured = {
        "doc_id": doc_id,
        "year": year,
        "filing_type": filing_type,
        "document_header": header,
        "checkboxes": checkboxes,
        "extraction_timestamp": datetime.utcnow().isoformat(),
        "extraction_method": "textract_async_enhanced",
        "total_pages": get_page_count(blocks),
        "schedules": map_to_schedules(kv_pairs, tables, blocks)
    }
    
    return structured

def classify_document_type(blocks: List[Dict], kv_pairs: Dict[str, str]) -> str:
    """Classify the document type based on text content and form fields."""
    # 1. Check explicit form fields
    if "Filing Type" in kv_pairs:
        return kv_pairs["Filing Type"]
        
    # 2. Check first page text for keywords
    first_page_text = " ".join([
        b["Text"].upper() 
        for b in blocks 
        if b["BlockType"] == "LINE" and b.get("Page", 1) == 1
    ])
    
    if "PERIODIC TRANSACTION REPORT" in first_page_text:
        return "Periodic Transaction Report"
    elif "FINANCIAL DISCLOSURE REPORT" in first_page_text:
        if "AMENDMENT" in first_page_text:
            return "Amendment"
        return "Annual Report"
    elif "EXTENSION" in first_page_text:
        return "Extension"
        
    return "Unknown"

def extract_document_header(blocks: List[Dict], kv_pairs: Dict[str, str]) -> Dict:
    """Extract document header fields from key-value pairs."""
    return {
        "filing_id": kv_pairs.get("Filing ID", ""),
        "filer_name": kv_pairs.get("Name", ""),
        "status": kv_pairs.get("Status", ""),
        "state_district": kv_pairs.get("State/District", ""),
        "filing_type": kv_pairs.get("Filing Type", ""),
        "filing_year": kv_pairs.get("Filing Year", ""),
        "filing_date": kv_pairs.get("Filing Date", "")
    }

def extract_checkboxes(blocks: List[Dict], block_map: Dict) -> Dict:
    """Extract checkbox states using SELECTION_ELEMENT blocks."""
    import re
    
    checkboxes = {}
    
    for block in blocks:
        if block.get("BlockType") == "SELECTION_ELEMENT":
            is_selected = block.get("SelectionStatus") == "SELECTED"
            
            # Find nearby text to identify which checkbox this is
            page = block.get("Page", 1)
            bbox = block.get("Geometry", {}).get("BoundingBox", {})
            
            # Look for text blocks on the same line (similar Y coordinate)
            nearby_text = []
            for other_block in blocks:
                if (other_block.get("BlockType") == "LINE" and 
                    other_block.get("Page") == page):
                    other_bbox = other_block.get("Geometry", {}).get("BoundingBox", {})
                    # Check if roughly on same line (Y coordinates close)
                    if abs(bbox.get("Top", 0) - other_bbox.get("Top", 0)) < 0.02:
                        nearby_text.append(other_block.get("Text", ""))
            
            # Try to classify based on nearby text
            context = " ".join(nearby_text).upper()
            
            if "IPO" in context or "INITIAL PUBLIC OFFERING" in context:
                checkboxes["ipo_participation"] = is_selected
            elif "TRUST" in context:
                checkboxes["qualified_blind_trusts"] = is_selected
            elif "EXEMPTION" in context:
                checkboxes["has_exemptions"] = is_selected
            elif "TX" in context and "1,000" in context:
                # This is per-row checkbox, handle in table parsing
                pass
            elif "CAP" in context and "GAINS" in context:
                # This is per-row checkbox, handle in table parsing
                pass
    
    return checkboxes

def extract_tables_enhanced(blocks: List[Dict], block_map: Dict) -> List[Dict]:
    """Extract tables with enhanced cell parsing for codes and metadata."""
    import re
    
    tables = []
    
    for block in blocks:
        if block["BlockType"] == "TABLE":
            table_data = parse_table_block_enhanced(block, block_map)
            tables.append(table_data)
    
    return tables

def parse_table_block_enhanced(table_block: Dict, block_map: Dict) -> Dict:
    """Parse a single TABLE block with enhanced cell parsing."""
    import re
    
    rows = {}
    
    if "Relationships" in table_block:
        for relationship in table_block["Relationships"]:
            if relationship["Type"] == "CHILD":
                for cell_id in relationship["Ids"]:
                    cell = block_map.get(cell_id)
                    if cell and cell["BlockType"] == "CELL":
                        row_index = cell.get("RowIndex", 0)
                        col_index = cell.get("ColumnIndex", 0)
                        
                        if row_index not in rows:
                            rows[row_index] = {}
                        
                        # Enhanced cell parsing
                        cell_text = get_text_from_block(cell, block_map, "Cell")
                        parsed_cell = parse_cell_with_metadata(cell_text)
                        
                        rows[row_index][col_index] = parsed_cell
    
    return {"rows": [rows.get(i, {}) for i in sorted(rows.keys())]}

def parse_cell_with_metadata(cell_text: str) -> Dict:
    """Parse cell to extract codes, locations, descriptions."""
    import re
    
    result = {"value": cell_text}
    
    if not cell_text or not cell_text.strip():
        return result
    
    # Extract asset type code [XX]
    type_match = re.search(r'\[([A-Z]{2})\]', cell_text)
    if type_match:
        result["asset_type_code"] = type_match.group(1)
        # Remove code from value
        result["value"] = cell_text.replace(type_match.group(0), "").strip()
    
    # Extract owner code (SP, JT, DC at start)
    owner_match = re.match(r'^(SP|JT|DC)\s+(.+)', cell_text)
    if owner_match:
        result["owner_code"] = owner_match.group(1)
        result["value"] = owner_match.group(2)
    
    # Extract location
    location_match = re.search(r'LOCATION:\s*(.+?)(?:\n|$)', cell_text, re.IGNORECASE)
    if location_match:
        result["location"] = location_match.group(1).strip()
    
    # Extract description
    desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?:\n|$)', cell_text, re.IGNORECASE)
    if desc_match:
        result["description"] = desc_match.group(1).strip()
    
    # Extract transaction type (single letter: P, S, E)
    if len(cell_text.strip()) == 1 and cell_text.strip() in ['P', 'S', 'E']:
        result["transaction_type_code"] = cell_text.strip()
    
    return result

def extract_key_value_pairs(blocks: List[Dict], block_map: Dict) -> Dict[str, str]:
    """Extract form key-value pairs from Textract blocks."""
    kv_pairs = {}
    
    for block in blocks:
        if block["BlockType"] == "KEY_VALUE_SET" and "KEY" in block.get("EntityTypes", []):
            key_text = get_text_from_block(block, block_map, "Key")
            value_block = get_value_block(block, block_map)
            value_text = get_text_from_block(value_block, block_map, "Value") if value_block else ""
            
            if key_text:
                kv_pairs[key_text] = value_text
    
    return kv_pairs



def get_text_from_block(block: Dict, block_map: Dict, context: str = "") -> str:
    """Extract text from a block and its child WORD blocks."""
    if not block:
        return ""
    
    text_parts = []
    
    if "Relationships" in block:
        for relationship in block["Relationships"]:
            if relationship["Type"] == "CHILD":
                for child_id in relationship["Ids"]:
                    child = block_map.get(child_id)
                    if child and child["BlockType"] == "WORD":
                        text_parts.append(child.get("Text", ""))
    
    return " ".join(text_parts).strip()

def get_value_block(key_block: Dict, block_map: Dict) -> Dict:
    """Get the VALUE block associated with a KEY block."""
    if "Relationships" in key_block:
        for relationship in key_block["Relationships"]:
            if relationship["Type"] == "VALUE":
                for value_id in relationship["Ids"]:
                    value_block = block_map.get(value_id)
                    if value_block and "VALUE" in value_block.get("EntityTypes", []):
                        return value_block
    return None

def get_page_count(blocks: List[Dict]) -> int:
    """Count unique pages in blocks."""
    pages = set()
    for block in blocks:
        if "Page" in block:
            pages.add(block["Page"])
    return len(pages)

def map_to_schedules(kv_pairs: Dict[str, str], tables: List[Dict], blocks: List[Dict]) -> Dict:
    """Map extracted data to schedules A-I using content-based classification.
    
    Logic:
    Inspects the first row (header) of each table to identify keywords specific to each schedule.
    """
    schedules = {
        "A": {"type": "Assets", "data": [], "tables": []},
        "B": {"type": "Transactions", "data": [], "tables": []},
        "C": {"type": "Earned Income", "data": [], "tables": []},
        "D": {"type": "Liabilities", "data": [], "tables": []},
        "E": {"type": "Positions", "data": [], "tables": []},
        "F": {"type": "Agreements", "data": [], "tables": []},
        "G": {"type": "Gifts", "data": [], "tables": []},
        "H": {"type": "Travel", "data": [], "tables": []},
        "I": {"type": "Charity", "data": [], "tables": []},
    }
    
    for table in tables:
        rows = table.get("rows", [])
        if not rows:
            continue
            
        # Get header text (first row values concatenated)
        header_text = " ".join(str(val).upper() for val in rows[0].values())
        
        # Classification Rules
        target_schedule = "Unknown"
        
        if "ASSET" in header_text and "INCOME" in header_text and "TX." not in header_text:
            target_schedule = "A" # Assets
        elif "ASSET" in header_text and ("TRANSACTION" in header_text or "TX." in header_text):
            target_schedule = "B" # Transactions
        elif "SOURCE" in header_text and "TYPE" in header_text and "AMOUNT" in header_text:
            target_schedule = "C" # Earned Income (often shares headers with E)
            # Disambiguation: Schedule C usually has "Amount", E usually doesn't or is "Positions"
            if "POSITION" in header_text:
                target_schedule = "E"
        elif "CREDITOR" in header_text or "LIABILITY" in header_text:
            target_schedule = "D" # Liabilities
        elif "POSITION" in header_text:
            target_schedule = "E" # Positions
        elif "PARTIES TO" in header_text or "TERMS OF AGREEMENT" in header_text:
            target_schedule = "F" # Agreements
        elif "GIFT" in header_text or ("SOURCE" in header_text and "VALUE" in header_text):
            target_schedule = "G" # Gifts
        elif "SOURCE" in header_text and "CITY" in header_text:
            target_schedule = "H" # Travel
        elif "CHARITY" in header_text:
            target_schedule = "I" # Charity
            
        # Fallback: if we can't classify, check if it looks like continuation of previous
        # For now, just append to "Unknown" or log warning
        
        if target_schedule in schedules:
            schedules[target_schedule]["tables"].append(table)
        else:
            # Try to disambiguate C vs E based on content if headers are generic
            pass

    return schedules

def upload_structured_json(doc_id: str, year: int, data: Dict[str, Any]) -> str:
    """Write the structured JSON to the silver layer and return the S3 key."""
    json_key = f"{S3_SILVER_PREFIX}/house/financial/structured/year={year}/doc_id={doc_id}.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=json_key,
        Body=json.dumps(data, indent=2).encode("utf-8"),
        ContentType="application/json"
    )
    logger.info(f"Uploaded JSON to s3://{S3_BUCKET}/{json_key}")
    return json_key

def update_document_record(doc_id: str, year: int, json_s3_key: str):
    """Update the documents DynamoDB table with the json_s3_key."""
    try:
        documents_table.update_item(
            Key={"doc_id": doc_id, "year": year},
            UpdateExpression="SET json_s3_key = :jsk, json_extraction_timestamp = :ts",
            ExpressionAttributeValues={
                ":jsk": json_s3_key,
                ":ts": datetime.utcnow().isoformat()
            }
        )
        logger.info(f"Updated documents table for {doc_id} with json_s3_key")
    except Exception as e:
        logger.error(f"Failed to update documents table for {doc_id}: {e}")
