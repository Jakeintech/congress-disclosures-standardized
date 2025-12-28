"""Campaign Notice (Type D) extractor.

Extracts data from Campaign Notice forms.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class TypeDCampaignNoticeExtractor(BaseExtractor):
    """Extract structured data from Campaign Notice forms (Type D)."""

    def __init__(self):
        """Initialize the extractor."""
        self.extraction_version = "1.0.0"

    def extract_from_text(self, text: str, pdf_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract Campaign Notice data from text (regex-based).

        Args:
            text: Extracted text from PDF
            pdf_properties: Optional PDF metadata

        Returns:
            Structured data for campaign notice
        """
        logger.info("Extracting Campaign Notice data from text")
        
        # Clean text of null bytes and excessive whitespace
        text = text.replace('\x00', '')
        
        # Extract filer info using regex
        filer_info = self._extract_filer_info_regex(text)
        
        # Extract signature
        signature = self._extract_signature_regex(text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(filer_info, signature)

        result = {
            "filing_type": "D",
            "filer_info": filer_info,
            "signature": signature,
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
            "name": None,
            "status": "Congressional Candidate",
            "state_district": None
        }
        
        # Name
        name_match = re.search(r'Name:\s*(.+?)(?:\n|$|Status:)', text, re.IGNORECASE)
        if name_match:
            info["name"] = name_match.group(1).strip()
            
        # Status
        status_match = re.search(r'Status:\s*(.+?)(?:\n|$|State)', text, re.IGNORECASE)
        if status_match:
            info["status"] = status_match.group(1).strip()
            
        # State/District
        dist_match = re.search(r'(?:State/)?District:\s*([A-Z]{2}[\d]{1,2}|[A-Z]{2}\s+\d{1,2})', text, re.IGNORECASE)
        if dist_match:
            info["state_district"] = dist_match.group(1).strip()
            
        return info

    def _extract_signature_regex(self, text: str) -> Dict[str, Any]:
        """Extract signature using regex."""
        sig = {"digitally_signed_by": None, "signature_date": None}
        
        match = re.search(r'Digitally Signed:\s*(.+?),\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        if match:
            sig["digitally_signed_by"] = match.group(1).strip()
            sig["signature_date"] = match.group(2).strip()
            
        return sig

    def _calculate_confidence(self, filer_info: Dict, signature: Dict) -> float:
        """Calculate confidence score."""
        filled = sum([
            bool(filer_info.get("name")),
            bool(filer_info.get("state_district")),
            bool(signature.get("digitally_signed_by")),
            bool(signature.get("signature_date"))
        ])
        return round(filled / 4, 2)
