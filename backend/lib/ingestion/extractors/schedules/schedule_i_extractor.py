"""Schedule I: Payments Made to Charity in Lieu of Honoraria extractor.

Parses Schedule I tables containing payments made to charity.
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ScheduleIExtractor:
    """Extract Schedule I (Charity Contributions) from table data."""

    def parse_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Schedule I table into list of contributions.

        Args:
            table: Parsed table dict with 'headers' and 'rows'

        Returns:
            List of contribution dictionaries matching schedule_i schema
        """
        contributions = []
        headers = [h.lower() for h in table.get("headers", [])]
        rows = table.get("rows", [])

        logger.debug(f"Parsing Schedule I table with {len(rows)} rows")

        for row in rows:
            contribution = self._parse_row(row, headers)
            if contribution:
                contributions.append(contribution)

        logger.info(f"Extracted {len(contributions)} contributions from Schedule I")
        return contributions

    def _parse_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a single table row into a contribution dictionary.

        Args:
            row: List of cell values
            headers: List of column headers (lowercase)

        Returns:
            Contribution dictionary or None if row is empty/invalid
        """
        # Skip empty rows
        if not any(cell.strip() for cell in row if cell):
            return None

        contribution = {
            "source": None,
            "activity": None,
            "date": None,
            "amount": None,
            "charity_name": None
        }

        # Map columns by header keywords
        for idx, header in enumerate(headers):
            if idx >= len(row):
                break

            cell_value = row[idx].strip()
            if not cell_value:
                continue

            # Source
            if "source" in header:
                contribution["source"] = cell_value

            # Activity
            elif "activity" in header:
                contribution["activity"] = cell_value

            # Date
            elif "date" in header:
                contribution["date"] = cell_value

            # Amount
            elif "amount" in header:
                contribution["amount"] = self._parse_amount(cell_value)

            # Charity Name
            elif "charity" in header or "recipient" in header:
                contribution["charity_name"] = cell_value

        # Validate contribution has at least source
        if not contribution["source"]:
            logger.debug("Skipping row without source")
            return None

        return contribution

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string into float value."""
        if not amount_str:
            return None
        
        clean_str = amount_str.replace('$', '').replace(',', '').strip()
        try:
            return float(clean_str)
        except ValueError:
            return None
