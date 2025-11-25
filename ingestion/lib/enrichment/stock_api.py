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
from typing import Optional, Dict, Any
import yfinance as yf

from .cache import EnrichmentCache

logger = logging.getLogger(__name__)


class StockAPIEnricher:
    """Enricher for stock data using Yahoo Finance."""

    # Common ticker patterns in PTR asset names
    TICKER_PATTERNS = [
        r'\(([A-Z]{1,5})\)$',  # "Company Name (TICKER)"
        r'\b([A-Z]{2,5})\s*$',  # "TICKER" at end
        r'ticker:\s*([A-Z]{1,5})',  # "ticker: TICKER"
        r'symbol:\s*([A-Z]{1,5})'  # "symbol: TICKER"
    ]

    def __init__(self, use_cache: bool = True):
        """
        Initialize stock API enricher.

        Args:
            use_cache: Whether to use caching (default True)
        """
        self.cache = EnrichmentCache() if use_cache else None

    def extract_ticker_from_name(self, asset_name: str) -> Optional[str]:
        """
        Extract ticker symbol from asset name using regex patterns.

        Args:
            asset_name: Full asset name from PTR

        Returns:
            Ticker symbol or None
        """
        for pattern in self.TICKER_PATTERNS:
            match = re.search(pattern, asset_name, re.IGNORECASE)
            if match:
                ticker = match.group(1).upper()
                # Validate ticker (1-5 uppercase letters)
                if re.match(r'^[A-Z]{1,5}$', ticker):
                    return ticker

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
                logger.info(f"Cache hit for ticker {ticker}")
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
            asset_name: Full asset name from PTR

        Returns:
            Enriched asset data dict
        """
        # Extract ticker
        ticker = self.extract_ticker_from_name(asset_name)

        if not ticker:
            return {
                'ticker_symbol': None,
                'company_name': None,
                'sector': None,
                'industry': None,
                'market_cap': None,
                'market_cap_category': None,
                'exchange': None,
                'is_publicly_traded': False,
                'enrichment_status': 'ticker_not_found',
                'extraction_method': 'regex_failed'
            }

        # Validate and fetch stock info
        stock_info = self.get_stock_info(ticker)

        if not stock_info:
            return {
                'ticker_symbol': ticker,
                'company_name': None,
                'sector': None,
                'industry': None,
                'market_cap': None,
                'market_cap_category': None,
                'exchange': None,
                'is_publicly_traded': False,
                'enrichment_status': 'api_failed',
                'extraction_method': 'regex'
            }

        # Success
        stock_info['enrichment_status'] = 'success'
        stock_info['extraction_method'] = 'regex+yahoo_finance'
        return stock_info

    def classify_asset_type(self, asset_name: str) -> str:
        """
        Classify asset type from name.

        Args:
            asset_name: Full asset name

        Returns:
            Asset type string
        """
        name_lower = asset_name.lower()

        if any(x in name_lower for x in ['etf', 'index fund', 'spdr', 'ishares']):
            return 'ETF'
        elif any(x in name_lower for x in ['mutual fund', 'fund']):
            return 'Mutual Fund'
        elif any(x in name_lower for x in ['bond', 'treasury', 'note']):
            return 'Bond'
        elif any(x in name_lower for x in ['bitcoin', 'ethereum', 'crypto', 'btc', 'eth']):
            return 'Cryptocurrency'
        elif any(x in name_lower for x in ['option', 'call', 'put']):
            return 'Option'
        elif any(x in name_lower for x in ['real estate', 'property', 'land']):
            return 'Real Estate'
        elif any(x in name_lower for x in ['stock', 'common stock', 'equity']):
            return 'Stock'
        else:
            # Default to Stock if ticker found
            ticker = self.extract_ticker_from_name(asset_name)
            return 'Stock' if ticker else 'Other'
