"""Type T (Termination) extractor.

Extracts structured data from Termination reports.
"""

import logging
import re
from typing import Dict, List, Any
from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class TypeTExtractor(BaseExtractor):
    """Extract structured data from Termination reports."""

    def extract_from_text(self, text: str, pdf_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract Type T data from text.

        Args:
            text: Extracted text from PDF
            pdf_properties: Optional PDF metadata

        Returns:
            Structured data matching house_fd_termination.json schema
        """
        pdf_properties = pdf_properties or {}
        logger.info("Extracting Termination data from text")

        filer_info = self._extract_filer_info(text)
        termination_date = self._extract_termination_date(text)
        certification = self._extract_certification(text)

        # Termination reports are often simple, just confirming no new assets/liabilities
        # or listing final ones.
        
        result = {
            "filer_info": filer_info,
            "report_type": {
                "filing_type": "T",
                "termination_date": termination_date
            },
            "certification": certification,
            "extraction_metadata": self.create_extraction_metadata(
                confidence=0.9 if termination_date else 0.5,
                method="regex"
            )
        }

        return result

    def _extract_filer_info(self, text: str) -> Dict[str, Any]:
        """Extract filer information."""
        filer_info = {
            "full_name": None,
            "filer_type": None,
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

    def _extract_termination_date(self, text: str) -> str:
        """Extract termination date."""
        # Look for "Termination Date:" or similar
        date_match = re.search(r'Termination Date:\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        if date_match:
            return self.extract_date(date_match.group(1))
        return None

    def _extract_certification(self, text: str) -> Dict[str, Any]:
        """Extract certification."""
        cert = {
            "filer_certified": False,
            "filer_signature": None,
            "filer_signature_date": None
        }

        if "I CERTIFY" in text:
            cert["filer_certified"] = True

        sig_match = re.search(r'Digitally Signed:\s*(.+?)\s*,\s*(\d{2}/\d{2}/\d{4})', text)
        if sig_match:
            cert["filer_signature"] = sig_match.group(1).strip()
            cert["filer_signature_date"] = self.extract_date(sig_match.group(2))

        return cert
