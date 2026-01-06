"""Withdrawal Notice (Type W) extractor.

Extracts data from withdrawal notices where candidates withdraw from candidacy.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class TypeWWithdrawalNoticeExtractor(BaseExtractor):
    """Extract structured data from Withdrawal Notice forms (Type W)."""

    def __init__(self):
        """Initialize the extractor."""
        self.extraction_version = "1.0.0"

    def extract_from_text(self, text: str, pdf_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract Withdrawal Notice data from text (regex-based).

        Args:
            text: Extracted text from PDF
            pdf_properties: Optional PDF metadata

        Returns:
            Structured data for withdrawal notice
        """
        logger.info("Extracting Withdrawal Notice data from text")
        
        # Clean text of null bytes and excessive whitespace
        text = text.replace('\x00', '')
        
        # Extract filer info
        filer_info = self._extract_filer_info_regex(text)
        
        # Extract withdrawal date
        withdrawal_date = self._extract_withdrawal_date_regex(text)
        
        # Extract signature
        signature = self._extract_signature_regex(text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(filer_info, withdrawal_date, signature)

        result = {
            "filing_type": "W",
            "withdrawal_date": withdrawal_date,
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

    def _extract_withdrawal_date_regex(self, text: str) -> Optional[str]:
        """Extract withdrawal date using regex."""
        # Handle multiline "on \n MM/DD/YYYY"
        match = re.search(r'withdrew.*?on\s+(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
        # Try finding date on the line after "on"
        match_multiline = re.search(r'withdrew.*?on\s*\n\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE | re.DOTALL)
        if match_multiline:
            return match_multiline.group(1)
            
        return None

    def _extract_signature_regex(self, text: str) -> Dict[str, Any]:
        """Extract signature using regex."""
        sig = {"digitally_signed_by": None, "signature_date": None}
        
        match = re.search(r'Digitally Signed:\s*(.+?),\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        if match:
            sig["digitally_signed_by"] = match.group(1).strip()
            sig["signature_date"] = match.group(2).strip()
            
        return sig

    def _calculate_confidence(self, filer_info: Dict, withdrawal_date: Optional[str], signature: Dict) -> float:
        """Calculate confidence score."""
        filled = sum([
            bool(filer_info.get("name")),
            bool(filer_info.get("state_district")),
            bool(withdrawal_date),
            bool(signature.get("digitally_signed_by")),
            bool(signature.get("signature_date"))
        ])
        return round(filled / 5, 2)
