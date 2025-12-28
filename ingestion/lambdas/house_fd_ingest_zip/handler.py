"""Lambda handler for ingesting House FD zip files.

This Lambda:
1. Downloads YEARFD.zip from House website
2. Uploads raw zip to S3 bronze layer
3. Extracts and uploads index files (XML, TXT)
4. Extracts and uploads individual PDFs (from zip OR individual downloads)
5. Sends extraction jobs to SQS queue
"""

import io
import json
import logging
import os
import time
import zipfile
import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import boto3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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

# House FD base URL (allow override via env for flexibility)
HOUSE_FD_BASE_URL = os.environ.get(
    "HOUSE_FD_BASE_URL",
    "https://disclosures-clerk.house.gov/public_disc/financial-pdfs",
)

# Conservative request headers to avoid 403 from origin/CDN
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://disclosures-clerk.house.gov/",
    "Connection": "keep-alive",
}


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
        index_files, filing_type_map = extract_upload_and_parse_index(zip_bytes, year)

        # Step 4: Extract and upload PDFs + send to SQS
        logger.info("Step 4: Extracting and uploading PDFs")
        skip_existing = event.get("skip_existing", False)
        pdf_count, sqs_message_count, skipped_count = extract_and_upload_pdfs(zip_bytes, year, filing_type_map, skip_existing)

        result = {
            "status": "success",
            "year": year,
            "zip_url": zip_url,
            "raw_zip_s3_key": raw_zip_key,
            "index_files": index_files,
            "pdfs_uploaded": pdf_count,
            "pdfs_skipped": skipped_count,
            "sqs_messages_sent": sqs_message_count,
            "index_entry_count": len(filing_type_map),
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


def _requests_session() -> requests.Session:
    """Create a requests session with retries and sensible defaults."""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504, 403],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(REQUEST_HEADERS)
    return session


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
    session = _requests_session()

    tried_urls = []
    last_response = None

    def _try_download(u: str):
        nonlocal last_response
        logger.info(f"HTTP GET {u}")
        tried_urls.append(u)
        resp = session.get(u, timeout=timeout, stream=True, allow_redirects=True)
        last_response = resp
        if resp.status_code == 200:
            return resp
        return None

    # Primary URL
    response = _try_download(url)

    # Fallback URL pattern some years use: include year subdirectory
    if response is None:
        try:
            # Extract year and filename from provided URL
            # Expected format: .../financial-pdfs/{year}FD.zip
            base, filename = url.rsplit("/", 1)
            year_part = filename.replace("FD.zip", "")
            alt_url = f"{base}/{year_part}/{filename}"
            logger.info(f"Primary download failed (status={getattr(last_response, 'status_code', 'n/a')}). Trying fallback URL: {alt_url}")
            response = _try_download(alt_url)
        except Exception:
            # Ignore fallback construction errors
            pass

    # If still not successful, raise a descriptive error
    if response is None:
        status = getattr(last_response, "status_code", "n/a")
        headers = getattr(last_response, "headers", {})
        duration = time.time() - start_time
        tried = ", ".join(tried_urls)
        raise requests.HTTPError(
            f"Failed to download FD zip (status={status}) after {duration:.2f}s. Tried: {tried}. "
            f"Content-Type={headers.get('Content-Type')}, Server={headers.get('Server')}"
        )

    # Read into memory (zip files are ~100-500 MB, within Lambda memory)
    zip_bytes = response.content
    duration = time.time() - start_time

    metadata = {
        "source_url": response.url,
        "download_timestamp": datetime.now(timezone.utc).isoformat(),
        "file_size_bytes": str(len(zip_bytes)),
        "duration_seconds": f"{duration:.2f}",
        "http_status": str(response.status_code),
        "content_type": response.headers.get("Content-Type", ""),
        "tried_urls": ",".join(tried_urls),
    }

    # Add HTTP caching headers if available
    if "ETag" in response.headers:
        metadata["http_etag"] = response.headers["ETag"]
    if "Last-Modified" in response.headers:
        metadata["http_last_modified"] = response.headers["Last-Modified"]

    logger.info(f"Downloaded {len(zip_bytes)} bytes in {duration:.2f}s from {response.url}")

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
        Tagging=f"year={year}&ingest_version={EXTRACTION_VERSION}"
    )

    logger.info(f"Uploaded raw zip to s3://{S3_BUCKET}/{s3_key}")


def extract_upload_and_parse_index(zip_bytes: bytes, year: int) -> tuple:
    """Extract and upload index files, and parse XML for filing types.

    Args:
        zip_bytes: Zip file bytes
        year: Year

    Returns:
        Tuple of (uploaded_keys, filing_type_map)
    """
    uploaded_keys = []
    filing_type_map = {}

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

                # Parse XML to build filing type map
                if file_ext == ".xml":
                    try:
                        import xml.etree.ElementTree as ET
                        root = ET.fromstring(file_data)
                        for member in root.findall('Member'):
                            doc_id = member.find('DocID').text
                            filing_type = member.find('FilingType').text
                            if doc_id and filing_type:
                                filing_type_map[doc_id] = filing_type
                        logger.info(f"Parsed {len(filing_type_map)} entries from XML index")
                    except Exception as e:
                        logger.warning(f"Failed to parse XML index: {e}")

    return uploaded_keys, filing_type_map


# Import metadata tagger
try:
    from lib.metadata_tagger import calculate_quality_score
except ImportError:
    # Fallback for local testing or if lib structure differs
    try:
        from ingestion.lib.metadata_tagger import calculate_quality_score
    except ImportError:
        logger.warning("Could not import metadata_tagger, quality scoring disabled")
        calculate_quality_score = lambda *args: 0.0

def extract_and_upload_pdfs(zip_bytes: bytes, year: int, filing_type_map: Dict[str, str], skip_existing: bool = False) -> tuple:
    """Extract and upload PDFs, send SQS messages for extraction.

    Args:
        zip_bytes: Zip file bytes
        year: Year
        filing_type_map: Map of DocID to FilingType
        skip_existing: If True, skip upload if object exists

    Returns:
        Tuple of (pdf_count, sqs_message_count, skipped_count)
    """
    pdf_count = 0
    skipped_count = 0
    sqs_message_count = 0
    sqs_messages_batch = []
    
    # Check if zip contains PDFs
    has_pdfs_in_zip = False
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for filename in zf.namelist():
            if filename.lower().endswith(".pdf"):
                has_pdfs_in_zip = True
                break
    
    if has_pdfs_in_zip:
        logger.info("Zip contains PDFs, extracting from zip...")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for filename in zf.namelist():
                if filename.lower().endswith(".pdf"):
                    # Extract doc_id from filename (e.g., "8221216.pdf" -> "8221216")
                    doc_id = Path(filename).stem
                    pdf_data = zf.read(filename)
                    
                    result = process_pdf_upload(
                        doc_id, year, pdf_data, filing_type_map.get(doc_id, "U"), 
                        filename, skip_existing
                    )
                    
                    if result == "skipped":
                        skipped_count += 1
                    elif result:
                        pdf_count += 1
                        sqs_messages_batch.append(result)
                        
                        if len(sqs_messages_batch) >= 10:
                            send_sqs_batch(sqs_messages_batch)
                            sqs_message_count += len(sqs_messages_batch)
                            sqs_messages_batch = []
    else:
        logger.info("Zip does NOT contain PDFs. Downloading individually...")
        
        # Use ThreadPoolExecutor for parallel downloads
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_doc = {
                executor.submit(download_and_process_individual_pdf, doc_id, year, filing_type, skip_existing): doc_id
                for doc_id, filing_type in filing_type_map.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_doc):
                doc_id = future_to_doc[future]
                try:
                    result = future.result()
                    if result == "skipped":
                        skipped_count += 1
                    elif result:
                        pdf_count += 1
                        sqs_messages_batch.append(result)
                        
                        if len(sqs_messages_batch) >= 10:
                            send_sqs_batch(sqs_messages_batch)
                            sqs_message_count += len(sqs_messages_batch)
                            sqs_messages_batch = []
                except Exception as e:
                    logger.error(f"Failed to process {doc_id}: {e}")

    # Send remaining messages
    if sqs_messages_batch:
        send_sqs_batch(sqs_messages_batch)
        sqs_message_count += len(sqs_messages_batch)

    logger.info(f"Processed {pdf_count} PDFs, skipped {skipped_count}, sent {sqs_message_count} SQS messages")

    return pdf_count, sqs_message_count, skipped_count


def download_and_process_individual_pdf(doc_id: str, year: int, filing_type: str, skip_existing: bool):
    """Download individual PDF and process upload."""
    url = f"{HOUSE_FD_BASE_URL}/{year}/{doc_id}.pdf"
    
    # Check if exists first to avoid download
    s3_key = f"{S3_BRONZE_PREFIX}/house/financial/year={year}/filing_type={filing_type}/pdfs/{doc_id}.pdf"
    if skip_existing:
        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
            return "skipped"
        except ClientError:
            pass

    try:
        session = _requests_session()
        response = session.get(url, timeout=30)
        if response.status_code == 200:
            return process_pdf_upload(
                doc_id, year, response.content, filing_type, f"{doc_id}.pdf", False
            )
        else:
            logger.warning(f"Failed to download {url}: {response.status_code}")
            return None
    except Exception as e:
        logger.warning(f"Error downloading {url}: {e}")
        return None


def process_pdf_upload(doc_id: str, year: int, pdf_data: bytes, filing_type: str, filename: str, skip_existing: bool):
    """Process PDF upload to S3 and return SQS message dict."""
    s3_key = f"{S3_BRONZE_PREFIX}/house/financial/year={year}/filing_type={filing_type}/pdfs/{doc_id}.pdf"

    if skip_existing:
        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
            return "skipped"
        except ClientError:
            pass

    # Calculate quality score
    page_count = 0
    has_text = False
    try:
        import pypdf
        pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_data))
        page_count = len(pdf_reader.pages)
        if page_count > 0:
            text = pdf_reader.pages[0].extract_text()
            if text and len(text.strip()) > 50:
                has_text = True
    except Exception as e:
        logger.warning(f"Failed to analyze PDF {filename}: {e}")

    quality_score = calculate_quality_score(has_text, page_count, str(year), "Unknown")

    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=pdf_data,
        Metadata={
            "doc_id": doc_id,
            "year": str(year),
            "source_filename": filename,
            "filing_type": filing_type,
            "quality_score": str(quality_score),
            "page_count": str(page_count),
            "has_text_layer": str(has_text).lower(),
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
        },
        ContentType="application/pdf",
        Tagging=f"doc_id={doc_id}&year={year}&filing_type={filing_type}"
    )

    return {
        "Id": doc_id,
        "MessageBody": json.dumps(
            {
                "doc_id": doc_id,
                "year": year,
                "s3_pdf_key": s3_key,
                "filing_type": filing_type
            }
        ),
    }


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
