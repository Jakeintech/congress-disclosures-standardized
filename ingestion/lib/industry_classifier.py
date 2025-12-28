#!/usr/bin/env python3
"""
Industry classification for bills based on keywords and policy areas.

Classifies bills into 8 major industry categories:
- Defense
- Healthcare
- Finance
- Energy
- Technology
- Agriculture
- Transportation
- Real Estate
"""

from typing import Dict, List, Tuple, Set
import re
from collections import defaultdict


# Industry keyword dictionaries (lowercase for case-insensitive matching)
INDUSTRY_KEYWORDS = {
    'Defense': [
        'military', 'armed forces', 'pentagon', 'weapon', 'defense contractor',
        'f-35', 'navy', 'army', 'air force', 'marines', 'national security',
        'defense budget', 'missile', 'aircraft carrier', 'submarine', 'drone',
        'combat', 'veteran', 'department of defense', 'dod', 'warfare',
        'nuclear weapon', 'ballistic', 'fighter jet', 'military base',
        'defense spending', 'armed services', 'national defense'
    ],
    'Healthcare': [
        'medicare', 'medicaid', 'hospital', 'pharmaceutical', 'drug pricing',
        'fda', 'health insurance', 'healthcare', 'medical', 'prescription',
        'doctor', 'nurse', 'patient', 'disease', 'vaccine', 'clinic',
        'health coverage', 'affordable care act', 'obamacare', 'health plan',
        'medical device', 'biotech', 'clinical trial', 'health care',
        'pharmacy', 'opioid', 'mental health', 'telehealth'
    ],
    'Finance': [
        'bank', 'securities', 'sec', 'financial institution', 'credit', 'loan',
        'wall street', 'cryptocurrency', 'bitcoin', 'blockchain', 'fintech',
        'investment', 'stock market', 'trading', 'dodd-frank', 'consumer financial',
        'mortgage', 'derivatives', 'hedge fund', 'private equity', 'capital markets',
        'financial services', 'banking', 'federal reserve', 'treasury',
        'tax credit', 'tax deduction', 'irs', 'taxation'
    ],
    'Energy': [
        'oil', 'gas', 'renewable', 'solar', 'wind', 'pipeline', 'coal',
        'electric vehicle', 'epa', 'clean energy', 'fossil fuel', 'climate',
        'carbon', 'emissions', 'nuclear energy', 'hydroelectric', 'geothermal',
        'energy efficiency', 'power plant', 'electricity', 'grid', 'transmission',
        'natural gas', 'fracking', 'offshore drilling', 'energy sector',
        'battery', 'energy storage', 'climate change'
    ],
    'Technology': [
        'broadband', 'internet', 'cybersecurity', 'artificial intelligence',
        'privacy', 'data protection', 'tech company', 'semiconductor', 'chip',
        'software', 'hardware', 'telecommunications', 'wireless', '5g',
        'data breach', 'encryption', 'cloud computing', 'ai', 'machine learning',
        'social media', 'big tech', 'antitrust tech', 'digital', 'cyber',
        'information technology', 'tech innovation', 'research and development'
    ],
    'Agriculture': [
        'farm', 'agriculture', 'crop', 'livestock', 'usda', 'food supply',
        'agricultural', 'farmer', 'ranch', 'dairy', 'grain', 'commodity',
        'food stamp', 'snap', 'rural', 'farming', 'agribusiness', 'pesticide',
        'fertilizer', 'irrigation', 'harvest', 'agricultural subsidy',
        'farm bill', 'food security', 'organic farming'
    ],
    'Transportation': [
        'transportation', 'highway', 'infrastructure', 'railroad', 'airline',
        'aviation', 'faa', 'transit', 'bridge', 'road', 'train', 'bus',
        'airport', 'transportation infrastructure', 'amtrak', 'public transit',
        'mass transit', 'shipping', 'port', 'freight', 'railway', 'dot',
        'department of transportation', 'vehicle safety', 'traffic'
    ],
    'Real Estate': [
        'real estate', 'housing', 'property', 'mortgage', 'rent', 'landlord',
        'tenant', 'affordable housing', 'public housing', 'home ownership',
        'residential', 'commercial property', 'development', 'construction',
        'building', 'zoning', 'urban development', 'hud', 'housing market',
        'foreclosure', 'eviction', 'homeless'
    ]
}

# Congress.gov policy area to industry mapping
POLICY_AREA_MAPPING = {
    'Armed Forces and National Security': 'Defense',
    'Health': 'Healthcare',
    'Finance and Financial Sector': 'Finance',
    'Energy': 'Energy',
    'Science, Technology, Communications': 'Technology',
    'Agriculture and Food': 'Agriculture',
    'Transportation and Public Works': 'Transportation',
    'Housing and Community Development': 'Real Estate',
    'Economics and Public Finance': 'Finance',
    'Taxation': 'Finance',
    'Environmental Protection': 'Energy',
    'Commerce': 'Finance',
    'Public Lands and Natural Resources': 'Energy'
}

# Common acronyms to exclude from ticker detection (false positives)
TICKER_EXCLUSIONS = {
    'USA', 'SEC', 'FDA', 'DOD', 'NASA', 'EPA', 'IRS', 'FBI', 'CIA', 'NSA',
    'USDA', 'HUD', 'DOT', 'FAA', 'FCC', 'FTC', 'SBA', 'VA', 'HHS', 'DOE',
    'DOJ', 'DHS', 'FEMA', 'OSHA', 'NLRB', 'EEOC', 'ATF', 'DEA', 'ICE',
    'TSA', 'SSA', 'CMS', 'CDC', 'NIH', 'NSF', 'NOAA', 'NPS', 'BLM',
    'NATO', 'UN', 'EU', 'OPEC', 'IMF', 'WHO', 'GDP', 'CPI', 'LLC', 'INC',
    'LTD', 'CORP', 'CO', 'PLC', 'LP', 'LLP', 'PC', 'PA', 'PLLC',
    'ACT', 'BILL', 'HR', 'SENATE', 'HOUSE', 'TITLE', 'SECTION'
}


class IndustryClassifier:
    """Classify bills into industry categories based on content analysis."""

    def __init__(self):
        self.industry_keywords = INDUSTRY_KEYWORDS
        self.policy_area_mapping = POLICY_AREA_MAPPING
        self.ticker_exclusions = TICKER_EXCLUSIONS

    def classify_text(self, text: str, policy_area: str = None) -> List[Dict[str, any]]:
        """
        Classify text into industries with confidence scores.

        Args:
            text: Bill title, summary, or combined text
            policy_area: Congress.gov policy area (optional)

        Returns:
            List of dicts with industry, confidence, and matched keywords
        """
        if not text:
            return []

        text_lower = text.lower()
        results = []

        # 1. Keyword matching
        for industry, keywords in self.industry_keywords.items():
            matched_keywords = []
            for keyword in keywords:
                if keyword in text_lower:
                    matched_keywords.append(keyword)

            if matched_keywords:
                # Confidence based on number of unique keyword matches
                confidence = min(0.8, 0.3 + (len(matched_keywords) * 0.1))
                results.append({
                    'industry': industry,
                    'confidence': round(confidence, 2),
                    'method': 'keyword',
                    'matched_keywords': matched_keywords[:10]  # Limit to top 10
                })

        # 2. Policy area mapping (if provided)
        if policy_area and policy_area in self.policy_area_mapping:
            mapped_industry = self.policy_area_mapping[policy_area]
            # Check if already exists from keyword matching
            existing = next((r for r in results if r['industry'] == mapped_industry), None)
            if existing:
                # Boost confidence for policy area match
                existing['confidence'] = min(1.0, existing['confidence'] + 0.2)
                existing['method'] = 'keyword+policy_area'
            else:
                results.append({
                    'industry': mapped_industry,
                    'confidence': 0.6,
                    'method': 'policy_area',
                    'matched_keywords': []
                })

        # Sort by confidence descending
        results.sort(key=lambda x: x['confidence'], reverse=True)

        return results

    def extract_tickers(self, text: str, known_tickers: Set[str] = None) -> List[Dict[str, str]]:
        """
        Extract stock ticker symbols from text.

        Args:
            text: Bill text or description
            known_tickers: Set of valid ticker symbols (S&P 500, common stocks)

        Returns:
            List of dicts with ticker and context
        """
        if not text:
            return []

        # Regex for ticker patterns (1-5 uppercase letters surrounded by word boundaries)
        pattern = r'\b([A-Z]{1,5})\b'
        matches = re.finditer(pattern, text)

        results = []
        seen_tickers = set()

        for match in matches:
            ticker = match.group(1)

            # Skip if excluded acronym
            if ticker in self.ticker_exclusions:
                continue

            # Skip if already found
            if ticker in seen_tickers:
                continue

            # If known_tickers provided, validate
            if known_tickers and ticker not in known_tickers:
                continue

            # Get surrounding context (30 chars before and after)
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end].replace('\n', ' ').strip()

            results.append({
                'ticker': ticker,
                'context': context,
                'confidence': 0.8 if known_tickers and ticker in known_tickers else 0.5
            })

            seen_tickers.add(ticker)

        return results

    def classify_bill(
        self,
        title: str = '',
        summary: str = '',
        policy_area: str = None,
        subjects: List[str] = None,
        known_tickers: Set[str] = None
    ) -> Dict[str, any]:
        """
        Comprehensive bill classification combining multiple signals.

        Args:
            title: Bill title
            summary: Bill summary text
            policy_area: Congress.gov policy area
            subjects: List of subject terms
            known_tickers: Set of valid ticker symbols

        Returns:
            Dict with industry tags, tickers, and aggregate confidence
        """
        # Combine all text sources
        combined_text = ' '.join(filter(None, [
            title or '',
            summary or '',
            ' '.join(subjects or [])
        ]))

        # Get industry classifications
        industry_tags = self.classify_text(combined_text, policy_area)

        # Extract tickers
        tickers = self.extract_tickers(combined_text, known_tickers)

        # Calculate aggregate confidence per industry
        industry_scores = defaultdict(lambda: {'confidence': 0.0, 'methods': [], 'keywords': []})

        for tag in industry_tags:
            industry = tag['industry']
            industry_scores[industry]['confidence'] = max(
                industry_scores[industry]['confidence'],
                tag['confidence']
            )
            industry_scores[industry]['methods'].append(tag['method'])
            industry_scores[industry]['keywords'].extend(tag.get('matched_keywords', []))

        # Boost confidence if ticker found and mapped to industry
        if tickers and industry_tags:
            for tag in industry_tags:
                tag['has_ticker_mention'] = True

        return {
            'industry_tags': [
                {
                    'industry': industry,
                    'confidence': scores['confidence'],
                    'methods': list(set(scores['methods'])),
                    'matched_keywords': list(set(scores['keywords']))[:10]
                }
                for industry, scores in industry_scores.items()
            ],
            'tickers': tickers,
            'has_industry_tags': len(industry_scores) > 0,
            'has_tickers': len(tickers) > 0
        }


def load_sp500_tickers() -> Set[str]:
    """
    Load S&P 500 ticker symbols.

    In production, this would load from a reference file.
    For now, returns common tech/defense/healthcare tickers.
    """
    return {
        # Technology
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA',
        'AMD', 'INTC', 'ORCL', 'IBM', 'CRM', 'CSCO', 'ADBE', 'NFLX',
        # Defense
        'LMT', 'RTX', 'BA', 'NOC', 'GD', 'LHX', 'HII', 'TXT',
        # Healthcare
        'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'CVS',
        'BMY', 'AMGN', 'GILD', 'CI', 'HUM', 'ISRG',
        # Finance
        'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP',
        # Energy
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'NEE',
        # Add more as needed
    }


# Convenience function for quick classification
def classify_bill_quick(title: str, summary: str = '') -> List[str]:
    """
    Quick classification returning just industry names.

    Args:
        title: Bill title
        summary: Bill summary

    Returns:
        List of industry names (e.g., ['Defense', 'Technology'])
    """
    classifier = IndustryClassifier()
    result = classifier.classify_bill(title, summary)
    return [tag['industry'] for tag in result['industry_tags']]


if __name__ == '__main__':
    # Test examples
    classifier = IndustryClassifier()

    print("=" * 80)
    print("Industry Classifier Test")
    print("=" * 80)

    # Test 1: Defense bill
    test1 = classifier.classify_bill(
        title="National Defense Authorization Act for Fiscal Year 2024",
        summary="To authorize appropriations for the Department of Defense for military activities and prescribe military personnel strengths.",
        policy_area="Armed Forces and National Security"
    )
    print("\nTest 1 - Defense Bill:")
    print(f"  Industries: {[t['industry'] for t in test1['industry_tags']]}")
    print(f"  Top match: {test1['industry_tags'][0] if test1['industry_tags'] else 'None'}")

    # Test 2: Healthcare bill
    test2 = classifier.classify_bill(
        title="Lower Drug Costs Now Act",
        summary="To establish Medicare prescription drug price negotiation and establish affordability measures for insulin and other drugs.",
        policy_area="Health"
    )
    print("\nTest 2 - Healthcare Bill:")
    print(f"  Industries: {[t['industry'] for t in test2['industry_tags']]}")

    # Test 3: Technology with ticker
    test3 = classifier.classify_bill(
        title="CHIPS and Science Act",
        summary="To provide investments in semiconductor manufacturing including companies like NVDA and INTC.",
        known_tickers=load_sp500_tickers()
    )
    print("\nTest 3 - Technology Bill:")
    print(f"  Industries: {[t['industry'] for t in test3['industry_tags']]}")
    print(f"  Tickers: {[t['ticker'] for t in test3['tickers']]}")

    print("\n✅ Industry classifier tests complete!")
