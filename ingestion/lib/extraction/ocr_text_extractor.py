"""
OCR Text Extractor

Extracts text from image-based PDFs using pytesseract with image preprocessing.
"""

import logging
import time
from typing import Union, List
from io import BytesIO

from .text_extraction_strategy import TextExtractionStrategy
from .extraction_result import ExtractionResult
from .image_preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


class OCRTextExtractor(TextExtractionStrategy):
    """Extract text from images using pytesseract with preprocessing."""

    def __init__(self, preprocessor: ImagePreprocessor = None, dpi: int = 300):
        """
        Initialize OCR text extractor.

        Args:
            preprocessor: ImagePreprocessor instance (creates default if None)
            dpi: DPI for PDF to image conversion (default: 300)
        """
        self.name = "ocr_tesseract"
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.dpi = dpi

        # Lazy load dependencies
        self._pytesseract = None
        self._pdf2image = None

    @property
    def pytesseract(self):
        """Lazy load pytesseract."""
        if self._pytesseract is None:
            try:
                import pytesseract
                self._pytesseract = pytesseract
            except ImportError:
                logger.error("pytesseract not installed")
                raise ImportError("pytesseract required. Install with: pip install pytesseract")
        return self._pytesseract

    @property
    def pdf2image(self):
        """Lazy load pdf2image."""
        if self._pdf2image is None:
            try:
                from pdf2image import convert_from_path, convert_from_bytes
                self._pdf2image = {
                    'convert_from_path': convert_from_path,
                    'convert_from_bytes': convert_from_bytes
                }
            except ImportError:
                logger.error("pdf2image not installed")
                raise ImportError("pdf2image required. Install with: pip install pdf2image")
        return self._pdf2image

    def get_strategy_name(self) -> str:
        """Return strategy identifier."""
        return self.name

    def get_priority(self) -> int:
        """Lower priority - use as fallback."""
        return 50

    def can_handle(self, pdf_source: Union[str, bytes]) -> bool:
        """OCR can handle any PDF."""
        return True

    def estimate_cost(self, pdf_source: Union[str, bytes]) -> float:
        """
        OCR is free (pytesseract) but CPU-intensive.

        Returns estimated processing time as proxy for "cost".
        """
        try:
            # Estimate based on page count
            # (rough estimate: 3-5 seconds per page)
            page_count = self._get_page_count(pdf_source)
            estimated_time_seconds = page_count * 4  # Average 4 seconds per page
            return estimated_time_seconds

        except Exception:
            return 60.0  # Default estimate

    def extract_text(self, pdf_source: Union[str, bytes]) -> ExtractionResult:
        """
        Extract text using OCR with image preprocessing.

        Pipeline:
        1. Convert PDF pages to images (pdf2image)
        2. Preprocess each image (ImagePreprocessor)
        3. Run OCR on preprocessed images (pytesseract)
        4. Combine results

        Args:
            pdf_source: Either file path or PDF bytes

        Returns:
            ExtractionResult with OCR'd text and metadata
        """
        start_time = time.time()

        try:
            logger.info("Starting OCR extraction")

            # Step 1: Convert PDF to images
            images = self._pdf_to_images(pdf_source)
            page_count = len(images)

            logger.info(f"Converted PDF to {page_count} images at {self.dpi} DPI")

            # Step 2 & 3: Preprocess and OCR each page
            text_pages = []
            page_quality_metrics = []

            for i, image in enumerate(images, 1):
                logger.info(f"OCR processing page {i}/{page_count}")

                # Detect quality issues before preprocessing
                quality_before = self.preprocessor.detect_quality_issues(image)

                # Preprocess image
                preprocessed = self.preprocessor.preprocess(image)

                # Run OCR
                page_text = self.pytesseract.image_to_string(preprocessed, lang='eng')
                text_pages.append(page_text)

                # Track quality metrics
                page_quality_metrics.append({
                    "page": i,
                    "quality_before": quality_before,
                    "characters_extracted": len(page_text)
                })

            # Step 4: Combine all pages
            full_text = "\n\n".join(text_pages)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(
                full_text, text_pages, page_quality_metrics
            )

            # Calculate confidence
            confidence = self._calculate_confidence(full_text, quality_metrics)

            # Build result
            result = ExtractionResult(
                text=full_text,
                confidence_score=confidence,
                extraction_method="ocr",
                strategy_name=self.name,
                page_count=page_count,
                character_count=len(full_text),
                word_count=len(full_text.split()),
                processing_time_seconds=processing_time,
                estimated_cost_usd=0.0,  # Free (but CPU-intensive)
                quality_metrics=quality_metrics
            )

            # Add warnings and recommendations
            if processing_time > 30:
                result.add_warning(f"OCR took {processing_time:.1f}s - document is large")

            avg_chars_per_page = len(full_text) / page_count if page_count > 0 else 0
            if avg_chars_per_page < 100:
                result.add_warning("Very little text extracted - OCR may have struggled")
                result.add_recommendation("Document may need manual review")

            if confidence < 0.6:
                result.add_warning("Low OCR confidence")
                result.add_recommendation("Consider using premium OCR (AWS Textract)")

            logger.info(f"OCR extraction complete: {len(full_text)} chars, "
                       f"confidence={confidence:.2f}, time={processing_time:.1f}s")

            return result

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}", exc_info=True)
            return ExtractionResult(
                text="",
                confidence_score=0.0,
                extraction_method="ocr",
                strategy_name=self.name,
                page_count=0,
                character_count=0,
                word_count=0,
                processing_time_seconds=time.time() - start_time,
                estimated_cost_usd=0.0,
                quality_metrics={"error": str(e)},
                warnings=[f"OCR extraction failed: {e}"],
                recommendations=["Try premium OCR service or manual review"]
            )

    def _pdf_to_images(self, pdf_source: Union[str, bytes]) -> List:
        """Convert PDF to images."""
        if isinstance(pdf_source, bytes):
            return self.pdf2image['convert_from_bytes'](pdf_source, dpi=self.dpi)
        else:
            return self.pdf2image['convert_from_path'](pdf_source, dpi=self.dpi)

    def _get_page_count(self, pdf_source: Union[str, bytes]) -> int:
        """Get PDF page count."""
        try:
            from pypdf import PdfReader
            if isinstance(pdf_source, bytes):
                reader = PdfReader(BytesIO(pdf_source))
            else:
                reader = PdfReader(pdf_source)
            return len(reader.pages)
        except Exception:
            return 1  # Default estimate

    def _calculate_quality_metrics(
        self, full_text: str, text_pages: List[str], page_metrics: List[dict]
    ) -> dict:
        """Calculate OCR quality metrics."""
        metrics = {
            "total_characters": len(full_text),
            "total_words": len(full_text.split()),
            "page_count": len(text_pages),
            "avg_chars_per_page": len(full_text) / len(text_pages) if text_pages else 0,
            "empty_pages": sum(1 for page in text_pages if len(page.strip()) < 10),
            "non_empty_pages": sum(1 for page in text_pages if len(page.strip()) >= 10),
            "dpi": self.dpi,
            "preprocessing_enabled": self.preprocessor.enable_preprocessing
        }

        # Aggregate page quality metrics
        if page_metrics:
            avg_blur = sum(
                p['quality_before'].get('blur_score', 0) for p in page_metrics
            ) / len(page_metrics)
            avg_contrast = sum(
                p['quality_before'].get('contrast_score', 0) for p in page_metrics
            ) / len(page_metrics)

            metrics["avg_image_blur_score"] = avg_blur
            metrics["avg_image_contrast_score"] = avg_contrast

        return metrics

    def _calculate_confidence(self, text: str, metrics: dict) -> float:
        """
        Calculate OCR confidence score.

        Factors:
        - Text length
        - Characters per page
        - Image quality metrics
        - Preprocessing success
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
        avg_chars = metrics.get("avg_chars_per_page", 0)
        if avg_chars > 300:
            confidence += 0.3
        elif avg_chars > 150:
            confidence += 0.2
        elif avg_chars > 50:
            confidence += 0.1

        # Factor 3: Image quality (0-0.2)
        blur_score = metrics.get("avg_image_blur_score", 0)
        if blur_score > 200:  # Very sharp
            confidence += 0.2
        elif blur_score > 100:  # Acceptable
            confidence += 0.1

        # Factor 4: Page coverage (0-0.2)
        if metrics.get("page_count", 0) > 0:
            coverage = metrics.get("non_empty_pages", 0) / metrics["page_count"]
            confidence += coverage * 0.2

        return min(confidence, 1.0)
