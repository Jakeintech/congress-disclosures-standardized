"""Campaign Notice (Type D) extractor.

Extracts data from "Campaign Notice Regarding Financial Disclosure Requirement" forms.
This is a simple one-page notice filed by candidates who have NOT raised/spent $5,000 yet.

Form fields:
- Name
- Status (always "Congressional Candidate")
- State/District
- Digital Signature (name + date)
- Filing ID
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CampaignNoticeExtractor:
    """Extract structured data from Campaign Notice forms (Type D)."""

    def __init__(self):
        """Initialize the extractor."""
        self.extraction_version = "1.0.0"

    def extract_from_textract(
        self,
        doc_id: str,
        year: int,
        textract_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract Campaign Notice data from Textract blocks.

        Args:
            doc_id: Document ID
            year: Filing year
            textract_blocks: List of Textract block dictionaries

        Returns:
            Structured data for campaign notice
        """
        logger.info(f"Extracting Campaign Notice data for doc_id={doc_id}, year={year}")

        # Build block map
        block_map = {block["Id"]: block for block in textract_blocks}

        # Extract key-value pairs
        kv_pairs = self._extract_key_value_pairs(textract_blocks, block_map)

        # Extract filer information
        filer_info = self._extract_filer_info(kv_pairs, textract_blocks)

        # Extract signature
        signature = self._extract_signature(textract_blocks)

        # Build structured output
        result = {
            "doc_id": doc_id,
            "filing_year": year,
            "filing_type": "Campaign Notice",
            "notice_type": "below_threshold",  # Haven't raised/spent $5,000
            "filer_info": filer_info,
            "signature": signature,
            "metadata": {
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "extraction_method": "textract_forms",
                "extraction_version": self.extraction_version,
                "confidence_score": self._calculate_confidence(filer_info, signature)
            }
        }

        return result

    def _extract_key_value_pairs(
        self,
        blocks: List[Dict[str, Any]],
        block_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, str]:
        """Extract key-value pairs from Textract KEY_VALUE_SET blocks."""
        kv_pairs = {}

        for block in blocks:
            if block.get("BlockType") != "KEY_VALUE_SET":
                continue

            entity_types = block.get("EntityTypes", [])

            if "KEY" in entity_types:
                key_text = self._get_text_from_relationships(block, block_map, "CHILD")
                value_text = self._get_text_from_relationships(block, block_map, "VALUE")

                if key_text and value_text:
                    key_clean = key_text.strip().lower().replace(":", "")
                    kv_pairs[key_clean] = value_text.strip()

        return kv_pairs

    def _get_text_from_relationships(
        self,
        block: Dict[str, Any],
        block_map: Dict[str, Dict[str, Any]],
        relationship_type: str
    ) -> str:
        """Get text from blocks related via relationships."""
        text_parts = []
        relationships = block.get("Relationships", [])

        for rel in relationships:
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
        """Extract filer information fields."""
        filer_info = {
            "name": None,
            "status": "Congressional Candidate",  # Always this value
            "state_district": None
        }

        # Try to find fields from key-value pairs
        filer_info["name"] = self._find_value(
            kv_pairs,
            ["name", "candidate name", "filer name"]
        )

        filer_info["state_district"] = self._find_value(
            kv_pairs,
            ["state/district", "state district", "district"]
        )

        # Fallback: search text blocks
        if not filer_info["name"]:
            filer_info["name"] = self._find_name_from_text(blocks)

        if not filer_info["state_district"]:
            filer_info["state_district"] = self._find_state_district_from_text(blocks)

        return filer_info

    def _extract_signature(self, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract digital signature information."""
        signature = {
            "digitally_signed_by": None,
            "signature_date": None
        }

        text_blocks = [b for b in blocks if b.get("BlockType") == "LINE"]

        for block in text_blocks:
            text = block.get("Text", "")

            # Look for "Digitally Signed: Name, MM/DD/YYYY" pattern
            sig_match = re.search(
                r'Digitally Signed:\s*(.+?),\s*(\d{1,2}/\d{1,2}/\d{4})',
                text,
                re.IGNORECASE
            )
            if sig_match:
                signature["digitally_signed_by"] = sig_match.group(1).strip()
                signature["signature_date"] = sig_match.group(2).strip()
                break

        return signature

    def _find_value(self, kv_pairs: Dict[str, str], possible_keys: List[str]) -> Optional[str]:
        """Find value in key-value pairs by trying multiple possible keys."""
        for key in possible_keys:
            if key in kv_pairs:
                value = kv_pairs[key].strip()
                if value and value.lower() not in ["", "n/a", "none"]:
                    return value
        return None

    def _find_name_from_text(self, blocks: List[Dict[str, Any]]) -> Optional[str]:
        """Find candidate name from text blocks."""
        text_blocks = [b for b in blocks if b.get("BlockType") == "LINE"]

        for block in text_blocks:
            text = block.get("Text", "")
            # Look for "Name:" pattern
            if "name:" in text.lower():
                match = re.search(r'name:\s*(.+)', text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return None

    def _find_state_district_from_text(self, blocks: List[Dict[str, Any]]) -> Optional[str]:
        """Find state/district from text blocks."""
        text_blocks = [b for b in blocks if b.get("BlockType") == "LINE"]

        for block in text_blocks:
            text = block.get("Text", "")
            # Look for "State/District:" pattern
            if "state/district" in text.lower() or "district" in text.lower():
                match = re.search(r'(?:state/)?district:\s*(.+)', text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return None

    def _calculate_confidence(
        self,
        filer_info: Dict[str, Any],
        signature: Dict[str, Any]
    ) -> float:
        """Calculate extraction confidence score."""
        total_fields = 4  # name, state_district, signature_by, signature_date
        filled_fields = 0

        if filer_info.get("name"):
            filled_fields += 1
        if filer_info.get("state_district"):
            filled_fields += 1
        if signature.get("digitally_signed_by"):
            filled_fields += 1
        if signature.get("signature_date"):
            filled_fields += 1

        confidence = filled_fields / total_fields
        return round(confidence, 2)
