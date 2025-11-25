"""
Gold layer enrichment utilities.

This package provides functions to enrich gold layer data with external APIs:
- Congress.gov API: Member bioguide IDs, party, committees
- Yahoo Finance: Stock tickers, sectors, market caps
- Coinbase API: Cryptocurrency classification
"""

from .congress_api import CongressAPIEnricher
from .stock_api import StockAPIEnricher
from .cache import EnrichmentCache

__all__ = [
    'CongressAPIEnricher',
    'StockAPIEnricher',
    'EnrichmentCache'
]
