"""Base extractor with common extraction utilities.

Provides format-agnostic extraction with text-first, OCR-fallback strategy.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from .pdf_analyzer import PDFAnalyzer, PDFFormat, TemplateType

logger = logging.getLogger(__name__)


class BaseExtractor:
    """Base class for all extractors with common utilities."""

    def __init__(self, pdf_path: Optional[str] = None, pdf_bytes: Optional[bytes] = None):
        """Initialize extractor.

        Args:
            pdf_path: Path to PDF file
            pdf_bytes: PDF content as bytes
        """
        self.pdf_path = pdf_path
        self.pdf_bytes = pdf_bytes

        # Analyze PDF (only if provided)
        if pdf_path or pdf_bytes:
            self.analyzer = PDFAnalyzer(pdf_path=pdf_path, pdf_bytes=pdf_bytes)
            self.analysis = self.analyzer.analyze()

            self.template_type = self.analysis["template_type"]
            self.pdf_format = self.analysis["pdf_format"]
            self.requires_ocr = self.analysis["requires_ocr"]

            logger.info(f"Initialized extractor: template={self.template_type}, format={self.pdf_format}")
        else:
            # Text-only mode (no PDF provided)
            self.analyzer = None
            self.analysis = None
            self.template_type = None
            self.pdf_format = None
            self.requires_ocr = False
            logger.info("Initialized extractor in text-only mode")

        # Cache extracted text
        self._text = None

    @property
    def text(self) -> str:
        """Get extracted text (cached)."""
        if self._text is None:
            if self.pdf_format == PDFFormat.IMAGE:
                # For image PDFs, need OCR
                logger.warning("PDF is image-based, text extraction will be limited")
                self._text = ""
            else:
                self._text = self.analyzer.extract_all_text()
        return self._text

    def extract_with_fallback(self) -> Dict[str, Any]:
        """Extract with text-first, OCR-fallback strategy.

        Returns:
            Extracted structured data
        """
        try:
            # Try text extraction first
            if self.pdf_format in [PDFFormat.TEXT, PDFFormat.HYBRID]:
                logger.info("Attempting text-based extraction")
                result = self.extract_from_text(self.text)
                result["extraction_metadata"]["extraction_method"] = "regex"
                result["extraction_metadata"]["pdf_type"] = self.pdf_format.value
                return result
        except Exception as e:
            logger.warning(f"Text extraction failed: {e}")

        # Fallback to OCR if needed or text failed
        if self.requires_ocr:
            logger.info("Falling back to OCR extraction")
            try:
                result = self.extract_from_ocr()
                result["extraction_metadata"]["extraction_method"] = "ocr_fallback"
                result["extraction_metadata"]["pdf_type"] = self.pdf_format.value
                return result
            except NotImplementedError:
                logger.error("OCR extraction not implemented")
                raise
            except Exception as e:
                logger.error(f"OCR extraction failed: {e}")
                raise

        raise RuntimeError("All extraction methods failed")

    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """Extract from text-based PDF. Override in subclasses.

        Args:
            text: Extracted text from PDF

        Returns:
            Structured data dict
        """
        raise NotImplementedError("Subclass must implement extract_from_text")

    def extract_from_ocr(self) -> Dict[str, Any]:
        """Extract from image-based PDF using OCR.

        Returns:
            Structured data dict
        """
        try:
            import pytesseract
            from pdf2image import convert_from_path
        except ImportError as e:
            logger.error(f"OCR dependencies not installed: {e}")
            logger.error("Install with: pip install pytesseract pdf2image")
            raise NotImplementedError("OCR extraction requires pytesseract and pdf2image")

        logger.info("Performing OCR extraction on PDF...")

        try:
            # Convert PDF pages to images
            if self.pdf_path:
                images = convert_from_path(self.pdf_path, dpi=300)
            elif self.pdf_bytes:
                from pdf2image import convert_from_bytes
                images = convert_from_bytes(self.pdf_bytes, dpi=300)
            else:
                raise ValueError("No PDF path or bytes provided for OCR")
                
            logger.info(f"Converted {len(images)} PDF pages to images")

            # OCR each page
            ocr_text_pages = []
            # Initialize preprocessor
            try:
                from ..extraction.image_preprocessor import ImagePreprocessor
                preprocessor = ImagePreprocessor()
                logger.info("Image preprocessor initialized")
            except ImportError as e:
                logger.warning(f"Could not import ImagePreprocessor: {e}")
                preprocessor = None

            for i, image in enumerate(images, 1):
                logger.info(f"OCR processing page {i}/{len(images)}...")
                
                # Preprocess image if available
                if preprocessor:
                    try:
                        image = preprocessor.preprocess(image)
                    except Exception as e:
                        logger.warning(f"Preprocessing failed for page {i}: {e}")

                text = pytesseract.image_to_string(image, lang='eng')
                ocr_text_pages.append(text)

            # Combine all pages
            full_text = "\n\n".join(ocr_text_pages)
            self._text = full_text # Store OCR text for debugging/access
            logger.info(f"OCR extracted {len(full_text)} characters total")

            # Use the same text extraction method, just with OCR'd text
            return self.extract_from_text(full_text, pdf_properties={
                "page_count": len(images),
                "extraction_method": "ocr",
                "pdf_type": "image"
            })

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise

    # ============================================================
    # Common Extraction Utilities
    # ============================================================

    def extract_date(self, text: str, pattern: str = r"(\d{1,2})/(\d{1,2})/(\d{2,4})") -> Optional[str]:
        """Extract date and normalize to YYYY-MM-DD.

        Args:
            text: Text to search
            pattern: Regex pattern for date

        Returns:
            Date string in YYYY-MM-DD format or None
        """
        match = re.search(pattern, text)
        if not match:
            return None

        month, day, year = match.groups()

        # Handle 2-digit years
        if len(year) == 2:
            year_int = int(year)
            year = f"20{year}" if year_int < 50 else f"19{year}"

        try:
            # Validate date
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            logger.warning(f"Invalid date: {month}/{day}/{year}")
            return None

    def extract_amount_range(self, text: str) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        """Parse amount range and normalize to schema format.

        Schema format: '$1,001-$15,000' (no spaces around dash)

        Args:
            text: Text containing amount range

        Returns:
            Tuple of (low, high, normalized_text)
        """
        # Pattern: $X,XXX - $Y,YYY or $X,XXX-$Y,YYY (with or without $ and spaces)
        pattern = r'\$?([\d,]+)\s*[-–]\s*\$?([\d,]+)'
        match = re.search(pattern, text)

        if not match:
            # Try "Over $X" pattern
            over_match = re.search(r'Over\s+\$?([\d,]+)', text, re.IGNORECASE)
            if over_match:
                low = int(over_match.group(1).replace(',', ''))
                # Normalize to schema format
                normalized = f"Over ${low:,}"
                return (low, None, normalized)
            return (None, None, None)

        low_str, high_str = match.groups()
        low = int(low_str.replace(',', ''))
        high = int(high_str.replace(',', ''))

        # Normalize to schema format: $X,XXX - $Y,YYY (with spaces)
        normalized = f"${low:,} - ${high:,}"

        return (low, high, normalized)

    def detect_checkbox(self, text: str, options: List[str], context_window: int = 50) -> Optional[str]:
        """Detect which checkbox is marked in text.

        Args:
            text: Text to search
            options: List of possible checkbox values
            context_window: Characters around option to search for marks

        Returns:
            Selected option or None
        """
        checkbox_markers = ['☒', '[X]', '[x]', '(X)', '(x)', '☑']

        for option in options:
            # Find option in text
            option_pos = text.lower().find(option.lower())
            if option_pos == -1:
                continue

            # Check context around option for checkbox markers
            start = max(0, option_pos - context_window)
            end = min(len(text), option_pos + len(option) + context_window)
            context = text[start:end]

            # Check if any marker is near this option
            for marker in checkbox_markers:
                if marker in context:
                    return option

            # Check for "X" near option (common in text PDFs)
            x_pattern = r'\bX\b'
            if re.search(x_pattern, context):
                return option

        return None

    def extract_owner_code(self, text: str) -> Optional[str]:
        """Extract owner code (SP, DC, JT) from text.

        Args:
            text: Text to search

        Returns:
            Owner code or None
        """
        # Look for standalone codes
        codes = ['SP', 'DC', 'JT']
        for code in codes:
            # Match code as standalone word
            if re.search(rf'\b{code}\b', text):
                return code
        return None

    def extract_multi_line_field(self, text: str, start_marker: str, end_marker: Optional[str] = None,
                                  max_lines: int = 10) -> Optional[str]:
        """Extract multi-line field between markers.

        Args:
            text: Full text to search
            start_marker: Starting marker (e.g., "Description:")
            end_marker: Ending marker (e.g., "Schedule") or None for next section
            max_lines: Maximum lines to extract

        Returns:
            Extracted field content
        """
        lines = text.split('\n')
        start_idx = None

        # Find start marker
        for i, line in enumerate(lines):
            if start_marker in line:
                start_idx = i + 1
                break

        if start_idx is None:
            return None

        # Extract lines until end marker or max_lines
        result_lines = []
        for i in range(start_idx, min(start_idx + max_lines, len(lines))):
            line = lines[i].strip()

            # Stop at end marker
            if end_marker and end_marker in line:
                break

            # Stop at empty line (unless it's the first)
            if not line and result_lines:
                break

            if line:
                result_lines.append(line)

        return '\n'.join(result_lines) if result_lines else None

    def parse_table_section(self, text: str, section_header: str) -> List[Dict[str, Any]]:
        """Parse tabular section from text.

        Args:
            text: Full text
            section_header: Header marking start of section (e.g., "Schedule A")

        Returns:
            List of row dicts
        """
        # Find section
        section_match = re.search(rf'{section_header}.*?\n(.*?)(?=\n\s*Schedule|\n\s*S\s+[A-Z]|\Z)',
                                 text, re.DOTALL | re.IGNORECASE)

        if not section_match:
            logger.debug(f"Section not found: {section_header}")
            return []

        section_text = section_match.group(1)

        # This is a basic implementation - subclasses should override with specific parsing
        logger.warning(f"Using basic table parsing for {section_header}")
        return []

    def create_extraction_metadata(self, confidence: float = 1.0,
                                   method: Optional[str] = None,
                                   field_confidence: Optional[Dict[str, float]] = None,
                                   extraction_attempts: Optional[List[Dict[str, Any]]] = None,
                                   data_completeness: Optional[Dict[str, Any]] = None,
                                   processing_time: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Create comprehensive extraction metadata for full audit trail.

        Args:
            confidence: Overall confidence score (0-1)
            method: Extraction method override
            field_confidence: Per-field confidence scores
            extraction_attempts: History of extraction attempts
            data_completeness: Metrics about extraction completeness
            processing_time: Performance metrics breakdown

        Returns:
            Comprehensive metadata dict with full audit trail
        """
        import os

        # Get PDF properties from analyzer
        pdf_properties = {}
        if self.pdf_path and os.path.exists(self.pdf_path):
            pdf_properties["file_size_bytes"] = os.path.getsize(self.pdf_path)

        # Get PDF metadata from pypdf
        if hasattr(self.analyzer, 'reader') and self.analyzer.reader:
            reader = self.analyzer.reader
            pdf_properties["page_count"] = len(reader.pages)
            pdf_properties["is_encrypted"] = reader.is_encrypted

            # Try to get PDF metadata
            if hasattr(reader, 'metadata') and reader.metadata:
                metadata = reader.metadata
                if hasattr(metadata, 'get'):
                    # PDF version
                    if hasattr(reader, 'pdf_header'):
                        pdf_properties["pdf_version"] = reader.pdf_header

                    # Creation/modification dates
                    if '/CreationDate' in metadata:
                        pdf_properties["creation_date"] = str(metadata['/CreationDate'])
                    if '/ModDate' in metadata:
                        pdf_properties["modification_date"] = str(metadata['/ModDate'])
                    if '/Producer' in metadata:
                        pdf_properties["producer"] = str(metadata['/Producer'])

        result = {
            "extraction_method": method or ("regex" if self.pdf_format == PDFFormat.TEXT else "ocr"),
            "extraction_timestamp": datetime.utcnow().isoformat() + "Z",
            "extraction_version": "1.0.0",
            "confidence_score": confidence,
            "pdf_type": self.pdf_format.value if self.pdf_format else "text_only",
            "requires_manual_review": confidence < 0.85
        }

        # Add optional comprehensive fields if provided
        if field_confidence:
            result["field_confidence"] = field_confidence

        if pdf_properties:
            result["pdf_properties"] = pdf_properties

        if extraction_attempts:
            result["extraction_attempts"] = extraction_attempts

        if data_completeness:
            result["data_completeness"] = data_completeness

        if processing_time:
            result["processing_time"] = processing_time

        return result

    def validate_required_fields(self, data: Dict, required_fields: List[str]) -> bool:
        """Validate that required fields are present.

        Args:
            data: Extracted data dict
            required_fields: List of required field paths (e.g., "filer_info.name")

        Returns:
            True if all required fields present
        """
        for field_path in required_fields:
            parts = field_path.split('.')
            current = data

            for part in parts:
                if isinstance(current, dict):
                    if part not in current or current[part] is None:
                        logger.warning(f"Missing required field: {field_path}")
                        return False
                    current = current[part]
                else:
                    logger.warning(f"Invalid field path: {field_path}")
                    return False

        return True
