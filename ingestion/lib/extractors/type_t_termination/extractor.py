"""Termination (Type T) extractor.

Extracts data from Termination Reports.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..type_a_b_annual.extractor import TypeABAnnualExtractor

logger = logging.getLogger(__name__)


class TypeTTerminationExtractor(TypeABAnnualExtractor):
    """Extract structured data from Termination Reports (Type T)."""

    def __init__(self):
        """Initialize the extractor."""
        super().__init__()
        self.extraction_version = "1.0.0"

    def extract_from_text(self, text: str, pdf_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract Termination Report data from text (regex-based).

        Args:
            text: Extracted text from PDF
            pdf_properties: Optional PDF metadata

        Returns:
            Structured data for termination report
        """
        logger.info("Extracting Termination Report data from text")
        
        # Use parent class to extract standard fields (schedules, filer info, etc.)
        result = super().extract_from_text(text, pdf_properties)
        
        # Override filing type
        result["filing_type"] = "T"
        result["report_type"]["filing_type"] = "T"
        
        # Extract termination date
        termination_date = self._extract_termination_date_regex(text)
        result["termination_date"] = termination_date
        
        # Add termination date to metadata if found
        if termination_date:
            result["metadata"] = result.get("metadata", {})
            result["metadata"]["termination_date"] = termination_date

        return result

    def _extract_termination_date_regex(self, text: str) -> Optional[str]:
        """Extract termination date using regex."""
        # Look for "Filing Date" or "Termination Date"
        match = re.search(r'(?:Filing|Termination)\s*Date:\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
