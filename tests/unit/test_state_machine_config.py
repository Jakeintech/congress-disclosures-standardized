"""
Unit tests for Step Functions state machine configurations.

Tests validate critical configuration values like MaxConcurrency to ensure
they match architectural requirements and prevent throttling issues.
"""

import json
import os
import pytest


class TestStateMachineConfiguration:
    """Test Step Functions state machine configuration values."""

    @pytest.fixture
    def house_fd_pipeline(self):
        """Load house_fd_pipeline.json state machine definition."""
        pipeline_path = os.path.join(
            os.path.dirname(__file__),
            "../../state_machines/house_fd_pipeline.json"
        )
        with open(pipeline_path, "r") as f:
            return json.load(f)

    @pytest.fixture
    def congress_pipeline(self):
        """Load congress_pipeline.json state machine definition."""
        pipeline_path = os.path.join(
            os.path.dirname(__file__),
            "../../state_machines/congress_pipeline.json"
        )
        with open(pipeline_path, "r") as f:
            return json.load(f)

    @pytest.fixture
    def lobbying_pipeline(self):
        """Load lobbying_pipeline.json state machine definition."""
        pipeline_path = os.path.join(
            os.path.dirname(__file__),
            "../../state_machines/lobbying_pipeline.json"
        )
        with open(pipeline_path, "r") as f:
            return json.load(f)

    def find_map_states(self, obj, path=""):
        """
        Recursively find all Map states in a state machine definition.

        Args:
            obj: The state machine definition (dict, list, or other)
            path: Current path in the object tree

        Returns:
            List of tuples: (path, state_name, max_concurrency)
        """
        results = []
        if isinstance(obj, dict):
            # Check if this is a Map state
            if obj.get("Type") == "Map":
                state_name = path.split(".")[-1] if "." in path else path
                max_conc = obj.get("MaxConcurrency", None)
                results.append((path, state_name, max_conc))

            # Recurse into nested objects
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                results.extend(self.find_map_states(value, new_path))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                results.extend(self.find_map_states(item, f"{path}[{i}]"))

        return results

    def test_house_fd_extract_documents_map_concurrency(self, house_fd_pipeline):
        """
        Test STORY-002: ExtractDocumentsMap should have MaxConcurrency = 10.

        This prevents Lambda throttling while enabling 10x speedup over sequential
        processing (41 hours → 4 hours).
        """
        map_states = self.find_map_states(house_fd_pipeline)

        # Find ExtractDocumentsMap state
        extract_map = None
        for path, state_name, max_conc in map_states:
            if "ExtractDocumentsMap" in path:
                extract_map = (path, state_name, max_conc)
                break

        assert extract_map is not None, "ExtractDocumentsMap state not found"
        path, state_name, max_conc = extract_map

        assert max_conc == 10, (
            f"ExtractDocumentsMap MaxConcurrency should be 10 (found {max_conc}). "
            "This value prevents Lambda throttling while enabling parallel processing."
        )

    def test_house_fd_multi_year_iterator_concurrency(self, house_fd_pipeline):
        """
        Test multi-year iterator has reasonable concurrency (≤2).

        Multi-year processing should be limited to prevent overwhelming the system
        with too many simultaneous year-level executions.
        """
        map_states = self.find_map_states(house_fd_pipeline)

        # Find MultiYearIterator state
        multi_year = None
        for path, state_name, max_conc in map_states:
            if "MultiYearIterator" in path:
                multi_year = (path, state_name, max_conc)
                break

        assert multi_year is not None, "MultiYearIterator state not found"
        path, state_name, max_conc = multi_year

        assert max_conc is not None, "MultiYearIterator should have MaxConcurrency set"
        assert max_conc <= 2, (
            f"MultiYearIterator MaxConcurrency should be ≤2 (found {max_conc}). "
            "Higher values could overwhelm the system."
        )

    def test_all_map_states_have_max_concurrency(self, house_fd_pipeline):
        """
        Test that all Map states have MaxConcurrency explicitly set.

        This prevents unexpected default behavior and ensures performance is predictable.
        """
        map_states = self.find_map_states(house_fd_pipeline)

        assert len(map_states) > 0, "Expected at least one Map state in house_fd_pipeline"

        for path, state_name, max_conc in map_states:
            assert max_conc is not None, (
                f"Map state '{state_name}' at {path} should have MaxConcurrency set. "
                "All Map states should explicitly define concurrency limits."
            )
            assert isinstance(max_conc, int), (
                f"MaxConcurrency for '{state_name}' should be an integer (found {type(max_conc)})"
            )
            assert max_conc >= 1, (
                f"MaxConcurrency for '{state_name}' should be ≥1 (found {max_conc})"
            )

    def test_congress_pipeline_map_states(self, congress_pipeline):
        """Test Congress pipeline Map states have reasonable MaxConcurrency values."""
        map_states = self.find_map_states(congress_pipeline)

        assert len(map_states) > 0, "Expected at least one Map state in congress_pipeline"

        for path, state_name, max_conc in map_states:
            assert max_conc is not None, f"Map state '{state_name}' should have MaxConcurrency set"
            assert max_conc <= 20, (
                f"Congress pipeline MaxConcurrency should be ≤20 (found {max_conc} in {state_name}). "
                "Higher values may exceed Congress.gov API rate limits."
            )

    def test_lobbying_pipeline_map_states(self, lobbying_pipeline):
        """Test Lobbying pipeline Map states have reasonable MaxConcurrency values."""
        map_states = self.find_map_states(lobbying_pipeline)

        assert len(map_states) > 0, "Expected at least one Map state in lobbying_pipeline"

        for path, state_name, max_conc in map_states:
            assert max_conc is not None, f"Map state '{state_name}' should have MaxConcurrency set"
            # Lobbying pipeline typically processes quarterly data, doesn't need high concurrency
            assert max_conc <= 5, (
                f"Lobbying pipeline MaxConcurrency should be ≤5 (found {max_conc} in {state_name})"
            )

    def test_house_fd_pipeline_structure(self, house_fd_pipeline):
        """Test basic structure of house_fd_pipeline.json."""
        assert "Comment" in house_fd_pipeline
        assert "StartAt" in house_fd_pipeline
        assert "States" in house_fd_pipeline
        assert isinstance(house_fd_pipeline["States"], dict)

        # Verify key states exist
        expected_states = [
            "CheckExecutionType",
            "IngestZip",
            "IndexToSilver",
            "ExtractDocumentsMap",
            "ValidateSilverQuality",
            "TransformToGoldParallel",
        ]
        for state in expected_states:
            assert state in house_fd_pipeline["States"], f"Missing state: {state}"

    def test_extract_documents_map_uses_distributed_mode(self, house_fd_pipeline):
        """
        Test that ExtractDocumentsMap uses Distributed Map for scalability.

        Distributed Map can handle 10,000+ items efficiently, unlike inline Map (40 max).
        """
        extract_map = house_fd_pipeline["States"]["ExtractDocumentsMap"]

        assert "ItemProcessor" in extract_map, "ExtractDocumentsMap should use ItemProcessor"
        processor_config = extract_map["ItemProcessor"].get("ProcessorConfig", {})

        assert processor_config.get("Mode") == "DISTRIBUTED", (
            "ExtractDocumentsMap should use DISTRIBUTED mode for processing 1000+ PDFs"
        )
        assert processor_config.get("ExecutionType") in ["STANDARD", "EXPRESS"], (
            "ExecutionType should be STANDARD or EXPRESS"
        )

    def test_extract_documents_map_has_item_reader(self, house_fd_pipeline):
        """
        Test that ExtractDocumentsMap uses S3 ItemReader for Distributed Map.

        Distributed Map requires ItemReader to specify where items come from (S3).
        """
        extract_map = house_fd_pipeline["States"]["ExtractDocumentsMap"]

        assert "ItemReader" in extract_map, "Distributed Map requires ItemReader"
        item_reader = extract_map["ItemReader"]

        assert item_reader.get("Resource") == "arn:aws:states:::s3:getObject", (
            "ItemReader should use S3 getObject for reading item manifests"
        )
        assert "ReaderConfig" in item_reader, "ItemReader should have ReaderConfig"
        assert item_reader["ReaderConfig"].get("InputType") == "JSON", (
            "ItemReader should expect JSON input"
        )
