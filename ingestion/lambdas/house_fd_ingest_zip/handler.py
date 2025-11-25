"""Lambda handler for ingesting House FD zip files.

This Lambda:
1. Downloads YEARFD.zip from House website
2. Uploads raw zip to S3 bronze layer
3. Extracts and uploads index files (XML, TXT)
4. Extracts and uploads individual PDFs
5. Sends extraction jobs to SQS queue
"""

import io
import json
import logging
import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import boto3
import requests
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
EXTRACTION_VERSION = os.environ.get("EXTRACTION_VERSION", "1.0.0")

# AWS clients
s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")

# House FD base URL
HOUSE_FD_BASE_URL = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs"


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler.

    Args:
        event: Lambda event with 'year' parameter
        context: Lambda context

    Returns:
        Dict with status and stats

    Example event:
        {
            "year": 2025
        }
    """
    try:
        # Extract year from event
        year = event.get("year")
        if not year:
            raise ValueError("Missing required parameter: year")

        year = int(year)

        logger.info(f"Starting ingestion for year {year}")

        # Step 1: Download zip file
        logger.info(f"Step 1: Downloading {year}FD.zip")
        zip_url = f"{HOUSE_FD_BASE_URL}/{year}FD.zip"
        zip_bytes, download_meta = download_zip_file(zip_url)

        # Step 2: Upload raw zip to bronze
        logger.info("Step 2: Uploading raw zip to bronze layer")
        raw_zip_key = (
            f"{S3_BRONZE_PREFIX}/house/financial/year={year}/raw_zip/{year}FD.zip"
        )
        upload_raw_zip(zip_bytes, raw_zip_key, download_meta, year)

        # Step 3: Extract and upload index files
        logger.info("Step 3: Extracting and uploading index files")
        index_files = extract_and_upload_index(zip_bytes, year)

        # Step 4: Extract and upload PDFs + send to SQS
        logger.info("Step 4: Extracting and uploading PDFs")
        pdf_count, sqs_message_count = extract_and_upload_pdfs(zip_bytes, year)

        # Trigger index-to-silver Lambda (synchronous)
        logger.info("Step 5: Triggering index-to-silver Lambda")
        trigger_index_to_silver(year)

        result = {
            "status": "success",
            "year": year,
            "zip_url": zip_url,
            "raw_zip_s3_key": raw_zip_key,
            "index_files": index_files,
            "pdfs_uploaded": pdf_count,
            "sqs_messages_sent": sqs_message_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Ingestion complete: {json.dumps(result)}")

        return result

    except Exception as e:
        logger.error(f"Ingestion failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def download_zip_file(url: str, timeout: int = 120) -> tuple:
    """Download zip file from House website.

    Args:
        url: URL to download
        timeout: Request timeout in seconds

    Returns:
        Tuple of (zip_bytes, metadata_dict)

    Raises:
        requests.RequestException: If download fails
    """
    logger.info(f"Downloading from {url}")

    start_time = time.time()

    response = requests.get(url, timeout=timeout, stream=True)
    response.raise_for_status()

    # Read into memory (zip files are ~100-500 MB, within Lambda memory)
    zip_bytes = response.content

    duration = time.time() - start_time

    metadata = {
        "source_url": url,
        "download_timestamp": datetime.now(timezone.utc).isoformat(),
        "file_size_bytes": str(len(zip_bytes)),
        "duration_seconds": f"{duration:.2f}",
        "http_status": str(response.status_code),
        "content_type": response.headers.get("Content-Type", ""),
    }

    # Add HTTP caching headers if available
    if "ETag" in response.headers:
        metadata["http_etag"] = response.headers["ETag"]
    if "Last-Modified" in response.headers:
        metadata["http_last_modified"] = response.headers["Last-Modified"]

    logger.info(f"Downloaded {len(zip_bytes)} bytes in {duration:.2f}s")

    return zip_bytes, metadata


def upload_raw_zip(zip_bytes: bytes, s3_key: str, metadata: Dict[str, str], year: int):
    """Upload raw zip file to S3 bronze layer.

    Args:
        zip_bytes: Zip file bytes
        s3_key: S3 key
        metadata: Metadata dict
        year: Year

    Raises:
        ClientError: If upload fails
    """
    upload_metadata = {
        **metadata,
        "ingest_version": EXTRACTION_VERSION,
        "year": str(year),
    }

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=zip_bytes,
        Metadata=upload_metadata,
        ContentType="application/zip",
    )

    logger.info(f"Uploaded raw zip to s3://{S3_BUCKET}/{s3_key}")


def extract_and_upload_index(zip_bytes: bytes, year: int) -> List[str]:
    """Extract and upload index files (XML, TXT).

    Args:
        zip_bytes: Zip file bytes
        year: Year

    Returns:
        List of uploaded S3 keys

    Raises:
        Exception: If extraction fails
    """
    uploaded_keys = []

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Find index files
        for filename in zf.namelist():
            if filename.endswith((".xml", ".txt")) and f"{year}FD" in filename:
                logger.info(f"Extracting index file: {filename}")

                file_data = zf.read(filename)
                file_ext = Path(filename).suffix

                s3_key = f"{S3_BRONZE_PREFIX}/house/financial/year={year}/index/{year}FD{file_ext}"

                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=s3_key,
                    Body=file_data,
                    Metadata={
                        "source_filename": filename,
                        "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                        "year": str(year),
                    },
                    ContentType="application/xml"
                    if file_ext == ".xml"
                    else "text/plain",
                )

                uploaded_keys.append(s3_key)
                logger.info(f"Uploaded index to s3://{S3_BUCKET}/{s3_key}")

    return uploaded_keys


def extract_and_upload_pdfs(zip_bytes: bytes, year: int) -> tuple:
    """Extract and upload PDFs, send SQS messages for extraction.

    Args:
        zip_bytes: Zip file bytes
        year: Year

    Returns:
        Tuple of (pdf_count, sqs_message_count)

    Raises:
        Exception: If extraction fails
    """
    pdf_count = 0
    sqs_message_count = 0
    sqs_messages_batch = []

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for filename in zf.namelist():
            if filename.lower().endswith(".pdf"):
                pdf_count += 1

                # Extract doc_id from filename (e.g., "8221216.pdf" -> "8221216")
                doc_id = Path(filename).stem

                logger.debug(
                    f"Processing PDF {pdf_count}: {filename} (doc_id={doc_id})"
                )

                # Read PDF
                pdf_data = zf.read(filename)

                # Upload to S3
                s3_key = f"{S3_BRONZE_PREFIX}/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf"

                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=s3_key,
                    Body=pdf_data,
                    Metadata={
                        "doc_id": doc_id,
                        "year": str(year),
                        "source_filename": filename,
                        "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    ContentType="application/pdf",
                )

                logger.debug(f"Uploaded PDF to s3://{S3_BUCKET}/{s3_key}")

                # Prepare SQS message
                sqs_messages_batch.append(
                    {
                        "Id": doc_id,
                        "MessageBody": json.dumps(
                            {
                                "doc_id": doc_id,
                                "year": year,
                                "s3_pdf_key": s3_key,
                            }
                        ),
                    }
                )

                # Send batch if we have 10 messages (SQS max batch size)
                if len(sqs_messages_batch) >= 10:
                    send_sqs_batch(sqs_messages_batch)
                    sqs_message_count += len(sqs_messages_batch)
                    sqs_messages_batch = []

    # Send remaining messages
    if sqs_messages_batch:
        send_sqs_batch(sqs_messages_batch)
        sqs_message_count += len(sqs_messages_batch)

    logger.info(f"Processed {pdf_count} PDFs, sent {sqs_message_count} SQS messages")

    return pdf_count, sqs_message_count


def send_sqs_batch(messages: List[Dict[str, str]]):
    """Send batch of messages to SQS.

    Args:
        messages: List of SQS message dicts

    Raises:
        ClientError: If send fails
    """
    try:
        response = sqs_client.send_message_batch(
            QueueUrl=SQS_QUEUE_URL,
            Entries=messages,
        )

        failed = response.get("Failed", [])
        if failed:
            logger.warning(f"Some SQS messages failed: {failed}")

    except ClientError as e:
        logger.error(f"Failed to send SQS batch: {e}")
        raise


def trigger_index_to_silver(year: int):
    """Trigger index-to-silver Lambda synchronously.

    Args:
        year: Year to process

    Raises:
        ClientError: If invocation fails
    """
    lambda_client = boto3.client("lambda")

    # Get function name from environment or construct it
    function_name = os.environ.get(
        "INDEX_TO_SILVER_FUNCTION_NAME",
        (
            f"congress-disclosures-{os.environ.get('ENVIRONMENT', 'development')}"
            f"-index-to-silver"
        ),
    )

    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",  # Synchronous
            Payload=json.dumps({"year": year}),
        )

        # Parse response
        response_payload = json.loads(response["Payload"].read())

        if response.get("StatusCode") == 200:
            logger.info(f"Successfully triggered index-to-silver: {response_payload}")
        else:
            logger.warning(f"Index-to-silver returned non-200: {response_payload}")

    except Exception as e:
        # Don't fail ingestion if index processing fails - it can be retried manually
        logger.warning(f"Failed to trigger index-to-silver Lambda: {e}")
