#!/usr/bin/env python3
"""
Unit tests for industry classifier.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from ingestion.lib.industry_classifier import IndustryClassifier, load_sp500_tickers


def test_defense_bill_classification():
    """Test classification of defense bills."""
    classifier = IndustryClassifier()

    result = classifier.classify_bill(
        title="National Defense Authorization Act for Fiscal Year 2024",
        summary="To authorize appropriations for the Department of Defense for military activities.",
        policy_area="Armed Forces and National Security"
    )

    # Should detect Defense industry
    assert result['has_industry_tags']
    industries = [tag['industry'] for tag in result['industry_tags']]
    assert 'Defense' in industries

    # Check confidence
    defense_tag = next(t for t in result['industry_tags'] if t['industry'] == 'Defense')
    assert defense_tag['confidence'] > 0.5


def test_healthcare_bill_classification():
    """Test classification of healthcare bills."""
    classifier = IndustryClassifier()

    result = classifier.classify_bill(
        title="Lower Drug Costs Now Act",
        summary="To establish Medicare prescription drug price negotiation for pharmaceutical companies.",
        policy_area="Health"
    )

    assert result['has_industry_tags']
    industries = [tag['industry'] for tag in result['industry_tags']]
    assert 'Healthcare' in industries


def test_technology_bill_with_tickers():
    """Test technology bill with ticker extraction."""
    classifier = IndustryClassifier()
    known_tickers = load_sp500_tickers()

    result = classifier.classify_bill(
        title="CHIPS and Science Act",
        summary="To provide investments in semiconductor manufacturing including companies like NVDA and INTC.",
        known_tickers=known_tickers
    )

    assert result['has_industry_tags']
    industries = [tag['industry'] for tag in result['industry_tags']]
    assert 'Technology' in industries

    # Should extract tickers
    assert result['has_tickers']
    tickers = [t['ticker'] for t in result['tickers']]
    assert 'NVDA' in tickers
    assert 'INTC' in tickers


def test_ticker_extraction_excludes_acronyms():
    """Test that common acronyms are excluded from ticker extraction."""
    classifier = IndustryClassifier()

    text = "The SEC and FDA will regulate this bill under USA law."
    tickers = classifier.extract_tickers(text)

    # Should not extract SEC, FDA, USA
    ticker_list = [t['ticker'] for t in tickers]
    assert 'SEC' not in ticker_list
    assert 'FDA' not in ticker_list
    assert 'USA' not in ticker_list


def test_multi_industry_bill():
    """Test bill that should match multiple industries."""
    classifier = IndustryClassifier()

    result = classifier.classify_bill(
        title="Clean Energy and Transportation Infrastructure Act",
        summary="To invest in renewable energy, solar power, wind energy, and electric vehicle infrastructure."
    )

    industries = [tag['industry'] for tag in result['industry_tags']]

    # Should detect both Energy and Transportation
    assert 'Energy' in industries
    assert 'Transportation' in industries


def test_policy_area_mapping():
    """Test policy area to industry mapping."""
    classifier = IndustryClassifier()

    # Test with policy area only, no keywords
    result = classifier.classify_bill(
        title="A Bill",
        summary="Some general text",
        policy_area="Finance and Financial Sector"
    )

    industries = [tag['industry'] for tag in result['industry_tags']]
    assert 'Finance' in industries


def test_confidence_scoring():
    """Test confidence scoring based on keyword matches."""
    classifier = IndustryClassifier()

    # Multiple defense keywords
    result1 = classifier.classify_bill(
        title="Military Weapons Systems Act",
        summary="Pentagon defense contractor missile weapon systems for armed forces."
    )

    # Single defense keyword
    result2 = classifier.classify_bill(
        title="A Bill",
        summary="Something about military."
    )

    defense1 = next(t for t in result1['industry_tags'] if t['industry'] == 'Defense')
    defense2 = next(t for t in result2['industry_tags'] if t['industry'] == 'Defense')

    # More keywords should result in higher confidence
    assert defense1['confidence'] > defense2['confidence']


def test_no_industry_tags():
    """Test bill with no industry matches."""
    classifier = IndustryClassifier()

    result = classifier.classify_bill(
        title="A General Bill",
        summary="Some generic text without industry keywords."
    )

    assert not result['has_industry_tags']
    assert len(result['industry_tags']) == 0


def test_keyword_matching():
    """Test keyword matching is case-insensitive."""
    classifier = IndustryClassifier()

    result = classifier.classify_text("MILITARY weapons DEFENSE")

    assert len(result) > 0
    assert result[0]['industry'] == 'Defense'
    assert 'military' in result[0]['matched_keywords']
    assert 'defense' in result[0]['matched_keywords']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
