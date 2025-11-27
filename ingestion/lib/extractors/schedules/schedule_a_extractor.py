"""Schedule A: Assets and Unearned Income extractor.

Parses Schedule A tables containing asset holdings and income generated from those assets.
Handles various asset types including stocks, bonds, real estate, mutual funds, etc.
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ScheduleAExtractor:
    """Extract Schedule A (Assets and Unearned Income) from table data."""

    # Value range mappings (common formats in disclosure forms)
    VALUE_RANGES = {
        "$1,001 - $15,000": (1001, 15000),
        "$15,001 - $50,000": (15001, 50000),
        "$50,001 - $100,000": (50001, 100000),
        "$100,001 - $250,000": (100001, 250000),
        "$250,001 - $500,000": (250001, 500000),
        "$500,001 - $1,000,000": (500001, 1000000),
        "$1,000,001 - $5,000,000": (1000001, 5000000),
        "$5,000,001 - $25,000,000": (5000001, 25000000),
        "$25,000,001 - $50,000,000": (25000001, 50000000),
        "Over $50,000,000": (50000001, None),
    }

    # Asset type codes (two-letter codes used in some forms)
    # Extended based on https://fd.house.gov/reference/asset-type-codes.aspx
    ASSET_TYPE_CODES = {
        "BA": "Bank Account",
        "RP": "Real Property",
        "ST": "Stock",
        "BD": "Bond",
        "MF": "Mutual Fund",
        "RT": "Retirement Account",
        "TR": "Trust",
        "OT": "Other",
        "HE": "Hedge Fund",
        "OL": "Other Liability",
        "5F": "529 Plan",
        "IH": "Investment/Hedge Fund",
        "PS": "Private Sector",
        "EF": "Exchange Traded Fund",
        "WU": "Whole Life Insurance",
        "DC": "Defined Contribution Plan",
    }

    # Regex patterns for extracting embedded data
    ASSET_TYPE_CODE_REGEX = r'\[([A-Z0-9]{2,3})\]'  # [HE], [OL], [5F]
    STOCK_TICKER_REGEX = r'\(([A-Z]{1,5})\)$'  # (AMZN), (AAPL) at end
    DESCRIPTION_LINE_REGEX = r'(?:^|\n)DESCRIPTION:\s*(.+?)(?=\n|$)'
    LOCATION_LINE_REGEX = r'(?:^|\n)LOCATION:\s*(.+?)(?=\n|$)'
    ACCOUNT_GROUPING_REGEX = r'^(.+?(?:IRA|401K|Brokerage|529)\s*\d*)\s*⇒'

    def parse_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Schedule A table into list of assets.

        Args:
            table: Parsed table dict with 'headers' and 'rows'

        Returns:
            List of asset dictionaries matching schedule_a_assets schema
        """
        assets = []
        headers = [h.lower() for h in table.get("headers", [])]
        rows = table.get("rows", [])

        logger.debug(f"Parsing Schedule A table with {len(rows)} rows")

        for row in rows:
            asset = self._parse_row(row, headers)
            if asset:
                assets.append(asset)

        logger.info(f"Extracted {len(assets)} assets from Schedule A")
        return assets

    def _parse_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a single table row into an asset dictionary.

        Args:
            row: List of cell values
            headers: List of column headers (lowercase)

        Returns:
            Asset dictionary or None if row is empty/invalid
        """
        # Skip empty rows
        if not any(cell.strip() for cell in row if cell):
            return None

        asset = {
            "asset_name": None,
            "asset_type_code": None,
            "ticker": None,  # NEW: Stock ticker
            "account_grouping": None,  # NEW: IRA, 529 Plan, etc.
            "owner_code": None,
            "value_low": None,
            "value_high": None,
            "value_code": None,
            "location": None,
            "description": None,
            "income": []
        }

        # Map columns by header keywords
        for idx, header in enumerate(headers):
            if idx >= len(row):
                break

            cell_value = row[idx].strip()
            if not cell_value:
                continue

            # Asset description/name (usually first column)
            if any(kw in header for kw in ["asset", "description", "name"]):
                asset["asset_name"] = cell_value

                # Extract asset type code if present in brackets [XX] or [5F]
                type_code_match = re.search(self.ASSET_TYPE_CODE_REGEX, cell_value)
                if type_code_match:
                    asset["asset_type_code"] = type_code_match.group(1)
                    # Remove code from asset name
                    asset["asset_name"] = re.sub(self.ASSET_TYPE_CODE_REGEX, '', asset["asset_name"]).strip()

                # Extract stock ticker if present in parentheses (AMZN)
                ticker_match = re.search(self.STOCK_TICKER_REGEX, asset["asset_name"])
                if ticker_match:
                    asset["ticker"] = ticker_match.group(1)
                    # Optionally keep ticker in asset name for readability

                # Extract account grouping if present (IRA 1 ⇒, 529 Plan ⇒)
                grouping_match = re.search(self.ACCOUNT_GROUPING_REGEX, cell_value)
                if grouping_match:
                    asset["account_grouping"] = grouping_match.group(1).strip()

                # Check for DESCRIPTION: line embedded in cell value
                desc_match = re.search(self.DESCRIPTION_LINE_REGEX, cell_value, re.MULTILINE)
                if desc_match:
                    asset["description"] = desc_match.group(1).strip()
                    # Remove DESCRIPTION line from asset name
                    asset["asset_name"] = re.sub(self.DESCRIPTION_LINE_REGEX, '', asset["asset_name"], flags=re.MULTILINE).strip()

                # Check for LOCATION: line embedded in cell value
                loc_match = re.search(self.LOCATION_LINE_REGEX, cell_value, re.MULTILINE)
                if loc_match:
                    asset["location"] = loc_match.group(1).strip()
                    # Remove LOCATION line from asset name
                    asset["asset_name"] = re.sub(self.LOCATION_LINE_REGEX, '', asset["asset_name"], flags=re.MULTILINE).strip()

            # Owner code (SP/DC/JT/blank)
            elif any(kw in header for kw in ["owner", "sp/dc/jt"]):
                owner = cell_value.upper()
                if owner in ["SP", "DC", "JT", ""]:
                    asset["owner_code"] = owner if owner else ""

            # Value (range or specific amount)
            elif any(kw in header for kw in ["value", "amount"]):
                asset["value_code"] = cell_value
                value_range = self._parse_value_range(cell_value)
                if value_range:
                    asset["value_low"], asset["value_high"] = value_range

            # Location (for real property)
            elif "location" in header or "city" in header:
                asset["location"] = cell_value

            # Income type (can be comma-separated: "Capital Gains, Dividends")
            elif any(kw in header for kw in ["income type", "type of income"]):
                # Handle multiple income types separated by commas
                income_types = [t.strip() for t in cell_value.split(',')]

                if asset["income"] and len(asset["income"]) > 0:
                    # Add to last income entry
                    asset["income"][-1]["income_types"] = income_types
                    asset["income"][-1]["income_type"] = income_types[0]  # Keep first for backward compat
                else:
                    # Create new income entry
                    asset["income"].append({
                        "income_types": income_types,
                        "income_type": income_types[0]
                    })

            # Income amount (current year)
            elif any(kw in header for kw in ["income", "current year"]):
                income_range = self._parse_value_range(cell_value)
                if income_range:
                    if not asset["income"]:
                        asset["income"].append({})
                    asset["income"][-1]["current_year_low"] = income_range[0]
                    asset["income"][-1]["current_year_high"] = income_range[1]

        # Validate asset has at least a name
        if not asset["asset_name"]:
            logger.debug("Skipping row without asset name")
            return None

        # Categorize asset if type code present
        if asset["asset_type_code"] and asset["asset_type_code"] in self.ASSET_TYPE_CODES:
            asset["description"] = self.ASSET_TYPE_CODES[asset["asset_type_code"]]

        return asset

    def _parse_value_range(self, value_str: str) -> Optional[tuple]:
        """Parse value range string into (low, high) tuple.

        Args:
            value_str: Value string (e.g., "$100,001 - $250,000" or "Over $50,000,000")

        Returns:
            Tuple of (low, high) integers, or None if parsing fails
        """
        value_str = value_str.strip()

        # Try exact match first
        if value_str in self.VALUE_RANGES:
            return self.VALUE_RANGES[value_str]

        # Try pattern matching for custom ranges
        # Pattern: $X - $Y or $X,XXX - $Y,YYY
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

        # Pattern: Over $X or More than $X
        over_match = re.search(r'(?:Over|More than)\s*\$?([\d,]+)', value_str, re.IGNORECASE)
        if over_match:
            try:
                low = int(over_match.group(1).replace(',', ''))
                return (low, None)
            except ValueError:
                pass

        # Pattern: $X or less
        under_match = re.search(r'\$?([\d,]+)\s*or less', value_str, re.IGNORECASE)
        if under_match:
            try:
                high = int(under_match.group(1).replace(',', ''))
                return (0, high)
            except ValueError:
                pass

        # Pattern: Single value $X,XXX
        single_match = re.search(r'\$?([\d,]+)', value_str)
        if single_match:
            try:
                value = int(single_match.group(1).replace(',', ''))
                # Treat as exact value
                return (value, value)
            except ValueError:
                pass

        return None
