"""Utility functions for extracting fields from Annual Financial Disclosure forms.

This module provides reusable extraction utilities specific to Type A/N (Annual/New Filer)
financial disclosures, including asset values, income types, and standardized codes.
"""

import re
from typing import Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def extract_asset_value_range(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse asset value ranges from disclosure text.
    
    Annual filings use standardized value ranges from the House ethics form.
    Common ranges include:
    - None (or less than $1,001)
    - $1,001 - $15,000
    - $15,001 - $50,000
    - $50,001 - $100,000
    - $100,001 - $250,000
    - $250,001 - $500,000
    - $500,001 - $1,000,000
    - $1,000,001 - $5,000,000
    - $5,000,001 - $25,000,000
    - $25,000,001 - $50,000,000
    - Over $50,000,000
    
    Args:
        text: Text containing value range
        
    Returns:
        Tuple of (low, high) in dollars, or (None, None) if not found
    """
    if not text:
        return (None, None)
    
    # Handle "None" or "less than" cases
    if re.search(r'None|N/A|less than|under \$1,?001', text, re.IGNORECASE):
        return (0, 1000)
    
    # Handle "Over $X,XXX,XXX" cases
    over_match = re.search(r'Over\s+\$?([\d,]+)', text, re.IGNORECASE)
    if over_match:
        amount = int(over_match.group(1).replace(',', ''))
        return (amount + 1, None)  # High bound is None for "over" values
    
    # Standard range pattern: "$X,XXX - $X,XXX" or "$X,XXX-$X,XXX"
    range_match = re.search(
        r'\$?([\d,]+)\s*[-–]\s*\$?([\d,]+)',
        text
    )
    
    if range_match:
        try:
            low = int(range_match.group(1).replace(',', ''))
            high = int(range_match.group(2).replace(',', ''))
            return (low, high)
        except ValueError:
            logger.warning(f"Failed to parse value range: {text}")
            return (None, None)
    
    # Single value pattern: "$X,XXX"
    single_match = re.search(r'\$?([\d,]+)', text)
    if single_match:
        try:
            value = int(single_match.group(1).replace(',', ''))
            # If single value, use it as both bounds
            return (value, value)
        except ValueError:
            pass
    
    return (None, None)


def extract_income_type(text: str) -> str:
    """Identify and standardize income type from disclosure text.
    
    Common income types on Schedule A:
    - Dividends
    - Rent
    - Interest
    - Capital Gains (short-term or long-term)
    - Earned Income (non-investment income)
    - Other
    
    Args:
        text: Text containing income type information
        
    Returns:
        Standardized income type string
    """
    if not text:
        return "Unknown"
    
    text_lower = text.lower()
    
    # Map keywords to standard types
    if 'dividend' in text_lower:
        return "Dividends"
    elif 'rent' in text_lower or 'rental' in text_lower:
        return "Rent"
    elif 'interest' in text_lower:
        return "Interest"
    elif 'capital gain' in text_lower or 'cap gain' in text_lower:
        if 'long' in text_lower:
            return "Capital Gains (Long-Term)"
        elif 'short' in text_lower:
            return "Capital Gains (Short-Term)"
        return "Capital Gains"
    elif 'earned' in text_lower or 'salary' in text_lower or 'wages' in text_lower:
        return "Earned Income"
    elif 'royalt' in text_lower:
        return "Royalties"
    elif 'none' in text_lower or 'n/a' in text_lower:
        return "None"
    else:
        return "Other"


def parse_owner_code(text: str) -> str:
    """Extract and validate owner code from disclosure text.
    
    Standard owner codes:
    - SP: Spouse
    - DC: Dependent Child
    - JT: Joint (with spouse)
    - Self: Filer alone (default if no code found)
    
    Args:
        text: Text containing owner code
        
    Returns:
        Standardized owner code
    """
    if not text:
        return "Self"
    
    # Look for standard codes
    text_upper = text.upper()
    
    if 'SP' in text_upper and 'SPOUSE' not in text_upper:
        return "SP"
    elif 'SPOUSE' in text_upper:
        return "SP"
    elif 'DC' in text_upper or 'DEPENDENT CHILD' in text_upper:
        return "DC"
    elif 'JT' in text_upper or 'JOINT' in text_upper:
        return "JT"
    elif 'SELF' in text_upper or 'FILER' in text_upper:
        return "Self"
    
    # Default to Self if no clear code
    return "Self"


def extract_asset_type(text: str) -> str:
    """Classify asset type based on description.
    
    Common asset types:
    - Stock (publicly traded)
    - Bond
    - Mutual Fund
    - ETF (Exchange-Traded Fund)
    - Real Property
    - Retirement Account (IRA, 401k, etc.)
    - Bank Account
    - Trust
    - Partnership Interest
    - LLC Interest
    - Other
    
    Args:
        text: Asset description text
        
    Returns:
        Classified asset type
    """
    if not text:
        return "Unknown"
    
    text_lower = text.lower()
    
    # Check for specific keywords
    # Check for Stock Option first to avoid misclassification as Stock
    if 'stock option' in text_lower or 'option' in text_lower:
        return "Stock Option"
    elif 'stock' in text_lower or 'class a' in text_lower or 'class b' in text_lower:
        return "Stock"
    elif 'bond' in text_lower or 'treasury' in text_lower or 'municipal' in text_lower:
        return "Bond"
    elif 'mutual fund' in text_lower or 'fund' in text_lower:
        return "Mutual Fund"
    elif 'etf' in text_lower or 'exchange-traded' in text_lower or 'exchange traded' in text_lower:
        return "ETF"
    elif 'real property' in text_lower or 'real estate' in text_lower or 'land' in text_lower:
        return "Real Property"
    elif 'ira' in text_lower or '401' in text_lower or 'retirement' in text_lower or 'pension' in text_lower:
        return "Retirement Account"
    elif 'bank account' in text_lower or 'savings' in text_lower or 'checking' in text_lower:
        return "Bank Account"
    elif 'trust' in text_lower:
        return "Trust"
    elif 'partnership' in text_lower or 'limited partner' in text_lower:
        return "Partnership Interest"
    elif 'llc' in text_lower or 'limited liability' in text_lower:
        return "LLC Interest"
    elif 'cryptocurrency' in text_lower or 'bitcoin' in text_lower or 'crypto' in text_lower:
        return "Cryptocurrency"
    else:
        return "Other"


def normalize_date_format(date_str: str) -> Optional[str]:
    """Convert various date formats to ISO 8601 (YYYY-MM-DD).
    
    Handles common formats:
    - MM/DD/YYYY
    - MM-DD-YYYY
    - Month DD, YYYY
    - DD Month YYYY
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        ISO 8601 formatted date string (YYYY-MM-DD) or None if parsing fails
    """
    if not date_str:
        return None
    
    # Clean the input
    date_str = date_str.strip()
    
    # Try common formats
    formats = [
        '%m/%d/%Y',      # 12/31/2024
        '%m-%d-%Y',      # 12-31-2024
        '%m/%d/%y',      # 12/31/24
        '%B %d, %Y',     # December 31, 2024
        '%b %d, %Y',     # Dec 31, 2024
        '%d %B %Y',      # 31 December 2024
        '%d %b %Y',      # 31 Dec 2024
        '%Y-%m-%d',      # 2024-12-31 (already ISO)
        '%Y/%m/%d',      # 2024/12/31
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    logger.warning(f"Failed to parse date: {date_str}")
    return None


def extract_ticker_symbol(text: str) -> Optional[str]:
    """Extract stock ticker symbol from asset description.
    
    Examples:
    - "Apple Inc. (AAPL)"
    - "(MSFT) Microsoft Corporation"
    - "GOOGL - Alphabet Inc."
    
    Args:
        text: Asset description containing ticker
        
    Returns:
        Ticker symbol or None if not found
    """
    if not text:
        return None
    
    # Pattern 1: Ticker in parentheses
    paren_match = re.search(r'\(([A-Z]{1,5})\)', text)
    if paren_match:
        return paren_match.group(1)
    
    # Pattern 2: Ticker followed by dash or colon
    dash_match = re.search(r'\b([A-Z]{1,5})\s*[-:]\s', text)
    if dash_match:
        return dash_match.group(1)
    
    # Pattern 3: Standalone uppercase word (risky, but common)
    # Only if it's at the start or after specific keywords
    standalone_match = re.search(r'(?:^|Ticker:|Symbol:)\s*([A-Z]{1,5})\b', text)
    if standalone_match:
        return standalone_match.group(1)
    
    return None


def map_value_to_disclosure_category(low: Optional[int], high: Optional[int]) -> str:
    """Map numeric value range to disclosure category letter.
    
    Annual filings use category codes (letters) to represent value ranges.
    This is useful for standardization and comparison.
    
    Standard categories (approximations):
    - A: $1,001 - $15,000
    - B: $15,001 - $50,000
    - C: $50,001 - $100,000
    - D: $100,001 - $250,000
    - E: $250,001 - $500,000
    - F: $500,001 - $1,000,000
    - G: $1,000,001 - $5,000,000
    - H: $5,000,001 - $25,000,000
    - I: $25,000,001 - $50,000,000
    - J: Over $50,000,000
    
    Args:
        low: Lower bound of range
        high: Upper bound of range
        
    Returns:
        Category letter (A-J) or "Unknown"
    """
    if low is None or high is None:
        return "Unknown"
    
    # Use midpoint for categorization
    midpoint = (low + high) / 2 if high is not None else low
    
    if midpoint <= 15000:
        return "A"
    elif midpoint <= 50000:
        return "B"
    elif midpoint <= 100000:
        return "C"
    elif midpoint <= 250000:
        return "D"
    elif midpoint <= 500000:
        return "E"
    elif midpoint <= 1000000:
        return "F"
    elif midpoint <= 5000000:
        return "G"
    elif midpoint <= 25000000:
        return "H"
    elif midpoint <= 50000000:
        return "I"
    else:
        return "J"


def clean_asset_name(text: str) -> str:
    """Clean and normalize asset name for consistency.
    
    Args:
        text: Raw asset name text
        
    Returns:
        Cleaned asset name
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', text).strip()
    
    # Remove common prefixes that don't add value
    cleaned = re.sub(r'^(Asset:|Description:)\s*', '', cleaned, flags=re.IGNORECASE)

    # Remove noise patterns (Filing ID, Doc ID, Page numbers)
    noise_patterns = [
        r'Filing\s+ID\s+#?\d+',
        r'Doc\s+ID\s+#?\d+',
        r'Page\s+\d+\s+of\s+\d+',
    ]
    for noise in noise_patterns:
        cleaned = re.sub(noise, '', cleaned, flags=re.IGNORECASE).strip()
    
    # Convert multiple dashes to single
    cleaned = re.sub(r'-{2,}', '-', cleaned)
    
    # Remove trailing punctuation
    cleaned = cleaned.rstrip('.,;:')
    
    return cleaned
