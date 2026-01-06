"""Enhanced bill reference extraction with fuzzy matching and context awareness.

This module extends the basic regex matching with:
1. Popular name matching ("ACA", "Infrastructure Bill", etc.)
2. Title similarity matching using fuzzy string matching
3. Sponsor name matching
4. Subject/keyword matching
5. Context-aware inference from timeframe
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from difflib import SequenceMatcher

import boto3
import gzip
import json

logger = logging.getLogger(__name__)


@dataclass
class EnhancedBillReference:
    """Enhanced bill reference with metadata."""

    bill_id: str  # Full ID: "119-hr-1234"
    bill_type: str
    bill_number: int
    congress: int
    confidence: float  # 0.0-1.0
    match_type: str  # "explicit", "popular_name", "title_fuzzy", "sponsor", "subject"
    context_snippet: str
    raw_match: str
    bill_title: Optional[str] = None  # If matched via bill database


# Popular bill names and their IDs
# This should be expanded with a database query, but here are common ones
POPULAR_BILL_NAMES = {
    # 117th Congress (2021-2022)
    "infrastructure bill": "117-hr-3684",
    "infrastructure investment and jobs act": "117-hr-3684",
    "iija": "117-hr-3684",
    "build back better": "117-hr-5376",
    "bbb": "117-hr-5376",
    "inflation reduction act": "117-hr-5376",
    "ira": "117-hr-5376",

    # 118th Congress (2023-2024)
    "chips act": "118-hr-4346",
    "chips and science act": "118-hr-4346",
    "secure act 2.0": "118-hr-2954",

    # 119th Congress (2025-2026)
    # Add as they emerge

    # Historical - always relevant
    "affordable care act": "111-hr-3590",
    "aca": "111-hr-3590",
    "obamacare": "111-hr-3590",
    "dodd-frank": "111-hr-4173",
    "dodd-frank act": "111-hr-4173",
    "tax cuts and jobs act": "115-hr-1",
    "tcja": "115-hr-1",
}

# Common bill title patterns that appear in lobbying descriptions
TITLE_KEYWORDS = {
    "infrastructure": ["infrastructure", "roads", "bridges", "transportation"],
    "healthcare": ["healthcare", "health care", "medicaid", "medicare", "aca"],
    "tax": ["tax", "taxation", "revenue", "irs", "internal revenue"],
    "defense": ["defense", "military", "armed forces", "national security"],
    "energy": ["energy", "renewable", "solar", "wind", "fossil", "climate"],
    "education": ["education", "student", "school", "college", "university"],
    "immigration": ["immigration", "border", "visa", "citizenship"],
    "trade": ["trade", "tariff", "export", "import", "commerce"],
}


class EnhancedBillReferenceExtractor:
    """Enhanced extractor with fuzzy matching and bill database lookup."""

    def __init__(
        self,
        filing_year: int,
        s3_bucket: str = "congress-disclosures-standardized",
        use_fuzzy: bool = True,
    ):
        """Initialize enhanced extractor.

        Args:
            filing_year: Year of the filing
            s3_bucket: S3 bucket with bill data
            use_fuzzy: Enable fuzzy matching (slower but more comprehensive)
        """
        self.filing_year = filing_year
        self.congress_number = self._infer_congress_number(filing_year)
        self.s3_bucket = s3_bucket
        self.use_fuzzy = use_fuzzy

        # Cache for bill data (loaded lazily)
        self._bill_cache = None
        self._bill_titles_lower = None
        self._sponsor_cache = None

    @staticmethod
    def _infer_congress_number(filing_year: int) -> int:
        """Infer Congress number from filing year."""
        if filing_year >= 2025:
            return 119
        if filing_year >= 2023:
            return 118
        if filing_year >= 2021:
            return 117
        if filing_year >= 2019:
            return 116
        if filing_year >= 2017:
            return 115
        if filing_year >= 2015:
            return 114
        # General formula for older congresses
        return 117 + ((filing_year - 2021) // 2)

    def _load_bill_cache(self):
        """Load bill data from S3 for this congress session."""
        if self._bill_cache is not None:
            return

        logger.info(f"Loading bill cache for {self.congress_number}th Congress...")

        try:
            s3 = boto3.client("s3")

            # Load bills from Silver layer
            prefix = f"silver/congress/bills/congress={self.congress_number}/"

            # Try to read parquet file
            try:
                import pandas as pd
                import pyarrow.parquet as pq
                import io

                # List all parquet files
                response = s3.list_objects_v2(Bucket=self.s3_bucket, Prefix=prefix)

                if "Contents" not in response:
                    logger.warning(f"No bills found for {self.congress_number}th Congress")
                    self._bill_cache = {}
                    self._bill_titles_lower = {}
                    self._sponsor_cache = {}
                    return

                # Read first parquet file
                key = response["Contents"][0]["Key"]
                obj = s3.get_object(Bucket=self.s3_bucket, Key=key)

                df = pd.read_parquet(io.BytesIO(obj["Body"].read()))

                # Build caches
                self._bill_cache = {}
                self._bill_titles_lower = {}
                self._sponsor_cache = {}

                for _, row in df.iterrows():
                    bill_id = row.get("bill_id")
                    title = row.get("title", "")
                    sponsor = row.get("sponsor_name", "")

                    if not bill_id:
                        continue

                    self._bill_cache[bill_id] = {
                        "title": title,
                        "sponsor": sponsor,
                        "type": row.get("bill_type"),
                        "number": row.get("bill_number"),
                    }

                    if title:
                        self._bill_titles_lower[title.lower()] = bill_id

                    if sponsor:
                        sponsor_last = sponsor.split()[-1].lower()
                        if sponsor_last not in self._sponsor_cache:
                            self._sponsor_cache[sponsor_last] = []
                        self._sponsor_cache[sponsor_last].append(bill_id)

                logger.info(f"Loaded {len(self._bill_cache)} bills for {self.congress_number}th Congress")

            except Exception as e:
                logger.warning(f"Could not load bill cache: {e}")
                self._bill_cache = {}
                self._bill_titles_lower = {}
                self._sponsor_cache = {}

        except Exception as e:
            logger.error(f"Error loading bill cache: {e}")
            self._bill_cache = {}
            self._bill_titles_lower = {}
            self._sponsor_cache = {}

    def extract_popular_name_references(self, text: str) -> List[EnhancedBillReference]:
        """Extract bills by popular names."""
        references = []
        text_lower = text.lower()

        for popular_name, bill_id in POPULAR_BILL_NAMES.items():
            if popular_name in text_lower:
                # Extract congress and bill parts
                parts = bill_id.split("-")
                congress = int(parts[0])
                bill_type = parts[1]
                bill_number = int(parts[2])

                # Get context
                idx = text_lower.find(popular_name)
                start = max(0, idx - 50)
                end = min(len(text), idx + len(popular_name) + 50)
                context = text[start:end]

                ref = EnhancedBillReference(
                    bill_id=bill_id,
                    bill_type=bill_type,
                    bill_number=bill_number,
                    congress=congress,
                    confidence=0.85,  # High confidence for popular names
                    match_type="popular_name",
                    context_snippet=context,
                    raw_match=popular_name,
                )

                references.append(ref)

        return references

    def extract_fuzzy_title_references(
        self,
        text: str,
        min_similarity: float = 0.75,
    ) -> List[EnhancedBillReference]:
        """Extract bills by fuzzy matching against bill titles."""
        if not self.use_fuzzy:
            return []

        self._load_bill_cache()

        if not self._bill_titles_lower:
            return []

        references = []
        text_lower = text.lower()

        # Extract candidate phrases (3-10 words)
        words = text_lower.split()
        for i in range(len(words)):
            for phrase_len in range(3, 11):
                if i + phrase_len > len(words):
                    break

                phrase = " ".join(words[i:i+phrase_len])

                # Check against bill titles
                for bill_title_lower, bill_id in self._bill_titles_lower.items():
                    # Skip if titles are too different in length
                    if abs(len(phrase) - len(bill_title_lower)) > 50:
                        continue

                    # Calculate similarity
                    similarity = SequenceMatcher(None, phrase, bill_title_lower).ratio()

                    if similarity >= min_similarity:
                        # Found a fuzzy match!
                        bill_data = self._bill_cache[bill_id]
                        parts = bill_id.split("-")

                        # Get context
                        start = max(0, text.lower().find(phrase) - 50)
                        end = min(len(text), text.lower().find(phrase) + len(phrase) + 50)
                        context = text[start:end]

                        ref = EnhancedBillReference(
                            bill_id=bill_id,
                            bill_type=parts[1],
                            bill_number=int(parts[2]),
                            congress=int(parts[0]),
                            confidence=min(0.95, similarity),
                            match_type="title_fuzzy",
                            context_snippet=context,
                            raw_match=phrase,
                            bill_title=bill_data["title"],
                        )

                        references.append(ref)

        return references

    def extract_sponsor_references(self, text: str) -> List[EnhancedBillReference]:
        """Extract bills by sponsor name mentions."""
        self._load_bill_cache()

        if not self._sponsor_cache:
            return []

        references = []
        text_lower = text.lower()

        # Pattern: "Senator X's bill", "Rep Y bill", etc.
        sponsor_patterns = [
            r"senator\s+(\w+)(?:'s)?\s+bill",
            r"rep(?:resentative)?\s+(\w+)(?:'s)?\s+bill",
            r"(\w+)(?:'s)?\s+(?:sponsored|introduced)\s+bill",
        ]

        for pattern in sponsor_patterns:
            for match in re.finditer(pattern, text_lower):
                sponsor_name = match.group(1).lower()

                # Look up in sponsor cache
                if sponsor_name in self._sponsor_cache:
                    bill_ids = self._sponsor_cache[sponsor_name]

                    # Use first match (could be enhanced to pick most relevant)
                    if bill_ids:
                        bill_id = bill_ids[0]
                        parts = bill_id.split("-")

                        # Get context
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        context = text[start:end]

                        ref = EnhancedBillReference(
                            bill_id=bill_id,
                            bill_type=parts[1],
                            bill_number=int(parts[2]),
                            congress=int(parts[0]),
                            confidence=0.70,  # Lower confidence - sponsor name alone is weak
                            match_type="sponsor",
                            context_snippet=context,
                            raw_match=match.group(0),
                        )

                        references.append(ref)

        return references

    def extract_all_references(
        self,
        text: str,
        include_explicit: bool = True,
    ) -> List[EnhancedBillReference]:
        """Extract all bill references using all methods.

        Args:
            text: Text to extract from
            include_explicit: Also use explicit pattern matching (H.R. 1234)

        Returns:
            Combined list of references from all methods
        """
        all_refs = []

        # 1. Popular name matching (fast, high confidence)
        popular_refs = self.extract_popular_name_references(text)
        all_refs.extend(popular_refs)
        logger.debug(f"Found {len(popular_refs)} popular name references")

        # 2. Sponsor matching (medium speed, medium confidence)
        sponsor_refs = self.extract_sponsor_references(text)
        all_refs.extend(sponsor_refs)
        logger.debug(f"Found {len(sponsor_refs)} sponsor references")

        # 3. Fuzzy title matching (slow, variable confidence)
        # Only run if we haven't found many matches yet
        if len(all_refs) < 5 and self.use_fuzzy:
            fuzzy_refs = self.extract_fuzzy_title_references(text, min_similarity=0.80)
            all_refs.extend(fuzzy_refs)
            logger.debug(f"Found {len(fuzzy_refs)} fuzzy title references")

        # 4. Explicit pattern matching (fast, highest confidence)
        if include_explicit:
            from backend.lib.ingestion.bill_reference_extractor import BillReferenceExtractor

            basic_extractor = BillReferenceExtractor(self.filing_year)
            explicit_refs_basic = basic_extractor.extract_references(text)

            # Convert to EnhancedBillReference
            for ref in explicit_refs_basic:
                enhanced = EnhancedBillReference(
                    bill_id=basic_extractor.format_bill_id(ref),
                    bill_type=ref.bill_type,
                    bill_number=ref.bill_number,
                    congress=ref.congress,
                    confidence=ref.confidence,
                    match_type="explicit",
                    context_snippet=ref.context_snippet,
                    raw_match=ref.raw_match,
                )
                all_refs.append(enhanced)

            logger.debug(f"Found {len(explicit_refs_basic)} explicit references")

        # Deduplicate by bill_id (keep highest confidence)
        deduped = self._deduplicate(all_refs)

        # Sort by confidence
        deduped.sort(key=lambda r: r.confidence, reverse=True)

        logger.info(
            f"Extracted {len(deduped)} total bill references "
            f"(from {len(all_refs)} before dedup)"
        )

        return deduped

    def _deduplicate(self, references: List[EnhancedBillReference]) -> List[EnhancedBillReference]:
        """Deduplicate references by bill_id."""
        seen = {}
        result = []

        for ref in references:
            if ref.bill_id not in seen:
                seen[ref.bill_id] = ref
                result.append(ref)
            else:
                # Keep higher confidence match
                if ref.confidence > seen[ref.bill_id].confidence:
                    idx = result.index(seen[ref.bill_id])
                    result[idx] = ref
                    seen[ref.bill_id] = ref

        return result

    def format_for_storage(
        self,
        references: List[EnhancedBillReference],
        min_confidence: float = 0.7,
    ) -> List[Dict[str, any]]:
        """Format references as dicts for Parquet storage."""
        filtered = [r for r in references if r.confidence >= min_confidence]

        return [
            {
                "bill_id": ref.bill_id,
                "bill_type": ref.bill_type,
                "bill_number": ref.bill_number,
                "congress": ref.congress,
                "confidence": ref.confidence,
                "match_type": ref.match_type,
                "context_snippet": ref.context_snippet,
                "raw_match": ref.raw_match,
                "bill_title": ref.bill_title,
            }
            for ref in filtered
        ]


def extract_bill_references_from_filing_enhanced(
    filing: Dict[str, any],
    filing_year: int,
    s3_bucket: str = "congress-disclosures-standardized",
    use_fuzzy: bool = True,
) -> List[Dict[str, any]]:
    """Enhanced extraction from LDA filing.

    Args:
        filing: LDA filing dict
        filing_year: Year of filing
        s3_bucket: S3 bucket with bill data
        use_fuzzy: Enable fuzzy matching

    Returns:
        List of bill references with activity_id
    """
    extractor = EnhancedBillReferenceExtractor(
        filing_year=filing_year,
        s3_bucket=s3_bucket,
        use_fuzzy=use_fuzzy,
    )

    all_references = []
    lobbying_activities = filing.get("lobbying_activities", [])
    filing_uuid = filing.get("filing_uuid")

    for idx, activity in enumerate(lobbying_activities):
        # Generate same activity_id as activities table
        activity_id = f"{filing_uuid}_{idx}"
        description = activity.get("description", "")

        if not description:
            continue

        # Extract using enhanced matcher
        references = extractor.extract_all_references(description)
        formatted = extractor.format_for_storage(references, min_confidence=0.70)

        # Add activity_id
        for ref in formatted:
            ref["activity_id"] = activity_id
            all_references.append(ref)

    logger.info(
        f"Enhanced extraction: {len(all_references)} bill references from "
        f"filing {filing_uuid} ({len(lobbying_activities)} activities)"
    )

    return all_references
