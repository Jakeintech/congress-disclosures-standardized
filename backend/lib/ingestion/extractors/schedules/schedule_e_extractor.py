"""Schedule E: Positions Held Outside U.S. Government extractor.

Parses Schedule E tables containing outside positions held by the filer,
such as board memberships, officer positions, or other roles in organizations.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ScheduleEExtractor:
    """Extract Schedule E (Outside Positions) from table data."""

    def parse_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Schedule E table into list of positions.

        Args:
            table: Parsed table dict with 'headers' and 'rows'

        Returns:
            List of position dictionaries matching schedule_e_positions schema
        """
        positions = []
        headers = [h.lower() for h in table.get("headers", [])]
        rows = table.get("rows", [])

        logger.debug(f"Parsing Schedule E table with {len(rows)} rows")

        for row in rows:
            position = self._parse_row(row, headers)
            if position:
                positions.append(position)

        logger.info(f"Extracted {len(positions)} positions from Schedule E")
        return positions

    def _parse_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a single table row into a position dictionary.

        Args:
            row: List of cell values
            headers: List of column headers (lowercase)

        Returns:
            Position dictionary or None if row is empty/invalid
        """
        # Skip empty rows
        if not any(cell.strip() for cell in row if cell):
            return None

        position = {
            "position": None,
            "organization": None
        }

        # Map columns by header keywords
        for idx, header in enumerate(headers):
            if idx >= len(row):
                break

            cell_value = row[idx].strip()
            if not cell_value:
                continue

            # Position title
            if any(kw in header for kw in ["position", "title", "role"]):
                position["position"] = cell_value

            # Organization name
            elif any(kw in header for kw in ["organization", "name", "entity"]):
                position["organization"] = cell_value

        # Validate position has both fields
        if not position["position"] or not position["organization"]:
            logger.debug("Skipping row without position or organization")
            return None

        return position
