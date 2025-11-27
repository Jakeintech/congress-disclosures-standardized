"""Withdrawal Notice (Type W) extractor.

Extracts data from withdrawal notices where candidates withdraw from candidacy.
Similar to Campaign Notice but indicates withdrawal from race.

Form fields:
- Name
- Status (Congressional Candidate)
- State/District
- Withdrawal Date
- Digital Signature
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WithdrawalNoticeExtractor:
    """Extract structured data from Withdrawal Notice forms (Type W)."""

    def __init__(self):
        """Initialize the extractor."""
        self.extraction_version = "1.0.0"

    def extract_from_textract(
        self,
        doc_id: str,
        year: int,
        textract_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract Withdrawal Notice data from Textract blocks.

        Args:
            doc_id: Document ID
            year: Filing year
            textract_blocks: List of Textract block dictionaries

        Returns:
            Structured data for withdrawal notice
        """
        logger.info(f"Extracting Withdrawal Notice data for doc_id={doc_id}, year={year}")

        # Extract key-value pairs
        block_map = {block["Id"]: block for block in textract_blocks}
        kv_pairs = self._extract_key_value_pairs(textract_blocks, block_map)

        # Extract filer information
        filer_info = self._extract_filer_info(kv_pairs, textract_blocks)

        # Extract withdrawal date from text
        withdrawal_date = self._extract_withdrawal_date(textract_blocks)

        # Extract signature
        signature = self._extract_signature(textract_blocks)

        # Build structured output
        result = {
            "doc_id": doc_id,
            "filing_year": year,
            "filing_type": "Withdrawal Notice",
            "withdrawal_date": withdrawal_date,
            "filer_info": filer_info,
            "signature": signature,
            "metadata": {
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "extraction_method": "textract_forms",
                "extraction_version": self.extraction_version,
                "confidence_score": self._calculate_confidence(filer_info, withdrawal_date, signature)
            }
        }

        return result

    def _extract_key_value_pairs(
        self,
        blocks: List[Dict[str, Any]],
        block_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, str]:
        """Extract key-value pairs from Textract."""
        kv_pairs = {}
        for block in blocks:
            if block.get("BlockType") != "KEY_VALUE_SET":
                continue
            entity_types = block.get("EntityTypes", [])
            if "KEY" in entity_types:
                key_text = self._get_text_from_relationships(block, block_map, "CHILD")
                value_text = self._get_text_from_relationships(block, block_map, "VALUE")
                if key_text and value_text:
                    kv_pairs[key_text.strip().lower().replace(":", "")] = value_text.strip()
        return kv_pairs

    def _get_text_from_relationships(
        self,
        block: Dict[str, Any],
        block_map: Dict[str, Dict[str, Any]],
        relationship_type: str
    ) -> str:
        """Get text from related blocks."""
        text_parts = []
        for rel in block.get("Relationships", []):
            if rel.get("Type") == relationship_type:
                for block_id in rel.get("Ids", []):
                    related_block = block_map.get(block_id)
                    if related_block and related_block.get("BlockType") == "WORD":
                        text_parts.append(related_block.get("Text", ""))
        return " ".join(text_parts)

    def _extract_filer_info(
        self,
        kv_pairs: Dict[str, str],
        blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract filer information."""
        return {
            "name": self._find_value(kv_pairs, ["name"]) or self._find_name_from_text(blocks),
            "status": "Congressional Candidate",
            "state_district": self._find_value(kv_pairs, ["state/district", "district"]) or self._find_state_district_from_text(blocks)
        }

    def _extract_withdrawal_date(self, blocks: List[Dict[str, Any]]) -> Optional[str]:
        """Extract withdrawal date from text."""
        text_blocks = [b for b in blocks if b.get("BlockType") == "LINE"]
        for block in text_blocks:
            text = block.get("Text", "")
            # Look for "withdrew my candidacy...on MM/DD/YYYY" pattern
            match = re.search(r'withdrew.*?on\s+(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_signature(self, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract digital signature."""
        signature = {"digitally_signed_by": None, "signature_date": None}
        text_blocks = [b for b in blocks if b.get("BlockType") == "LINE"]
        for block in text_blocks:
            text = block.get("Text", "")
            match = re.search(r'Digitally Signed:\s*(.+?),\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
            if match:
                signature["digitally_signed_by"] = match.group(1).strip()
                signature["signature_date"] = match.group(2).strip()
                break
        return signature

    def _find_value(self, kv_pairs: Dict[str, str], keys: List[str]) -> Optional[str]:
        """Find value by trying multiple keys."""
        for key in keys:
            if key in kv_pairs and kv_pairs[key].lower() not in ["", "n/a"]:
                return kv_pairs[key].strip()
        return None

    def _find_name_from_text(self, blocks: List[Dict[str, Any]]) -> Optional[str]:
        """Find name from text blocks."""
        for block in [b for b in blocks if b.get("BlockType") == "LINE"]:
            text = block.get("Text", "")
            match = re.search(r'name:\s*(.+)', text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _find_state_district_from_text(self, blocks: List[Dict[str, Any]]) -> Optional[str]:
        """Find state/district from text."""
        for block in [b for b in blocks if b.get("BlockType") == "LINE"]:
            text = block.get("Text", "")
            match = re.search(r'(?:state/)?district:\s*(.+)', text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

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
