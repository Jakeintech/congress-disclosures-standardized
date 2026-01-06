"""PDF analyzer to detect template type and extraction format.

This module determines:
1. Template type (Form A, Form B, PTR, etc.) from PDF content
2. PDF format (text-extractable vs image-based)
3. Per-page format (for hybrid PDFs)
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pypdf import PdfReader
import io

logger = logging.getLogger(__name__)


class TemplateType(str, Enum):
    """Known form templates."""
    FORM_A = "Form A"  # Annual and Termination filers
    FORM_B = "Form B"  # New Members, Candidates, New Employees
    PTR = "PTR"  # Periodic Transaction Report
    UNKNOWN = "Unknown"


class PDFFormat(str, Enum):
    """PDF extraction format."""
    TEXT = "text"  # Text-extractable
    IMAGE = "image"  # Requires OCR
    HYBRID = "hybrid"  # Mix of text and image pages


class PDFAnalyzer:
    """Analyzes PDF to determine template type and optimal extraction strategy."""

    # Signature phrases that identify template types
    TEMPLATE_MARKERS = {
        TemplateType.FORM_A: [
            "For Use by Annual and Termination Filers",
            "FORM A",
            "Annual Report",
            "Termination Report"
        ],
        TemplateType.FORM_B: [
            "For Use by New Members, Candidates, and New Employees",
            "FORM B",
            "Candidate Report",
            "New Member"
        ],
        TemplateType.PTR: [
            "PERIODIC TRANSACTION REPORT",
            "PTR",
            "Type of Transaction",
            "Purchase Sale Exchange",
            "AMOUNT OF TRANSACTION"
        ]
    }

    # Minimum text lines to consider a page "text-extractable"
    MIN_TEXT_LINES_PER_PAGE = 10

    def __init__(self, pdf_path: Optional[str] = None, pdf_bytes: Optional[bytes] = None):
        """Initialize analyzer with PDF file path or bytes.

        Args:
            pdf_path: Path to PDF file
            pdf_bytes: PDF content as bytes
        """
        if pdf_path:
            self.reader = PdfReader(pdf_path)
        elif pdf_bytes:
            self.reader = PdfReader(io.BytesIO(pdf_bytes))
        else:
            raise ValueError("Must provide either pdf_path or pdf_bytes")

        self.page_count = len(self.reader.pages)
        self._full_text = None
        self._page_texts = None

    def extract_all_text(self) -> str:
        """Extract all text from PDF."""
        if self._full_text is None:
            texts = []
            for page in self.reader.pages:
                try:
                    texts.append(page.extract_text())
                except Exception as e:
                    logger.warning(f"Failed to extract text from page: {e}")
                    texts.append("")
            self._full_text = "\n".join(texts)
        return self._full_text

    def extract_page_texts(self) -> List[str]:
        """Extract text from each page separately."""
        if self._page_texts is None:
            self._page_texts = []
            for i, page in enumerate(self.reader.pages):
                try:
                    text = page.extract_text()
                    self._page_texts.append(text)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {i}: {e}")
                    self._page_texts.append("")
        return self._page_texts

    def detect_template_type(self) -> TemplateType:
        """Detect which form template this PDF uses.

        Returns:
            TemplateType enum value
        """
        full_text = self.extract_all_text()

        # Score each template based on marker presence
        scores = {template: 0 for template in TemplateType}

        for template, markers in self.TEMPLATE_MARKERS.items():
            for marker in markers:
                if marker.lower() in full_text.lower():
                    scores[template] += 1

        # Return template with highest score
        max_score = max(scores.values())
        if max_score == 0:
            logger.warning("Could not detect template type from PDF content")
            return TemplateType.UNKNOWN

        detected = max(scores, key=scores.get)
        logger.info(f"Detected template type: {detected} (score: {scores[detected]})")
        return detected

    def detect_pdf_format(self) -> PDFFormat:
        """Detect if PDF is text-extractable, image-based, or hybrid.

        Returns:
            PDFFormat enum value
        """
        page_texts = self.extract_page_texts()

        text_pages = 0
        image_pages = 0

        for page_text in page_texts:
            # Count non-empty lines
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            line_count = len(lines)

            if line_count >= self.MIN_TEXT_LINES_PER_PAGE:
                text_pages += 1
            else:
                image_pages += 1

        logger.info(f"PDF format analysis: {text_pages} text pages, {image_pages} image pages")

        if text_pages == self.page_count:
            return PDFFormat.TEXT
        elif image_pages == self.page_count:
            return PDFFormat.IMAGE
        else:
            return PDFFormat.HYBRID

    def analyze_page_formats(self) -> List[PDFFormat]:
        """Analyze format of each page individually.

        Returns:
            List of PDFFormat for each page
        """
        page_texts = self.extract_page_texts()
        formats = []

        for page_text in page_texts:
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            line_count = len(lines)

            if line_count >= self.MIN_TEXT_LINES_PER_PAGE:
                formats.append(PDFFormat.TEXT)
            else:
                formats.append(PDFFormat.IMAGE)

        return formats

    def analyze(self) -> Dict:
        """Perform complete analysis of PDF.

        Returns:
            Dict with:
                - template_type: TemplateType
                - pdf_format: PDFFormat
                - page_count: int
                - page_formats: List[PDFFormat]
                - text_extractable: bool
                - requires_ocr: bool
        """
        template_type = self.detect_template_type()
        pdf_format = self.detect_pdf_format()
        page_formats = self.analyze_page_formats()

        analysis = {
            "template_type": template_type,
            "pdf_format": pdf_format,
            "page_count": self.page_count,
            "page_formats": page_formats,
            "text_extractable": pdf_format in [PDFFormat.TEXT, PDFFormat.HYBRID],
            "requires_ocr": pdf_format in [PDFFormat.IMAGE, PDFFormat.HYBRID],
        }

        logger.info(f"PDF Analysis complete: {analysis}")
        return analysis

    @staticmethod
    def quick_detect(pdf_path: Optional[str] = None, pdf_bytes: Optional[bytes] = None) -> Tuple[TemplateType, PDFFormat]:
        """Quick detection of template and format.

        Args:
            pdf_path: Path to PDF file
            pdf_bytes: PDF content as bytes

        Returns:
            Tuple of (TemplateType, PDFFormat)
        """
        analyzer = PDFAnalyzer(pdf_path=pdf_path, pdf_bytes=pdf_bytes)
        return analyzer.detect_template_type(), analyzer.detect_pdf_format()
