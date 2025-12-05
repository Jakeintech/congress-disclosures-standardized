#!/usr/bin/env python3
"""
Unit tests for ticker-to-industry mapper.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from ingestion.lib.ticker_industry_mapper import TickerIndustryMapper, get_ticker_industry


def test_defense_ticker_mapping():
    """Test defense company ticker mappings."""
    mapper = TickerIndustryMapper()

    # Lockheed Martin
    industries = mapper.get_all_industries('LMT')
    assert 'Defense' in industries

    # Raytheon
    industries = mapper.get_all_industries('RTX')
    assert 'Defense' in industries


def test_healthcare_ticker_mapping():
    """Test healthcare company ticker mappings."""
    mapper = TickerIndustryMapper()

    # Johnson & Johnson
    assert mapper.get_primary_industry('JNJ') == 'Healthcare'

    # Pfizer
    assert mapper.get_primary_industry('PFE') == 'Healthcare'

    # UnitedHealth
    industries = mapper.get_all_industries('UNH')
    assert 'Healthcare' in industries


def test_technology_ticker_mapping():
    """Test technology company ticker mappings."""
    mapper = TickerIndustryMapper()

    # Apple
    assert mapper.get_primary_industry('AAPL') == 'Technology'

    # Microsoft
    assert mapper.get_primary_industry('MSFT') == 'Technology'

    # NVIDIA (should have Defense as secondary)
    industries = mapper.get_all_industries('NVDA')
    assert 'Technology' in industries
    assert 'Defense' in industries


def test_multi_industry_ticker():
    """Test ticker with multiple industry classifications."""
    mapper = TickerIndustryMapper()

    # Amazon (Tech + Transportation + Finance)
    industries = mapper.get_all_industries('AMZN')
    assert 'Technology' in industries
    assert len(industries) > 1


def test_tickers_for_industry():
    """Test getting all tickers for an industry."""
    mapper = TickerIndustryMapper()

    defense_tickers = mapper.tickers_for_industry('Defense')
    assert 'LMT' in defense_tickers
    assert 'RTX' in defense_tickers
    assert 'BA' in defense_tickers

    # Should be sorted
    assert defense_tickers == sorted(defense_tickers)


def test_is_ticker_in_industry():
    """Test checking if ticker is in industry."""
    mapper = TickerIndustryMapper()

    assert mapper.is_ticker_in_industry('LMT', 'Defense')
    assert mapper.is_ticker_in_industry('PFE', 'Healthcare')
    assert mapper.is_ticker_in_industry('NVDA', 'Technology')

    # NVDA should also match Defense (secondary)
    assert mapper.is_ticker_in_industry('NVDA', 'Defense')

    # Should not match wrong industry
    assert not mapper.is_ticker_in_industry('PFE', 'Defense')


def test_match_bill_to_tickers():
    """Test matching bill industries to ticker."""
    mapper = TickerIndustryMapper()

    # Defense bill + Defense ticker
    bill_industries = ['Defense', 'Technology']
    match = mapper.match_bill_to_tickers(bill_industries, 'LMT')

    assert match['matches']
    assert match['match_type'] == 'primary'
    assert 'Defense' in match['matched_industries']
    assert match['confidence'] == 0.9

    # Healthcare bill + Healthcare ticker
    bill_industries = ['Healthcare']
    match = mapper.match_bill_to_tickers(bill_industries, 'PFE')

    assert match['matches']
    assert match['match_type'] == 'primary'

    # No match
    bill_industries = ['Agriculture']
    match = mapper.match_bill_to_tickers(bill_industries, 'AAPL')

    assert not match['matches']


def test_match_secondary_industry():
    """Test matching on secondary industry."""
    mapper = TickerIndustryMapper()

    # NVDA has Defense as secondary
    bill_industries = ['Defense']
    match = mapper.match_bill_to_tickers(bill_industries, 'NVDA', match_secondary=True)

    assert match['matches']
    assert match['match_type'] == 'secondary'
    assert match['confidence'] == 0.6

    # Without secondary matching
    match = mapper.match_bill_to_tickers(bill_industries, 'NVDA', match_secondary=False)
    assert not match['matches']


def test_get_ticker_stats():
    """Test ticker mapping statistics."""
    mapper = TickerIndustryMapper()

    stats = mapper.get_ticker_stats()

    assert stats['total_tickers'] > 0
    assert 'by_industry' in stats
    assert stats['by_industry']['Defense'] > 0
    assert stats['by_industry']['Healthcare'] > 0
    assert stats['multi_industry'] > 0


def test_unknown_ticker():
    """Test handling of unknown ticker."""
    mapper = TickerIndustryMapper()

    industries = mapper.get_all_industries('UNKNWN')
    assert industries == []

    primary = mapper.get_primary_industry('UNKNWN')
    assert primary is None


def test_case_insensitive():
    """Test ticker lookup is case-insensitive."""
    mapper = TickerIndustryMapper()

    # Should work with lowercase
    industries_lower = mapper.get_all_industries('aapl')
    industries_upper = mapper.get_all_industries('AAPL')

    assert industries_lower == industries_upper


def test_get_all_known_tickers():
    """Test getting set of all known tickers."""
    mapper = TickerIndustryMapper()

    tickers = mapper.get_all_known_tickers()

    assert isinstance(tickers, set)
    assert 'AAPL' in tickers
    assert 'MSFT' in tickers
    assert 'LMT' in tickers
    assert len(tickers) > 50


def test_convenience_function():
    """Test convenience function."""
    industry = get_ticker_industry('AAPL')
    assert industry == 'Technology'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
