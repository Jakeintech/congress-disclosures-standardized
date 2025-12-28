"""Unit tests for Schedule G Extractor."""

import pytest
from ingestion.lib.extractors.schedules.schedule_g_extractor import ScheduleGExtractor


@pytest.fixture
def extractor():
    return ScheduleGExtractor()


def test_parse_table_valid_row(extractor):
    """Test parsing a valid gift row."""
    table = {
        "headers": ["Source", "Description", "Value", "Date Received"],
        "rows": [
            ["Friend", "Painting", "$500", "01/15/2023"]
        ]
    }
    
    results = extractor.parse_table(table)
    assert len(results) == 1
    assert results[0]["source"] == "Friend"
    assert results[0]["description"] == "Painting"
    assert results[0]["value"] == 500.0
    assert results[0]["date_received"] == "01/15/2023"


def test_parse_table_amount_formats(extractor):
    """Test parsing various amount formats."""
    table = {
        "headers": ["Source", "Value"],
        "rows": [
            ["A", "$1,000"],
            ["B", "250.50"],
            ["C", "Under $100"]
        ]
    }
    
    results = extractor.parse_table(table)
    assert len(results) == 3
    assert results[0]["value"] == 1000.0
    assert results[1]["value"] == 250.50
    assert results[2]["value"] == 100.0  # Extracts first number


def test_parse_table_varied_headers(extractor):
    """Test parsing with varied header names."""
    table = {
        "headers": ["Donor", "Item", "Amount", "Date"],
        "rows": [
            ["Org X", "Ticket", "$50", "02/2023"]
        ]
    }
    
    results = extractor.parse_table(table)
    assert len(results) == 1
    assert results[0]["source"] == "Org X"
    assert results[0]["description"] == "Ticket"
    assert results[0]["value"] == 50.0
