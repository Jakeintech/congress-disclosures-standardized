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
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import shared libraries
from lib import s3_utils, pdf_extractor, parquet_writer  # noqa: E402
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver")
EXTRACTION_VERSION = os.environ.get("EXTRACTION_VERSION", "1.0.0")
TEXTRACT_MAX_PAGES_SYNC = int(os.environ.get("TEXTRACT_MAX_PAGES_SYNC", "10"))
TEXTRACT_MONTHLY_PAGE_LIMIT = int(os.environ.get("TEXTRACT_MONTHLY_PAGE_LIMIT", "1000"))

# Load JSON schema
SCHEMAS_DIR = Path(__file__).parent / "schemas"
with open(SCHEMAS_DIR / "house_fd_documents.json") as f:
    DOCUMENTS_SCHEMA = json.load(f)


def get_textract_pages_used_this_month() -> int:
    """Query documents table to count Textract pages used this month.

    Returns:
        int: Total pages processed with Textract this month

    Raises:
        Exception: If query fails
    """
    try:
        from datetime import date

        # Get current month in YYYY-MM format
        current_month = date.today().strftime("%Y-%m")

        logger.info(f"Counting Textract pages used in {current_month}")

        # Query all years (we need to check all documents in current month)
        s3_client = boto3.client("s3")
        total_pages = 0

        # List all year partitions
        paginator = s3_client.get_paginator("list_objects_v2")
        prefix = f"{S3_SILVER_PREFIX}/house/financial/documents/"

        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix, Delimiter="/"):
            # Get year directories
            for prefix_obj in page.get("CommonPrefixes", []):
                year_prefix = prefix_obj["Prefix"]

                # Check if parquet file exists for this year
                parquet_key = f"{year_prefix}part-0000.parquet"

                try:
                    # Download and read parquet file
                    import pyarrow.parquet as pq
                    import io

                    obj = s3_client.get_object(Bucket=S3_BUCKET, Key=parquet_key)
                    parquet_bytes = obj["Body"].read()

                    # Read parquet file
                    table = pq.read_table(io.BytesIO(parquet_bytes))
                    df = table.to_pandas()

                    # Filter by current month and sum textract_pages_used
                    if "extraction_month" in df.columns and "textract_pages_used" in df.columns:
                        month_df = df[df["extraction_month"] == current_month]
                        month_pages = month_df["textract_pages_used"].sum()
                        total_pages += int(month_pages)
                        logger.debug(
                            f"Year {year_prefix}: {len(month_df)} docs, "
                            f"{month_pages} Textract pages in {current_month}"
                        )

                except s3_client.exceptions.NoSuchKey:
                    # File doesn't exist yet, skip
                    continue
                except Exception as e:
                    logger.warning(f"Failed to read {parquet_key}: {e}")
                    continue

        logger.info(f"Total Textract pages used in {current_month}: {total_pages}")
        return total_pages

    except Exception as e:
        logger.error(f"Failed to count Textract pages: {e}")
        # Return 0 to be safe (won't block processing)
        return 0


def download_pdf_from_house_website(doc_id: str, year: int, s3_pdf_key: str, pdf_path: Path):
    """Download PDF from House website and upload to bronze layer.

    Args:
        doc_id: Document ID
        year: Filing year
        s3_pdf_key: S3 key to upload to
        pdf_path: Local path to save PDF

    Raises:
        Exception: If download or upload fails
    """
    # House PDF URL pattern
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
        # Check if PDF exists in bronze layer, if not download from House website
        if not s3_utils.s3_object_exists(S3_BUCKET, s3_pdf_key):
            logger.info(f"PDF not in bronze, downloading from House website: {doc_id}")
            download_pdf_from_house_website(doc_id, year, s3_pdf_key, pdf_path)
        else:
            logger.info(f"Downloading PDF from bronze: s3://{S3_BUCKET}/{s3_pdf_key}")
            s3_utils.download_file_from_s3(S3_BUCKET, s3_pdf_key, pdf_path)

        # Calculate PDF hash and metadata
        pdf_sha256 = s3_utils.calculate_sha256(pdf_path)
        pdf_file_size = pdf_path.stat().st_size

        logger.info(
            f"PDF downloaded: {pdf_file_size} bytes, SHA256={pdf_sha256[:16]}..."
        )

        # Step 1.5: Check Textract budget
        textract_pages_used = get_textract_pages_used_this_month()
        textract_budget_remaining = TEXTRACT_MONTHLY_PAGE_LIMIT - textract_pages_used

        logger.info(
            f"Textract budget: {textract_pages_used}/{TEXTRACT_MONTHLY_PAGE_LIMIT} pages used, "
            f"{textract_budget_remaining} remaining"
        )

        # Step 2: Extract text
        logger.info("Extracting text from PDF")

        extraction_result = pdf_extractor.extract_text_from_pdf(
            pdf_path=pdf_path,
            textract_max_pages_sync=TEXTRACT_MAX_PAGES_SYNC,
            s3_bucket=S3_BUCKET,
            s3_key=s3_pdf_key,  # For Textract async if needed
            textract_budget_remaining=textract_budget_remaining,
        )

        # Step 3: Upload extracted text to silver (partitioned by extraction method)
        logger.info("Uploading extracted text to silver")

        # Normalize extraction method for partitioning (remove suffixes like -budget-limit)
        extraction_method = extraction_result["extraction_method"]
        method_for_path = extraction_method.replace("-budget-limit", "")
        if method_for_path.startswith("textract-"):
            method_for_path = "textract"

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

        # Step 3b: If Textract was used, save raw JSON response for comparison
        if "textract_raw_response" in extraction_result:
            logger.info("Saving raw Textract JSON for comparison")
            textract_json_key = (
                f"{S3_SILVER_PREFIX}/house/financial/text/"
                f"extraction_method=textract/year={year}/"
                f"doc_id={doc_id}/textract_response.json.gz"
            )

            import gzip
            textract_json_bytes = json.dumps(extraction_result["textract_raw_response"]).encode('utf-8')
            textract_json_gzipped = gzip.compress(textract_json_bytes)

            s3_client = boto3.client("s3")
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=textract_json_key,
                Body=textract_json_gzipped,
                ContentType="application/json",
                ContentEncoding="gzip",
                Metadata={
                    "doc_id": doc_id,
                    "year": str(year),
                    "extraction_method": extraction_result["extraction_method"],
                    "extraction_version": EXTRACTION_VERSION,
                }
            )
            logger.info(f"Saved raw Textract JSON: s3://{S3_BUCKET}/{textract_json_key}")

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
    from datetime import date

    # Calculate total duration
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Calculate extraction month (YYYY-MM format)
    extraction_month = date.today().strftime("%Y-%m")

    # Calculate textract_pages_used (pages if Textract was used, 0 otherwise)
    extraction_method = extraction_result["extraction_method"]
    textract_pages_used = 0
    if extraction_method in ["textract-detect-sync", "textract-detect-async", "textract-analyze"]:
        textract_pages_used = extraction_result["pages"]

    # Get requires_textract_reprocessing flag
    requires_textract_reprocessing = extraction_result.get("requires_textract_reprocessing", False)

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
        "extraction_method": extraction_method,
        "extraction_status": "success",
        "extraction_version": EXTRACTION_VERSION,
        "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
        "extraction_error": None,
        "extraction_duration_seconds": duration,
        "text_s3_key": text_s3_key,
        "json_s3_key": None,  # For future structured extraction
        "textract_job_id": extraction_result.get("textract_job_id"),
        "char_count": len(extraction_result["text"]),
        "extraction_month": extraction_month,
        "textract_pages_used": textract_pages_used,
        "requires_textract_reprocessing": requires_textract_reprocessing,
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
            "extraction_month": extraction_month,
            "textract_pages_used": 0,
            "requires_textract_reprocessing": False,
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
