"""Lambda handler for extracting text from House FD PDFs.

This Lambda (triggered by SQS):
1. Downloads PDF from bronze layer
2. Extracts text using local strategies (pypdf + OCR pipeline)
3. Uploads extracted text to silver layer (gzipped)
4. Updates house_fd_documents record with extraction results
"""

import json
import logging
import os
os.environ["HOME"] = "/tmp"
import sys
import tempfile
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import shared libraries
from lib import s3_utils, pdf_extractor, parquet_writer  # noqa: E402
from lib.extraction import ExtractionPipeline, DirectTextExtractor, OCRTextExtractor, ImagePreprocessor  # noqa: E402
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver")
EXTRACTION_VERSION = os.environ.get("EXTRACTION_VERSION", "1.0.0")
CODE_EXTRACTION_QUEUE_URL = os.environ.get("CODE_EXTRACTION_QUEUE_URL")  # NEW: Code-based extraction (FREE)

# Initialize SQS client for queuing structured extraction
sqs_client = boto3.client('sqs')

# Load JSON schema
SCHEMAS_DIR = Path(__file__).parent / "schemas"
with open(SCHEMAS_DIR / "house_fd_documents.json") as f:
    DOCUMENTS_SCHEMA = json.load(f)


def update_bronze_pdf_metadata(
    s3_pdf_key: str,
    extraction_result: Dict[str, Any],
    text_s3_key: str,
    filing_type: str = None,
    filer_name: str = None,
    filing_date: str = None,
    state_district: str = None
):
    """Update Bronze PDF S3 metadata to track extraction processing.

    Tagging prevents duplicate work and simplifies auditing across pipelines.
    
    Args:
        s3_pdf_key: S3 key of the Bronze PDF
        extraction_result: Result from pdf_extractor
        text_s3_key: S3 key of extracted text in Silver
        structured_s3_key: Optional S3 key of structured JSON in Silver
        filing_type: Optional filing type to tag
        filer_name: Optional filer name
        filing_date: Optional filing date
        state_district: Optional state/district
    """
    try:
        s3_client = boto3.client("s3")
        
        # Copy object to itself with new metadata (preserves object, updates metadata)
        copy_source = {"Bucket": S3_BUCKET, "Key": s3_pdf_key}
        
        metadata = {
            "extraction-processed": "true",
            "extraction-version": EXTRACTION_VERSION,
            "extraction-timestamp": datetime.now(timezone.utc).isoformat(),
            "extraction-method": extraction_result["extraction_method"],
            "extraction-pages": str(extraction_result["pages"]),
            "text-location": text_s3_key,
        }
        
        if filing_type:
            metadata["filing-type"] = filing_type
        if filer_name:
            metadata["filer-name"] = filer_name
        if filing_date:
            metadata["filing-date"] = filing_date
        if state_district:
            metadata["state-district"] = state_district
        
        # structured_s3_key is optional, passed as parameter if available
        
        s3_client.copy_object(
            Bucket=S3_BUCKET,
            Key=s3_pdf_key,
            CopySource=copy_source,
            Metadata=metadata,
            MetadataDirective="REPLACE"
        )
        
        logger.info(f"Updated Bronze PDF metadata for {s3_pdf_key}")
        
    except Exception as e:
        # Log but don't fail - metadata update is best-effort
        logger.warning(f"Failed to update Bronze PDF metadata: {e}")

def download_pdf_from_house_website(doc_id: str, year: int, s3_pdf_key: str, pdf_path: Path, filing_type: str = None):
    """Download PDF from House website and upload to bronze layer.

    Args:
        doc_id: Document ID
        year: Filing year
        s3_pdf_key: S3 key to upload to
        pdf_path: Local path to save PDF
        filing_type: Filing type code (e.g. 'P' for PTR)

    Raises:
        Exception: If download or upload fails
    """
    # House PDF URL pattern
    # Type P (PTR) documents are stored in a different directory
    if filing_type == 'P':
        house_url = f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"
    else:
        house_url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}/{doc_id}.pdf"

    logger.info(f"Downloading from House website: {house_url}")

    try:
        response = requests.get(house_url, timeout=30)
        response.raise_for_status()

        # Write to temp file
        pdf_path.write_bytes(response.content)

        logger.info(f"Downloaded {len(response.content)} bytes from House website")

        # Upload to bronze layer
        s3_client = boto3.client("s3")
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_pdf_key,
            Body=response.content,
            ContentType="application/pdf",
            Metadata={
                "doc_id": doc_id,
                "year": str(year),
                "source_url": house_url,
                "download_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"Uploaded PDF to bronze: s3://{S3_BUCKET}/{s3_pdf_key}")

    except requests.RequestException as e:
        logger.error(f"Failed to download PDF from House website: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to upload PDF to bronze: {str(e)}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler (triggered by SQS or direct invocation).

    Args:
        event: SQS event with batch of messages OR direct dict with doc_id
        context: Lambda context

    Returns:
        Dict with batch item failures for SQS, or simple success dict for direct
    """
    # Case 1: Direct invocation from Step Functions (Map state)
    if "doc_id" in event:
        try:
            logger.info(f"Processing direct invocation for doc_id={event['doc_id']}")
            doc_id = event["doc_id"]
            year = event["year"]
            s3_pdf_key = event["s3_pdf_key"]
            filing_type = event.get("filing_type")
            filer_name = event.get("filer_name")
            filing_date = event.get("filing_date")
            state_district = event.get("state_district")

            process_document(
                doc_id, 
                year, 
                s3_pdf_key, 
                filing_type,
                filer_name,
                filing_date,
                state_district
            )
            return {"status": "success", "doc_id": doc_id}
        except Exception as e:
            logger.error(f"Failed to process direct invocation: {str(e)}", exc_info=True)
            raise  # Raise so Step Functions knows it failed

    # Case 2: SQS Trigger
    batch_item_failures = []

    for record in event.get("Records", []):
        try:
            # Parse SQS message
            message_body = json.loads(record["body"])
            doc_id = message_body["doc_id"]
            year = message_body["year"]
            s3_pdf_key = message_body["s3_pdf_key"]
            filing_type = message_body.get("filing_type")
            filer_name = message_body.get("filer_name")
            filing_date = message_body.get("filing_date")
            state_district = message_body.get("state_district")

            logger.info(f"Processing doc_id={doc_id}, year={year}, type={filing_type}")

            # Process document
            process_document(
                doc_id, 
                year, 
                s3_pdf_key, 
                filing_type,
                filer_name,
                filing_date,
                state_district
            )

            logger.info(f"Successfully processed doc_id={doc_id}")

        except Exception as e:
            logger.error(f"Failed to process record: {str(e)}", exc_info=True)

            # Add to batch failures (SQS will retry)
            batch_item_failures.append({"itemIdentifier": record["messageId"]})

    # Return batch failures for SQS partial batch response
    return {"batchItemFailures": batch_item_failures}


def process_document(
    doc_id: str,
    year: int,
    s3_pdf_key: str,
    filing_type: str = None,
    filer_name: str = None,
    filing_date: str = None,
    state_district: str = None
):
    """Process a single PDF document.

    Args:
        doc_id: Document ID
        year: Filing year
        s3_pdf_key: S3 key of PDF in bronze layer
        filing_type: Filing type code
        filer_name: Filer name
        filing_date: Filing date
        state_district: State/District
    """
    start_time = datetime.now(timezone.utc)

    # Step 1: Download PDF to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        pdf_path = Path(tmp_file.name)

    try:
        # Check if PDF exists in bronze layer, if not download from House website
        if not s3_utils.s3_object_exists(S3_BUCKET, s3_pdf_key):
            logger.info(f"PDF not in bronze, downloading from House website: {doc_id}")
            download_pdf_from_house_website(doc_id, year, s3_pdf_key, pdf_path, filing_type)
        else:
            logger.info(f"Downloading PDF from bronze: s3://{S3_BUCKET}/{s3_pdf_key}")
            s3_utils.download_file_from_s3(S3_BUCKET, s3_pdf_key, pdf_path)

        # Calculate PDF hash and metadata
        pdf_sha256 = s3_utils.calculate_sha256(pdf_path)
        pdf_file_size = pdf_path.stat().st_size

        logger.info(
            f"PDF downloaded: {pdf_file_size} bytes, SHA256={pdf_sha256[:16]}..."
        )

        # Step 2: Extract text using new ExtractionPipeline
        logger.info("Extracting text from PDF using ExtractionPipeline")

        # Initialize extraction pipeline with fallback strategies
        pipeline = ExtractionPipeline(
            min_confidence=0.5,  # Lower threshold for initial extraction
            min_characters=50,
            enable_fallback=True
        )

        # Extract text with automatic strategy selection
        extraction_pipeline_result = pipeline.extract(str(pdf_path))

        # Convert ExtractionResult to legacy format for compatibility
        extraction_result = {
            "text": extraction_pipeline_result.text,
            "pages": extraction_pipeline_result.page_count,
            "extraction_method": extraction_pipeline_result.extraction_method,
            "has_embedded_text": extraction_pipeline_result.extraction_method == "direct_text",
            "confidence_score": extraction_pipeline_result.confidence_score,
            "processing_time": extraction_pipeline_result.processing_time_seconds,
            "quality_metrics": extraction_pipeline_result.quality_metrics,
            "warnings": extraction_pipeline_result.warnings,
            "requires_additional_ocr": extraction_pipeline_result.confidence_score < 0.3,
        }

        logger.info(
            f"Extraction complete: method={extraction_result['extraction_method']}, "
            f"confidence={extraction_result['confidence_score']:.2%}, "
            f"chars={len(extraction_result['text'])}, "
            f"time={extraction_result['processing_time']:.2f}s"
        )

        # Step 3: Upload extracted text to silver (partitioned by extraction method)
        logger.info("Uploading extracted text to silver")

        # Normalize extraction method for partitioning (remove suffixes like -budget-limit)
        extraction_method = extraction_result["extraction_method"]
        method_for_path = extraction_method.replace("-budget-limit", "")

        text_s3_key = (
            f"{S3_SILVER_PREFIX}/house/financial/text/"
            f"extraction_method={method_for_path}/year={year}/"
            f"doc_id={doc_id}/raw_text.txt.gz"
        )

        s3_utils.upload_text_gzipped(
            text=extraction_result["text"],
            bucket=S3_BUCKET,
            s3_key=text_s3_key,
            metadata={
                "doc_id": doc_id,
                "year": str(year),
                "extraction_method": extraction_result["extraction_method"],
                "extraction_version": EXTRACTION_VERSION,
                "pages": str(extraction_result["pages"]),
                "char_count": str(len(extraction_result["text"])),
            },
        )

        # Step 4: Update house_fd_documents record
        logger.info("Updating house_fd_documents record")

        # Step 4a: Update Bronze PDF metadata to prevent duplicate Textract calls
        logger.info("Updating Bronze PDF metadata")
        update_bronze_pdf_metadata(
            s3_pdf_key=s3_pdf_key,
            extraction_result=extraction_result,
            text_s3_key=text_s3_key,
            filing_type=filing_type,
            filer_name=filer_name,
            filing_date=filing_date,
            state_district=state_district
        )
        
        # Step 4b: Update house_fd_documents record
        logger.info("Updating house_fd_documents record")
        
        update_document_record(
            doc_id=doc_id,
            year=year,
            s3_pdf_key=s3_pdf_key,
            pdf_sha256=pdf_sha256,
            pdf_file_size=pdf_file_size,
            extraction_result=extraction_result,
            text_s3_key=text_s3_key,
            start_time=start_time,
        )

        # Step 5: Queue CODE-BASED structured extraction (FREE - no Textract)
        if CODE_EXTRACTION_QUEUE_URL:
            logger.info("Queuing document for CODE-BASED structured extraction (FREE)")
            try:
                sqs_client.send_message(
                    QueueUrl=CODE_EXTRACTION_QUEUE_URL,
                    MessageBody=json.dumps({
                        'doc_id': doc_id,
                        'year': year,
                        'text_s3_key': text_s3_key,
                        'extraction_method': extraction_result['extraction_method'],
                        'has_embedded_text': extraction_result.get('has_embedded_text', False),
                        'filing_type': filing_type  # Pass filing type to next stage
                    })
                )
                logger.info(f"✅ Queued code-based extraction for doc_id={doc_id}")
            except Exception as e:
                logger.error(f"Failed to queue code-based extraction: {e}")
                # Don't fail the entire extraction if queuing fails
        else:
            logger.warning("CODE_EXTRACTION_QUEUE_URL not set - skipping code-based extraction queuing")

        logger.info(f"Document processing complete for doc_id={doc_id}")

    finally:
        # Clean up temp file
        if pdf_path.exists():
            pdf_path.unlink()


def update_document_record(
    doc_id: str,
    year: int,
    s3_pdf_key: str,
    pdf_sha256: str,
    pdf_file_size: int,
    extraction_result: Dict[str, Any],
    text_s3_key: str,
    start_time: datetime,
):
    """Update house_fd_documents record with extraction results.

    Args:
        doc_id: Document ID
        year: Filing year
        pdf_sha256: PDF file hash
        pdf_file_size: PDF file size in bytes
        extraction_result: Result from pdf_extractor
        text_s3_key: S3 key of uploaded text
        start_time: Extraction start timestamp

    Raises:
        Exception: If update fails
    """
    from datetime import date

    # Calculate total duration
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Calculate extraction month (YYYY-MM format)
    extraction_month = date.today().strftime("%Y-%m")

    # Build updated record
    updated_record = {
        "doc_id": doc_id,
        "year": year,
        "pdf_s3_key": s3_pdf_key,  # Use actual S3 key from SQS message, don't reconstruct
        "pdf_sha256": pdf_sha256,
        "pdf_file_size_bytes": pdf_file_size,
        "pages": extraction_result["pages"],
        "has_embedded_text": extraction_result.get("has_embedded_text", False),
        "extraction_method": extraction_result["extraction_method"],
        "extraction_status": "success",
        "extraction_version": EXTRACTION_VERSION,
        "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
        "extraction_error": None,
        "extraction_duration_seconds": duration,
        "text_s3_key": text_s3_key,
        "json_s3_key": None,  # For future structured extraction
        "char_count": len(extraction_result["text"]),
        "extraction_month": extraction_month,
        "requires_additional_ocr": extraction_result.get("requires_additional_ocr", False),
        "filing_date": None,  # TODO: Get from filings table if needed
        "processing_priority": None,  # TODO: Calculate from filing date if needed
    }

    # Read existing records
    documents_s3_key = (
        f"{S3_SILVER_PREFIX}/house/financial/documents/year={year}/part-0000.parquet"
    )

    # Upsert record
    parquet_writer.upsert_parquet_records(
        new_records=[updated_record],
        bucket=S3_BUCKET,
        s3_key=documents_s3_key,
        key_columns=["year", "doc_id"],
        schema=DOCUMENTS_SCHEMA,
    )

    logger.info(f"Updated house_fd_documents for doc_id={doc_id}")


def handle_extraction_error(doc_id: str, year: int, error: Exception):
    """Update house_fd_documents record with error status.

    Args:
        doc_id: Document ID
        year: Filing year
        error: Exception that occurred

    Raises:
        Exception: If update fails
    """
    try:
        from datetime import date

        # Calculate extraction month
        extraction_month = date.today().strftime("%Y-%m")

        updated_record = {
            "doc_id": doc_id,
            "year": year,
            "pdf_s3_key": f"{S3_BRONZE_PREFIX}/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf",
            "pdf_sha256": None,  # Unknown since we failed
            "pdf_file_size_bytes": 0,
            "pages": 0,
            "has_embedded_text": False,
            "extraction_method": "failed",
            "extraction_status": "failed",
            "extraction_version": EXTRACTION_VERSION,
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "extraction_error": str(error)[:1000],  # Truncate to max length
            "extraction_duration_seconds": None,
            "text_s3_key": None,
            "json_s3_key": None,
            "char_count": None,
            "extraction_month": extraction_month,
            "requires_additional_ocr": False,
            "filing_date": None,
            "processing_priority": None,
        }

        documents_s3_key = f"{S3_SILVER_PREFIX}/house/financial/documents/year={year}/part-0000.parquet"

        parquet_writer.upsert_parquet_records(
            new_records=[updated_record],
            bucket=S3_BUCKET,
            s3_key=documents_s3_key,
            key_columns=["year", "doc_id"],
            schema=DOCUMENTS_SCHEMA,
        )

        logger.info(f"Updated house_fd_documents with error status for doc_id={doc_id}")

    except Exception as e:
        # Log but don't raise - extraction error handling is best-effort
        logger.error(f"Failed to update error status: {e}")
