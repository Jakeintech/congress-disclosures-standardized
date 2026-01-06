"""Schedule G: Gifts extractor.

Parses Schedule G tables containing gifts received by the filer.
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ScheduleGExtractor:
    """Extract Schedule G (Gifts) from table data."""

    def parse_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Schedule G table into list of gifts.

        Args:
            table: Parsed table dict with 'headers' and 'rows'

        Returns:
            List of gift dictionaries matching schedule_g schema
        """
        gifts = []
        headers = [h.lower() for h in table.get("headers", [])]
        rows = table.get("rows", [])

        logger.debug(f"Parsing Schedule G table with {len(rows)} rows")

        for row in rows:
            gift = self._parse_row(row, headers)
            if gift:
                gifts.append(gift)

        logger.info(f"Extracted {len(gifts)} gifts from Schedule G")
        return gifts

    def _parse_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a single table row into a gift dictionary.

        Args:
            row: List of cell values
            headers: List of column headers (lowercase)

        Returns:
            Gift dictionary or None if row is empty/invalid
        """
        # Skip empty rows
        if not any(cell.strip() for cell in row if cell):
            return None

        gift = {
            "source": None,
            "description": None,
            "value": None,
            "date_received": None
        }

        # Map columns by header keywords
        for idx, header in enumerate(headers):
            if idx >= len(row):
                break

            cell_value = row[idx].strip()
            if not cell_value:
                continue

            # Source
            if "source" in header or "donor" in header:
                gift["source"] = cell_value

            # Description
            elif "description" in header or "item" in header:
                gift["description"] = cell_value

            # Value
            elif "value" in header or "amount" in header:
                gift["value"] = self._parse_amount(cell_value)

            # Date
            elif "date" in header:
                gift["date_received"] = cell_value

        # Validate gift has at least source
        if not gift["source"]:
            logger.debug("Skipping row without source")
            return None

        return gift

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string into float value."""
        if not amount_str:
            return None
        
        # Handle text like "Under $250" or similar if needed, but for now standard parsing
        clean_str = amount_str.replace('$', '').replace(',', '').strip()
        try:
            return float(clean_str)
        except ValueError:
            # Try to find first number
            match = re.search(r'([\d.]+)', clean_str)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
            return None
