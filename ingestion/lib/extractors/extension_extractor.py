"""Extension Request (Type X) extractor.

Extracts structured data from Extension Requests.
These are simple forms requesting more time to file financial disclosures.
"""

import logging
import re
from typing import Dict, Any, List
from datetime import datetime

from .form_ab_extractor import FormABExtractor

logger = logging.getLogger(__name__)


class ExtensionExtractor(FormABExtractor):
    """Extract structured data from Extension Requests."""

    def __init__(self):
        """Initialize the extractor."""
        super().__init__()
        self.extraction_version = "1.0.0-extension"

    def extract_from_textract(
        self,
        doc_id: str,
        year: int,
        textract_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract Extension Request data.
        
        Args:
            doc_id: Document ID
            year: Filing year
            textract_blocks: List of Textract block dictionaries

        Returns:
            Structured data matching extension schema
        """
        logger.info(f"Extracting Extension Request data for doc_id={doc_id}")

        # Build block map
        block_map = {block["Id"]: block for block in textract_blocks}

        # Extract key-value pairs
        kv_pairs = self._extract_key_value_pairs(textract_blocks, block_map)
        
        # Initialize result structure
        result = {
            "doc_id": doc_id,
            "year": year,
            "filing_type": "Extension Request",
            "filer_info": {
                "name": None,
                "status": None,
                "state_district": None
            },
            "extension_details": {
                "request_date": None,
                "extension_length": None,
                "new_due_date": None,
                "report_type_due": None,
                "original_due_date": None,
                "filing_year": None
            },
            "extraction_metadata": {
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "extraction_method": "textract_kv_pairs",
                "extraction_version": self.extraction_version
            }
        }

        # Map Filer Info
        # PDF fields: Name, Status, State/District
        if "Name" in kv_pairs:
            result["filer_info"]["name"] = kv_pairs["Name"]
        if "Status" in kv_pairs:
            result["filer_info"]["status"] = kv_pairs["Status"]
        if "State/District" in kv_pairs:
            result["filer_info"]["state_district"] = kv_pairs["State/District"]

        # Map Extension Details
        # PDF fields: Request Date, Extension Length, New Due Date, Report Type Due, Filing Year, Original Due Date
        field_map = {
            "Request Date": "request_date",
            "Extension Length": "extension_length",
            "New Due Date": "new_due_date",
            "Report Type Due": "report_type_due",
            "Filing Year": "filing_year",
            "Original Due Date": "original_due_date"
        }

        for pdf_key, json_key in field_map.items():
            if pdf_key in kv_pairs:
                result["extension_details"][json_key] = kv_pairs[pdf_key]

        # Calculate confidence
        # Simple metric: how many expected fields were found
        expected_fields = ["Name", "New Due Date", "Extension Length"]
        found_count = sum(1 for f in expected_fields if f in kv_pairs)
        confidence = found_count / len(expected_fields)
        result["extraction_metadata"]["overall_confidence"] = confidence

        logger.debug(f"Extracted extension data: {result}")
        return result
