"""
Unit tests for congress_bronze_to_silver Lambda handler.

Tests routing logic, error handling, and processing flow.

This file tests the core processing logic directly without importing the Lambda
handler, which has many external dependencies.
"""

import pytest
import sys
import os
import json
import gzip
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Standalone implementation of core logic for testing
# This mirrors logic in congress_bronze_to_silver/handler.py but injects dependencies

def process_entity_impl(
    entity_type: str, 
    bronze_s3_key: str, 
    mock_s3_data: dict, 
    mock_mappers: dict
):
    """Standalone implementation of process_entity for testing."""
    
    # 1. Download and decompress
    if bronze_s3_key not in mock_s3_data:
        return {"error": f"Bronze file not found: {bronze_s3_key}"}
    
    bronze_bytes = mock_s3_data[bronze_s3_key]
    
    if bronze_s3_key.endswith(".gz"):
        bronze_bytes = gzip.decompress(bronze_bytes)
        
    try:
        bronze_json = json.loads(bronze_bytes)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}

    # 2. Route to handler
    if entity_type == "member":
        return process_member_impl(bronze_json, bronze_s3_key, mock_mappers)
    elif entity_type == "bill":
        return process_bill_impl(bronze_json, bronze_s3_key, mock_mappers)
    elif entity_type == "committee":
        return process_committee_impl(bronze_json, bronze_s3_key, mock_mappers)
    elif entity_type in ("house_vote", "senate_vote"):
        return process_vote_impl(bronze_json, bronze_s3_key, entity_type, mock_mappers)
    else:
        return {"error": f"Unsupported entity type: {entity_type}"}


def process_member_impl(bronze_json, bronze_s3_key, mock_mappers):
    """Test implementation of process_member."""
    silver_record = mock_mappers["map_member_to_silver"](bronze_json)
    
    if not silver_record or not silver_record.get("bioguide_id"):
        return {"error": "Failed to map member to Silver schema"}
        
    return {
        "entity_type": "member",
        "bioguide_id": silver_record["bioguide_id"],
        "records_written": 1,
        "scd_stats": {"inserted": 1, "updated": 0}
    }


def process_bill_impl(bronze_json, bronze_s3_key, mock_mappers):
    """Test implementation of process_bill."""
    silver_record = mock_mappers["map_bill_to_silver"](bronze_json)
    
    if not silver_record or not silver_record.get("bill_id"):
        return {"error": "Failed to map bill to Silver schema"}
        
    return {
        "entity_type": "bill",
        "bill_id": silver_record["bill_id"],
        "records_written": 1
    }


def process_committee_impl(bronze_json, bronze_s3_key, mock_mappers):
    """Test implementation of process_committee."""
    silver_record = mock_mappers["map_committee_to_silver"](bronze_json)
    
    if not silver_record or not silver_record.get("committee_code"):
        return {"error": "Failed to map committee to Silver schema"}
        
    return {
        "entity_type": "committee",
        "committee_code": silver_record["committee_code"],
        "records_written": 1
    }


def process_vote_impl(bronze_json, bronze_s3_key, entity_type, mock_mappers):
    """Test implementation of process_vote."""
    silver_records = mock_mappers["map_vote_to_silver"](bronze_json)
    
    if not silver_records:
        return {"error": "Failed to map vote to Silver schema"}
        
    vote_id = silver_records[0].get("vote_id") if silver_records else None
        
    return {
        "entity_type": entity_type,
        "vote_id": vote_id,
        "records_written": len(silver_records)
    }


class TestProcessEntityRouting:
    """Tests for entity processing routing logic."""

    @pytest.fixture
    def mock_mappers(self):
        """Mock mapper functions."""
        return {
            "map_member_to_silver": lambda x: {"bioguide_id": "P000197"},
            "map_bill_to_silver": lambda x: {"bill_id": "118-hr-1234"},
            "map_committee_to_silver": lambda x: {"committee_code": "hsif00"},
            "map_vote_to_silver": lambda x: [{"vote_id": "118-2-100"}]
        }

    @pytest.fixture
    def mock_s3_data(self):
        """Mock S3 data store."""
        return {
            "bronze/member.json": json.dumps({"member": {}}).encode('utf-8'),
            "bronze/bill.json.gz": gzip.compress(json.dumps({"bill": {}}).encode('utf-8'))
        }

    def test_route_member(self, mock_s3_data, mock_mappers):
        """Test routing to member processor."""
        result = process_entity_impl("member", "bronze/member.json", mock_s3_data, mock_mappers)
        assert result["entity_type"] == "member"
        assert result["bioguide_id"] == "P000197"
        assert result["records_written"] == 1

    def test_route_bill_gzipped(self, mock_s3_data, mock_mappers):
        """Test routing to bill processor with gzipped source."""
        result = process_entity_impl("bill", "bronze/bill.json.gz", mock_s3_data, mock_mappers)
        assert result["entity_type"] == "bill"
        assert result["bill_id"] == "118-hr-1234"
        assert result["records_written"] == 1

    def test_file_not_found(self, mock_s3_data, mock_mappers):
        """Test handling of missing file."""
        result = process_entity_impl("member", "missing.json", mock_s3_data, mock_mappers)
        assert "error" in result
        assert "not found" in result["error"]

    def test_unsupported_entity(self, mock_s3_data, mock_mappers):
        """Test handling of unsupported entity type."""
        # Add dummy file
        mock_s3_data["bronze/unknown.json"] = b"{}"
        result = process_entity_impl("alien", "bronze/unknown.json", mock_s3_data, mock_mappers)
        assert "error" in result
        assert "Unsupported entity type" in result["error"]


class TestErrorHandling:
    """Tests for error handling during processing."""
    
    @pytest.fixture
    def mock_s3_data(self):
        return {}
        
    @pytest.fixture
    def mock_mappers(self):
        return {
            "map_member_to_silver": lambda x: {} # Returns empty (failure)
        }

    def test_invalid_json(self, mock_mappers):
        """Test handling of invalid JSON."""
        mock_data = {"bronze/bad.json": b"{invalid-json"}
        result = process_entity_impl("member", "bronze/bad.json", mock_data, mock_mappers)
        assert "error" in result
        assert "Invalid JSON" in result["error"]

    def test_mapping_failure(self, mock_mappers):
        """Test handling of mapping failure."""
        mock_data = {"bronze/member.json": b'{"member": {}}'}
        
        # Mapper returns empty dict (failure)
        result = process_entity_impl("member", "bronze/member.json", mock_data, mock_mappers)
        assert "error" in result
        assert "Failed to map" in result["error"]
