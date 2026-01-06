"""
Company name to ticker symbol lookup with fuzzy matching.

This module provides functionality to match company names from financial disclosures
to their ticker symbols using the SEC's company ticker mapping.

Uses difflib for fuzzy string matching to handle variations in company names.
"""

import os
import json
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class CompanyTickerLookup:
    """
    Lookup ticker symbols from company names using SEC data with fuzzy matching.

    This class loads the SEC company tickers database and provides fuzzy matching
    to find ticker symbols from company names that may have slight variations.
    """

    # Common corporate suffixes to remove for normalization
    CORPORATE_SUFFIXES = [
        'Inc.', 'Inc', 'Incorporated',
        'Corp.', 'Corp', 'Corporation',
        'Ltd.', 'Ltd', 'Limited',
        'LLC', 'L.L.C.', 'L.L.C',
        'LP', 'L.P.', 'L.P',
        'LLP', 'L.L.P.', 'L.L.P',
        'PLC', 'P.L.C.', 'P.L.C',
        'SA', 'S.A.', 'S.A',
        'AG', 'NV', 'SE', 'Co.', 'Co', 'Company', 'Companies',
        '/DE/', '/DE', '/MD/', '/MD', '/NV/', '/NV', '/CA/', '/CA',
        '\\DE\\', '\\DE', '\\MD\\', '\\MD',
    ]

    def __init__(self, sec_tickers_path: Optional[str] = None):
        """
        Initialize company ticker lookup.

        Args:
            sec_tickers_path: Path to SEC tickers JSON file. If None, uses default path.
        """
        if sec_tickers_path is None:
            # Default path relative to this file
            default_path = Path(__file__).parent / 'data' / 'sec_tickers.json'
            sec_tickers_path = str(default_path)

        self.sec_tickers_path = sec_tickers_path
        self.company_index: Dict[str, str] = {}  # normalized_name -> ticker
        self.ticker_to_company: Dict[str, str] = {}  # ticker -> original_name

        self._load_sec_data()

    def _load_sec_data(self):
        """Load and index SEC company tickers data."""
        if not os.path.exists(self.sec_tickers_path):
            logger.warning(f"SEC tickers file not found: {self.sec_tickers_path}")
            return

        try:
            with open(self.sec_tickers_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Build index: normalized name -> ticker
            for key, company_data in data.items():
                ticker = company_data.get('ticker', '').upper()
                title = company_data.get('title', '')

                if not ticker or not title:
                    continue

                # Store original name
                self.ticker_to_company[ticker] = title

                # Normalize and index
                normalized = self.normalize_company_name(title)
                if normalized:
                    self.company_index[normalized] = ticker

            logger.info(f"Loaded {len(self.company_index)} companies from SEC data")

        except Exception as e:
            logger.error(f"Error loading SEC tickers: {e}")

    def normalize_company_name(self, company_name: str) -> str:
        """
        Normalize company name for matching.

        Args:
            company_name: Raw company name

        Returns:
            Normalized name (lowercase, no suffixes, no special chars)
        """
        if not company_name:
            return ""

        # Start with original
        normalized = company_name

        # Remove corporate suffixes (case insensitive)
        for suffix in self.CORPORATE_SUFFIXES:
            # Try exact match at end
            pattern = re.compile(re.escape(suffix) + r'\s*$', re.IGNORECASE)
            normalized = pattern.sub('', normalized)

            # Also try with word boundaries
            pattern = re.compile(r'\b' + re.escape(suffix) + r'\b\s*', re.IGNORECASE)
            normalized = pattern.sub('', normalized)

        # Remove special characters but keep spaces
        normalized = re.sub(r'[^a-zA-Z0-9\s]', ' ', normalized)

        # Collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized)

        # Lowercase and strip
        normalized = normalized.lower().strip()

        return normalized

    def similarity_score(self, str1: str, str2: str) -> float:
        """
        Calculate similarity score between two strings.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score 0-100
        """
        return SequenceMatcher(None, str1, str2).ratio() * 100

    def lookup_ticker(self, company_name: str, threshold: float = 85.0) -> Optional[Tuple[str, float]]:
        """
        Lookup ticker symbol from company name using fuzzy matching.

        Args:
            company_name: Company name to lookup
            threshold: Minimum similarity score (0-100)

        Returns:
            Tuple of (ticker, confidence_score) or None if no match
        """
        if not company_name or not self.company_index:
            return None

        # Normalize input
        normalized_input = self.normalize_company_name(company_name)

        if not normalized_input:
            return None

        # First try exact match
        if normalized_input in self.company_index:
            ticker = self.company_index[normalized_input]
            logger.info(f"Exact match: '{company_name}' → {ticker}")
            return (ticker, 100.0)

        # Fuzzy match: find best match above threshold
        best_match = None
        best_score = 0.0
        best_ticker = None

        for indexed_name, ticker in self.company_index.items():
            score = self.similarity_score(normalized_input, indexed_name)

            if score > best_score:
                best_score = score
                best_match = indexed_name
                best_ticker = ticker

        if best_score >= threshold and best_ticker:
            logger.info(f"Fuzzy match: '{company_name}' → {best_ticker} "
                       f"(score: {best_score:.1f}%, matched: '{best_match}')")
            return (best_ticker, best_score)

        logger.debug(f"No match found for '{company_name}' (best score: {best_score:.1f}%)")
        return None

    def get_company_name(self, ticker: str) -> Optional[str]:
        """
        Get official company name for a ticker.

        Args:
            ticker: Ticker symbol

        Returns:
            Company name or None
        """
        return self.ticker_to_company.get(ticker.upper())
