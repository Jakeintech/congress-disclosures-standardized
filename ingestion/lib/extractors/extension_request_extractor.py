"""Extension Request (Type X) extractor.

Extracts data from Candidate Financial Disclosure Extension Request forms.
This is a simple one-page form with ~10 fields requesting extensions (30/60/90 days)
for filing financial disclosures.

Form fields:
- Name of Requestor
- Request Date
- Date of Primary/Special Election
- State/District of Election
- Statement Type (checkboxes: 2024/Amendment/Other)
- Days Requested (checkboxes: 30/60/90/Other)
- Days Granted (Committee decision)
- Committee Decision Date
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ExtensionRequestExtractor:
    """Extract structured data from Extension Request forms (Type X)."""

    def __init__(self):
        """Initialize the extractor."""
        self.extraction_version = "1.0.0"

    def extract_from_textract(
        self,
        doc_id: str,
        year: int,
        textract_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract Extension Request data from Textract blocks.

        Args:
            doc_id: Document ID
            year: Filing year
            textract_blocks: List of Textract block dictionaries

        Returns:
            Structured data for extension request
        """
        logger.info(f"Extracting Extension Request data for doc_id={doc_id}, year={year}")

        # Build block map for efficient lookups
        block_map = {block["Id"]: block for block in textract_blocks}

        # Extract key-value pairs (Textract forms)
        kv_pairs = self._extract_key_value_pairs(textract_blocks, block_map)

        # Extract filer information
        filer_info = self._extract_filer_info(kv_pairs, textract_blocks)

        # Extract extension details
        extension_details = self._extract_extension_details(kv_pairs, textract_blocks)

        # Build structured output
        result = {
            "doc_id": doc_id,
            "filing_year": year,
            "filing_type": "Extension Request",
            "filer_info": filer_info,
            "extension_details": extension_details,
            "metadata": {
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "extraction_method": "textract_forms",
                "extraction_version": self.extraction_version,
                "confidence_score": self._calculate_confidence(filer_info, extension_details)
            }
        }

        return result

    def _extract_key_value_pairs(
        self,
        blocks: List[Dict[str, Any]],
        block_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, str]:
        """Extract key-value pairs from Textract KEY_VALUE_SET blocks.

        Args:
            blocks: Textract blocks
            block_map: Block ID to block mapping

        Returns:
            Dictionary of key -> value mappings
        """
        kv_pairs = {}

        for block in blocks:
            if block.get("BlockType") != "KEY_VALUE_SET":
                continue

            entity_types = block.get("EntityTypes", [])

            # Process KEY blocks
            if "KEY" in entity_types:
                key_text = self._get_text_from_relationships(block, block_map, "CHILD")
                value_text = self._get_text_from_relationships(block, block_map, "VALUE")

                if key_text and value_text:
                    # Clean up key text
                    key_clean = key_text.strip().lower().replace(":", "")
                    kv_pairs[key_clean] = value_text.strip()

        logger.debug(f"Extracted {len(kv_pairs)} key-value pairs")
        return kv_pairs

    def _get_text_from_relationships(
        self,
        block: Dict[str, Any],
        block_map: Dict[str, Dict[str, Any]],
        relationship_type: str
    ) -> str:
        """Get text from blocks related via relationships.

        Args:
            block: Source block
            block_map: Block ID to block mapping
            relationship_type: Type of relationship (CHILD, VALUE)

        Returns:
            Concatenated text from related blocks
        """
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
        """Extract filer information fields.

        Args:
            kv_pairs: Key-value pairs from Textract
            blocks: All Textract blocks (for fallback text search)

        Returns:
            Filer information dictionary
        """
        filer_info = {
            "name_of_requestor": None,
            "request_date": None,
            "election_date": None,
            "state_district": None
        }

        # Try to find fields from key-value pairs
        filer_info["name_of_requestor"] = self._find_value(
            kv_pairs,
            ["name of requestor", "requestor", "name"]
        )

        filer_info["request_date"] = self._find_value(
            kv_pairs,
            ["date", "request date"]
        )

        filer_info["election_date"] = self._find_value(
            kv_pairs,
            ["date of primary", "date of election", "election date", "primary date"]
        )

        filer_info["state_district"] = self._find_value(
            kv_pairs,
            ["state/district", "state district", "district"]
        )

        # Fallback: search all text blocks for patterns
        if not filer_info["name_of_requestor"]:
            filer_info["name_of_requestor"] = self._find_name_from_text(blocks)

        if not filer_info["election_date"]:
            filer_info["election_date"] = self._find_election_date_from_text(blocks)

        # Parse dates to consistent format if possible
        if filer_info["request_date"]:
            filer_info["request_date"] = self._parse_date(filer_info["request_date"])

        if filer_info["election_date"]:
            filer_info["election_date"] = self._parse_date(filer_info["election_date"])

        return filer_info

    def _extract_extension_details(
        self,
        kv_pairs: Dict[str, str],
        blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract extension request details.

        Args:
            kv_pairs: Key-value pairs from Textract
            blocks: All Textract blocks

        Returns:
            Extension details dictionary
        """
        details = {
            "statement_type": None,
            "statement_type_detail": None,
            "days_requested": None,
            "days_granted": None,
            "committee_decision_date": None
        }

        # Extract statement type (checkbox selection)
        details["statement_type"] = self._extract_statement_type(blocks)

        # Extract days requested (30/60/90/Other)
        details["days_requested"] = self._extract_days_requested(blocks)

        # Extract days granted
        days_granted_str = self._find_value(
            kv_pairs,
            ["days granted", "granted"]
        )
        if days_granted_str:
            details["days_granted"] = self._parse_days(days_granted_str)

        # Fallback: if not in KV pairs, search text
        if not details["days_granted"]:
            details["days_granted"] = self._extract_days_granted_from_text(blocks)

        # Extract committee decision date
        decision_date = self._find_value(
            kv_pairs,
            ["date", "decision date", "committee date"]
        )
        if decision_date:
            details["committee_decision_date"] = self._parse_date(decision_date)

        # If not found in KV pairs, search text blocks
        if not details["committee_decision_date"]:
            details["committee_decision_date"] = self._find_decision_date_from_text(blocks)

        return details

    def _find_value(self, kv_pairs: Dict[str, str], possible_keys: List[str]) -> Optional[str]:
        """Find value in key-value pairs by trying multiple possible keys.

        Args:
            kv_pairs: Key-value pairs dictionary
            possible_keys: List of possible key names to try

        Returns:
            Value if found, None otherwise
        """
        for key in possible_keys:
            if key in kv_pairs:
                value = kv_pairs[key].strip()
                if value and value.lower() not in ["", "n/a", "none"]:
                    return value
        return None

    def _find_name_from_text(self, blocks: List[Dict[str, Any]]) -> Optional[str]:
        """Find requestor name from text blocks.

        Args:
            blocks: Textract blocks

        Returns:
            Name if found, None otherwise
        """
        text_blocks = [b for b in blocks if b.get("BlockType") == "LINE"]

        for block in text_blocks:
            text = block.get("Text", "")
            # Look for "Name of Requestor:" pattern
            if "name of requestor" in text.lower():
                # Name might be on same line after colon
                match = re.search(r'name of requestor[:\s]+(.+)', text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return None

    def _find_election_date_from_text(self, blocks: List[Dict[str, Any]]) -> Optional[str]:
        """Find election date from text blocks.

        Args:
            blocks: Textract blocks

        Returns:
            Election date if found, None otherwise
        """
        text_blocks = [b for b in blocks if b.get("BlockType") == "LINE"]

        for block in text_blocks:
            text = block.get("Text", "")
            # Look for "Date of Primary/Special Election:" pattern
            if "date of primary" in text.lower() or "election" in text.lower():
                # Date might follow
                match = re.search(r'election[:\s]+(.+)', text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return None

    def _extract_statement_type(self, blocks: List[Dict[str, Any]]) -> Optional[str]:
        """Extract which statement type checkbox is selected.

        Args:
            blocks: Textract blocks

        Returns:
            Statement type string or None
        """
        text_blocks = [b for b in blocks if b.get("BlockType") == "LINE"]

        # Look for checkbox indicators
        for i, block in enumerate(text_blocks):
            text = block.get("Text", "").lower()

            # Look for statement type section
            if "statement" in text and "type" in text:
                # Check next few lines for checked boxes
                for j in range(i, min(i + 5, len(text_blocks))):
                    line = text_blocks[j].get("Text", "")

                    # Look for checkbox with X or checkmark
                    if "☑" in line or "✓" in line or "[x]" in line.lower():
                        if "2024" in line:
                            return "Statement due in 2024"
                        elif "amendment" in line.lower():
                            return "Amendment"
                        elif "other" in line.lower():
                            # Try to get the "Other" details
                            detail_match = re.search(r'other[:\s]+(.+)', line, re.IGNORECASE)
                            if detail_match:
                                return f"Other: {detail_match.group(1).strip()}"
                            return "Other"
                        elif "2025" in line:
                            return "Statement due in 2025"

        return None

    def _extract_days_requested(self, blocks: List[Dict[str, Any]]) -> Optional[int]:
        """Extract number of days requested.

        Args:
            blocks: Textract blocks

        Returns:
            Number of days (30/60/90) or None
        """
        text_blocks = [b for b in blocks if b.get("BlockType") == "LINE"]

        for i, block in enumerate(text_blocks):
            text = block.get("Text", "").lower()

            # Look for "days" keyword
            if "days" in text and "request" in text:
                # Check next few lines for checked box
                for j in range(i, min(i + 5, len(text_blocks))):
                    line = text_blocks[j].get("Text", "")

                    if "☑" in line or "✓" in line or "[x]" in line.lower():
                        # Extract number
                        if "30" in line:
                            return 30
                        elif "60" in line:
                            return 60
                        elif "90" in line:
                            return 90

        return None

    def _extract_days_granted_from_text(self, blocks: List[Dict[str, Any]]) -> Optional[int]:
        """Extract days granted from text.

        Args:
            blocks: Textract blocks

        Returns:
            Number of days granted or None
        """
        text_blocks = [b for b in blocks if b.get("BlockType") == "LINE"]

        for block in text_blocks:
            text = block.get("Text", "")

            # Look for "Days granted:" pattern
            if "days granted" in text.lower():
                # Extract number
                match = re.search(r'granted[:\s]+(\d+)', text, re.IGNORECASE)
                if match:
                    return int(match.group(1))

        return None

    def _find_decision_date_from_text(self, blocks: List[Dict[str, Any]]) -> Optional[str]:
        """Find committee decision date from text.

        Args:
            blocks: Textract blocks

        Returns:
            Decision date if found, None otherwise
        """
        text_blocks = [b for b in blocks if b.get("BlockType") == "LINE"]

        # Look near end of document for date
        for block in reversed(text_blocks[-10:]):  # Check last 10 lines
            text = block.get("Text", "")

            # Look for date pattern MM/DD/YYYY
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
            if date_match:
                return self._parse_date(date_match.group(1))

        return None

    def _parse_date(self, date_str: str) -> str:
        """Parse various date formats to consistent format.

        Args:
            date_str: Date string (various formats)

        Returns:
            Standardized date string (MM/DD/YYYY format)
        """
        date_str = date_str.strip()

        # Already in MM/DD/YYYY format
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_str):
            return date_str

        # Written format: "August 19, 2025" or "June 2, 2025"
        written_match = re.match(
            r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})',
            date_str
        )
        if written_match:
            month_name = written_match.group(1)
            day = written_match.group(2)
            year = written_match.group(3)

            # Convert month name to number
            month_map = {
                "january": "01", "february": "02", "march": "03",
                "april": "04", "may": "05", "june": "06",
                "july": "07", "august": "08", "september": "09",
                "october": "10", "november": "11", "december": "12"
            }
            month_num = month_map.get(month_name.lower())
            if month_num:
                return f"{month_num}/{day.zfill(2)}/{year}"

        # Return as-is if can't parse
        return date_str

    def _parse_days(self, days_str: str) -> Optional[int]:
        """Parse days from string.

        Args:
            days_str: String containing number of days

        Returns:
            Integer number of days or None
        """
        # Extract first number found
        match = re.search(r'(\d+)', days_str)
        if match:
            return int(match.group(1))
        return None

    def _calculate_confidence(
        self,
        filer_info: Dict[str, Any],
        extension_details: Dict[str, Any]
    ) -> float:
        """Calculate extraction confidence score.

        Args:
            filer_info: Filer information dictionary
            extension_details: Extension details dictionary

        Returns:
            Confidence score (0.0 to 1.0)
        """
        total_fields = 7  # Total expected fields
        filled_fields = 0

        # Count filled filer info fields
        for value in filer_info.values():
            if value is not None:
                filled_fields += 1

        # Count filled extension detail fields
        if extension_details["days_requested"] is not None:
            filled_fields += 1
        if extension_details["days_granted"] is not None:
            filled_fields += 1
        if extension_details["committee_decision_date"] is not None:
            filled_fields += 1

        confidence = filled_fields / total_fields
        return round(confidence, 2)
