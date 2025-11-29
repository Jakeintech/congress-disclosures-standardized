"""Type X (Extension) extractor.

Extracts structured data from Extension requests.
"""

import logging
import re
from typing import Dict, Any
from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class TypeXExtractor(BaseExtractor):
    """Extract structured data from Extension requests."""

    def extract_from_text(self, text: str, pdf_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract Type X data from text.

        Args:
            text: Extracted text from PDF
            pdf_properties: Optional PDF metadata

        Returns:
            Structured data matching house_fd_extension.json schema
        """
        pdf_properties = pdf_properties or {}
        logger.info("Extracting Extension data from text")

        filer_info = self._extract_filer_info(text)
        extension_details = self._extract_extension_details(text)
        
        result = {
            "filer_info": filer_info,
            "report_type": {
                "filing_type": "X"
            },
            "extension_details": extension_details,
            "extraction_metadata": self.create_extraction_metadata(
                confidence=0.9 if extension_details.get("days_requested") else 0.5,
                method="regex"
            )
        }

        return result

    def _extract_filer_info(self, text: str) -> Dict[str, Any]:
        """Extract filer information."""
        filer_info = {
            "full_name": None,
            "state": None,
            "district": None
        }

        name_match = re.search(r'Name:\s*(.+?)(?:\n|Status:)', text, re.IGNORECASE)
        if name_match:
            filer_info["full_name"] = name_match.group(1).strip()

        state_dist_match = re.search(r'State/District:\s*([A-Z]{2})(\d{1,2})', text)
        if state_dist_match:
            filer_info["state"] = state_dist_match.group(1)
            filer_info["district"] = state_dist_match.group(2)

        return filer_info

    def _extract_extension_details(self, text: str) -> Dict[str, Any]:
        """Extract extension request details."""
        details = {
            "days_requested": None,
            "due_date": None,
            "reason": None
        }

        # Extract days requested
        days_match = re.search(r'requesting a\s*(\d+)\s*day extension', text, re.IGNORECASE)
        if days_match:
            details["days_requested"] = int(days_match.group(1))

        # Extract due date
        due_match = re.search(r'due date:\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        if due_match:
            details["due_date"] = self.extract_date(due_match.group(1))

        return details
