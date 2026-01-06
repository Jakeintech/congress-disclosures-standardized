"""PDF text extraction utilities using local processing only."""

import logging
import time
from pathlib import Path
from typing import Dict, Union

from pypdf import PdfReader

logger = logging.getLogger(__name__)


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

def extract_text_from_pdf(pdf_path: Union[str, Path]) -> Dict[str, any]:
    """Extract text from PDF using local parsing only.

    The function prefers embedded text and falls back to pypdf even for
    image-based PDFs (which may result in minimal text). Use downstream OCR
    if `requires_additional_ocr` is True.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dict with extraction results including:
            - pages: int
            - text: str (full text)
            - text_by_page: List[str]
            - extraction_method: str
            - has_embedded_text: bool
            - duration_seconds: float
            - pdf_file_size_bytes: int
            - requires_additional_ocr: bool
    """
    pdf_path = Path(pdf_path)
    file_size = pdf_path.stat().st_size

    logger.info(f"Starting text extraction: {pdf_path.name} ({file_size} bytes)")

    has_text = detect_has_text_layer(pdf_path)
    result = extract_text_pypdf(pdf_path)

    # Normalize metadata for downstream consumers
    result["has_embedded_text"] = has_text
    result["extraction_method"] = "pypdf" if has_text else "pypdf-no-text-layer"
    result["requires_additional_ocr"] = not has_text and len(result["text"].strip()) == 0
    result["pdf_file_size_bytes"] = file_size
    result["pdf_filename"] = pdf_path.name

    if result["requires_additional_ocr"]:
        logger.info(
            "PDF appears to be image-based and produced minimal text; flagging for OCR reprocessing."
        )

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
