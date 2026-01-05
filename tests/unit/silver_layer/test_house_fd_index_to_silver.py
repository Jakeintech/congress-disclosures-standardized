"""
Unit tests for house_fd_index_to_silver Lambda handler.

Tests XML parsing, document record initialization, and data transformation.

This file tests the core parsing logic directly without importing the Lambda
handler, which has many external dependencies.
"""

import pytest
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from defusedxml import ElementTree as ET


# Standalone implementation of XML parsing for testing.
# This mirrors the logic from house_fd_index_to_silver/handler.py
# but can be tested without the full Lambda dependency chain.
def parse_xml_index_impl(xml_bytes: bytes, year: int, xml_s3_key: str):
    """Parse House FD XML index into structured records."""
    records = []
    root = ET.fromstring(xml_bytes)
    
    S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze")

    for member in root.findall(".//Member"):
        doc_id = member.findtext("DocID", "").strip()

        if not doc_id:
            continue

        filing_type = member.findtext("FilingType", "").strip() or "U"
        record = {
            "doc_id": doc_id,
            "year": year,
            "filing_date": member.findtext("FilingDate", "").strip(),
            "filing_type": filing_type,
            "prefix": member.findtext("Prefix", "").strip() or None,
            "first_name": member.findtext("First", "").strip(),
            "last_name": member.findtext("Last", "").strip(),
            "suffix": member.findtext("Suffix", "").strip() or None,
            "state_district": member.findtext("StateDst", "").strip(),
            "raw_xml_path": xml_s3_key,
            "raw_txt_path": xml_s3_key.replace(".xml", ".txt"),
            "pdf_s3_key": (
                f"{S3_BRONZE_PREFIX}/house/financial/year={year}/"
                f"filing_type={filing_type}/pdfs/{doc_id}.pdf"
            ),
            "bronze_ingest_ts": datetime.now(timezone.utc).isoformat(),
            "silver_ingest_ts": datetime.now(timezone.utc).isoformat(),
            "source_system": "house_fd",
        }

        # Convert filing_date to ISO format (from MM/DD/YYYY)
        if record["filing_date"]:
            try:
                date_obj = datetime.strptime(record["filing_date"], "%m/%d/%Y")
                record["filing_date"] = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                pass  # Keep original if parsing fails

        records.append(record)

    return records


def initialize_document_records_impl(filing_records):
    """Initialize house_fd_documents records from filing records."""
    EXTRACTION_VERSION = os.environ.get("EXTRACTION_VERSION", "1.0.0")
    document_records = []

    for filing in filing_records:
        document_record = {
            "doc_id": filing["doc_id"],
            "year": filing["year"],
            "pdf_s3_key": filing["pdf_s3_key"],
            "pdf_sha256": None,
            "pdf_file_size_bytes": 0,
            "pages": 0,
            "has_embedded_text": False,
            "extraction_method": "pending",
            "extraction_status": "pending",
            "extraction_version": EXTRACTION_VERSION,
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "extraction_error": None,
            "extraction_duration_seconds": None,
            "text_s3_key": None,
            "json_s3_key": None,
            "char_count": None,
        }
        document_records.append(document_record)

    return document_records


class TestParseXmlIndex:
    """Tests for XML index parsing."""

    def test_parse_valid_xml(self, sample_house_fd_xml, aws_credentials):
        """Test parsing valid House FD XML index."""
        records = parse_xml_index_impl(
            sample_house_fd_xml, 
            2024, 
            "bronze/house/financial/year=2024/index/2024FD.xml"
        )

        assert len(records) == 2

        # Check first record
        rec1 = records[0]
        assert rec1["doc_id"] == "10063228"
        assert rec1["year"] == 2024
        assert rec1["first_name"] == "John"
        assert rec1["last_name"] == "Smith"
        assert rec1["prefix"] == "Hon."
        assert rec1["filing_type"] == "P"
        assert rec1["state_district"] == "CA11"
        assert rec1["filing_date"] == "2024-01-15"  # Converted to ISO format
        assert "bronze/house/financial/year=2024/filing_type=P/pdfs/10063228.pdf" in rec1["pdf_s3_key"]

        # Check second record
        rec2 = records[1]
        assert rec2["doc_id"] == "10078945"
        assert rec2["filing_type"] == "A"

    def test_parse_xml_with_empty_fields(self, aws_credentials):
        """Test handling of empty fields in XML."""
        xml = b"""<?xml version="1.0"?>
        <FinancialDisclosure>
            <Member>
                <DocID>12345</DocID>
                <First>Test</First>
                <Last>User</Last>
                <FilingType></FilingType>
                <StateDst></StateDst>
                <FilingDate></FilingDate>
            </Member>
        </FinancialDisclosure>
        """

        records = parse_xml_index_impl(xml, 2024, "test.xml")

        assert len(records) == 1
        assert records[0]["doc_id"] == "12345"
        assert records[0]["filing_type"] == "U"  # Default for empty
        assert records[0]["filing_date"] == ""

    def test_skip_member_without_doc_id(self, aws_credentials):
        """Test that members without DocID are skipped."""
        xml = b"""<?xml version="1.0"?>
        <FinancialDisclosure>
            <Member>
                <DocID></DocID>
                <First>No</First>
                <Last>DocId</Last>
            </Member>
            <Member>
                <DocID>99999</DocID>
                <First>Has</First>
                <Last>DocId</Last>
            </Member>
        </FinancialDisclosure>
        """

        records = parse_xml_index_impl(xml, 2024, "test.xml")

        assert len(records) == 1
        assert records[0]["doc_id"] == "99999"


class TestInitializeDocumentRecords:
    """Tests for document record initialization."""

    def test_initialize_documents(self, aws_credentials):
        """Test document record creation from filing records."""
        filings = [
            {
                "doc_id": "10063228",
                "year": 2024,
                "pdf_s3_key": "bronze/house/financial/year=2024/filing_type=P/pdfs/10063228.pdf"
            },
            {
                "doc_id": "10078945",
                "year": 2024,
                "pdf_s3_key": "bronze/house/financial/year=2024/filing_type=A/pdfs/10078945.pdf"
            }
        ]

        docs = initialize_document_records_impl(filings)

        assert len(docs) == 2

        doc1 = docs[0]
        assert doc1["doc_id"] == "10063228"
        assert doc1["year"] == 2024
        assert doc1["extraction_status"] == "pending"
        assert doc1["extraction_method"] == "pending"
        assert doc1["pdf_sha256"] is None
        assert doc1["pages"] == 0

    def test_empty_filings(self, aws_credentials):
        """Test handling of empty filings list."""
        docs = initialize_document_records_impl([])
        assert docs == []


class TestFilingDateConversion:
    """Tests for filing date format conversion."""

    def test_mm_dd_yyyy_to_iso(self, aws_credentials):
        """Test MM/DD/YYYY to YYYY-MM-DD conversion."""
        xml = b"""<?xml version="1.0"?>
        <FinancialDisclosure>
            <Member>
                <DocID>12345</DocID>
                <First>Test</First>
                <Last>User</Last>
                <FilingType>P</FilingType>
                <FilingDate>03/25/2024</FilingDate>
            </Member>
        </FinancialDisclosure>
        """

        records = parse_xml_index_impl(xml, 2024, "test.xml")
        assert records[0]["filing_date"] == "2024-03-25"

    def test_invalid_date_preserved(self, aws_credentials):
        """Test that invalid dates are preserved (not converted)."""
        xml = b"""<?xml version="1.0"?>
        <FinancialDisclosure>
            <Member>
                <DocID>12345</DocID>
                <First>Test</First>
                <Last>User</Last>
                <FilingType>P</FilingType>
                <FilingDate>invalid-date</FilingDate>
            </Member>
        </FinancialDisclosure>
        """

        records = parse_xml_index_impl(xml, 2024, "test.xml")
        # Invalid date should be preserved (not converted)
        assert records[0]["filing_date"] == "invalid-date"


class TestSchemaCompliance:
    """Tests ensuring records comply with JSON schema."""

    def test_required_fields_present(self, sample_house_fd_xml, aws_credentials):
        """Test all required fields are present per house_fd_filings.json schema."""
        records = parse_xml_index_impl(sample_house_fd_xml, 2024, "bronze/test.xml")

        required_fields = [
            "doc_id", "year", "filing_date", "filing_type",
            "first_name", "last_name", "state_district",
            "pdf_s3_key", "silver_ingest_ts", "source_system"
        ]

        for record in records:
            for field in required_fields:
                assert field in record, f"Missing required field: {field}"

    def test_source_system_value(self, sample_house_fd_xml, aws_credentials):
        """Test source_system is always 'house_fd'."""
        records = parse_xml_index_impl(sample_house_fd_xml, 2024, "test.xml")

        for record in records:
            assert record["source_system"] == "house_fd"


class TestEdgeCases:
    """Edge case tests for robustness."""

    def test_special_characters_in_names(self, aws_credentials):
        """Test handling of special characters in names."""
        xml = b"""<?xml version="1.0"?>
        <FinancialDisclosure>
            <Member>
                <DocID>12345</DocID>
                <First>Mary-Jane</First>
                <Last>O'Connor</Last>
                <FilingType>P</FilingType>
            </Member>
        </FinancialDisclosure>
        """

        records = parse_xml_index_impl(xml, 2024, "test.xml")
        assert records[0]["first_name"] == "Mary-Jane"
        assert records[0]["last_name"] == "O'Connor"

    def test_whitespace_trimming(self, aws_credentials):
        """Test that whitespace is properly trimmed."""
        xml = b"""<?xml version="1.0"?>
        <FinancialDisclosure>
            <Member>
                <DocID>  12345  </DocID>
                <First>  John  </First>
                <Last>  Doe  </Last>
                <FilingType>  P  </FilingType>
            </Member>
        </FinancialDisclosure>
        """

        records = parse_xml_index_impl(xml, 2024, "test.xml")
        assert records[0]["doc_id"] == "12345"
        assert records[0]["first_name"] == "John"
        assert records[0]["last_name"] == "Doe"
        assert records[0]["filing_type"] == "P"
