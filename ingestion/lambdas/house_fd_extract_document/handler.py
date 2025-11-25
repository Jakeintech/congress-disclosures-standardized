"""Lambda handler for extracting text from House FD PDFs.

This Lambda (triggered by SQS):
1. Downloads PDF from bronze layer
2. Extracts text using pypdf or AWS Textract
3. Uploads extracted text to silver layer (gzipped)
4. Updates house_fd_documents record with extraction results
"""

import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import shared libraries
from lib import s3_utils, pdf_extractor, parquet_writer  # noqa: E402

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver")
EXTRACTION_VERSION = os.environ.get("EXTRACTION_VERSION", "1.0.0")
TEXTRACT_MAX_PAGES_SYNC = int(os.environ.get("TEXTRACT_MAX_PAGES_SYNC", "10"))

# Load JSON schema
SCHEMAS_DIR = Path(__file__).parent / "schemas"
with open(SCHEMAS_DIR / "house_fd_documents.json") as f:
    DOCUMENTS_SCHEMA = json.load(f)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler (triggered by SQS).

    Args:
        event: SQS event with batch of messages
        context: Lambda context

    Returns:
        Dict with batch item failures for SQS

    Example event:
        {
            "Records": [
                {
                    "messageId": "...",
                    "body": "{\"doc_id\": \"8221216\", \"year\": 2025, \"s3_pdf_key\": \"...\"}"
                }
            ]
        }
    """
    batch_item_failures = []

    for record in event.get("Records", []):
        try:
            # Parse SQS message
            message_body = json.loads(record["body"])
            doc_id = message_body["doc_id"]
            year = message_body["year"]
            s3_pdf_key = message_body["s3_pdf_key"]

            logger.info(f"Processing doc_id={doc_id}, year={year}")

            # Process document
            process_document(doc_id, year, s3_pdf_key)

            logger.info(f"Successfully processed doc_id={doc_id}")

        except Exception as e:
            logger.error(f"Failed to process record: {str(e)}", exc_info=True)

            # Add to batch failures (SQS will retry)
            batch_item_failures.append({"itemIdentifier": record["messageId"]})

    # Return batch failures for SQS partial batch response
    return {"batchItemFailures": batch_item_failures}


def process_document(doc_id: str, year: int, s3_pdf_key: str):
    """Process a single PDF document.

    Args:
        doc_id: Document ID
        year: Filing year
        s3_pdf_key: S3 key of PDF in bronze layer

    Raises:
        Exception: If processing fails
    """
    start_time = datetime.now(timezone.utc)

    # Step 1: Download PDF to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        pdf_path = Path(tmp_file.name)

    try:
        logger.info(f"Downloading PDF: s3://{S3_BUCKET}/{s3_pdf_key}")
        s3_utils.download_file_from_s3(S3_BUCKET, s3_pdf_key, pdf_path)

        # Calculate PDF hash and metadata
        pdf_sha256 = s3_utils.calculate_sha256(pdf_path)
        pdf_file_size = pdf_path.stat().st_size

        logger.info(
            f"PDF downloaded: {pdf_file_size} bytes, SHA256={pdf_sha256[:16]}..."
        )

        # Step 2: Extract text
        logger.info("Extracting text from PDF")

        extraction_result = pdf_extractor.extract_text_from_pdf(
            pdf_path=pdf_path,
            textract_max_pages_sync=TEXTRACT_MAX_PAGES_SYNC,
            s3_bucket=S3_BUCKET,
            s3_key=s3_pdf_key,  # For Textract async if needed
        )

        # Step 3: Upload extracted text to silver
        logger.info("Uploading extracted text to silver")

        text_s3_key = (
            f"{S3_SILVER_PREFIX}/house/financial/text/year={year}/"
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

        update_document_record(
            doc_id=doc_id,
            year=year,
            pdf_sha256=pdf_sha256,
            pdf_file_size=pdf_file_size,
            extraction_result=extraction_result,
            text_s3_key=text_s3_key,
            start_time=start_time,
        )

        logger.info(f"Document processing complete for doc_id={doc_id}")

    finally:
        # Clean up temp file
        if pdf_path.exists():
            pdf_path.unlink()


def update_document_record(
    doc_id: str,
    year: int,
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
    # Calculate total duration
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Build updated record
    updated_record = {
        "doc_id": doc_id,
        "year": year,
        "pdf_s3_key": (
            f"{S3_BRONZE_PREFIX}/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf"
        ),
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
        "textract_job_id": extraction_result.get("textract_job_id"),
        "char_count": len(extraction_result["text"]),
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
        updated_record = {
            "doc_id": doc_id,
            "year": year,
            "pdf_s3_key": f"{S3_BRONZE_PREFIX}/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf",
            "pdf_sha256": "",  # Unknown since we failed
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
            "textract_job_id": None,
            "char_count": None,
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
