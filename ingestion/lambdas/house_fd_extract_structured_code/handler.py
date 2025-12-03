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
from typing import Dict, Any, List, Optional
import boto3

# Setup logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# AWS clients
s3 = boto3.client('s3')

# Environment variables
S3_BUCKET = os.environ['S3_BUCKET_NAME']
S3_SILVER_PREFIX = os.environ.get('S3_SILVER_PREFIX', 'silver')

# Import extractors
from lib.extractors.type_p_ptr.extractor import PTRExtractor
from lib.extractors.type_a_b_annual.extractor import TypeABAnnualExtractor
from lib.extractors.type_t_termination.extractor import TypeTTerminationExtractor
from lib.extractors.type_x_extension_request.extractor import TypeXExtensionRequestExtractor
from lib.extractors.type_d_campaign_notice.extractor import TypeDCampaignNoticeExtractor
from lib.extractors.type_w_withdrawal_notice.extractor import TypeWWithdrawalNoticeExtractor
# PDFAnalyzer not needed - we work with pre-extracted text


def lambda_handler(event, context):
    """
    Process SQS messages for code-based structured extraction.

    Expected message format:
    {
        "doc_id": "20026548",
        "year": 2025,
        "text_s3_key": "silver/house/financial/text/.../raw_text.txt.gz",
        "filing_type": "P"  # REQUIRED
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
            
            # Get authoritative filing type from message
            filing_type = body.get('filing_type')
            
            # Get other bronze metadata if available
            bronze_metadata = {
                'filer_name': body.get('filer_name'),
                'filing_date': body.get('filing_date'),
                'state_district': body.get('state_district')
            }
            
            if not filing_type:
                logger.warning(f"Missing filing_type for doc_id={doc_id}, defaulting to 'Unknown'")
                filing_type = "Unknown"
            else:
                logger.info(f"Processing doc_id={doc_id}, year={year}, type={filing_type}")

            # Download and decompress text
            text = download_text(text_s3_key)

            # Download PDF for OCR fallback (optional, but helpful for image PDFs)
            pdf_bytes = None
            try:
                # Construct PDF path: bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf
                # Note: Current data structure does NOT use filing_type partition for PDFs
                pdf_s3_key = f"bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf"
                pdf_bytes = download_bytes(pdf_s3_key)
                logger.info(f"Downloaded PDF: {len(pdf_bytes)} bytes")
            except Exception as e:
                logger.warning(f"Could not download PDF for {doc_id} (path: {pdf_s3_key}): {e}")

            if (not text or len(text.strip()) < 100) and not pdf_bytes:
                logger.warning(f"Text too short ({len(text) if text else 0} chars) and no PDF, skipping doc_id={doc_id}")
                continue

            # Route to appropriate extractor
            result = extract_structured_data(doc_id, year, text, filing_type, pdf_bytes=pdf_bytes)
            
            # Ensure filing_type is in the result for S3 partitioning
            if 'filing_type' not in result:
                result['filing_type'] = filing_type

            # Add metadata and raw text
            result['extraction_metadata'] = {
                'extraction_method': 'code_based',
                'filing_type': filing_type,
                'extraction_timestamp': datetime.now(timezone.utc).isoformat(),
                'processed_at': datetime.now(timezone.utc).isoformat(),
                'text_length': len(text),
                'confidence_score': result.get('confidence_score', 0.0)
            }
            
            # Add bronze metadata
            result['bronze_metadata'] = bronze_metadata
            
            # Include extracted text content for UI inspection
            result['extracted_text_content'] = text

            # Add link to bronze PDF
            # Construct standard bronze path: bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf
            # This ensures we have a direct link even if not passed explicitly
            bronze_key = f"bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf"
            result['bronze_pdf_s3_key'] = bronze_key

            # Upload structured JSON
            json_s3_key = upload_structured_json(doc_id, year, result)
            logger.info(f"Uploaded structured JSON: {json_s3_key}")

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


def download_bytes(s3_key: str) -> bytes:
    """Download raw bytes from S3."""
    # logger.info(f"Downloading bytes from s3://{S3_BUCKET}/{s3_key}")
    response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
    return response['Body'].read()



def extract_structured_data(doc_id: str, year: int, text: str, filing_type: str, pdf_bytes: bytes = None) -> Dict[str, Any]:
    """
    Extract structured data based on filing type using code-based extractors.

    Routes to appropriate extractor based on filing type code:
    - P: PTRExtractor
    - A, B: TypeABAnnualExtractor
    - T: TypeTTerminationExtractor
    - X: TypeXExtensionRequestExtractor
    - D: TypeDCampaignNoticeExtractor
    - W: TypeWWithdrawalNoticeExtractor
    - Others: Generic fallback
    """
    
    # Initialize appropriate extractor
    extractor = None
    
    # Initialize with PDF bytes if available (for OCR fallback)
    extractor_kwargs = {"pdf_bytes": pdf_bytes} if pdf_bytes else {}
    
    if filing_type == "P":
        extractor = PTRExtractor(**extractor_kwargs)
    elif filing_type in ["A", "B", "C"]:
        extractor = TypeABAnnualExtractor(**extractor_kwargs)
    elif filing_type == "T":
        extractor = TypeTTerminationExtractor(**extractor_kwargs)
    elif filing_type == "X":
        extractor = TypeXExtensionRequestExtractor(**extractor_kwargs)
    elif filing_type == "D":
        extractor = TypeDCampaignNoticeExtractor(**extractor_kwargs)
    elif filing_type == "W":
        extractor = TypeWWithdrawalNoticeExtractor(**extractor_kwargs)
        
    if extractor:
        try:
            # Extract data using fallback strategy (Text -> OCR)
            # If text is provided, BaseExtractor uses it first.
            # If text is empty/bad and pdf_bytes provided, it tries OCR.
            
            # We need to manually inject the text if we want to skip re-extraction
            if text and hasattr(extractor, '_text'):
                 extractor._text = text
                 # Also set format to TEXT if text is good? 
                 # BaseExtractor logic is: if pdf_format is TEXT, use text.
                 # If we pass pdf_bytes, it analyzes it.
                 # If we don't pass pdf_bytes, it's text-only mode.
            
            if pdf_bytes:
                result = extractor.extract_with_fallback()
            else:
                # Text-only mode
                result = extractor.extract_from_text(text)
            
            # Add common metadata
            result["doc_id"] = doc_id
            result["year"] = year
            result["filing_type"] = filing_type
            
            return result
        except Exception as e:
            logger.error(f"Extraction failed for {doc_id} ({filing_type}): {e}")
            # Fall through to generic handler
            pass

    # Generic/Fallback extraction for unsupported types or errors
    return extract_simple_notice(doc_id, year, text, filing_type)


def extract_simple_notice(doc_id: str, year: int, text: str, filing_type: str) -> Dict[str, Any]:
    """Extract simple notice types (D, E, N, B, F, G, U)."""
    import re

    extracted = {
        "doc_id": doc_id,
        "year": year,
        "filing_type": filing_type,
        "document_header": {},
        "notice_type": {
            "D": "Duplicate Filing",
            "E": "Electronic Copy",
            "N": "New Filer Notification",
            "B": "Blind Trust Report",
            "F": "Final Amendment",
            "G": "Gift Travel Report",
            "U": "Unknown/Other"
        }.get(filing_type, "Unknown"),
        "missing_fields": []
    }

    # Extract basic fields
    filing_id_match = re.search(r'Filing\s*ID:?\s*#?(\d+)', text, re.IGNORECASE)
    if filing_id_match:
        extracted['document_header']['filing_id'] = filing_id_match.group(1)
    else:
        extracted['missing_fields'].append('filing_id')

    name_match = re.search(r'Name:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
    if name_match:
        extracted['document_header']['filer_name'] = name_match.group(1)
    else:
        extracted['missing_fields'].append('filer_name')

    date_match = re.search(r'Date:?\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
    if date_match:
        extracted['document_header']['filing_date'] = date_match.group(1)
    else:
        extracted['missing_fields'].append('filing_date')

    # Calculate confidence based on fields found
    total_fields = 3
    found_fields = total_fields - len(extracted['missing_fields'])
    extracted['confidence_score'] = found_fields / total_fields

    extracted['manual_review_required'] = extracted['confidence_score'] < 0.5

    return extracted


def upload_structured_json(doc_id: str, year: int, data: Dict[str, Any]) -> str:
    """Upload structured JSON to S3."""

    # Path: silver/objects/filing_type={type}/year={year}/doc_id={doc_id}/extraction.json
    filing_type = data.get('filing_type', 'Unknown').replace('/', '_').replace(' ', '_').lower()
    # Ensure filing_type starts with 'type_' if it's a single letter code
    if len(filing_type) == 1:
        filing_type = f"type_{filing_type}"

    s3_key = f"{S3_SILVER_PREFIX}/objects/filing_type={filing_type}/year={year}/doc_id={doc_id}/extraction.json"

    json_str = json.dumps(data, indent=2)

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json_str.encode('utf-8'),
        ContentType='application/json'
    )

    logger.info(f"Uploaded structured JSON to s3://{S3_BUCKET}/{s3_key}")
    return s3_key
