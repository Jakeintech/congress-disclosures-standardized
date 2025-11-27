"""Schedule H: Travel Payments and Reimbursements extractor.

Parses Schedule H tables containing travel reimbursements and payments.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ScheduleHExtractor:
    """Extract Schedule H (Travel) from table data."""

    def parse_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Schedule H table into list of travel entries.

        Args:
            table: Parsed table dict with 'headers' and 'rows'

        Returns:
            List of travel dictionaries matching schedule_h schema
        """
        travel_entries = []
        headers = [h.lower() for h in table.get("headers", [])]
        rows = table.get("rows", [])

        logger.debug(f"Parsing Schedule H table with {len(rows)} rows")

        for row in rows:
            entry = self._parse_row(row, headers)
            if entry:
                travel_entries.append(entry)

        logger.info(f"Extracted {len(travel_entries)} travel entries from Schedule H")
        return travel_entries

    def _parse_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a single table row into a travel dictionary.

        Args:
            row: List of cell values
            headers: List of column headers (lowercase)

        Returns:
            Travel dictionary or None if row is empty/invalid
        """
        # Skip empty rows
        if not any(cell.strip() for cell in row if cell):
            return None

        travel = {
            "source": None,
            "date_from": None,
            "date_to": None,
            "itinerary": None, # location/destination
            "purpose": None,
            "type": None # e.g. "gift-travel"
        }

        # Map columns by header keywords
        for idx, header in enumerate(headers):
            if idx >= len(row):
                break

            cell_value = row[idx].strip()
            if not cell_value:
                continue

            # Source
            if "source" in header or "sponsor" in header:
                travel["source"] = cell_value

            # Dates
            elif "date" in header:
                # Often "Dates" column has range like "01/01/2023 - 01/05/2023"
                if "-" in cell_value:
                    parts = cell_value.split("-")
                    if len(parts) >= 2:
                        travel["date_from"] = parts[0].strip()
                        travel["date_to"] = parts[1].strip()
                    else:
                        travel["date_from"] = cell_value
                else:
                    travel["date_from"] = cell_value

            # Itinerary / Location
            elif "itinerary" in header or "location" in header or "destination" in header:
                travel["itinerary"] = cell_value

            # Purpose
            elif "purpose" in header:
                travel["purpose"] = cell_value
            
            # Type
            elif "type" in header:
                travel["type"] = cell_value

        # Validate travel has at least source
        if not travel["source"]:
            logger.debug("Skipping row without source")
            return None

        return travel
