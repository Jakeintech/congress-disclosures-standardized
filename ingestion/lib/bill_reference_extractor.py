"""Extract bill references from lobbying activity descriptions.

This module uses regex patterns and NLP techniques to identify bill references
in lobbying disclosure text and map them to Congress.gov bill IDs.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BillReference:
    """A bill reference extracted from text."""

    bill_type: str  # HR, S, HJRES, SJRES, etc.
    bill_number: int
    congress: Optional[int] = None  # Inferred from filing year
    confidence: float = 1.0  # 0.0-1.0
    context_snippet: str = ""  # Surrounding text
    raw_match: str = ""  # Original matched text


# Bill type patterns
BILL_PATTERNS = [
    # H.R. 1234, HR 1234, H.R.1234
    (
        r"\b(?:H\.?\s*R\.?|HR)\s*(\d{1,5})\b",
        "hr",
        1.0,  # High confidence - explicit format
    ),
    # S. 1234, S 1234, S.1234
    (r"\b(?:S\.?)\s*(\d{1,5})\b", "s", 1.0),
    # H.J.Res. 45, HJRes 45
    (r"\b(?:H\.?\s*J\.?\s*RES\.?|HJRES)\s*(\d{1,5})\b", "hjres", 1.0),
    # S.J.Res. 45, SJRes 45
    (r"\b(?:S\.?\s*J\.?\s*RES\.?|SJRES)\s*(\d{1,5})\b", "sjres", 1.0),
    # H.Con.Res. 45
    (r"\b(?:H\.?\s*CON\.?\s*RES\.?|HCONRES)\s*(\d{1,5})\b", "hconres", 1.0),
    # S.Con.Res. 45
    (r"\b(?:S\.?\s*CON\.?\s*RES\.?|SCONRES)\s*(\d{1,5})\b", "sconres", 1.0),
    # H.Res. 45
    (r"\b(?:H\.?\s*RES\.?|HRES)\s*(\d{1,5})\b", "hres", 0.9),  # Slightly lower - could be ambiguous
    # S.Res. 45
    (r"\b(?:S\.?\s*RES\.?|SRES)\s*(\d{1,5})\b", "sres", 0.9),
]

# Contextual keywords that boost confidence
LEGISLATIVE_KEYWORDS = [
    "bill",
    "legislation",
    "act",
    "amendment",
    "sponsor",
    "cosponsor",
    "introduced",
    "passed",
    "voted",
    "congress",
    "senate",
    "house",
    "committee",
]


class BillReferenceExtractor:
    """Extract and validate bill references from text."""

    def __init__(self, filing_year: Optional[int] = None):
        """Initialize extractor.

        Args:
            filing_year: Year of the filing (used to infer Congress number)
        """
        self.filing_year = filing_year
        self.congress_number = self._infer_congress_number(filing_year)

    @staticmethod
    def _infer_congress_number(filing_year: Optional[int]) -> Optional[int]:
        """Infer Congress number from filing year.

        Congress sessions:
        - 117th: 2021-2022
        - 118th: 2023-2024
        - 119th: 2025-2026
        - etc.

        Args:
            filing_year: Year of the filing

        Returns:
            Congress number or None
        """
        if not filing_year:
            return None

        # 117th Congress started in 2021
        # Each Congress is 2 years
        # Formula: congress_number = 117 + ((year - 2021) // 2)
        if filing_year >= 2021:
            return 117 + ((filing_year - 2021) // 2)

        # Historical data (before 117th)
        if filing_year >= 2019:
            return 116
        if filing_year >= 2017:
            return 115
        if filing_year >= 2015:
            return 114
        if filing_year >= 2013:
            return 113
        if filing_year >= 2011:
            return 112
        if filing_year >= 2009:
            return 111
        if filing_year >= 2007:
            return 110

        # For years before 2007, use general formula
        # 110th Congress started in 2007
        return 110 - ((2007 - filing_year + 1) // 2)

    def extract_references(self, text: str, context_window: int = 100) -> List[BillReference]:
        """Extract all bill references from text.

        Args:
            text: Text to extract from
            context_window: Number of chars before/after match for context

        Returns:
            List of BillReference objects
        """
        if not text:
            return []

        references = []
        text_lower = text.lower()

        for pattern, bill_type, base_confidence in BILL_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                bill_number = int(match.group(1))

                # Get context snippet
                start = max(0, match.start() - context_window)
                end = min(len(text), match.end() + context_window)
                context = text[start:end].strip()

                # Calculate confidence score
                confidence = self._calculate_confidence(
                    context.lower(), base_confidence
                )

                # Create reference
                ref = BillReference(
                    bill_type=bill_type,
                    bill_number=bill_number,
                    congress=self.congress_number,
                    confidence=confidence,
                    context_snippet=context,
                    raw_match=match.group(0),
                )

                references.append(ref)

        # Deduplicate references (same bill_type + bill_number)
        references = self._deduplicate_references(references)

        # Sort by confidence (highest first)
        references.sort(key=lambda r: r.confidence, reverse=True)

        return references

    def _calculate_confidence(self, context: str, base_confidence: float) -> float:
        """Calculate confidence score based on context.

        Args:
            context: Context text (lowercased)
            base_confidence: Base confidence from pattern

        Returns:
            Adjusted confidence score (0.0-1.0)
        """
        confidence = base_confidence

        # Boost confidence if legislative keywords present
        keyword_count = sum(1 for keyword in LEGISLATIVE_KEYWORDS if keyword in context)

        if keyword_count >= 3:
            confidence = min(1.0, confidence + 0.05)
        elif keyword_count >= 2:
            confidence = min(1.0, confidence + 0.03)
        elif keyword_count >= 1:
            confidence = min(1.0, confidence + 0.01)

        # Reduce confidence for very short context (might be false positive)
        if len(context) < 50:
            confidence *= 0.9

        return round(confidence, 2)

    def _deduplicate_references(self, references: List[BillReference]) -> List[BillReference]:
        """Remove duplicate bill references, keeping highest confidence.

        Args:
            references: List of references

        Returns:
            Deduplicated list
        """
        seen = {}
        result = []

        for ref in references:
            key = (ref.bill_type, ref.bill_number)

            if key not in seen:
                seen[key] = ref
                result.append(ref)
            else:
                # Keep reference with higher confidence
                if ref.confidence > seen[key].confidence:
                    # Replace in result
                    idx = result.index(seen[key])
                    result[idx] = ref
                    seen[key] = ref

        return result

    def format_bill_id(self, ref: BillReference) -> str:
        """Format bill reference as Congress.gov bill ID.

        Args:
            ref: BillReference object

        Returns:
            Formatted bill ID (e.g., "118-hr-1234")
        """
        if ref.congress:
            return f"{ref.congress}-{ref.bill_type}-{ref.bill_number}"
        else:
            # Without congress number, use generic format
            return f"{ref.bill_type}-{ref.bill_number}"

    def extract_and_format(self, text: str, min_confidence: float = 0.7) -> List[Dict[str, any]]:
        """Extract references and format as dicts for storage.

        Args:
            text: Text to extract from
            min_confidence: Minimum confidence threshold

        Returns:
            List of dicts with bill reference data
        """
        references = self.extract_references(text)

        # Filter by confidence
        references = [r for r in references if r.confidence >= min_confidence]

        # Convert to dicts
        results = []
        for ref in references:
            results.append({
                "bill_id": self.format_bill_id(ref),
                "bill_type": ref.bill_type,
                "bill_number": ref.bill_number,
                "congress": ref.congress,
                "confidence": ref.confidence,
                "context_snippet": ref.context_snippet,
                "raw_match": ref.raw_match,
            })

        return results


def extract_bill_references_from_filing(
    filing: Dict[str, any], filing_year: int
) -> List[Dict[str, any]]:
    """Extract bill references from a full LDA filing.

    Args:
        filing: LDA filing dict with lobbying_activities
        filing_year: Year of the filing

    Returns:
        List of extracted bill references with activity_id
    """
    extractor = BillReferenceExtractor(filing_year)
    all_references = []

    lobbying_activities = filing.get("lobbying_activities", [])

    for activity in lobbying_activities:
        activity_id = activity.get("id")
        description = activity.get("description", "")

        if not description:
            continue

        # Extract references from description
        references = extractor.extract_and_format(description, min_confidence=0.7)

        # Add activity_id to each reference
        for ref in references:
            ref["activity_id"] = activity_id
            all_references.append(ref)

    logger.info(
        f"Extracted {len(all_references)} bill references from filing "
        f"{filing.get('filing_uuid', 'unknown')}"
    )

    return all_references
