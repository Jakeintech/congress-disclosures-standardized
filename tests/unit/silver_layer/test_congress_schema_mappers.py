"""
Unit tests for congress_schema_mappers.py - Silver layer transformation logic.

Tests the core mapping functions that transform Bronze JSON to Silver records.
"""

import pytest
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ingestion"))

from lib.congress_schema_mappers import (
    map_member_to_silver,
    map_bill_to_silver,
    map_committee_to_silver,
    map_vote_to_silver,
    map_bill_actions_to_silver,
    map_bill_cosponsors_to_silver,
    get_silver_table_path,
    _normalize_party,
    _normalize_chamber,
    _safe_int,
    _parse_date,
)


class TestMapMemberToSilver:
    """Tests for member Bronze->Silver transformation."""

    def test_basic_member_mapping(self, sample_member_bronze_json):
        """Test successful member mapping with all fields."""
        result = map_member_to_silver(sample_member_bronze_json)

        assert result["bioguide_id"] == "P000197"
        assert result["first_name"] == "Nancy"
        assert result["last_name"] == "Pelosi"
        assert result["party"] == "D"
        assert result["state"] == "CA"
        assert result["district"] == 12
        assert result["chamber"] == "house"
        assert result["term_start_year"] == 2021
        assert result["term_end_year"] == 2023
        assert "bioguide.congress.gov" in result["depiction_url"]

    def test_missing_member_key(self):
        """Test handling of missing 'member' key."""
        result = map_member_to_silver({})
        assert result == {}

    def test_empty_member(self):
        """Test handling of empty member object."""
        result = map_member_to_silver({"member": {}})
        assert result.get("bioguide_id") is None

    def test_missing_terms(self, sample_member_bronze_json):
        """Test handling when terms are missing."""
        del sample_member_bronze_json["member"]["terms"]
        result = map_member_to_silver(sample_member_bronze_json)

        assert result["chamber"] == "unknown"
        assert result["term_start_year"] is None


class TestMapBillToSilver:
    """Tests for bill Bronze->Silver transformation."""

    def test_basic_bill_mapping(self, sample_bill_bronze_json):
        """Test successful bill mapping with all fields."""
        result = map_bill_to_silver(sample_bill_bronze_json)

        assert result["bill_id"] == "118-hr-1234"
        assert result["congress"] == 118
        assert result["bill_type"] == "hr"
        assert result["bill_number"] == 1234
        assert result["title"] == "Test Bill for Unit Testing"
        assert result["sponsor_bioguide_id"] == "P000197"
        assert result["sponsor_party"] == "D"
        assert result["policy_area"] == "Government Operations"
        assert result["cosponsors_count"] == 15

    def test_missing_bill_key(self):
        """Test handling of missing 'bill' key."""
        result = map_bill_to_silver({})
        assert result == {}

    def test_no_sponsors(self, sample_bill_bronze_json):
        """Test handling when no sponsors."""
        sample_bill_bronze_json["bill"]["sponsors"] = []
        result = map_bill_to_silver(sample_bill_bronze_json)

        assert result["sponsor_bioguide_id"] is None
        assert result["sponsor_name"] is None

    def test_no_policy_area(self, sample_bill_bronze_json):
        """Test handling when no policy area."""
        del sample_bill_bronze_json["bill"]["policyArea"]
        result = map_bill_to_silver(sample_bill_bronze_json)

        assert result["policy_area"] is None


class TestMapCommitteeToSilver:
    """Tests for committee Bronze->Silver transformation."""

    def test_basic_committee_mapping(self, sample_committee_bronze_json):
        """Test successful committee mapping."""
        result = map_committee_to_silver(sample_committee_bronze_json)

        assert result["committee_code"] == "hsif00"
        assert result["name"] == "Energy and Commerce Committee"
        assert result["chamber"] == "house"
        assert result["committee_type"] == "Standing"

    def test_missing_committee_key(self):
        """Test handling of missing 'committee' key."""
        result = map_committee_to_silver({})
        assert result == {}


class TestMapVoteToSilver:
    """Tests for vote Bronze->Silver transformation."""

    def test_basic_vote_mapping(self, sample_vote_bronze_json):
        """Test successful vote mapping - returns list of member votes."""
        result = map_vote_to_silver(sample_vote_bronze_json)

        assert len(result) == 2  # Two members voted

        # Check first member vote
        vote1 = result[0]
        assert vote1["vote_id"] == "118-2-100"
        assert vote1["bioguide_id"] == "P000197"
        assert vote1["vote_cast"] == "Yea"
        assert vote1["bill_id"] == "118-hr-1234"
        assert vote1["congress"] == 118
        assert vote1["session"] == 2

        # Check second member vote
        vote2 = result[1]
        assert vote2["bioguide_id"] == "M000317"
        assert vote2["vote_cast"] == "Nay"

    def test_missing_vote_key(self):
        """Test handling of missing 'vote' key."""
        result = map_vote_to_silver({})
        assert result == []

    def test_vote_without_bill(self, sample_vote_bronze_json):
        """Test vote not related to a bill."""
        del sample_vote_bronze_json["vote"]["bill"]
        result = map_vote_to_silver(sample_vote_bronze_json)

        assert result[0]["bill_id"] is None


class TestMapBillActionsToSilver:
    """Tests for bill actions Bronze->Silver transformation."""

    def test_bill_actions_mapping(self):
        """Test mapping bill actions."""
        bronze_json = {
            "actions": [
                {
                    "actionDate": "2024-01-15",
                    "text": "Introduced in House",
                    "type": "IntroReferral",
                    "actionCode": "Intro-H",
                    "sourceSystem": {"name": "House"}
                },
                {
                    "actionDate": "2024-01-20",
                    "text": "Referred to Committee",
                    "type": "Referral"
                }
            ]
        }

        result = map_bill_actions_to_silver(bronze_json, "118-hr-1234")

        assert len(result) == 2
        assert result[0]["bill_id"] == "118-hr-1234"
        assert result[0]["action_seq"] == 1
        assert result[0]["source_system"] == "House"
        assert result[1]["action_seq"] == 2


class TestMapBillCosponsorsToSilver:
    """Tests for bill cosponsors Bronze->Silver transformation."""

    def test_bill_cosponsors_mapping(self):
        """Test mapping bill cosponsors."""
        bronze_json = {
            "cosponsors": [
                {
                    "bioguideId": "S000033",
                    "fullName": "Bernie Sanders",
                    "sponsorshipDate": "2024-01-16",
                    "isOriginalCosponsor": True,
                    "party": "Independent",
                    "state": "VT"
                }
            ]
        }

        result = map_bill_cosponsors_to_silver(bronze_json, "118-hr-1234")

        assert len(result) == 1
        assert result[0]["bill_id"] == "118-hr-1234"
        assert result[0]["cosponsor_bioguide_id"] == "S000033"
        assert result[0]["party"] == "I"
        assert result[0]["is_original_cosponsor"] is True


class TestHelperFunctions:
    """Tests for internal helper functions."""

    def test_normalize_party(self):
        """Test party normalization."""
        assert _normalize_party("Democratic") == "D"
        assert _normalize_party("Republican") == "R"
        assert _normalize_party("Independent") == "I"
        assert _normalize_party("D") == "D"
        assert _normalize_party("R") == "R"
        assert _normalize_party(None) is None
        assert _normalize_party("") is None

    def test_normalize_chamber(self):
        """Test chamber normalization."""
        assert _normalize_chamber("House of Representatives") == "house"
        assert _normalize_chamber("Senate") == "senate"
        assert _normalize_chamber("Joint") == "joint"
        assert _normalize_chamber("HOUSE") == "house"
        assert _normalize_chamber("") == "unknown"
        assert _normalize_chamber(None) == "unknown"

    def test_safe_int(self):
        """Test safe integer conversion."""
        assert _safe_int(123) == 123
        assert _safe_int("123") == 123
        assert _safe_int(None) is None
        assert _safe_int("invalid") is None
        assert _safe_int("") is None

    def test_parse_date(self):
        """Test date parsing."""
        assert _parse_date("2024-01-15") == "2024-01-15"
        assert _parse_date("01/15/2024") == "2024-01-15"
        assert _parse_date("2024-01-15T10:30:00Z") == "2024-01-15"
        assert _parse_date(None) is None
        assert _parse_date("") is None


class TestGetSilverTablePath:
    """Tests for Silver S3 path generation."""

    def test_member_path(self):
        """Test member table path generation."""
        path = get_silver_table_path("member", chamber="house", is_current="true")
        assert path == "silver/congress/dim_member/chamber=house/is_current=true/part-0000.parquet"

    def test_bill_path(self):
        """Test bill table path generation."""
        path = get_silver_table_path("bill", congress=118, bill_type="hr")
        assert path == "silver/congress/dim_bill/congress=118/bill_type=hr/part-0000.parquet"

    def test_committee_path(self):
        """Test committee table path generation."""
        path = get_silver_table_path("committee", chamber="senate")
        assert path == "silver/congress/dim_committee/chamber=senate/part-0000.parquet"

    def test_vote_path(self):
        """Test vote table path generation."""
        path = get_silver_table_path("house_vote", congress=118, session=2)
        assert path == "silver/congress/house_vote_members/congress=118/session=2/part-0000.parquet"
