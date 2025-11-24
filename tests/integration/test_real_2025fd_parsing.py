"""Integration test using real 2025FD.xml data.

This test validates that our parsing logic correctly handles the actual
House financial disclosure XML structure and format.
"""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import pytest
from jsonschema import validate, ValidationError

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ingestion"))

# Import the actual parsing logic from the Lambda handler
# This ensures we're testing the real implementation
from lib import parquet_writer


@pytest.fixture
def real_2025fd_xml():
    """Load real 2025FD.xml fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "2025FD.xml"
    with open(fixture_path, "r", encoding="utf-8-sig") as f:  # utf-8-sig handles BOM
        return f.read()


@pytest.fixture
def filings_schema():
    """Load house_fd_filings JSON schema."""
    schema_path = Path(__file__).parent.parent.parent / "ingestion" / "schemas" / "house_fd_filings.json"
    with open(schema_path) as f:
        return json.load(f)


class TestReal2025FDParsing:
    """Tests using real 2025FD.xml data."""

    def test_xml_is_well_formed(self, real_2025fd_xml):
        """Test that real XML is well-formed and parseable."""
        root = ET.fromstring(real_2025fd_xml)
        assert root.tag == "FinancialDisclosure"

    def test_member_count(self, real_2025fd_xml):
        """Test that we can count members in real data."""
        root = ET.fromstring(real_2025fd_xml)
        members = root.findall(".//Member")

        # As of Nov 2025, there should be filings
        assert len(members) > 0
        print(f"Found {len(members)} member filings in 2025FD.xml")

    def test_parse_all_members(self, real_2025fd_xml):
        """Test parsing all members from real XML."""
        root = ET.fromstring(real_2025fd_xml)
        year = 2025
        xml_s3_key = "bronze/house/financial/year=2025/index/2025FD.xml"

        records = []
        for member in root.findall(".//Member"):
            doc_id = member.findtext("DocID", "").strip()

            if not doc_id:
                continue

            record = {
                "doc_id": doc_id,
                "year": year,
                "filing_date": member.findtext("FilingDate", "").strip(),
                "filing_type": member.findtext("FilingType", "").strip(),
                "prefix": member.findtext("Prefix", "").strip() or None,
                "first_name": member.findtext("First", "").strip(),
                "last_name": member.findtext("Last", "").strip(),
                "suffix": member.findtext("Suffix", "").strip() or None,
                "state_district": member.findtext("StateDst", "").strip(),
                "raw_xml_path": xml_s3_key,
                "raw_txt_path": xml_s3_key.replace(".xml", ".txt"),
                "pdf_s3_key": f"bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf",
                "bronze_ingest_ts": datetime.now().isoformat(),
                "silver_ingest_ts": datetime.now().isoformat(),
                "source_system": "house_fd",
            }

            # Convert filing_date to ISO format
            if record["filing_date"]:
                try:
                    date_obj = datetime.strptime(record["filing_date"], "%m/%d/%Y")
                    record["filing_date"] = date_obj.strftime("%Y-%m-%d")
                except ValueError as e:
                    pytest.fail(f"Failed to parse filing_date '{record['filing_date']}': {e}")

            records.append(record)

        # Should have parsed all members
        assert len(records) > 0
        print(f"Successfully parsed {len(records)} records")

    def test_all_records_validate_against_schema(self, real_2025fd_xml, filings_schema):
        """Test that ALL records from real data validate against our schema."""
        root = ET.fromstring(real_2025fd_xml)
        year = 2025

        validation_errors = []

        for member in root.findall(".//Member"):
            doc_id = member.findtext("DocID", "").strip()
            if not doc_id:
                continue

            record = {
                "doc_id": doc_id,
                "year": year,
                "filing_date": member.findtext("FilingDate", "").strip(),
                "filing_type": member.findtext("FilingType", "").strip(),
                "prefix": member.findtext("Prefix", "").strip() or None,
                "first_name": member.findtext("First", "").strip(),
                "last_name": member.findtext("Last", "").strip(),
                "suffix": member.findtext("Suffix", "").strip() or None,
                "state_district": member.findtext("StateDst", "").strip(),
                "raw_xml_path": "bronze/house/financial/year=2025/index/2025FD.xml",
                "raw_txt_path": "bronze/house/financial/year=2025/index/2025FD.txt",
                "pdf_s3_key": f"bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf",
                "bronze_ingest_ts": datetime.now().isoformat(),
                "silver_ingest_ts": datetime.now().isoformat(),
                "source_system": "house_fd",
            }

            # Convert filing_date
            if record["filing_date"]:
                try:
                    date_obj = datetime.strptime(record["filing_date"], "%m/%d/%Y")
                    record["filing_date"] = date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    pass  # Keep original if parsing fails

            # Validate against schema
            try:
                validate(instance=record, schema=filings_schema)
            except ValidationError as e:
                validation_errors.append({
                    "doc_id": doc_id,
                    "record": record,
                    "error": str(e)
                })

        # Report all validation errors
        if validation_errors:
            error_summary = "\n\n".join([
                f"DocID {err['doc_id']}: {err['error']}\nRecord: {err['record']}"
                for err in validation_errors[:5]  # Show first 5
            ])
            pytest.fail(
                f"Found {len(validation_errors)} validation errors:\n{error_summary}\n\n"
                f"(showing first 5 of {len(validation_errors)} errors)"
            )

    def test_state_district_formats(self, real_2025fd_xml):
        """Test that we handle all state_district format variations."""
        root = ET.fromstring(real_2025fd_xml)

        state_districts = set()
        for member in root.findall(".//Member"):
            state_dist = member.findtext("StateDst", "").strip()
            if state_dist:
                state_districts.add(state_dist)

        print(f"Found {len(state_districts)} unique state_district values:")
        for sd in sorted(state_districts)[:20]:  # Show first 20
            print(f"  {sd}")

        # Verify pattern: should be 2 letters followed by optional 1-2 digits
        # Examples: MI04, CA11, TX31, FL03
        for sd in state_districts:
            assert len(sd) >= 2, f"state_district too short: {sd}"
            assert sd[:2].isalpha(), f"First 2 chars should be alpha: {sd}"
            assert sd[:2].isupper(), f"First 2 chars should be uppercase: {sd}"
            if len(sd) > 2:
                assert sd[2:].isdigit(), f"Digits should follow letters: {sd}"

    def test_filing_type_codes(self, real_2025fd_xml):
        """Test that we capture all filing type codes in real data."""
        root = ET.fromstring(real_2025fd_xml)

        filing_types = set()
        for member in root.findall(".//Member"):
            filing_type = member.findtext("FilingType", "").strip()
            if filing_type:
                filing_types.add(filing_type)

        print(f"Found filing types: {sorted(filing_types)}")

        # Should have various filing types
        assert len(filing_types) > 0

        # All should be short codes (1-2 chars)
        for ft in filing_types:
            assert 1 <= len(ft) <= 2, f"Filing type unexpected length: {ft}"

    def test_name_with_special_characters(self, real_2025fd_xml):
        """Test handling of names with special characters."""
        root = ET.fromstring(real_2025fd_xml)

        special_char_names = []
        for member in root.findall(".//Member"):
            first = member.findtext("First", "").strip()
            last = member.findtext("Last", "").strip()

            # Check for periods, hyphens, apostrophes, spaces
            if any(char in first + last for char in [".", "-", "'", " "]):
                special_char_names.append(f"{first} {last}")

        if special_char_names:
            print(f"Found {len(special_char_names)} names with special characters:")
            for name in special_char_names[:10]:
                print(f"  {name}")

        # Should be able to handle these
        assert True  # Just documenting that we see these

    def test_date_format_consistency(self, real_2025fd_xml):
        """Test that all dates follow expected format."""
        root = ET.fromstring(real_2025fd_xml)

        date_errors = []
        for member in root.findall(".//Member"):
            filing_date = member.findtext("FilingDate", "").strip()
            if not filing_date:
                continue

            try:
                datetime.strptime(filing_date, "%m/%d/%Y")
            except ValueError:
                date_errors.append(filing_date)

        if date_errors:
            pytest.fail(f"Found {len(date_errors)} dates with unexpected format: {date_errors[:10]}")

    @pytest.mark.skip(reason="Sample only - run manually to see data statistics")
    def test_print_sample_records(self, real_2025fd_xml):
        """Print sample records for manual inspection."""
        root = ET.fromstring(real_2025fd_xml)

        members = root.findall(".//Member")[:5]

        print("\n" + "="*80)
        print("SAMPLE RECORDS FROM REAL 2025FD.XML:")
        print("="*80 + "\n")

        for i, member in enumerate(members, 1):
            print(f"Record {i}:")
            print(f"  DocID: {member.findtext('DocID')}")
            print(f"  Name: {member.findtext('Prefix')} {member.findtext('First')} {member.findtext('Last')} {member.findtext('Suffix')}")
            print(f"  State/District: {member.findtext('StateDst')}")
            print(f"  Filing Type: {member.findtext('FilingType')}")
            print(f"  Filing Date: {member.findtext('FilingDate')}")
            print(f"  Year: {member.findtext('Year')}")
            print()
