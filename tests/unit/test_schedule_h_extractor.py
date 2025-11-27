"""Unit tests for Schedule H Extractor."""

import pytest
from ingestion.lib.extractors.schedules.schedule_h_extractor import ScheduleHExtractor


@pytest.fixture
def extractor():
    return ScheduleHExtractor()


def test_parse_table_valid_row(extractor):
    """Test parsing a valid travel row."""
    table = {
        "headers": ["Source", "Date(s)", "Itinerary", "Purpose", "Type"],
        "rows": [
            ["Institute Y", "05/01/2023 - 05/05/2023", "DC to NY", "Conference", "Travel"]
        ]
    }
    
    results = extractor.parse_table(table)
    assert len(results) == 1
    assert results[0]["source"] == "Institute Y"
    assert results[0]["date_from"] == "05/01/2023"
    assert results[0]["date_to"] == "05/05/2023"
    assert results[0]["itinerary"] == "DC to NY"
    assert results[0]["purpose"] == "Conference"


def test_parse_table_single_date(extractor):
    """Test parsing a row with a single date."""
    table = {
        "headers": ["Source", "Date"],
        "rows": [
            ["Org Z", "06/01/2023"]
        ]
    }
    
    results = extractor.parse_table(table)
    assert len(results) == 1
    assert results[0]["date_from"] == "06/01/2023"
    assert "date_to" not in results[0] or results[0]["date_to"] is None


def test_parse_table_varied_headers(extractor):
    """Test parsing with varied header names."""
    table = {
        "headers": ["Sponsor", "Dates", "Destination", "Purpose"],
        "rows": [
            ["Group A", "07/01/2023", "Paris", "Meeting"]
        ]
    }
    
    results = extractor.parse_table(table)
    assert len(results) == 1
    assert results[0]["source"] == "Group A"
    assert results[0]["itinerary"] == "Paris"
