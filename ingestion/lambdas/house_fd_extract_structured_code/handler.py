"""
Code-Based Structured Extraction Lambda (NO Textract)

This Lambda extracts structured data from PDFs using CODE ONLY (regex, patterns).
Uses existing pypdf text extraction - does NOT call Textract.

Input: SQS message with {doc_id, year, text_s3_key}
Output: Partial structured JSON + gap analysis
"""

import json
import logging
import gzip
import os
from datetime import datetime, timezone
from typing import Dict, Any, List
import boto3

# Setup logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# AWS clients
s3 = boto3.client('s3')
sqs = boto3.client('sqs')

# Environment variables
S3_BUCKET = os.environ['S3_BUCKET_NAME']
S3_SILVER_PREFIX = os.environ.get('S3_SILVER_PREFIX', 'silver')
TEXTRACT_APPROVAL_QUEUE_URL = os.environ.get('TEXTRACT_APPROVAL_QUEUE_URL')  # For low-confidence docs

# Import extractors
from lib.extractors.ptr_extractor import PTRExtractor
from lib.extractors.pdf_analyzer import PDFAnalyzer


def lambda_handler(event, context):
    """
    Process SQS messages for code-based structured extraction.

    Expected message format:
    {
        "doc_id": "20026548",
        "year": 2025,
        "text_s3_key": "silver/house/financial/text/.../raw_text.txt.gz"
    }
    """

    logger.info(f"Received {len(event.get('Records', []))} messages")

    # Track failures for partial batch responses
    batch_item_failures = []

    for record in event.get('Records', []):
        message_id = record['messageId']

        try:
            # Parse message
            body = json.loads(record['body'])
            doc_id = body['doc_id']
            year = body['year']
            text_s3_key = body['text_s3_key']

            logger.info(f"Processing doc_id={doc_id}, year={year}")

            # Download and decompress text
            text = download_text(text_s3_key)

            if not text or len(text.strip()) < 100:
                logger.warning(f"Text too short ({len(text)} chars), skipping doc_id={doc_id}")
                continue

            # Detect filing type from text
            filing_type = detect_filing_type(text)
            logger.info(f"Detected filing type: {filing_type}")

            # Route to appropriate extractor
            result = extract_structured_data(doc_id, year, text, filing_type)

            # Add metadata
            result['extraction_metadata'] = {
                'method': 'code_based',
                'filing_type': filing_type,
                'extraction_timestamp': datetime.now(timezone.utc).isoformat(),
                'text_length': len(text),
                'confidence_score': result.get('confidence_score', 0.0),
                'textract_recommended': result.get('textract_recommended', False)
            }

            # Upload structured JSON
            json_s3_key = upload_structured_json(doc_id, year, result)
            logger.info(f"Uploaded structured JSON: {json_s3_key}")

            # If confidence is low, queue for Textract approval
            if result.get('textract_recommended') and TEXTRACT_APPROVAL_QUEUE_URL:
                queue_for_textract_approval(doc_id, year, result['confidence_score'], result.get('missing_fields', []))

            logger.info(f"Successfully processed doc_id={doc_id} (confidence: {result.get('confidence_score', 0):.1%})")

        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}", exc_info=True)
            batch_item_failures.append({"itemIdentifier": message_id})

    # Return partial batch failure response
    return {"batchItemFailures": batch_item_failures}


def download_text(s3_key: str) -> str:
    """Download and decompress text from S3."""
    logger.info(f"Downloading text from s3://{S3_BUCKET}/{s3_key}")

    response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)

    # Decompress gzipped text
    if s3_key.endswith('.gz'):
        compressed = response['Body'].read()
        text = gzip.decompress(compressed).decode('utf-8')
    else:
        text = response['Body'].read().decode('utf-8')

    logger.info(f"Downloaded {len(text)} characters")
    return text


def detect_filing_type(text: str) -> str:
    """
    Detect filing type from text content.

    Returns: "PTR", "Form A", "Form B", "Extension", etc.
    """
    text_lower = text.lower()
    text_upper = text.upper()

    # PTR - Periodic Transaction Report
    if 'periodic transaction report' in text_lower or 'ptr' in text_lower:
        return "PTR"

    # Extension Request (Type X)
    if 'request for extension' in text_lower or 'extension of time' in text_lower:
        return "Extension"

    # Withdrawal Notice (Type W)
    if 'notice of withdrawal' in text_lower or 'termination of employment' in text_lower:
        return "Withdrawal"

    # Campaign Notice (Type D)
    if 'campaign committee' in text_lower or 'notice of candidacy' in text_lower:
        return "Campaign"

    # Termination Notice (Type T)
    if 'termination report' in text_lower:
        return "Termination"

    # Form A - Annual Report (New Member or Candidate)
    if 'annual report' in text_lower or 'new member' in text_lower or 'schedule a' in text_lower:
        # Check for Part numbers to distinguish A vs B
        if 'part i' in text_lower and 'part ii' in text_lower:
            return "Form A"

    # Form B - Candidate Report
    if 'candidate report' in text_lower:
        return "Form B"

    # Default to Form A if has schedules
    if any(f'schedule {letter}' in text_lower for letter in 'ABCDEFGHI'):
        return "Form A"

    return "Unknown"


def extract_structured_data(doc_id: str, year: int, text: str, filing_type: str) -> Dict[str, Any]:
    """
    Extract structured data based on filing type using code-based extractors.

    Returns structured JSON with confidence score and gap analysis.
    """

    if filing_type == "PTR":
        return extract_ptr(doc_id, year, text)

    elif filing_type in ["Form A", "Form B"]:
        return extract_form_ab_text(doc_id, year, text)

    elif filing_type == "Extension":
        return extract_extension_text(doc_id, year, text)

    elif filing_type in ["Withdrawal", "Campaign", "Termination"]:
        return extract_simple_notice(doc_id, year, text, filing_type)

    else:
        # Unknown type - extract what we can
        return {
            "doc_id": doc_id,
            "year": year,
            "filing_type": filing_type,
            "extracted_data": {},
            "confidence_score": 0.0,
            "textract_recommended": True,
            "missing_fields": ["All fields - unknown filing type"]
        }


def extract_ptr(doc_id: str, year: int, text: str) -> Dict[str, Any]:
    """Extract PTR using existing PTRExtractor (text-based)."""
    extractor = PTRExtractor()

    try:
        structured = extractor.extract_from_text(text)

        # Calculate confidence based on field completion
        required_fields = ['filer_name', 'filing_date', 'transactions']
        fields_found = sum(1 for field in required_fields if structured.get(field))
        confidence = fields_found / len(required_fields)

        # Check transaction quality
        transactions = structured.get('transactions', [])
        if transactions:
            # Check if transactions have required fields
            tx_fields = ['date', 'asset_name', 'transaction_type']
            tx_completeness = sum(
                sum(1 for f in tx_fields if tx.get(f)) / len(tx_fields)
                for tx in transactions
            ) / len(transactions)
            confidence = (confidence + tx_completeness) / 2

        missing_fields = []
        if not structured.get('filer_name'):
            missing_fields.append('filer_name')
        if not structured.get('filing_date'):
            missing_fields.append('filing_date')
        if not transactions:
            missing_fields.append('transactions')

        structured['confidence_score'] = confidence
        structured['textract_recommended'] = confidence < 0.7
        structured['missing_fields'] = missing_fields

        return structured

    except Exception as e:
        logger.error(f"PTR extraction failed: {e}", exc_info=True)
        return {
            "doc_id": doc_id,
            "year": year,
            "filing_type": "PTR",
            "extraction_error": str(e),
            "confidence_score": 0.0,
            "textract_recommended": True,
            "missing_fields": ["Extraction failed"]
        }


def extract_form_ab_text(doc_id: str, year: int, text: str) -> Dict[str, Any]:
    """
    Extract Form A/B using TEXT-BASED methods (regex, patterns).

    NOTE: This is a placeholder. Full implementation in Sprint 2.
    For now, extract basic header fields only.
    """
    import re

    extracted = {
        "doc_id": doc_id,
        "year": year,
        "filing_type": "Form A/B",
        "document_header": {},
        "schedules": {},
        "missing_fields": []
    }

    # Extract Filing ID
    filing_id_match = re.search(r'Filing\s*ID:?\s*#?(\d+)', text, re.IGNORECASE)
    if filing_id_match:
        extracted['document_header']['filing_id'] = filing_id_match.group(1)
    else:
        extracted['missing_fields'].append('filing_id')

    # Extract name
    name_match = re.search(r'Name:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
    if name_match:
        extracted['document_header']['filer_name'] = name_match.group(1)
    else:
        extracted['missing_fields'].append('filer_name')

    # Extract dates
    date_match = re.search(r'Filing\s*Date:?\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
    if date_match:
        extracted['document_header']['filing_date'] = date_match.group(1)
    else:
        extracted['missing_fields'].append('filing_date')

    # For now, mark schedules as missing (will implement in Sprint 2)
    extracted['missing_fields'].extend([f'Schedule {l}' for l in 'ABCDEFGHI'])

    # Low confidence - needs full text extractor (Sprint 2)
    extracted['confidence_score'] = 0.3  # Only got header fields
    extracted['textract_recommended'] = True

    return extracted


def extract_extension_text(doc_id: str, year: int, text: str) -> Dict[str, Any]:
    """Extract extension request from text (simple notice)."""
    # Placeholder - implement full extraction
    return {
        "doc_id": doc_id,
        "year": year,
        "filing_type": "Extension",
        "confidence_score": 0.5,
        "textract_recommended": True,
        "missing_fields": ["Extension fields not yet implemented"]
    }


def extract_simple_notice(doc_id: str, year: int, text: str, filing_type: str) -> Dict[str, Any]:
    """Extract simple notice types (Withdrawal, Campaign, Termination)."""
    # Placeholder - these are usually 1-page simple forms
    return {
        "doc_id": doc_id,
        "year": year,
        "filing_type": filing_type,
        "confidence_score": 0.6,
        "textract_recommended": False,  # Usually simple enough
        "missing_fields": []
    }


def upload_structured_json(doc_id: str, year: int, data: Dict[str, Any]) -> str:
    """Upload structured JSON to S3."""

    # Path: silver/house/financial/structured_code/year=YYYY/filing_type=X/doc_id=XXXXX.json
    filing_type = data.get('filing_type', 'Unknown').replace('/', '_').replace(' ', '_')

    s3_key = f"{S3_SILVER_PREFIX}/house/financial/structured_code/year={year}/filing_type={filing_type}/doc_id={doc_id}.json"

    json_str = json.dumps(data, indent=2)

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json_str.encode('utf-8'),
        ContentType='application/json'
    )

    logger.info(f"Uploaded structured JSON to s3://{S3_BUCKET}/{s3_key}")
    return s3_key


def queue_for_textract_approval(doc_id: str, year: int, confidence: float, missing_fields: List[str]):
    """Queue document for human Textract approval review."""

    if not TEXTRACT_APPROVAL_QUEUE_URL:
        logger.warning("TEXTRACT_APPROVAL_QUEUE_URL not set, skipping approval queue")
        return

    message = {
        "doc_id": doc_id,
        "year": year,
        "confidence_score": confidence,
        "missing_fields": missing_fields,
        "reason": f"Low confidence ({confidence:.1%}) - human review recommended"
    }

    try:
        sqs.send_message(
            QueueUrl=TEXTRACT_APPROVAL_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        logger.info(f"Queued doc_id={doc_id} for Textract approval (confidence: {confidence:.1%})")
    except Exception as e:
        logger.error(f"Failed to queue for Textract approval: {e}")
