"""
Unit tests for state machine definitions.

Tests validate JSON structure and required states for Step Functions state machines.
"""

import json
import os
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
        """Test that congress_data_platform.json is valid JSON."""
        definition = congress_data_platform_definition
        
        assert definition is not None
        assert "States" in definition
        assert "StartAt" in definition
        assert "Comment" in definition

    def test_bronze_ingestion_parallel_state_exists(self, congress_data_platform_definition):
        """Test that BronzeIngestion Parallel state exists in congress_data_platform."""
        states = congress_data_platform_definition["States"]
        
        # Verify BronzeIngestion state exists
        assert "BronzeIngestion" in states, "BronzeIngestion state not found"
        
        bronze_state = states["BronzeIngestion"]
        
        # Verify it's a Parallel state
        assert bronze_state["Type"] == "Parallel", "BronzeIngestion must be a Parallel state"
        
        # Verify it has branches
        assert "Branches" in bronze_state, "BronzeIngestion must have Branches"
        assert len(bronze_state["Branches"]) == 3, "BronzeIngestion must have 3 branches"

    def test_bronze_ingestion_has_three_branches(self, congress_data_platform_definition):
        """Test that BronzeIngestion has House FD, Congress, and Lobbying branches."""
        bronze_state = congress_data_platform_definition["States"]["BronzeIngestion"]
        branches = bronze_state["Branches"]
        
        # Extract first state names from each branch
        branch_names = []
        for branch in branches:
            start_state = branch["StartAt"]
            branch_names.append(start_state)
        
        # Verify all three ingestion branches exist
        assert "IngestHouseFD" in branch_names, "House FD ingestion branch missing"
        assert "IngestCongress" in branch_names, "Congress ingestion branch missing"
        assert "IngestLobbying" in branch_names, "Lobbying ingestion branch missing"

    def test_bronze_ingestion_error_handling(self, congress_data_platform_definition):
        """Test that each branch has proper error handling (Retry, Catch)."""
        bronze_state = congress_data_platform_definition["States"]["BronzeIngestion"]
        branches = bronze_state["Branches"]
        
        for branch in branches:
            start_state = branch["StartAt"]
            states = branch["States"]
            
            # Get the first (ingestion) state
            ingest_state = states[start_state]
            
            # Verify it's a Task state
            assert ingest_state["Type"] == "Task", f"{start_state} must be a Task state"
            
            # Verify it has Retry configuration
            assert "Retry" in ingest_state, f"{start_state} must have Retry configuration"
            assert len(ingest_state["Retry"]) > 0, f"{start_state} must have at least one retry policy"
            
            # Verify it has Catch configuration
            assert "Catch" in ingest_state, f"{start_state} must have Catch configuration"
            assert len(ingest_state["Catch"]) > 0, f"{start_state} must have at least one catch policy"

    def test_bronze_ingestion_timeout_configured(self, congress_data_platform_definition):
        """Test that each ingestion Lambda has a timeout configured."""
        bronze_state = congress_data_platform_definition["States"]["BronzeIngestion"]
        branches = bronze_state["Branches"]
        
        for branch in branches:
            start_state = branch["StartAt"]
            states = branch["States"]
            ingest_state = states[start_state]
            
            # Verify timeout is configured
            assert "TimeoutSeconds" in ingest_state, f"{start_state} must have TimeoutSeconds configured"
            timeout = ingest_state["TimeoutSeconds"]
            
            # Verify timeout is reasonable (between 5 and 15 minutes)
            assert 300 <= timeout <= 900, f"{start_state} timeout should be between 300 and 900 seconds"

    def test_check_for_updates_parallel_state_exists(self, congress_data_platform_definition):
        """Test that CheckForUpdates Parallel state exists."""
        states = congress_data_platform_definition["States"]
        
        # Verify CheckForUpdates state exists
        assert "CheckForUpdates" in states, "CheckForUpdates state not found"
        
        check_state = states["CheckForUpdates"]
        
        # Verify it's a Parallel state
        assert check_state["Type"] == "Parallel", "CheckForUpdates must be a Parallel state"
        
        # Verify it has 3 branches (House FD, Congress, Lobbying)
        assert len(check_state["Branches"]) == 3, "CheckForUpdates must have 3 branches"

    def test_state_machine_has_timeout(self, congress_data_platform_definition):
        """Test that the state machine has a global timeout configured."""
        assert "TimeoutSeconds" in congress_data_platform_definition, "State machine must have TimeoutSeconds"
        timeout = congress_data_platform_definition["TimeoutSeconds"]
        
        # Verify timeout is 2 hours (7200 seconds) as per spec
        assert timeout == 7200, "State machine timeout should be 7200 seconds (2 hours)"

    def test_all_state_machines_valid_json(self):
        """Test that all state machine JSON files are valid."""
        for state_machine_file in STATE_MACHINES_DIR.glob("*.json"):
            # Skip interpolated files (they contain Terraform variables)
            if "interpolated" in state_machine_file.name:
                continue
            
            with open(state_machine_file, "r") as f:
                try:
                    definition = json.load(f)
                    assert definition is not None
                    assert "States" in definition
                    assert "StartAt" in definition
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {state_machine_file.name}: {e}")

    def test_extract_documents_map_concurrency(self, house_fd_pipeline_definition):
        """Test that ExtractDocumentsMap has MaxConcurrency set to 10."""
        states = house_fd_pipeline_definition["States"]

        # Verify ExtractDocumentsMap state exists
        assert "ExtractDocumentsMap" in states, "ExtractDocumentsMap state not found"

        extract_map_state = states["ExtractDocumentsMap"]

        # Verify it's a Map state
        assert extract_map_state["Type"] == "Map", "ExtractDocumentsMap must be a Map state"

        # Verify MaxConcurrency is set to 10
        assert "MaxConcurrency" in extract_map_state, "ExtractDocumentsMap must have MaxConcurrency configured"
        assert extract_map_state["MaxConcurrency"] == 10, "ExtractDocumentsMap MaxConcurrency must be 10"

    def test_multi_year_iterator_exists_house_fd(self, house_fd_pipeline_definition):
        """Test that MultiYearIterator state exists in house_fd_pipeline."""
        states = house_fd_pipeline_definition["States"]
        
        # Verify MultiYearIterator state exists
        assert "MultiYearIterator" in states, "MultiYearIterator state not found"
        
        iterator_state = states["MultiYearIterator"]
        
        # Verify it's a Map state
        assert iterator_state["Type"] == "Map", "MultiYearIterator must be a Map state"
        
        # Verify ItemsPath is configured
        assert "ItemsPath" in iterator_state, "MultiYearIterator must have ItemsPath"
        assert iterator_state["ItemsPath"] == "$.years", "ItemsPath must be $.years"

    def test_multi_year_iterator_sequential_processing(self, house_fd_pipeline_definition):
        """Test that MultiYearIterator processes years sequentially (MaxConcurrency=1)."""
        states = house_fd_pipeline_definition["States"]
        iterator_state = states["MultiYearIterator"]
        
        # Verify MaxConcurrency is set to 1 for sequential processing
        assert "MaxConcurrency" in iterator_state, "MultiYearIterator must have MaxConcurrency"
        assert iterator_state["MaxConcurrency"] == 1, "MultiYearIterator MaxConcurrency must be 1 for sequential processing"

    def test_multi_year_iterator_error_handling(self, house_fd_pipeline_definition):
        """Test that MultiYearIterator has proper error handling."""
        states = house_fd_pipeline_definition["States"]
        iterator_state = states["MultiYearIterator"]
        iterator_states = iterator_state["Iterator"]["States"]
        
        # Verify StartChildExecution has Catch configuration
        start_child = iterator_states["StartChildExecution"]
        assert "Catch" in start_child, "StartChildExecution must have Catch configuration"
        
        # Verify error is caught and routed to LogYearFailure
        catch_configs = start_child["Catch"]
        assert len(catch_configs) > 0, "Must have at least one catch configuration"
        assert catch_configs[0]["Next"] == "LogYearFailure", "Errors must route to LogYearFailure"

    def test_multi_year_iterator_continue_on_error(self, house_fd_pipeline_definition):
        """Test that MultiYearIterator continues processing after year failure."""
        states = house_fd_pipeline_definition["States"]
        iterator_state = states["MultiYearIterator"]
        iterator_states = iterator_state["Iterator"]["States"]
        
        # Verify LogYearFailure state exists
        assert "LogYearFailure" in iterator_states, "LogYearFailure state must exist"
        
        # Verify LogYearFailure ends gracefully (not a Fail state)
        log_failure_state = iterator_states["LogYearFailure"]
        assert log_failure_state["Type"] == "Task", "LogYearFailure must be a Task state (not Fail)"
        assert log_failure_state["Next"] == "YearCompleted", "LogYearFailure must continue to YearCompleted"

    def test_multi_year_iterator_cloudwatch_metrics(self, house_fd_pipeline_definition):
        """Test that MultiYearIterator publishes CloudWatch metrics for progress."""
        states = house_fd_pipeline_definition["States"]
        iterator_state = states["MultiYearIterator"]
        iterator_states = iterator_state["Iterator"]["States"]
        
        # Verify LogYearSuccess state exists
        assert "LogYearSuccess" in iterator_states, "LogYearSuccess state must exist"
        
        log_success_state = iterator_states["LogYearSuccess"]
        
        # Verify it's a Task that calls LAMBDA_PUBLISH_METRICS
        assert log_success_state["Type"] == "Task", "LogYearSuccess must be a Task"
        assert "LAMBDA_PUBLISH_METRICS" in log_success_state["Resource"], "Must call metrics Lambda"
        
        # Verify it has metric_name parameter
        params = log_success_state["Parameters"]
        assert "metric_name" in params, "Must have metric_name parameter"
        assert params["metric_name"] == "YearProcessingComplete", "Metric name must be YearProcessingComplete"

    def test_multi_year_iterator_summary_notification(self, house_fd_pipeline_definition):
        """Test that MultiYearIterator sends summary notification after completion."""
        states = house_fd_pipeline_definition["States"]
        
        # Verify SummarizeInitialLoad state exists
        assert "SummarizeInitialLoad" in states, "SummarizeInitialLoad state must exist"
        
        summary_state = states["SummarizeInitialLoad"]
        
        # Verify it's an SNS publish task
        assert summary_state["Type"] == "Task", "SummarizeInitialLoad must be a Task"
        assert "sns:publish" in summary_state["Resource"], "Must use SNS publish resource"
        
        # Verify subject includes "Initial Load"
        params = summary_state["Parameters"]
        assert "Initial Load" in params["Subject"], "Subject must mention Initial Load"

    def test_check_execution_type_routes_to_multi_year(self, house_fd_pipeline_definition):
        """Test that CheckExecutionType routes initial_load to MultiYearIterator."""
        states = house_fd_pipeline_definition["States"]
        
        # Verify CheckExecutionType exists
        assert "CheckExecutionType" in states, "CheckExecutionType state must exist"
        
        check_state = states["CheckExecutionType"]
        
        # Verify it's a Choice state
        assert check_state["Type"] == "Choice", "CheckExecutionType must be a Choice state"
        
        # Verify it has a choice for execution_type == "initial_load"
        choices = check_state["Choices"]
        initial_load_choice = next(
            (c for c in choices if c.get("Variable") == "$.execution_type" and c.get("StringEquals") == "initial_load"),
            None
        )
        
        assert initial_load_choice is not None, "Must have choice for execution_type=initial_load"
        assert initial_load_choice["Next"] == "MultiYearIterator", "initial_load must route to MultiYearIterator"

    def test_multi_year_iterator_exists_congress_platform(self, congress_data_platform_definition):
        """Test that MultiYearIterator state exists in congress_data_platform."""
        states = congress_data_platform_definition["States"]
        
        # Verify MultiYearIterator state exists
        assert "MultiYearIterator" in states, "MultiYearIterator state not found in congress_data_platform"
        
        iterator_state = states["MultiYearIterator"]
        
        # Verify it's a Map state with sequential processing
        assert iterator_state["Type"] == "Map", "MultiYearIterator must be a Map state"
        assert iterator_state["MaxConcurrency"] == 1, "MultiYearIterator MaxConcurrency must be 1"

    def test_multi_year_iterator_congress_platform_error_handling(self, congress_data_platform_definition):
        """Test that congress_data_platform MultiYearIterator has proper error handling."""
        states = congress_data_platform_definition["States"]
        iterator_state = states["MultiYearIterator"]
        iterator_states = iterator_state["Iterator"]["States"]
        
        # Verify continue-on-error behavior
        assert "LogYearFailure" in iterator_states, "LogYearFailure state must exist"
        log_failure_state = iterator_states["LogYearFailure"]
        assert log_failure_state["Next"] == "YearCompleted", "Must continue after failure"
