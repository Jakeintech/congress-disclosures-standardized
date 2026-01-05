"""
Unit tests for state machine definitions.

Tests validate JSON structure and required states for Step Functions state machines.
"""

import json
from pathlib import Path

import pytest


STATE_MACHINES_DIR = Path(__file__).parent.parent.parent / "state_machines"


@pytest.fixture(scope="module")
def congress_data_platform_definition():
    """Load congress_data_platform.json once for all tests."""
    state_machine_path = STATE_MACHINES_DIR / "congress_data_platform.json"

    with open(state_machine_path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def house_fd_pipeline_definition():
    """Load house_fd_pipeline.json once for all tests."""
    state_machine_path = STATE_MACHINES_DIR / "house_fd_pipeline.json"

    with open(state_machine_path, "r") as f:
        return json.load(f)


class TestStateMachineDefinitions:
    """Test suite for state machine JSON definitions."""

    def test_congress_data_platform_json_valid(self, congress_data_platform_definition):
        definition = congress_data_platform_definition

        assert definition is not None
        assert "States" in definition
        assert "StartAt" in definition
        assert "Comment" in definition

    def test_bronze_ingestion_parallel_state_exists(
        self, congress_data_platform_definition
    ):
        states = congress_data_platform_definition["States"]

        assert "BronzeIngestion" in states, "BronzeIngestion state not found"

        bronze_state = states["BronzeIngestion"]

        assert bronze_state["Type"] == "Parallel"
        assert "Branches" in bronze_state
        assert len(bronze_state["Branches"]) == 3

    def test_bronze_ingestion_has_three_branches(
        self, congress_data_platform_definition
    ):
        bronze_state = congress_data_platform_definition["States"]["BronzeIngestion"]
        branches = bronze_state["Branches"]

        branch_names = [branch["StartAt"] for branch in branches]

        assert "IngestHouseFD" in branch_names
        assert "IngestCongress" in branch_names
        assert "IngestLobbying" in branch_names

    def test_bronze_ingestion_error_handling(
        self, congress_data_platform_definition
    ):
        bronze_state = congress_data_platform_definition["States"]["BronzeIngestion"]

        for branch in bronze_state["Branches"]:
            start_state = branch["StartAt"]
            ingest_state = branch["States"][start_state]

            assert ingest_state["Type"] == "Task"
            assert "Retry" in ingest_state and len(ingest_state["Retry"]) > 0
            assert "Catch" in ingest_state and len(ingest_state["Catch"]) > 0

    def test_bronze_ingestion_timeout_configured(
        self, congress_data_platform_definition
    ):
        bronze_state = congress_data_platform_definition["States"]["BronzeIngestion"]

        for branch in bronze_state["Branches"]:
            start_state = branch["StartAt"]
            ingest_state = branch["States"][start_state]

            assert "TimeoutSeconds" in ingest_state
            assert 300 <= ingest_state["TimeoutSeconds"] <= 900

    def test_check_for_updates_parallel_state_exists(
        self, congress_data_platform_definition
    ):
        states = congress_data_platform_definition["States"]

        assert "CheckForUpdates" in states
        check_state = states["CheckForUpdates"]

        assert check_state["Type"] == "Parallel"
        assert len(check_state["Branches"]) == 3

    def test_state_machine_has_timeout(self, congress_data_platform_definition):
        assert "TimeoutSeconds" in congress_data_platform_definition
        assert congress_data_platform_definition["TimeoutSeconds"] == 7200

    def test_all_state_machines_valid_json(self):
        for state_machine_file in STATE_MACHINES_DIR.glob("*.json"):
            if "interpolated" in state_machine_file.name:
                continue

            with open(state_machine_file, "r") as f:
                try:
                    definition = json.load(f)
                    assert "States" in definition
                    assert "StartAt" in definition
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {state_machine_file.name}: {e}")

    def test_multi_year_iterator_sequential_processing(
        self, congress_data_platform_definition
    ):
        states = congress_data_platform_definition["States"]

        assert "MultiYearIterator" in states
        multi_year_state = states["MultiYearIterator"]

        assert multi_year_state["Type"] == "Map"
        assert multi_year_state["MaxConcurrency"] == 1

    def test_multi_year_iterator_error_handling(
        self, congress_data_platform_definition
    ):
        iterator_states = (
            congress_data_platform_definition["States"]["MultiYearIterator"]["Iterator"]["States"]
        )

        child_exec_state = iterator_states["StartChildExecution"]

        assert "Catch" in child_exec_state
        assert child_exec_state["Catch"][0]["Next"] == "LogYearFailure"

        assert iterator_states["LogYearFailure"]["Next"] == "YearComplete"

    def test_multi_year_iterator_cloudwatch_metrics(
        self, congress_data_platform_definition
    ):
        iterator_states = (
            congress_data_platform_definition["States"]["MultiYearIterator"]["Iterator"]["States"]
        )

        for state_name in ("LogYearSuccess", "LogYearFailure"):
            state = iterator_states[state_name]
            assert state["Type"] == "Task"
            assert "LAMBDA_PUBLISH_METRICS" in state["Resource"]

    def test_initial_load_summary_notification(
        self, congress_data_platform_definition
    ):
        states = congress_data_platform_definition["States"]

        assert "SummarizeInitialLoad" in states
        summary_state = states["SummarizeInitialLoad"]

        assert summary_state["Type"] == "Task"
        assert "sns:publish" in summary_state["Resource"]
        assert "Initial Load Complete" in summary_state["Parameters"]["Subject"]


class TestHouseFDPipelineMultiYear:
    """Test suite for House FD Pipeline multi-year initial load features."""

    def test_extract_documents_map_concurrency(self, house_fd_pipeline_definition):
        states = house_fd_pipeline_definition["States"]

        assert "ExtractDocumentsMap" in states
        extract_map_state = states["ExtractDocumentsMap"]

        assert extract_map_state["Type"] == "Map"
        assert "MaxConcurrency" in extract_map_state
        assert extract_map_state["MaxConcurrency"] == 40

    def test_house_fd_multi_year_iterator_sequential_processing(
        self, house_fd_pipeline_definition
    ):
        multi_year_state = house_fd_pipeline_definition["States"]["MultiYearIterator"]

        assert multi_year_state["Type"] == "Map"
        assert multi_year_state["MaxConcurrency"] == 1

    def test_house_fd_multi_year_iterator_error_handling(
        self, house_fd_pipeline_definition
    ):
        iterator_states = (
            house_fd_pipeline_definition["States"]["MultiYearIterator"]["Iterator"]["States"]
        )

        child_exec_state = iterator_states["StartChildExecution"]

        assert "Catch" in child_exec_state
        assert child_exec_state["Catch"][0]["Next"] == "LogYearFailure"

    def test_house_fd_multi_year_cloudwatch_metrics(
        self, house_fd_pipeline_definition
    ):
        iterator_states = (
            house_fd_pipeline_definition["States"]["MultiYearIterator"]["Iterator"]["States"]
        )

        for state_name in ("LogYearSuccess", "LogYearFailure"):
            assert "LAMBDA_PUBLISH_METRICS" in iterator_states[state_name]["Resource"]

    def test_house_fd_initial_load_summary(self, house_fd_pipeline_definition):
        states = house_fd_pipeline_definition["States"]

        assert "SummarizeInitialLoad" in states
        summary_state = states["SummarizeInitialLoad"]

        assert summary_state["Type"] == "Task"
        assert "sns:publish" in summary_state["Resource"]
        assert "House FD Initial Load Complete" in summary_state["Parameters"]["Subject"]
