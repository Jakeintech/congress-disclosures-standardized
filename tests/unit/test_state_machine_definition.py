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
