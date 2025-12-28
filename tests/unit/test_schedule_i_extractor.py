"""Unit tests for Schedule I Extractor."""

import pytest
from ingestion.lib.extractors.schedules.schedule_i_extractor import ScheduleIExtractor


@pytest.fixture
def extractor():
    return ScheduleIExtractor()


def test_parse_table_valid_row(extractor):
    """Test parsing a valid contribution row."""
    table = {
        "headers": ["Source", "Activity", "Date", "Amount", "Charity"],
        "rows": [
            ["Event X", "Speech", "08/01/2023", "$2,000", "Red Cross"]
        ]
    }
    
    results = extractor.parse_table(table)
    assert len(results) == 1
    assert results[0]["source"] == "Event X"
    assert results[0]["activity"] == "Speech"
    assert results[0]["date"] == "08/01/2023"
    assert results[0]["amount"] == 2000.0
    assert results[0]["charity_name"] == "Red Cross"


def test_parse_table_varied_headers(extractor):
    """Test parsing with varied header names."""
    table = {
        "headers": ["Source", "Activity", "Date", "Amount", "Recipient"],
        "rows": [
            ["Event Y", "Panel", "09/01/2023", "$1,000", "Local Charity"]
        ]
    }
    
    results = extractor.parse_table(table)
    assert len(results) == 1
    assert results[0]["source"] == "Event Y"
    assert results[0]["charity_name"] == "Local Charity"
