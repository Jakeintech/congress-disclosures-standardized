#!/usr/bin/env python3
"""
Map stock tickers to industry sectors for correlation analysis.

Uses GICS (Global Industry Classification Standard) sector codes
for S&P 500 stocks and common traded securities.
"""

from typing import List, Dict, Set
from collections import defaultdict


# Ticker to industry mapping (primary and secondary industries)
# Based on GICS sectors and common trading patterns
TICKER_INDUSTRY_MAP = {
    # Defense & Aerospace
    'LMT': {'primary': 'Defense', 'secondary': ['Technology']},
    'RTX': {'primary': 'Defense', 'secondary': ['Technology']},
    'BA': {'primary': 'Defense', 'secondary': ['Transportation']},
    'NOC': {'primary': 'Defense', 'secondary': ['Technology']},
    'GD': {'primary': 'Defense', 'secondary': []},
    'LHX': {'primary': 'Defense', 'secondary': ['Technology']},
    'HII': {'primary': 'Defense', 'secondary': []},
    'TXT': {'primary': 'Defense', 'secondary': ['Transportation']},

    # Healthcare & Pharmaceuticals
    'JNJ': {'primary': 'Healthcare', 'secondary': []},
    'UNH': {'primary': 'Healthcare', 'secondary': ['Finance']},
    'PFE': {'primary': 'Healthcare', 'secondary': []},
    'ABBV': {'primary': 'Healthcare', 'secondary': []},
    'MRK': {'primary': 'Healthcare', 'secondary': []},
    'TMO': {'primary': 'Healthcare', 'secondary': ['Technology']},
    'ABT': {'primary': 'Healthcare', 'secondary': []},
    'DHR': {'primary': 'Healthcare', 'secondary': ['Technology']},
    'CVS': {'primary': 'Healthcare', 'secondary': ['Finance']},
    'BMY': {'primary': 'Healthcare', 'secondary': []},
    'AMGN': {'primary': 'Healthcare', 'secondary': []},
    'GILD': {'primary': 'Healthcare', 'secondary': []},
    'CI': {'primary': 'Healthcare', 'secondary': ['Finance']},
    'HUM': {'primary': 'Healthcare', 'secondary': ['Finance']},
    'ISRG': {'primary': 'Healthcare', 'secondary': ['Technology']},
    'LLY': {'primary': 'Healthcare', 'secondary': []},
    'REGN': {'primary': 'Healthcare', 'secondary': []},
    'MRNA': {'primary': 'Healthcare', 'secondary': ['Technology']},
    'VRTX': {'primary': 'Healthcare', 'secondary': []},

    # Technology
    'AAPL': {'primary': 'Technology', 'secondary': []},
    'MSFT': {'primary': 'Technology', 'secondary': []},
    'GOOGL': {'primary': 'Technology', 'secondary': []},
    'GOOG': {'primary': 'Technology', 'secondary': []},
    'AMZN': {'primary': 'Technology', 'secondary': ['Transportation', 'Finance']},
    'META': {'primary': 'Technology', 'secondary': []},
    'NVDA': {'primary': 'Technology', 'secondary': ['Defense']},
    'TSLA': {'primary': 'Technology', 'secondary': ['Transportation', 'Energy']},
    'AMD': {'primary': 'Technology', 'secondary': ['Defense']},
    'INTC': {'primary': 'Technology', 'secondary': ['Defense']},
    'ORCL': {'primary': 'Technology', 'secondary': []},
    'IBM': {'primary': 'Technology', 'secondary': ['Defense']},
    'CRM': {'primary': 'Technology', 'secondary': []},
    'CSCO': {'primary': 'Technology', 'secondary': ['Defense']},
    'ADBE': {'primary': 'Technology', 'secondary': []},
    'NFLX': {'primary': 'Technology', 'secondary': []},
    'QCOM': {'primary': 'Technology', 'secondary': ['Defense']},
    'AVGO': {'primary': 'Technology', 'secondary': ['Defense']},
    'TXN': {'primary': 'Technology', 'secondary': ['Defense']},

    # Finance & Banking
    'JPM': {'primary': 'Finance', 'secondary': []},
    'BAC': {'primary': 'Finance', 'secondary': []},
    'WFC': {'primary': 'Finance', 'secondary': []},
    'C': {'primary': 'Finance', 'secondary': []},
    'GS': {'primary': 'Finance', 'secondary': []},
    'MS': {'primary': 'Finance', 'secondary': []},
    'BLK': {'primary': 'Finance', 'secondary': []},
    'SCHW': {'primary': 'Finance', 'secondary': []},
    'AXP': {'primary': 'Finance', 'secondary': []},
    'V': {'primary': 'Finance', 'secondary': ['Technology']},
    'MA': {'primary': 'Finance', 'secondary': ['Technology']},
    'PYPL': {'primary': 'Finance', 'secondary': ['Technology']},
    'SQ': {'primary': 'Finance', 'secondary': ['Technology']},
    'COIN': {'primary': 'Finance', 'secondary': ['Technology']},

    # Energy
    'XOM': {'primary': 'Energy', 'secondary': []},
    'CVX': {'primary': 'Energy', 'secondary': []},
    'COP': {'primary': 'Energy', 'secondary': []},
    'SLB': {'primary': 'Energy', 'secondary': []},
    'EOG': {'primary': 'Energy', 'secondary': []},
    'MPC': {'primary': 'Energy', 'secondary': []},
    'PSX': {'primary': 'Energy', 'secondary': []},
    'VLO': {'primary': 'Energy', 'secondary': []},
    'NEE': {'primary': 'Energy', 'secondary': []},
    'DUK': {'primary': 'Energy', 'secondary': []},
    'SO': {'primary': 'Energy', 'secondary': []},
    'D': {'primary': 'Energy', 'secondary': []},
    'AEP': {'primary': 'Energy', 'secondary': []},
    'ENPH': {'primary': 'Energy', 'secondary': ['Technology']},
    'SEDG': {'primary': 'Energy', 'secondary': ['Technology']},

    # Transportation
    'UPS': {'primary': 'Transportation', 'secondary': []},
    'FDX': {'primary': 'Transportation', 'secondary': []},
    'DAL': {'primary': 'Transportation', 'secondary': []},
    'AAL': {'primary': 'Transportation', 'secondary': []},
    'UAL': {'primary': 'Transportation', 'secondary': []},
    'LUV': {'primary': 'Transportation', 'secondary': []},
    'UNP': {'primary': 'Transportation', 'secondary': []},
    'CSX': {'primary': 'Transportation', 'secondary': []},
    'NSC': {'primary': 'Transportation', 'secondary': []},

    # Agriculture
    'ADM': {'primary': 'Agriculture', 'secondary': []},
    'BG': {'primary': 'Agriculture', 'secondary': []},
    'DE': {'primary': 'Agriculture', 'secondary': ['Technology']},
    'AGCO': {'primary': 'Agriculture', 'secondary': []},
    'CF': {'primary': 'Agriculture', 'secondary': []},
    'MOS': {'primary': 'Agriculture', 'secondary': []},

    # Real Estate
    'AMT': {'primary': 'Real Estate', 'secondary': ['Technology']},
    'PLD': {'primary': 'Real Estate', 'secondary': []},
    'CCI': {'primary': 'Real Estate', 'secondary': ['Technology']},
    'EQIX': {'primary': 'Real Estate', 'secondary': ['Technology']},
    'SPG': {'primary': 'Real Estate', 'secondary': []},
    'DLR': {'primary': 'Real Estate', 'secondary': ['Technology']},
    'PSA': {'primary': 'Real Estate', 'secondary': []},

    # ETFs (Exchange Traded Funds) - mapped to multiple sectors
    'SPY': {'primary': 'Finance', 'secondary': []},  # S&P 500 ETF
    'QQQ': {'primary': 'Technology', 'secondary': []},  # Nasdaq-100 ETF
    'DIA': {'primary': 'Finance', 'secondary': []},  # Dow Jones ETF
    'IWM': {'primary': 'Finance', 'secondary': []},  # Russell 2000 ETF
    'XLF': {'primary': 'Finance', 'secondary': []},  # Financial Select Sector
    'XLE': {'primary': 'Energy', 'secondary': []},  # Energy Select Sector
    'XLK': {'primary': 'Technology', 'secondary': []},  # Technology Select Sector
    'XLV': {'primary': 'Healthcare', 'secondary': []},  # Healthcare Select Sector
    'XLI': {'primary': 'Defense', 'secondary': ['Transportation']},  # Industrial Select Sector
}


class TickerIndustryMapper:
    """Map stock tickers to industry sectors."""

    def __init__(self):
        self.ticker_map = TICKER_INDUSTRY_MAP

    def get_industries(self, ticker: str) -> Dict[str, any]:
        """
        Get industries for a given ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            Dict with primary and secondary industries, or None if not found
        """
        ticker = ticker.upper()
        if ticker in self.ticker_map:
            return self.ticker_map[ticker]
        return None

    def get_primary_industry(self, ticker: str) -> str:
        """Get primary industry for a ticker."""
        mapping = self.get_industries(ticker)
        return mapping['primary'] if mapping else None

    def get_all_industries(self, ticker: str) -> List[str]:
        """Get all industries (primary + secondary) for a ticker."""
        mapping = self.get_industries(ticker)
        if not mapping:
            return []
        return [mapping['primary']] + mapping.get('secondary', [])

    def tickers_for_industry(self, industry: str) -> List[str]:
        """
        Get all tickers in a given industry.

        Args:
            industry: Industry name (e.g., 'Defense', 'Healthcare')

        Returns:
            List of ticker symbols
        """
        tickers = []
        for ticker, mapping in self.ticker_map.items():
            if mapping['primary'] == industry or industry in mapping.get('secondary', []):
                tickers.append(ticker)
        return sorted(tickers)

    def is_ticker_in_industry(self, ticker: str, industry: str) -> bool:
        """Check if a ticker is associated with an industry."""
        industries = self.get_all_industries(ticker)
        return industry in industries

    def get_ticker_stats(self) -> Dict[str, any]:
        """Get statistics about the ticker-industry mapping."""
        stats = {
            'total_tickers': len(self.ticker_map),
            'by_industry': defaultdict(int),
            'multi_industry': 0
        }

        for ticker, mapping in self.ticker_map.items():
            primary = mapping['primary']
            secondary = mapping.get('secondary', [])
            stats['by_industry'][primary] += 1

            if secondary:
                stats['multi_industry'] += 1
                for sec in secondary:
                    stats['by_industry'][sec] += 1

        return dict(stats)

    def get_all_known_tickers(self) -> Set[str]:
        """Get set of all known ticker symbols."""
        return set(self.ticker_map.keys())

    def match_bill_to_tickers(
        self,
        bill_industries: List[str],
        ticker: str,
        match_secondary: bool = True
    ) -> Dict[str, any]:
        """
        Check if a ticker matches bill industries.

        Args:
            bill_industries: List of industries tagged to a bill
            ticker: Stock ticker
            match_secondary: Whether to match on secondary industries

        Returns:
            Dict with match info including match_type and matched_industry
        """
        ticker_industries = self.get_all_industries(ticker) if match_secondary else [self.get_primary_industry(ticker)]

        if not ticker_industries or not bill_industries:
            return {'matches': False}

        # Find overlapping industries
        overlaps = set(ticker_industries) & set(bill_industries)

        if not overlaps:
            return {'matches': False}

        # Determine match type
        primary = self.get_primary_industry(ticker)
        match_type = 'primary' if primary in overlaps else 'secondary'

        return {
            'matches': True,
            'match_type': match_type,
            'matched_industries': list(overlaps),
            'ticker_industries': ticker_industries,
            'confidence': 0.9 if match_type == 'primary' else 0.6
        }


# Convenience function
def get_ticker_industry(ticker: str) -> str:
    """Quick lookup of primary industry for a ticker."""
    mapper = TickerIndustryMapper()
    return mapper.get_primary_industry(ticker)


if __name__ == '__main__':
    # Test the mapper
    mapper = TickerIndustryMapper()

    print("=" * 80)
    print("Ticker Industry Mapper Test")
    print("=" * 80)

    # Test 1: Individual ticker lookup
    print("\nTest 1 - Individual Ticker Lookups:")
    for ticker in ['LMT', 'NVDA', 'PFE', 'TSLA']:
        industries = mapper.get_all_industries(ticker)
        print(f"  {ticker}: {industries}")

    # Test 2: Industry to tickers
    print("\nTest 2 - Tickers by Industry:")
    for industry in ['Defense', 'Healthcare', 'Technology']:
        tickers = mapper.tickers_for_industry(industry)
        print(f"  {industry}: {len(tickers)} tickers - {tickers[:5]}...")

    # Test 3: Bill-ticker matching
    print("\nTest 3 - Bill-Ticker Matching:")
    bill_industries = ['Defense', 'Technology']
    for ticker in ['LMT', 'NVDA', 'PFE']:
        match = mapper.match_bill_to_tickers(bill_industries, ticker)
        print(f"  {ticker} vs {bill_industries}: {match}")

    # Test 4: Statistics
    print("\nTest 4 - Mapping Statistics:")
    stats = mapper.get_ticker_stats()
    print(f"  Total tickers: {stats['total_tickers']}")
    print(f"  Multi-industry: {stats['multi_industry']}")
    print(f"  By industry: {dict(stats['by_industry'])}")

    print("\n✅ Ticker industry mapper tests complete!")
