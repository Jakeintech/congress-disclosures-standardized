"""
Direct Text Extractor

Extracts text directly from PDF using pypdf (fast, free, preferred method).
"""

import logging
import time
from typing import Union
from io import BytesIO
from pypdf import PdfReader

from .text_extraction_strategy import TextExtractionStrategy
from .extraction_result import ExtractionResult

logger = logging.getLogger(__name__)


class DirectTextExtractor(TextExtractionStrategy):
    """Extract text directly from PDF using pypdf."""

    def __init__(self):
        """Initialize the direct text extractor."""
        self.name = "direct_text"

    def get_strategy_name(self) -> str:
        """Return strategy identifier."""
        return self.name

    def get_priority(self) -> int:
        """Highest priority - try this first."""
        return 0

    def can_handle(self, pdf_source: Union[str, bytes]) -> bool:
        """
        Check if PDF can be processed.

        Direct text extraction can attempt any PDF, but works best on text-based PDFs.
        """
        try:
            reader = self._get_reader(pdf_source)
            return len(reader.pages) > 0
        except Exception as e:
            logger.warning(f"Cannot handle PDF: {e}")
            return False

    def estimate_cost(self, pdf_source: Union[str, bytes]) -> float:
        """Direct text extraction is free."""
        return 0.0

    def extract_text(self, pdf_source: Union[str, bytes]) -> ExtractionResult:
        """
        Extract text from PDF using pypdf.

        Args:
            pdf_source: Either file path or PDF bytes

        Returns:
            ExtractionResult with extracted text and metadata
        """
        start_time = time.time()

        try:
            # Get PDF reader
            reader = self._get_reader(pdf_source)
            page_count = len(reader.pages)

            logger.info(f"Extracting text from {page_count} pages using pypdf")

            # Extract text from all pages
            text_pages = []
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    text_pages.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {i+1}: {e}")
                    text_pages.append("")

            # Combine all pages
            full_text = "\n\n".join(text_pages)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(full_text, text_pages)

            # Calculate confidence score
            confidence = self._calculate_confidence(full_text, quality_metrics)

            # Build result
            result = ExtractionResult(
                text=full_text,
                confidence_score=confidence,
                extraction_method="direct_text",
                strategy_name=self.name,
                page_count=page_count,
                character_count=len(full_text),
                word_count=len(full_text.split()),
                processing_time_seconds=processing_time,
                estimated_cost_usd=0.0,
                quality_metrics=quality_metrics
            )

            # Add warnings and recommendations
            if confidence < 0.5:
                result.add_warning("Low confidence - document may be image-based")
                result.add_recommendation("Consider using OCR extraction")

            if quality_metrics.get("avg_chars_per_page", 0) < 50:
                result.add_warning("Very little text extracted per page")
                result.add_recommendation("Document may be scanned image")

            logger.info(f"Direct text extraction complete: {len(full_text)} chars, "
                       f"confidence={confidence:.2f}, time={processing_time:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Direct text extraction failed: {e}")
            # Return empty result with error
            return ExtractionResult(
                text="",
                confidence_score=0.0,
                extraction_method="direct_text",
                strategy_name=self.name,
                page_count=0,
                character_count=0,
                word_count=0,
                processing_time_seconds=time.time() - start_time,
                estimated_cost_usd=0.0,
                quality_metrics={"error": str(e)},
                warnings=[f"Extraction failed: {e}"],
                recommendations=["Try OCR extraction"]
            )

    def _get_reader(self, pdf_source: Union[str, bytes]) -> PdfReader:
        """Get PdfReader from either file path or bytes."""
        if isinstance(pdf_source, bytes):
            return PdfReader(BytesIO(pdf_source))
        else:
            return PdfReader(pdf_source)

    def _calculate_quality_metrics(self, full_text: str, text_pages: list) -> dict:
        """Calculate quality metrics for extracted text."""
        metrics = {
            "total_characters": len(full_text),
            "total_words": len(full_text.split()),
            "page_count": len(text_pages),
            "avg_chars_per_page": len(full_text) / len(text_pages) if text_pages else 0,
            "empty_pages": sum(1 for page in text_pages if len(page.strip()) < 10),
            "non_empty_pages": sum(1 for page in text_pages if len(page.strip()) >= 10),
        }

        # Check for expected patterns
        metrics["has_dates"] = bool(self._has_date_pattern(full_text))
        metrics["has_dollar_amounts"] = "$" in full_text
        metrics["has_names"] = bool(self._has_name_pattern(full_text))

        return metrics

    def _calculate_confidence(self, text: str, metrics: dict) -> float:
        """
        Calculate confidence score based on extracted text quality.

        Confidence factors:
        - Text length
        - Characters per page
        - Presence of expected patterns (dates, names, amounts)
        - Ratio of printable characters
        """
        confidence = 0.0

        # Factor 1: Text length (0-0.3)
        if len(text) > 1000:
            confidence += 0.3
        elif len(text) > 500:
            confidence += 0.2
        elif len(text) > 100:
            confidence += 0.1

        # Factor 2: Characters per page (0-0.3)
        avg_chars_per_page = metrics.get("avg_chars_per_page", 0)
        if avg_chars_per_page > 500:
            confidence += 0.3
        elif avg_chars_per_page > 200:
            confidence += 0.2
        elif avg_chars_per_page > 50:
            confidence += 0.1

        # Factor 3: Expected patterns (0-0.3)
        pattern_score = 0.0
        if metrics.get("has_dates"):
            pattern_score += 0.1
        if metrics.get("has_dollar_amounts"):
            pattern_score += 0.1
        if metrics.get("has_names"):
            pattern_score += 0.1
        confidence += pattern_score

        # Factor 4: Page coverage (0-0.1)
        if metrics.get("page_count", 0) > 0:
            coverage = metrics.get("non_empty_pages", 0) / metrics["page_count"]
            confidence += coverage * 0.1

        return min(confidence, 1.0)

    def _has_date_pattern(self, text: str) -> bool:
        """Check if text contains date patterns."""
        import re
        # Match common date formats: MM/DD/YYYY, MM-DD-YYYY, etc.
        date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        return bool(re.search(date_pattern, text))

    def _has_name_pattern(self, text: str) -> bool:
        """Check if text contains name patterns."""
        import re
        # Match capitalized words (potential names)
        name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        matches = re.findall(name_pattern, text)
        return len(matches) > 3  # At least a few name-like patterns
