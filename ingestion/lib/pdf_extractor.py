"""PDF text extraction utilities with pypdf and AWS Textract support."""

import logging
import time
from pathlib import Path
from typing import Dict, Optional, Union

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from pypdf import PdfReader

logger = logging.getLogger(__name__)

# Configure boto3 for Textract
BOTO_CONFIG = Config(
    retries={"max_attempts": 3, "mode": "adaptive"},
    read_timeout=300,
    connect_timeout=10,
)

# Initialize Textract client
textract_client = None


def get_textract_client():
    """Get or create Textract client.

    Returns:
        boto3 Textract client
    """
    global textract_client
    if textract_client is None:
        textract_client = boto3.client("textract", config=BOTO_CONFIG)
    return textract_client


def detect_has_text_layer(pdf_path: Union[str, Path]) -> bool:
    """Detect if PDF has embedded text layer.

    Uses pypdf to sample first few pages and check for text content.

    Args:
        pdf_path: Path to PDF file

    Returns:
        True if PDF has extractable text, False if image-only

    Raises:
        Exception: If PDF cannot be read
    """
    pdf_path = Path(pdf_path)

    try:
        reader = PdfReader(str(pdf_path))
        page_count = len(reader.pages)

        # Sample first 2 pages (or all if fewer)
        sample_size = min(2, page_count)
        total_chars = 0

        for i in range(sample_size):
            page = reader.pages[i]
            text = page.extract_text()
            total_chars += len(text.strip())

        # If we have more than 100 characters, assume it has text layer
        has_text = total_chars > 100

        logger.info(
            f"PDF text detection: {pdf_path.name} - "
            f"{page_count} pages, {total_chars} chars in first {sample_size} pages, "
            f"has_text={has_text}"
        )

        return has_text

    except Exception as e:
        logger.error(f"Failed to detect text layer in {pdf_path}: {e}")
        raise


def extract_text_pypdf(pdf_path: Union[str, Path]) -> Dict[str, any]:
    """Extract text from PDF using pypdf.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dict with keys:
            - pages: int (number of pages)
            - text: str (full text concatenated)
            - text_by_page: List[str] (text per page)
            - extraction_method: str ('pypdf')
            - has_embedded_text: bool (True)

    Raises:
        Exception: If extraction fails
    """
    pdf_path = Path(pdf_path)

    try:
        start_time = time.time()
        reader = PdfReader(str(pdf_path))
        page_count = len(reader.pages)

        text_by_page = []
        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()
            text_by_page.append(page_text)
            logger.debug(f"Extracted {len(page_text)} chars from page {page_num}")

        full_text = "\n\n".join(text_by_page)
        duration = time.time() - start_time

        logger.info(
            f"pypdf extraction complete: {pdf_path.name} - "
            f"{page_count} pages, {len(full_text)} chars, {duration:.2f}s"
        )

        return {
            "pages": page_count,
            "text": full_text,
            "text_by_page": text_by_page,
            "extraction_method": "pypdf",
            "has_embedded_text": True,
            "duration_seconds": duration,
        }

    except Exception as e:
        logger.error(f"pypdf extraction failed for {pdf_path}: {e}")
        raise


def extract_text_textract_sync(pdf_bytes: bytes, max_pages: int = 10) -> Dict[str, any]:
    """Extract text from PDF using AWS Textract (synchronous).

    Suitable for PDFs with <= max_pages pages.

    Args:
        pdf_bytes: PDF file as bytes
        max_pages: Maximum pages to process synchronously

    Returns:
        Dict with extraction results

    Raises:
        ClientError: If Textract API fails
    """
    textract = get_textract_client()

    try:
        start_time = time.time()

        logger.info(f"Starting Textract sync extraction ({len(pdf_bytes)} bytes)")

        response = textract.detect_document_text(Document={"Bytes": pdf_bytes})

        # Parse Textract response
        text_by_page = []
        current_page_text = []
        current_page = 1

        for block in response.get("Blocks", []):
            if block["BlockType"] == "PAGE":
                # Save previous page if exists
                if current_page_text:
                    text_by_page.append("\n".join(current_page_text))
                    current_page_text = []
                current_page = block.get("Page", current_page)

            elif block["BlockType"] == "LINE":
                text = block.get("Text", "")
                current_page_text.append(text)

        # Add last page
        if current_page_text:
            text_by_page.append("\n".join(current_page_text))

        full_text = "\n\n".join(text_by_page)
        duration = time.time() - start_time

        logger.info(
            f"Textract sync extraction complete: "
            f"{len(text_by_page)} pages, {len(full_text)} chars, {duration:.2f}s"
        )

        return {
            "pages": len(text_by_page),
            "text": full_text,
            "text_by_page": text_by_page,
            "extraction_method": "textract-detect-sync",
            "has_embedded_text": False,
            "duration_seconds": duration,
            "textract_response_metadata": response.get("ResponseMetadata", {}),
            "textract_raw_response": response,  # Full raw response for comparison
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"Textract sync extraction failed: {error_code} - {e}")

        # Handle specific error cases
        if error_code == "ProvisionedThroughputExceededException":
            logger.warning("Textract throttled - consider retry with backoff")
        elif error_code == "InvalidParameterException":
            logger.error("Invalid Textract parameters - check PDF format")

        raise


def extract_text_textract_async(
    s3_bucket: str,
    s3_key: str,
    max_wait_seconds: int = 300,
) -> Dict[str, any]:
    """Extract text from PDF using AWS Textract (asynchronous).

    For PDFs with many pages or when sync API times out.
    PDF must be in S3 (Textract requirement).

    Args:
        s3_bucket: S3 bucket containing PDF
        s3_key: S3 key of PDF
        max_wait_seconds: Maximum time to wait for job completion

    Returns:
        Dict with extraction results

    Raises:
        ClientError: If Textract API fails
        TimeoutError: If job doesn't complete in time
    """
    textract = get_textract_client()

    try:
        start_time = time.time()

        logger.info(f"Starting Textract async extraction: s3://{s3_bucket}/{s3_key}")

        # Start async job
        start_response = textract.start_document_text_detection(
            DocumentLocation={
                "S3Object": {
                    "Bucket": s3_bucket,
                    "Name": s3_key,
                }
            }
        )

        job_id = start_response["JobId"]
        logger.info(f"Textract job started: {job_id}")

        # Poll for completion
        pages_text = []
        next_token = None
        job_complete = False

        while time.time() - start_time < max_wait_seconds:
            time.sleep(5)  # Poll every 5 seconds

            get_response = textract.get_document_text_detection(JobId=job_id)
            status = get_response["JobStatus"]

            logger.debug(f"Textract job {job_id} status: {status}")

            if status == "SUCCEEDED":
                # Collect results (may be paginated)
                text_by_page = []
                current_page_text = []

                for block in get_response.get("Blocks", []):
                    if block["BlockType"] == "PAGE":
                        if current_page_text:
                            text_by_page.append("\n".join(current_page_text))
                            current_page_text = []
                    elif block["BlockType"] == "LINE":
                        text = block.get("Text", "")
                        current_page_text.append(text)

                if current_page_text:
                    text_by_page.append("\n".join(current_page_text))

                # Handle pagination if results are large
                next_token = get_response.get("NextToken")
                if next_token:
                    logger.info("Fetching additional pages (NextToken exists)")
                    # Additional pagination would go here if needed
                    # For simplicity, we're assuming single response is enough

                job_complete = True
                break

            elif status == "FAILED":
                error_msg = get_response.get("StatusMessage", "Unknown error")
                raise Exception(f"Textract job failed: {error_msg}")

            elif status == "IN_PROGRESS":
                continue

        if not job_complete:
            raise TimeoutError(
                f"Textract job {job_id} did not complete within {max_wait_seconds}s"
            )

        full_text = "\n\n".join(text_by_page)
        duration = time.time() - start_time

        logger.info(
            "Textract async extraction complete: "
            f"{len(text_by_page)} pages, {len(full_text)} chars, {duration:.2f}s"
        )

        return {
            "pages": len(text_by_page),
            "text": full_text,
            "text_by_page": text_by_page,
            "extraction_method": "textract-detect-async",
            "has_embedded_text": False,
            "duration_seconds": duration,
            "textract_job_id": job_id,
            "textract_raw_response": get_response,  # Full raw response for comparison
        }

    except (ClientError, TimeoutError) as e:
        logger.error(f"Textract async extraction failed: {e}")
        raise


def extract_text_from_pdf(
    pdf_path: Union[str, Path],
    textract_max_pages_sync: int = 10,
    s3_bucket: Optional[str] = None,
    s3_key: Optional[str] = None,
    textract_budget_remaining: Optional[int] = None,
) -> Dict[str, any]:
    """Extract text from PDF using best available method.

    Decision logic:
    1. Check if PDF has embedded text layer
    2. If yes: use pypdf (fast, free)
    3. If no: check Textract budget
       - If budget exhausted: use pypdf anyway, mark for reprocessing
       - If budget available: use AWS Textract
         * If <= max_pages_sync: use sync API
         * If > max_pages_sync: use async API (requires S3 location)

    Args:
        pdf_path: Path to PDF file
        textract_max_pages_sync: Max pages for Textract sync API
        s3_bucket: S3 bucket (required for Textract async)
        s3_key: S3 key (required for Textract async)
        textract_budget_remaining: Pages remaining in monthly Textract budget (None = unlimited)

    Returns:
        Dict with extraction results including:
            - pages: int
            - text: str (full text)
            - text_by_page: List[str]
            - extraction_method: str
            - has_embedded_text: bool
            - duration_seconds: float
            - pdf_file_size_bytes: int
            - requires_textract_reprocessing: bool (True if budget prevented Textract)

    Raises:
        Exception: If extraction fails
    """
    pdf_path = Path(pdf_path)
    file_size = pdf_path.stat().st_size

    logger.info(f"Starting text extraction: {pdf_path.name} ({file_size} bytes)")

    # Step 1: Check for text layer
    has_text = detect_has_text_layer(pdf_path)

    if has_text:
        # Use pypdf (fast and free)
        result = extract_text_pypdf(pdf_path)
        result["requires_textract_reprocessing"] = False
    else:
        # PDF is image-based, check Textract budget
        logger.info(f"PDF is image-based: {pdf_path.name}")

        # Estimate page count (rough heuristic: 50KB per page average)
        estimated_pages = max(1, file_size // (50 * 1024))

        # Check if we have Textract budget remaining
        if textract_budget_remaining is not None and textract_budget_remaining < estimated_pages:
            logger.warning(
                f"Textract budget exhausted ({textract_budget_remaining} pages remaining, "
                f"need {estimated_pages}). Using pypdf fallback, marking for reprocessing."
            )
            # Use pypdf fallback (will extract blank or minimal text)
            result = extract_text_pypdf(pdf_path)
            result["extraction_method"] = "pypdf-budget-limit"
            result["has_embedded_text"] = has_text  # FIX: Preserve detected value, don't hardcode False
            result["requires_textract_reprocessing"] = True
        else:
            # Budget available, use Textract
            logger.info(
                f"Using Textract for {pdf_path.name} "
                f"(est. {estimated_pages} pages, budget: {textract_budget_remaining})"
            )

            # Read PDF bytes
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            if estimated_pages <= textract_max_pages_sync:
                # Use sync API
                result = extract_text_textract_sync(pdf_bytes, textract_max_pages_sync)
            else:
                # Need async API - requires S3 location
                if not s3_bucket or not s3_key:
                    raise ValueError(
                        f"PDF has {estimated_pages} pages (>{textract_max_pages_sync}). "
                        "Async Textract requires s3_bucket and s3_key parameters."
                    )

                result = extract_text_textract_async(s3_bucket, s3_key)

            result["requires_textract_reprocessing"] = False

    # Add file metadata to result
    result["pdf_file_size_bytes"] = file_size
    result["pdf_filename"] = pdf_path.name

    return result


def get_pdf_metadata(pdf_path: Union[str, Path]) -> Dict[str, any]:
    """Get PDF metadata without extracting text.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dict with metadata:
            - pages: int
            - file_size_bytes: int
            - has_embedded_text: bool
            - pdf_version: str
            - encrypted: bool

    Raises:
        Exception: If PDF cannot be read
    """
    pdf_path = Path(pdf_path)

    try:
        reader = PdfReader(str(pdf_path))
        page_count = len(reader.pages)
        file_size = pdf_path.stat().st_size
        has_text = detect_has_text_layer(pdf_path)

        metadata = reader.metadata or {}

        return {
            "pages": page_count,
            "file_size_bytes": file_size,
            "has_embedded_text": has_text,
            "pdf_version": reader.pdf_header,
            "encrypted": reader.is_encrypted,
            "metadata": {
                "title": metadata.get("/Title", ""),
                "author": metadata.get("/Author", ""),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "producer": metadata.get("/Producer", ""),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get PDF metadata for {pdf_path}: {e}")
        raise
