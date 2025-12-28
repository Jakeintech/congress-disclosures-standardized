"""
Stock API enrichment for asset data.

Enriches asset records with:
- Ticker symbol extraction/validation
- Company name
- Sector & industry (GICS classification)
- Market capitalization
- Exchange
"""

import os
import re
import logging
from typing import Optional, Dict, Any, Tuple
import yfinance as yf

from .cache import EnrichmentCache
from .company_lookup import CompanyTickerLookup

logger = logging.getLogger(__name__)


class StockAPIEnricher:
    """Enricher for stock data using Yahoo Finance."""

    # Common ticker patterns in PTR asset names
    # Prioritized: more specific patterns first
    TICKER_PATTERNS = [
        r'\(([A-Z]{1,5})\)',  # "Company Name (TICKER)" - most reliable
        r'ticker:\s*([A-Z]{1,5})',  # "ticker: TICKER"
        r'symbol:\s*([A-Z]{1,5})',  # "symbol: TICKER"
        r'\[([A-Z]{1,5})\]',  # "[TICKER] Company Name"
        r'^([A-Z]{1,5})\s*[-:]',  # "AAPL - Apple Inc" or "MSFT: Microsoft"
        r'\b([A-Z]{3,5})\b(?=\s+(?:stock|shares|common|ordinary|class))',  # "AAPL Stock", "MSFT Shares"
    ]

    # Blacklist of invalid "tickers" (common words, filing metadata, generic terms)
    TICKER_BLACKLIST = {
        # Common words that aren't tickers
        'STOCK', 'STOCKS', 'TRUST', 'TRUSTS', 'UNITS', 'UNIT', 'BANK',
        'BANKS', 'BOND', 'BONDS', 'FUND', 'FUNDS', 'GROUP', 'GROUPS',
        'CORP', 'CORPS', 'INC', 'LLC', 'LTD', 'LP', 'LLP', 'COMPANY',
        'COMPANIES', 'SHARES', 'SHARE', 'CLASS', 'SERIES', 'COMMON',
        'PREFERRED', 'ORDINARY', 'EQUITY', 'ASSET', 'ASSETS', 'HOLDING',
        'HOLDINGS', 'INVESTMENT', 'INVESTMENTS', 'CAPITAL', 'GROWTH',
        'VALUE', 'INDEX', 'REAL', 'ESTATE', 'PROPERTY', 'LAND',
        'NOTE', 'NOTES', 'SECURITY', 'SECURITIES', 'MUTUAL',
        # Filing metadata prefixes
        'SP', 'JT', 'DC', 'SO', 'FS', 'HN',
        # Common suffixes/words
        'CO', 'THE', 'AND', 'FOR', 'NEW', 'RENT', 'LIFE', 'CARE',
        'GLOBAL', 'INTERNATIONAL', 'NATIONAL', 'AMERICAN', 'US', 'USA',
        # Geographic indicators
        'USA', 'UK', 'EU', 'NYC', 'LA',
    }

    # Filing metadata prefixes to strip from asset names
    # Note: These patterns are applied iteratively, so order doesn't matter
    FILING_METADATA_PREFIXES = [
        r'^SP\s+',  # Spouse/Dependent
        r'^JT\s+',  # Joint
        r'^DC\s+',  # Dependent Child
        r'^SO\s+',  # Spouse Only
        r'^S\s+O:\s*[^\n]*\n',  # S O: prefix with content until newline
        r'^F\s+S:\s*[^\n]*\n',  # F S: prefix with content until newline
        r'^D:\s*[^\n]*\n',  # D: prefix with content until newline
        r'F\s+S:\s+New\s+',  # F S: New (inline)
        r'S\s+O:\s+',  # S O: (inline)
        r'D:\s+',  # D: (inline)
    ]

    def __init__(self, use_cache: bool = True, use_company_lookup: bool = True):
        """
        Initialize stock API enricher.

        Args:
            use_cache: Whether to use caching (default True)
            use_company_lookup: Whether to use company name lookup fallback (default True)
        """
        self.cache = EnrichmentCache() if use_cache else None
        self.company_lookup = CompanyTickerLookup() if use_company_lookup else None

    def clean_asset_name(self, asset_name: str) -> tuple[str, Optional[str]]:
        """
        Clean asset name by removing filing metadata prefixes.

        Args:
            asset_name: Raw asset name from PTR (may contain prefixes like "SP", "JT", etc.)

        Returns:
            Tuple of (cleaned_name, ownership_indicator)
            - cleaned_name: Asset name with metadata stripped
            - ownership_indicator: Detected prefix (SP, JT, DC, etc.) or None
        """
        if not asset_name:
            return asset_name, None

        # Detect ownership indicator by searching anywhere in the text
        # (not just at the start, since multiline text may have it embedded)
        ownership_indicator = None

        # Look for standalone SP/JT/DC indicators (word boundaries)
        if re.search(r'\bSP\b', asset_name, re.IGNORECASE):
            ownership_indicator = 'SP'
        elif re.search(r'\bJT\b', asset_name, re.IGNORECASE):
            ownership_indicator = 'JT'
        elif re.search(r'\bDC\b', asset_name, re.IGNORECASE):
            ownership_indicator = 'DC'
        elif re.search(r'\bSO\b|S\s+O:', asset_name, re.IGNORECASE):
            ownership_indicator = 'SO'

        # Strip all metadata prefixes (apply iteratively)
        cleaned = asset_name
        for pattern in self.FILING_METADATA_PREFIXES:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)

        # Additional cleanup: remove extra whitespace and newlines
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Remove leading/trailing punctuation
        cleaned = cleaned.strip('.,;:-_')

        # If we detected SP/JT/DC, remove it from the cleaned name as well
        if ownership_indicator:
            cleaned = re.sub(r'\b' + ownership_indicator + r'\b', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned, ownership_indicator

    def preprocess_arrow_notation(self, asset_name: str) -> str:
        """
        Preprocess arrow notation (⇒, →) to extract final asset.

        Arrow notation typically represents account transitions:
        "Old Account ⇒ Final Asset (TICKER)"

        Args:
            asset_name: Asset name potentially containing arrows

        Returns:
            Processed asset name (text after last arrow, or original if no arrows)
        """
        if not asset_name:
            return asset_name

        # Check for arrow symbols
        if '⇒' in asset_name:
            # Take text after LAST arrow
            parts = asset_name.split('⇒')
            return parts[-1].strip()
        elif '→' in asset_name:
            parts = asset_name.split('→')
            return parts[-1].strip()
        elif '->' in asset_name:
            parts = asset_name.split('->')
            return parts[-1].strip()

        return asset_name

    def extract_ticker_from_name(self, asset_name: str) -> Optional[Tuple[str, str]]:
        """
        Extract ticker symbol from asset name using regex patterns and company lookup.

        Extraction strategy:
        1. Preprocess arrow notation (⇒, →) to extract final asset
        2. Clean metadata (SP, JT, DC prefixes)
        3. Try regex pattern matching
        4. Fall back to company name fuzzy matching

        Args:
            asset_name: Full asset name from PTR

        Returns:
            Tuple of (ticker, extraction_method) or None
            extraction_method values:
            - 'regex_parentheses'
            - 'regex_brackets'
            - 'regex_prefix'
            - 'regex_suffix'
            - 'arrow_then_regex'
            - 'company_fuzzy_match'
        """
        if not asset_name:
            return None

        # Step 1: Preprocess arrow notation
        has_arrow = '⇒' in asset_name or '→' in asset_name or '->' in asset_name
        preprocessed = self.preprocess_arrow_notation(asset_name)

        # Step 2: Clean metadata
        cleaned_name, _ = self.clean_asset_name(preprocessed)

        # Step 3: Try regex pattern matching
        for i, pattern in enumerate(self.TICKER_PATTERNS):
            match = re.search(pattern, cleaned_name, re.IGNORECASE)
            if match:
                ticker = match.group(1).upper()

                # Validate ticker format (1-5 uppercase letters)
                if not re.match(r'^[A-Z]{1,5}$', ticker):
                    continue

                # Check against blacklist
                if ticker in self.TICKER_BLACKLIST:
                    logger.debug(f"Skipping blacklisted ticker: {ticker}")
                    continue

                # Determine extraction method based on pattern index
                if i == 0:  # parentheses
                    method = 'arrow_then_regex_paren' if has_arrow else 'regex_parentheses'
                elif i == 3:  # brackets
                    method = 'regex_brackets'
                elif i == 4:  # prefix
                    method = 'regex_prefix'
                else:
                    method = 'arrow_then_regex' if has_arrow else 'regex_other'

                return (ticker, method)

        # Step 4: Fall back to company name lookup
        if self.company_lookup:
            result = self.company_lookup.lookup_ticker(cleaned_name, threshold=85.0)
            if result:
                ticker, confidence = result
                return (ticker, f'company_fuzzy_match_{confidence:.0f}')

        return None

    def validate_ticker(self, ticker: str) -> bool:
        """
        Validate ticker symbol via Yahoo Finance.

        Args:
            ticker: Ticker symbol to validate

        Returns:
            True if ticker exists and is valid
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Check if ticker returns valid data
            if info and info.get('symbol'):
                return True

            return False

        except Exception:
            return False

    def get_stock_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get stock information from Yahoo Finance.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Stock info dict or None
        """
        # Check cache
        if self.cache:
            cached = self.cache.get('stock_api', ticker)
            if cached:
                # logger.info(f"Cache hit for ticker {ticker}")
                return cached

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or not info.get('symbol'):
                logger.warning(f"No data found for ticker {ticker}")
                return None

            # Extract relevant fields
            stock_data = {
                'ticker_symbol': info.get('symbol'),
                'company_name': info.get('longName') or info.get('shortName'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'market_cap': info.get('marketCap'),
                'market_cap_category': self._categorize_market_cap(info.get('marketCap')),
                'exchange': info.get('exchange'),
                'is_publicly_traded': True,
                'currency': info.get('currency'),
                'country': info.get('country')
            }

            # Cache result
            if self.cache:
                self.cache.set('stock_api', ticker, stock_data)

            logger.info(f"Enriched {ticker}: {stock_data.get('company_name')}")
            return stock_data

        except Exception as e:
            logger.error(f"Error fetching stock info for {ticker}: {e}")
            return None

    def _categorize_market_cap(self, market_cap: Optional[int]) -> Optional[str]:
        """Categorize market cap into size buckets."""
        if not market_cap:
            return None

        if market_cap >= 10_000_000_000:  # $10B+
            return "Large"
        elif market_cap >= 2_000_000_000:  # $2B-$10B
            return "Mid"
        elif market_cap >= 300_000_000:  # $300M-$2B
            return "Small"
        elif market_cap >= 50_000_000:  # $50M-$300M
            return "Micro"
        else:  # <$50M
            return "Nano"

    def enrich_asset(self, asset_name: str) -> Dict[str, Any]:
        """
        Enrich asset data with stock information.

        Args:
            asset_name: Full asset name from PTR (may contain metadata prefixes)

        Returns:
            Enriched asset data dict with cleaned names and ownership info
        """
        # Clean asset name and extract ownership indicator
        cleaned_name, ownership_indicator = self.clean_asset_name(asset_name)

        # Extract ticker from cleaned name (returns tuple of (ticker, method) or None)
        ticker_result = self.extract_ticker_from_name(asset_name)

        base_result = {
            'cleaned_asset_name': cleaned_name,
            'ownership_indicator': ownership_indicator,
        }

        if not ticker_result:
            return {
                **base_result,
                'ticker_symbol': None,
                'company_name': None,
                'sector': None,
                'industry': None,
                'market_cap': None,
                'market_cap_category': None,
                'exchange': None,
                'is_publicly_traded': False,
                'enrichment_status': 'ticker_not_found',
                'extraction_method': 'none'
            }

        # Unpack ticker and extraction method
        ticker, extraction_method = ticker_result

        # Validate and fetch stock info
        stock_info = self.get_stock_info(ticker)

        if not stock_info:
            return {
                **base_result,
                'ticker_symbol': ticker,
                'company_name': None,
                'sector': None,
                'industry': None,
                'market_cap': None,
                'market_cap_category': None,
                'exchange': None,
                'is_publicly_traded': False,
                'enrichment_status': 'api_failed',
                'extraction_method': extraction_method
            }

        # Success - merge with base result
        stock_info['enrichment_status'] = 'success'
        stock_info['extraction_method'] = extraction_method
        return {**base_result, **stock_info}

    def classify_asset_type(self, asset_name: str) -> str:
        """
        Classify asset type from name.

        Args:
            asset_name: Full asset name

        Returns:
            Asset type string
        """
        # Clean the name first for more accurate classification
        cleaned_name, _ = self.clean_asset_name(asset_name)
        name_lower = cleaned_name.lower()

        # Priority order: most specific first
        if any(x in name_lower for x in ['etf', 'exchange traded fund', 'spdr', 'ishares', 'vanguard etf']):
            return 'ETF'
        elif any(x in name_lower for x in ['mutual fund', 'index fund', 'vanguard fund']):
            return 'Mutual Fund'
        elif any(x in name_lower for x in ['bond', 'treasury', 'note', 'debenture']):
            return 'Bond'
        elif any(x in name_lower for x in ['bitcoin', 'ethereum', 'crypto', 'btc', 'eth', 'cryptocurrency']):
            return 'Cryptocurrency'
        elif any(x in name_lower for x in ['option', 'call option', 'put option', 'warrant']):
            return 'Option'
        elif any(x in name_lower for x in ['real estate', 'property', 'land', 'reit']):
            return 'Real Estate'
        elif 'hedge fund' in name_lower or 'private equity' in name_lower:
            return 'Alternative Investment'
        else:
            # Only classify as Stock if we can extract a valid ticker
            # Don't classify based on the word "stock" alone (too many false positives)
            ticker_result = self.extract_ticker_from_name(asset_name)
            if ticker_result:
                ticker, _ = ticker_result
                if ticker not in self.TICKER_BLACKLIST:
                    return 'Stock'
            # Check for specific stock-related keywords with company names
            if any(x in name_lower for x in ['inc.', 'corp.', 'corporation', 'incorporated', 'plc', 'ltd']) and \
                 not any(x in name_lower for x in ['fund', 'trust', 'partnership']):
                return 'Stock'
            else:
                return 'Other'
