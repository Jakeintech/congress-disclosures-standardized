"""
Unit tests for check_lobbying_updates watermarking (STORY-051)

Tests S3 existence-based watermarking for lobbying data.
"""
import pytest
from unittest.mock import patch
from datetime import datetime
import sys
import os
import importlib.util

# Import handler module with unique name to avoid caching issues
handler_path = os.path.join(
    os.path.dirname(__file__), 
    "../../../ingestion/lambdas/check_lobbying_updates/handler.py"
)
spec = importlib.util.spec_from_file_location("lobbying_handler", handler_path)
handler = importlib.util.module_from_spec(spec)
sys.modules["lobbying_handler"] = handler
spec.loader.exec_module(handler)


@pytest.fixture
def mock_s3():
    """Mock S3 client."""
    with patch.object(handler, "s3") as mock_s3_client:
        yield mock_s3_client


class TestLobbyingWatermarking:
    """Test lobbying watermarking functions."""

    def test_check_bronze_exists_true(self, mock_s3):
        """Test Bronze data exists."""
        mock_s3.list_objects_v2.return_value = {"KeyCount": 5}

        result = handler.check_bronze_exists(2025, "Q1")

        assert result is True
        mock_s3.list_objects_v2.assert_called_once()

    def test_check_bronze_exists_false(self, mock_s3):
        """Test Bronze data does not exist."""
        mock_s3.list_objects_v2.return_value = {"KeyCount": 0}

        result = handler.check_bronze_exists(2025, "Q1")

        assert result is False

    def test_all_quarters_exist(self, mock_s3):
        """Test when all quarters already exist."""
        mock_s3.list_objects_v2.return_value = {"KeyCount": 5}

        result = handler.lambda_handler({"year": 2025, "quarter": "all"}, {})

        assert result["has_new_filings"] is False
        assert len(result["quarters_to_process"]) == 0

    def test_some_quarters_missing(self, mock_s3):
        """Test when some quarters are missing."""
        # Q1 and Q3 exist, Q2 and Q4 missing
        mock_s3.list_objects_v2.side_effect = [
            {"KeyCount": 5},  # Q1 exists
            {"KeyCount": 0},  # Q2 missing
            {"KeyCount": 5},  # Q3 exists
            {"KeyCount": 0}   # Q4 missing
        ]

        result = handler.lambda_handler({"year": 2025, "quarter": "all"}, {})

        assert result["has_new_filings"] is True
        assert len(result["quarters_to_process"]) == 2
        assert "Q2" in result["quarters_to_process"]
        assert "Q4" in result["quarters_to_process"]

    def test_year_outside_lookback_window(self):
        """Test year validation outside lookback window."""
        current_year = datetime.now().year
        old_year = current_year - 10

        result = handler.lambda_handler({"year": old_year, "quarter": "Q1"}, {})

        assert result["has_new_filings"] is False
        assert "error" in result

    def test_invalid_quarter(self):
        """Test invalid quarter validation."""
        result = handler.lambda_handler({"year": 2025, "quarter": "Q5"}, {})

        assert result["has_new_filings"] is False
        assert "error" in result

    def test_scenario_1_current_quarter_already_ingested(self, mock_s3):
        """Test Acceptance Criteria Scenario 1: Current quarter already ingested.

        GIVEN: Bronze has complete Q4 2024 data
        WHEN: check_lobbying_updates executes for Q4 2024
        THEN: return {"has_new_filings": false}
        """
        mock_s3.list_objects_v2.return_value = {"KeyCount": 5}

        result = handler.lambda_handler({"year": 2024, "quarter": "Q4"}, {})

        assert result["has_new_filings"] is False
        assert result["year"] == 2024
        assert result["quarter"] == "Q4"
        assert len(result["quarters_to_process"]) == 0
        mock_s3.list_objects_v2.assert_called_once()

    def test_scenario_2_new_quarter_available(self, mock_s3):
        """Test Acceptance Criteria Scenario 2: New quarter available.

        GIVEN: Q1 2025 filings now available
        AND: Bronze has no Q1 2025 data
        WHEN: check_lobbying_updates executes
        THEN: return {"has_new_filings": true, ...}
        """
        mock_s3.list_objects_v2.return_value = {"KeyCount": 0}

        result = handler.lambda_handler({"year": 2025, "quarter": "Q1"}, {})

        assert result["has_new_filings"] is True
        assert result["year"] == 2025
        assert result["quarter"] == "Q1"
        assert "Q1" in result["quarters_to_process"]
        assert len(result["ingest_tasks"]) > 0
        mock_s3.list_objects_v2.assert_called_once()

    def test_scenario_3_year_outside_lookback_window(self):
        """Test Acceptance Criteria Scenario 3: Year/Quarter outside 5-year lookback.

        GIVEN: Request to check Q1 2015 (outside 5-year window)
        WHEN: check_lobbying_updates executes
        THEN: return {"has_new_filings": false, "reason": "outside_lookback_window"}
        AND: Log "Q1 2015 outside 5-year lookback window"
        """
        current_year = datetime.now().year
        old_year = current_year - 10  # 10 years ago, definitely outside 5-year window

        result = handler.lambda_handler({"year": old_year, "quarter": "Q1"}, {})

        assert result["has_new_filings"] is False
        assert "error" in result
        assert "lookback" in result["error"].lower()
        assert result["year"] == old_year
