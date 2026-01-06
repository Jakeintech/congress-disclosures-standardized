"""Schedule F: Agreements and Arrangements extractor.

Parses Schedule F tables containing agreements for future employment, leave of absence,
continuation of payments, etc.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ScheduleFExtractor:
    """Extract Schedule F (Agreements) from table data."""

    def parse_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Schedule F table into list of agreements.

        Args:
            table: Parsed table dict with 'headers' and 'rows'

        Returns:
            List of agreement dictionaries matching schedule_f schema
        """
        agreements = []
        headers = [h.lower() for h in table.get("headers", [])]
        rows = table.get("rows", [])

        logger.debug(f"Parsing Schedule F table with {len(rows)} rows")

        for row in rows:
            agreement = self._parse_row(row, headers)
            if agreement:
                agreements.append(agreement)

        logger.info(f"Extracted {len(agreements)} agreements from Schedule F")
        return agreements

    def _parse_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a single table row into an agreement dictionary.

        Args:
            row: List of cell values
            headers: List of column headers (lowercase)

        Returns:
            Agreement dictionary or None if row is empty/invalid
        """
        # Skip empty rows
        if not any(cell.strip() for cell in row if cell):
            return None

        agreement = {
            "date": None,
            "parties_involved": None,
            "type": None,
            "status": None,
            "terms": None
        }

        # Map columns by header keywords
        for idx, header in enumerate(headers):
            if idx >= len(row):
                break

            cell_value = row[idx].strip()
            if not cell_value:
                continue

            # Date
            if "date" in header:
                agreement["date"] = cell_value

            # Parties Involved
            elif "parties" in header or "employer" in header:
                agreement["parties_involved"] = cell_value

            # Type of agreement
            elif "type" in header:
                agreement["type"] = cell_value

            # Status
            elif "status" in header:
                agreement["status"] = cell_value

            # Terms/Description
            elif "terms" in header or "description" in header:
                agreement["terms"] = cell_value

        # Validate agreement has at least parties or terms
        if not agreement["parties_involved"] and not agreement["terms"]:
            logger.debug("Skipping row without parties or terms")
            return None

        return agreement
