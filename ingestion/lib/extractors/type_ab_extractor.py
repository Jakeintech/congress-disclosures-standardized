"""Type A/B (Annual/New Filer) extractor.

Extracts structured data from Form A (Annual) and Form B (New Filer) reports.
"""

import logging
import re
from typing import Dict, List, Any
from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class TypeABExtractor(BaseExtractor):
    """Extract structured data from Annual and New Filer reports."""

    def extract_from_text(self, text: str, pdf_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract Form A/B data from text.

        Args:
            text: Extracted text from PDF
            pdf_properties: Optional PDF metadata

        Returns:
            Structured data matching house_fd_annual.json schema
        """
        pdf_properties = pdf_properties or {}
        logger.info("Extracting Annual/New Filer data from text")

        # Extract sections
        filer_info = self._extract_filer_info(text)
        
        # Extract main schedules
        assets = self._extract_assets_and_income(text)
        liabilities = self._extract_liabilities(text)
        positions = self._extract_positions(text)
        agreements = self._extract_agreements(text)
        
        # Extract certification
        certification = self._extract_certification(text)

        # Calculate confidence
        field_confidence = self._calculate_field_confidence(filer_info, assets, certification)
        overall_confidence = sum(field_confidence.values()) / len(field_confidence) if field_confidence else 0.5

        result = {
            "filer_info": filer_info,
            "report_type": {
                "is_amendment": False,  # TODO: detect
                "filing_type": filer_info.get("filing_type", "A") 
            },
            "assets_and_income": assets,
            "liabilities": liabilities,
            "positions": positions,
            "agreements": agreements,
            "certification": certification,
            "filing_metadata": {
                "asset_count": len(assets),
                "liability_count": len(liabilities)
            },
            "extraction_metadata": self.create_extraction_metadata(
                confidence=overall_confidence,
                method="regex",
                field_confidence=field_confidence
            )
        }

        return result

    def _extract_filer_info(self, text: str) -> Dict[str, Any]:
        """Extract filer information from header."""
        filer_info = {
            "full_name": None,
            "filer_type": None,
            "state": None,
            "district": None,
            "year": None,
            "filing_type": "A" # Default to Annual
        }

        # Extract name
        name_match = re.search(r'Name:\s*(.+?)(?:\n|Status:)', text, re.IGNORECASE)
        if name_match:
            filer_info["full_name"] = name_match.group(1).strip()

        # Extract status
        status_match = re.search(r'Status:\s*(Member|Officer or Employee)', text, re.IGNORECASE)
        if status_match:
            filer_info["filer_type"] = status_match.group(1).strip()

        # Extract state/district
        state_dist_match = re.search(r'State/District:\s*([A-Z]{2})(\d{1,2})', text)
        if state_dist_match:
            filer_info["state"] = state_dist_match.group(1)
            filer_info["district"] = state_dist_match.group(2)
            
        # Detect filing type (Annual vs New Filer)
        if "New Filer" in text or "Form B" in text:
            filer_info["filing_type"] = "B"
            
        # Extract year
        year_match = re.search(r'Calendar Year:\s*(\d{4})', text)
        if year_match:
            filer_info["year"] = int(year_match.group(1))

        return filer_info

    def _extract_assets_and_income(self, text: str) -> List[Dict[str, Any]]:
        """Extract Schedule A: Assets and "Unearned" Income."""
        assets = []
        
        # Find section
        # Starts with "Schedule A" and ends with "Schedule B" or "Schedule C"
        section_match = re.search(r'Schedule A.*?\n(.*?)(?=\n\s*Schedule [BC]|\n\s*S\s+[BC]|\Z)', 
                                 text, re.DOTALL | re.IGNORECASE)
        
        if not section_match:
            return []
            
        section_text = section_match.group(1)
        
        # Basic line-based extraction for now
        # Ideally this would parse the table structure
        lines = section_text.split('\n')
        current_asset = None
        
        for line in lines:
            line = line.strip()
            if not line or "ID Owner Asset" in line:
                continue
                
            # Heuristic: lines starting with SP, DC, JT or None are likely assets
            # Format: [Owner] Asset Name [Type] [Value] [Income Type] [Income]
            
            # Very basic extraction - just capturing the line as description
            # TODO: Improve with robust table parsing
            if len(line) > 10:
                assets.append({
                    "asset_name": line,
                    "owner_code": self.extract_owner_code(line) or "Self"
                })
                
        return assets

    def _extract_liabilities(self, text: str) -> List[Dict[str, Any]]:
        """Extract Schedule D: Liabilities."""
        liabilities = []
        section_match = re.search(r'Schedule D.*?\n(.*?)(?=\n\s*Schedule [EF]|\n\s*S\s+[EF]|\Z)', 
                                 text, re.DOTALL | re.IGNORECASE)
        if section_match:
            section_text = section_match.group(1)
            lines = section_text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 10 and "ID Owner Creditor" not in line:
                    liabilities.append({
                        "creditor_name": line,
                        "owner_code": self.extract_owner_code(line)
                    })
        return liabilities

    def _extract_positions(self, text: str) -> List[Dict[str, Any]]:
        """Extract Schedule J: Positions."""
        positions = []
        section_match = re.search(r'Schedule J.*?\n(.*?)(?=\n\s*Schedule|\n\s*S\s+|\Z)', 
                                 text, re.DOTALL | re.IGNORECASE)
        if section_match:
            section_text = section_match.group(1)
            lines = section_text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 10 and "Position" not in line:
                    positions.append({
                        "position_title": line
                    })
        return positions

    def _extract_agreements(self, text: str) -> List[Dict[str, Any]]:
        """Extract Schedule IX: Agreements."""
        agreements = []
        section_match = re.search(r'Schedule IX.*?\n(.*?)(?=\n\s*Schedule|\n\s*S\s+|\Z)', 
                                 text, re.DOTALL | re.IGNORECASE)
        if section_match:
            section_text = section_match.group(1)
            lines = section_text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 10 and "Date Parties" not in line:
                    agreements.append({
                        "agreement_description": line
                    })
        return agreements

    def _extract_certification(self, text: str) -> Dict[str, Any]:
        """Extract certification information."""
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

    def _calculate_field_confidence(self, filer_info: Dict, assets: List[Dict], cert: Dict) -> Dict[str, float]:
        """Calculate confidence scores."""
        confidence = {}
        
        if filer_info.get("full_name"):
            confidence["filer_info.full_name"] = 0.95
            
        if assets:
            confidence["assets"] = 0.7  # Lower confidence due to basic extraction
            
        if cert.get("filer_certified"):
            confidence["certification"] = 1.0
            
        return confidence
