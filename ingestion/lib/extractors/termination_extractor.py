"""Termination Report (Type T) extractor.

Extracts structured data from Terminated Filer Reports.
These reports follow the same structure as Form A (Annual Report) but are filed
when a member leaves office. They cover the period from the last annual report
up to the termination date.
"""

import logging
from typing import Dict, Any, List

from .form_ab_extractor import FormABExtractor

logger = logging.getLogger(__name__)


class TerminationExtractor(FormABExtractor):
    """Extract structured data from Termination Reports."""

    def __init__(self):
        """Initialize the extractor."""
        super().__init__()
        self.extraction_version = "1.0.0-termination"

    def extract_from_textract(
        self,
        doc_id: str,
        year: int,
        textract_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract Termination Report data.
        
        Overrides base method to ensure filing_type is correctly set if not explicitly found,
        and to add any termination-specific validation.
        """
        result = super().extract_from_textract(doc_id, year, textract_blocks)
        
        # Enforce filing type if not extracted or generic
        if not result["header"].get("filing_type") or result["header"].get("filing_type") == "Annual Report":
            result["header"]["filing_type"] = "Terminated Filer Report"
            result["filing_type"] = "Terminated Filer Report"
            
        return result
