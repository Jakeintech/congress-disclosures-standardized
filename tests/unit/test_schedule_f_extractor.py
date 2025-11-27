"""Unit tests for Schedule F Extractor."""

import pytest
from ingestion.lib.extractors.schedules.schedule_f_extractor import ScheduleFExtractor


@pytest.fixture
def extractor():
    return ScheduleFExtractor()


def test_parse_table_valid_row(extractor):
    """Test parsing a valid agreement row."""
    table = {
        "headers": ["Date", "Parties Involved", "Type", "Status", "Terms"],
        "rows": [
            ["01/2023", "ABC Corp", "Employment", "Active", "Salary and benefits"]
        ]
    }
    
    results = extractor.parse_table(table)
    assert len(results) == 1
    assert results[0]["date"] == "01/2023"
    assert results[0]["parties_involved"] == "ABC Corp"
    assert results[0]["type"] == "Employment"
    assert results[0]["status"] == "Active"
    assert results[0]["terms"] == "Salary and benefits"


def test_parse_table_empty_row(extractor):
    """Test parsing a table with an empty row."""
    table = {
        "headers": ["Date", "Parties"],
        "rows": [
            ["", ""]
        ]
    }
    
    results = extractor.parse_table(table)
    assert len(results) == 0


def test_parse_table_missing_required_fields(extractor):
    """Test parsing a row missing required fields (parties/terms)."""
    table = {
        "headers": ["Date", "Parties"],
        "rows": [
            ["01/2023", ""]  # No parties
        ]
    }
    
    results = extractor.parse_table(table)
    assert len(results) == 0


def test_parse_table_varied_headers(extractor):
    """Test parsing with varied header names."""
    table = {
        "headers": ["Date", "Employer", "Type", "Status", "Description"],
        "rows": [
            ["01/2023", "XYZ Inc", "Consulting", "Done", "Advisory services"]
        ]
    }
    
    results = extractor.parse_table(table)
    assert len(results) == 1
    assert results[0]["parties_involved"] == "XYZ Inc"
    assert results[0]["terms"] == "Advisory services"
