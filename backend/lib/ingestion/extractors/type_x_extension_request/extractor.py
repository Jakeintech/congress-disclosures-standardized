"""Extension Request (Type X) extractor.

Extracts data from Candidate Financial Disclosure Extension Request forms.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class TypeXExtensionRequestExtractor(BaseExtractor):
    """Extract structured data from Extension Request forms (Type X)."""

    def __init__(self):
        """Initialize the extractor."""
        self.extraction_version = "1.0.0"

    def extract_from_text(self, text: str, pdf_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract Extension Request data from text (regex-based).

        Args:
            text: Extracted text from PDF
            pdf_properties: Optional PDF metadata

        Returns:
            Structured data for extension request
        """
        logger.info("Extracting Extension Request data from text")
        
        # Clean text of null bytes and excessive whitespace
        text = text.replace('\x00', '')
        
        # Extract filer info
        filer_info = self._extract_filer_info_regex(text)
        
        # Extract extension details
        extension_details = self._extract_extension_details_regex(text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(filer_info, extension_details)

        result = {
            "filing_type": "X",
            "filer_info": filer_info,
            "extension_details": extension_details,
            "metadata": {
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "extraction_method": "regex",
                "extraction_version": self.extraction_version,
                "confidence_score": confidence
            }
        }
        
        return result

    def _extract_filer_info_regex(self, text: str) -> Dict[str, Any]:
        """Extract filer info using regex."""
        info = {
            "name_of_requestor": None,
            "request_date": None,
            "election_date": None,
            "state_district": None
        }
        
        # Name
        name_match = re.search(r'Name:\s*(.+?)(?:\n|$|Status:)', text, re.IGNORECASE)
        if name_match:
            info["name_of_requestor"] = name_match.group(1).strip()
            
        # Request Date
        date_match = re.search(r'Request Date:\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        if date_match:
            info["request_date"] = date_match.group(1)
            
        # State/District
        dist_match = re.search(r'(?:State/)?District:\s*([A-Z]{2}[\d]{1,2}|[A-Z]{2}\s+\d{1,2})', text, re.IGNORECASE)
        if dist_match:
            info["state_district"] = dist_match.group(1).strip()
            
        return info

    def _extract_extension_details_regex(self, text: str) -> Dict[str, Any]:
        """Extract extension details using regex."""
        details = {
            "statement_type": None,
            "days_requested": None,
            "days_granted": None,
            "committee_decision_date": None,
            "new_due_date": None,
            "original_due_date": None
        }
        
        # Statement Type (Report Type Due)
        type_match = re.search(r'Report Type Due:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if type_match:
            details["statement_type"] = type_match.group(1).strip()
            
        # Days Requested (Extension Length)
        days_match = re.search(r'Extension Length:\s*(\d+)\s*days', text, re.IGNORECASE)
        if days_match:
            details["days_requested"] = int(days_match.group(1))
            
        # New Due Date
        new_due_match = re.search(r'New Due Date:\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        if new_due_match:
            details["new_due_date"] = new_due_match.group(1)
            
        # Original Due Date
        orig_due_match = re.search(r'Original Due Date:\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        if orig_due_match:
            details["original_due_date"] = orig_due_match.group(1)
            
        return details

    def _calculate_confidence(self, filer_info: Dict, extension_details: Dict) -> float:
        """Calculate confidence score."""
        filled = sum([
            bool(filer_info.get("name_of_requestor")),
            bool(filer_info.get("state_district")),
            bool(extension_details.get("days_requested")),
            bool(extension_details.get("new_due_date"))
        ])
        return round(filled / 4, 2)
