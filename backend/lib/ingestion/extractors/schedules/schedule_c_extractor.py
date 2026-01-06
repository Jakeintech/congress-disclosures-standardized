"""Schedule C: Earned Income and Honoraria extractor.

Parses Schedule C tables containing employment income, salaries, and honoraria received
by the filer or their spouse.
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ScheduleCExtractor:
    """Extract Schedule C (Earned Income) from table data."""

    def parse_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Schedule C table into list of income sources.

        Args:
            table: Parsed table dict with 'headers' and 'rows'

        Returns:
            List of income dictionaries matching schedule_c_earned_income schema
        """
        income_sources = []
        headers = [h.lower() for h in table.get("headers", [])]
        rows = table.get("rows", [])

        logger.debug(f"Parsing Schedule C table with {len(rows)} rows")

        for row in rows:
            income = self._parse_row(row, headers)
            if income:
                income_sources.append(income)

        logger.info(f"Extracted {len(income_sources)} income sources from Schedule C")
        return income_sources

    def _parse_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a single table row into an income dictionary.

        Args:
            row: List of cell values
            headers: List of column headers (lowercase)

        Returns:
            Income dictionary or None if row is empty/invalid
        """
        # Skip empty rows
        if not any(cell.strip() for cell in row if cell):
            return None

        income = {
            "source": None,
            "type": None,
            "current_year_amount": None,
            "preceding_year_amount": None,
            "description": None
        }

        # Map columns by header keywords
        for idx, header in enumerate(headers):
            if idx >= len(row):
                break

            cell_value = row[idx].strip()
            if not cell_value:
                continue

            # Source name (employer)
            if any(kw in header for kw in ["source", "employer", "name"]):
                income["source"] = cell_value

            # Type of income
            elif any(kw in header for kw in ["type", "salary", "honoraria"]):
                income["type"] = cell_value

            # Current year amount
            elif any(kw in header for kw in ["current year", "amount"]) and "preceding" not in header:
                amount = self._parse_amount(cell_value)
                if amount is not None:
                    income["current_year_amount"] = amount

            # Preceding year amount
            elif any(kw in header for kw in ["preceding year", "prior year"]):
                amount = self._parse_amount(cell_value)
                if amount is not None:
                    income["preceding_year_amount"] = amount

            # Description/brief description
            elif "description" in header or "brief" in header:
                income["description"] = cell_value

        # Validate income has at least source and type
        if not income["source"] or not income["type"]:
            logger.debug("Skipping row without source or type")
            return None

        return income

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string into float value.

        Args:
            amount_str: Amount string (e.g., "$125,000" or "125000")

        Returns:
            Float amount or None if parsing fails
        """
        if not amount_str:
            return None

        # Remove currency symbols, commas, whitespace
        amount_str = amount_str.replace('$', '').replace(',', '').strip()

        try:
            return float(amount_str)
        except ValueError:
            # Try to extract first number if present
            number_match = re.search(r'([\d.]+)', amount_str)
            if number_match:
                try:
                    return float(number_match.group(1))
                except ValueError:
                    pass

        logger.warning(f"Failed to parse amount: {amount_str}")
        return None
