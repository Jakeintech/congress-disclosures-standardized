"""
Test suite for validating the unified state machine JSON structure.

This test validates that the congress_data_platform.json state machine
meets all requirements specified in STORY-028.
"""

import json
import os
import re
from pathlib import Path

import pytest


# Path to state machine definition
STATE_MACHINE_PATH = Path(__file__).parent.parent / "state_machines" / "congress_data_platform.json"


@pytest.fixture
def state_machine():
    """Load the state machine JSON."""
    with open(STATE_MACHINE_PATH, 'r') as f:
        return json.load(f)


class TestStateMachineStructure:
    """Test the basic structure of the state machine."""

    def test_state_machine_exists(self):
        """Verify the state machine JSON file exists."""
        assert STATE_MACHINE_PATH.exists(), "congress_data_platform.json should exist"

    def test_valid_json(self, state_machine):
        """Verify the state machine is valid JSON."""
        assert state_machine is not None
        assert isinstance(state_machine, dict)

    def test_has_comment(self, state_machine):
        """Verify the state machine has a descriptive comment."""
        assert "Comment" in state_machine
        assert "Congress Data Platform" in state_machine["Comment"]

    def test_has_start_state(self, state_machine):
        """Verify the state machine has a StartAt state."""
        assert "StartAt" in state_machine
        assert state_machine["StartAt"] == "ValidateInput"

    def test_has_states(self, state_machine):
        """Verify the state machine has states defined."""
        assert "States" in state_machine
        assert len(state_machine["States"]) > 0

    def test_has_timeout(self, state_machine):
        """Verify the state machine has a timeout configured."""
        assert "TimeoutSeconds" in state_machine
        assert state_machine["TimeoutSeconds"] == 7200  # 2 hours


class TestPhases:
    """Test that all 6 required phases are present."""

    def test_update_detection_phase(self, state_machine):
        """Verify Update Detection phase exists."""
        assert "CheckForUpdates" in state_machine["States"]
        assert "EvaluateUpdates" in state_machine["States"]

    def test_bronze_phase(self, state_machine):
        """Verify Bronze ingestion phase exists."""
        assert "BronzeIngestion" in state_machine["States"]

    def test_silver_phase(self, state_machine):
        """Verify Silver transformation phase exists."""
        assert "SilverTransformation" in state_machine["States"]
        assert "ValidateSilverQuality" in state_machine["States"]

    def test_gold_phase(self, state_machine):
        """Verify Gold layer phase exists."""
        assert "GoldDimensions" in state_machine["States"]
        assert "GoldFacts" in state_machine["States"]
        assert "GoldAggregates" in state_machine["States"]

    def test_quality_phase(self, state_machine):
        """Verify Quality checks phase exists."""
        assert "ValidateGoldQuality" in state_machine["States"]
        assert "EvaluateQuality" in state_machine["States"]

    def test_publish_phase(self, state_machine):
        """Verify Publish phase exists."""
        assert "PublishMetrics" in state_machine["States"]


class TestParallelStates:
    """Test Parallel states for concurrent operations."""

    def test_has_parallel_states(self, state_machine):
        """Verify state machine uses Parallel states."""
        parallel_states = [
            name for name, config in state_machine["States"].items()
            if config.get("Type") == "Parallel"
        ]
        assert len(parallel_states) >= 4, "Should have at least 4 Parallel states"

    def test_update_detection_parallel(self, state_machine):
        """Verify Update Detection uses parallel checks."""
        check_updates = state_machine["States"]["CheckForUpdates"]
        assert check_updates["Type"] == "Parallel"
        assert len(check_updates["Branches"]) == 3  # House FD, Congress, Lobbying

    def test_bronze_ingestion_parallel(self, state_machine):
        """Verify Bronze Ingestion uses parallel processing."""
        bronze = state_machine["States"]["BronzeIngestion"]
        assert bronze["Type"] == "Parallel"
        assert len(bronze["Branches"]) == 3

    def test_silver_transformation_parallel(self, state_machine):
        """Verify Silver Transformation uses parallel processing."""
        silver = state_machine["States"]["SilverTransformation"]
        assert silver["Type"] == "Parallel"
        assert len(silver["Branches"]) == 3

    def test_gold_dimensions_parallel(self, state_machine):
        """Verify Gold Dimensions are built in parallel."""
        gold_dims = state_machine["States"]["GoldDimensions"]
        assert gold_dims["Type"] == "Parallel"
        assert len(gold_dims["Branches"]) == 3


class TestMapStates:
    """Test Map states with MaxConcurrency configuration."""

    def test_map_states_exist(self, state_machine):
        """Verify Map states exist for distributed processing."""
        # Map states are nested in Parallel branches
        map_found = False
        for state_name, state_config in state_machine["States"].items():
            if state_config.get("Type") == "Parallel":
                for branch in state_config.get("Branches", []):
                    for branch_state_name, branch_state_config in branch.get("States", {}).items():
                        if branch_state_config.get("Type") == "Map":
                            map_found = True
        assert map_found, "Should have Map states for distributed processing"

    def test_map_max_concurrency(self, state_machine):
        """Verify Map states have MaxConcurrency=10."""
        map_states = []
        for state_name, state_config in state_machine["States"].items():
            if state_config.get("Type") == "Parallel":
                for branch in state_config.get("Branches", []):
                    for branch_state_name, branch_state_config in branch.get("States", {}).items():
                        if branch_state_config.get("Type") == "Map":
                            map_states.append({
                                "name": branch_state_name,
                                "max_concurrency": branch_state_config.get("MaxConcurrency")
                            })
        
        assert len(map_states) >= 2, "Should have at least 2 Map states"
        for map_state in map_states:
            assert map_state["max_concurrency"] == 10, \
                f"{map_state['name']} should have MaxConcurrency=10"


class TestErrorHandling:
    """Test Catch and Retry error handling."""

    def test_states_with_retry(self, state_machine):
        """Verify states have Retry blocks."""
        states_with_retry = [
            name for name, config in state_machine["States"].items()
            if config.get("Retry")
        ]
        assert len(states_with_retry) > 0, "Should have states with Retry blocks"

    def test_states_with_catch(self, state_machine):
        """Verify states have Catch blocks."""
        states_with_catch = [
            name for name, config in state_machine["States"].items()
            if config.get("Catch")
        ]
        assert len(states_with_catch) > 0, "Should have states with Catch blocks"

    def test_retry_exponential_backoff(self, state_machine):
        """Verify Retry blocks use exponential backoff."""
        for state_name, state_config in state_machine["States"].items():
            if state_config.get("Retry"):
                for retry_block in state_config["Retry"]:
                    if "BackoffRate" in retry_block:
                        assert retry_block["BackoffRate"] >= 1.5, \
                            f"{state_name} should use exponential backoff (>= 1.5)"


class TestLambdaReferences:
    """Test Lambda function references."""

    def test_lambda_arns_referenced(self, state_machine):
        """Verify Lambda function ARNs are referenced."""
        state_machine_json = json.dumps(state_machine)
        lambda_refs = set(re.findall(r'LAMBDA_[A-Z_]+', state_machine_json))
        
        assert len(lambda_refs) >= 20, \
            f"Should reference at least 20 Lambda functions, found {len(lambda_refs)}"

    def test_critical_lambdas_present(self, state_machine):
        """Verify critical Lambda functions are referenced."""
        state_machine_json = json.dumps(state_machine)
        
        critical_lambdas = [
            "LAMBDA_CHECK_HOUSE_FD_UPDATES",
            "LAMBDA_CHECK_CONGRESS_UPDATES",
            "LAMBDA_CHECK_LOBBYING_UPDATES",
            "LAMBDA_RUN_SODA_CHECKS",
            "LAMBDA_PUBLISH_METRICS",
            "LAMBDA_BUILD_DIM_MEMBERS",
            "LAMBDA_BUILD_FACT_TRANSACTIONS",
        ]
        
        for lambda_name in critical_lambdas:
            assert lambda_name in state_machine_json, \
                f"{lambda_name} should be referenced in state machine"


class TestYearValidation:
    """Test year range input validation."""

    def test_year_range_validation_exists(self, state_machine):
        """Verify year range validation is present."""
        validate_input = state_machine["States"]["ValidateInput"]
        assert "Parameters" in validate_input
        assert "valid_year_range" in validate_input["Parameters"]

    def test_five_year_lookback(self, state_machine):
        """Verify 5-year lookback window (2020-2025)."""
        validate_input = state_machine["States"]["ValidateInput"]
        year_range = validate_input["Parameters"]["valid_year_range"]
        
        assert year_range["min_year"] == 2020, "Min year should be 2020"
        assert year_range["max_year"] == 2025, "Max year should be 2025"
        assert year_range["max_year"] - year_range["min_year"] == 5, \
            "Should have 5-year lookback window"


class TestChoiceStates:
    """Test Choice states for conditional execution."""

    def test_evaluate_updates_choice(self, state_machine):
        """Verify EvaluateUpdates Choice state exists."""
        assert "EvaluateUpdates" in state_machine["States"]
        evaluate = state_machine["States"]["EvaluateUpdates"]
        assert evaluate["Type"] == "Choice"
        assert "Choices" in evaluate
        assert len(evaluate["Choices"]) >= 1

    def test_evaluate_quality_choice(self, state_machine):
        """Verify EvaluateQuality Choice state exists."""
        assert "EvaluateQuality" in state_machine["States"]
        evaluate = state_machine["States"]["EvaluateQuality"]
        assert evaluate["Type"] == "Choice"
        assert "Choices" in evaluate


class TestStateTransitions:
    """Test state transitions follow the correct flow."""

    def test_start_state_exists(self, state_machine):
        """Verify start state exists in States."""
        start_state = state_machine["StartAt"]
        assert start_state in state_machine["States"]

    def test_success_state_exists(self, state_machine):
        """Verify pipeline has a success state."""
        assert "PipelineSuccess" in state_machine["States"]
        success = state_machine["States"]["PipelineSuccess"]
        assert success["Type"] == "Succeed"

    def test_failure_states_exist(self, state_machine):
        """Verify pipeline has failure states."""
        assert "PipelineFailed" in state_machine["States"]
        assert "QualityCheckFailed" in state_machine["States"]


class TestSNSNotifications:
    """Test SNS notification states."""

    def test_quality_failure_notification(self, state_machine):
        """Verify quality failure triggers SNS notification."""
        assert "NotifyQualityFailure" in state_machine["States"]
        notify = state_machine["States"]["NotifyQualityFailure"]
        assert notify["Type"] == "Task"
        assert "arn:aws:states:::sns:publish" in notify["Resource"]

    def test_pipeline_failure_notification(self, state_machine):
        """Verify pipeline failure triggers SNS notification."""
        assert "NotifyPipelineFailure" in state_machine["States"]
        notify = state_machine["States"]["NotifyPipelineFailure"]
        assert notify["Type"] == "Task"
        assert "arn:aws:states:::sns:publish" in notify["Resource"]


class TestDocumentation:
    """Test that documentation exists."""

    def test_readme_exists(self):
        """Verify README.md exists in state_machines directory."""
        readme_path = STATE_MACHINE_PATH.parent / "README.md"
        assert readme_path.exists(), "state_machines/README.md should exist"

    def test_readme_content(self):
        """Verify README has comprehensive documentation."""
        readme_path = STATE_MACHINE_PATH.parent / "README.md"
        with open(readme_path, 'r') as f:
            content = f.read()
        
        assert "Congress Data Platform" in content
        assert "State Transition Documentation" in content
        assert "Lambda Functions Referenced" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
