"""Schedule D: Liabilities extractor.

Parses Schedule D tables containing liabilities such as mortgages, loans, and other debts
owed by the filer or their spouse.
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ScheduleDExtractor:
    """Extract Schedule D (Liabilities) from table data."""

    # Same value range mappings as Schedule A
    VALUE_RANGES = {
        "$10,001 - $15,000": (10001, 15000),
        "$15,001 - $50,000": (15001, 50000),
        "$50,001 - $100,000": (50001, 100000),
        "$100,001 - $250,000": (100001, 250000),
        "$250,001 - $500,000": (250001, 500000),
        "$500,001 - $1,000,000": (500001, 1000000),
        "Over $1,000,000": (1000001, None),
    }

    def parse_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Schedule D table into list of liabilities.

        Args:
            table: Parsed table dict with 'headers' and 'rows'

        Returns:
            List of liability dictionaries matching schedule_d_liabilities schema
        """
        liabilities = []
        headers = [h.lower() for h in table.get("headers", [])]
        rows = table.get("rows", [])

        logger.debug(f"Parsing Schedule D table with {len(rows)} rows")

        for row in rows:
            liability = self._parse_row(row, headers)
            if liability:
                liabilities.append(liability)

        logger.info(f"Extracted {len(liabilities)} liabilities from Schedule D")
        return liabilities

    def _parse_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a single table row into a liability dictionary.

        Args:
            row: List of cell values
            headers: List of column headers (lowercase)

        Returns:
            Liability dictionary or None if row is empty/invalid
        """
        # Skip empty rows
        if not any(cell.strip() for cell in row if cell):
            return None

        liability = {
            "owner_code": None,
            "creditor": None,
            "date_incurred": None,
            "type": None,
            "amount_low": None,
            "amount_high": None
        }

        # Map columns by header keywords
        for idx, header in enumerate(headers):
            if idx >= len(row):
                break

            cell_value = row[idx].strip()
            if not cell_value:
                continue

            # Owner code (SP/DC/JT)
            if any(kw in header for kw in ["owner", "sp/dc/jt"]):
                owner = cell_value.upper()
                if owner in ["SP", "DC", "JT", ""]:
                    liability["owner_code"] = owner if owner else ""

            # Creditor name
            elif any(kw in header for kw in ["creditor", "lender", "name"]):
                liability["creditor"] = cell_value

            # Type of liability
            elif any(kw in header for kw in ["type", "description", "purpose"]):
                liability["type"] = cell_value

            # Date incurred
            elif any(kw in header for kw in ["date", "incurred", "month/year"]):
                liability["date_incurred"] = self._normalize_date(cell_value)

            # Amount (value range)
            elif any(kw in header for kw in ["amount", "value"]):
                value_range = self._parse_value_range(cell_value)
                if value_range:
                    liability["amount_low"], liability["amount_high"] = value_range

        # Validate liability has at least creditor and type
        if not liability["creditor"] or not liability["type"]:
            logger.debug("Skipping row without creditor or type")
            return None

        return liability

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to consistent format.

        Args:
            date_str: Date string (e.g., "July 2013", "07/2013", "2013-07")

        Returns:
            Normalized date string
        """
        if not date_str:
            return ""

        # Keep as-is for now (could convert to YYYY-MM format if needed)
        return date_str.strip()

    def _parse_value_range(self, value_str: str) -> Optional[tuple]:
        """Parse value range string into (low, high) tuple.

        Args:
            value_str: Value string (e.g., "$100,001 - $250,000")

        Returns:
            Tuple of (low, high) integers, or None if parsing fails
        """
        value_str = value_str.strip()

        # Try exact match first
        if value_str in self.VALUE_RANGES:
            return self.VALUE_RANGES[value_str]

        # Try pattern matching for custom ranges
        range_match = re.search(
            r'\$?([\d,]+)\s*-\s*\$?([\d,]+)',
            value_str
        )
        if range_match:
            try:
                low = int(range_match.group(1).replace(',', ''))
                high = int(range_match.group(2).replace(',', ''))
                return (low, high)
            except ValueError:
                logger.warning(f"Failed to parse value range: {value_str}")

        # Pattern: Over $X
        over_match = re.search(r'Over\s*\$?([\d,]+)', value_str, re.IGNORECASE)
        if over_match:
            try:
                low = int(over_match.group(1).replace(',', ''))
                return (low, None)
            except ValueError:
                pass

        return None
