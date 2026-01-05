"""
Shared pytest fixtures for Silver layer tests.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add ingestion lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ingestion"))


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for tests."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['S3_BRONZE_PREFIX'] = 'bronze'
    os.environ['S3_SILVER_PREFIX'] = 'silver'


@pytest.fixture
def mock_lambda_context():
    """Mock Lambda context object."""
    context = MagicMock()
    context.get_remaining_time_in_millis.return_value = 300000
    context.function_name = 'test-silver-function'
    context.aws_request_id = 'test-request-id'
    return context


@pytest.fixture
def sample_house_fd_xml():
    """Sample House FD XML index content."""
    return b"""<?xml version="1.0"?>
<FinancialDisclosure>
    <Member>
        <DocID>10063228</DocID>
        <Prefix>Hon.</Prefix>
        <Last>Smith</Last>
        <First>John</First>
        <Suffix></Suffix>
        <FilingType>P</FilingType>
        <StateDst>CA11</StateDst>
        <FilingDate>01/15/2024</FilingDate>
    </Member>
    <Member>
        <DocID>10078945</DocID>
        <Last>Doe</Last>
        <First>Jane</First>
        <FilingType>A</FilingType>
        <StateDst>NY10</StateDst>
        <FilingDate>02/20/2024</FilingDate>
    </Member>
</FinancialDisclosure>
"""


@pytest.fixture
def sample_member_bronze_json():
    """Sample Congress.gov member API response (Bronze JSON)."""
    return {
        "member": {
            "bioguideId": "P000197",
            "firstName": "Nancy",
            "lastName": "Pelosi",
            "partyName": "Democratic",
            "state": "CA",
            "district": 12,
            "terms": {
                "item": [
                    {
                        "chamber": "House of Representatives",
                        "startYear": 2021,
                        "endYear": 2023
                    }
                ]
            },
            "depiction": {
                "imageUrl": "https://bioguide.congress.gov/bioguide/photo/P/P000197.jpg"
            },
            "updateDate": "2024-01-15T10:30:00Z"
        }
    }


@pytest.fixture
def sample_bill_bronze_json():
    """Sample Congress.gov bill API response (Bronze JSON)."""
    return {
        "bill": {
            "congress": 118,
            "type": "HR",
            "number": 1234,
            "title": "Test Bill for Unit Testing",
            "shortTitle": "Test Bill",
            "introducedDate": "2024-01-15",
            "originChamber": "House",
            "sponsors": [
                {
                    "bioguideId": "P000197",
                    "fullName": "Nancy Pelosi",
                    "party": "D",
                    "state": "CA"
                }
            ],
            "policyArea": {"name": "Government Operations"},
            "latestAction": {
                "actionDate": "2024-02-01",
                "text": "Referred to committee"
            },
            "cosponsors": {"count": 15},
            "updateDate": "2024-02-01T12:00:00Z"
        }
    }


@pytest.fixture
def sample_committee_bronze_json():
    """Sample Congress.gov committee API response (Bronze JSON)."""
    return {
        "committee": {
            "systemCode": "hsif00",
            "name": "Energy and Commerce Committee",
            "chamber": "House",
            "committeeTypeCode": "Standing",
            "url": "https://energycommerce.house.gov",
            "updateDate": "2024-01-10T08:00:00Z"
        }
    }


@pytest.fixture
def sample_vote_bronze_json():
    """Sample Congress.gov vote API response (Bronze JSON)."""
    return {
        "vote": {
            "congress": 118,
            "session": 2,
            "rollCall": 100,
            "chamber": "House",
            "date": "2024-01-20",
            "question": "On Passage",
            "result": "Passed",
            "bill": {
                "congress": 118,
                "type": "HR",
                "number": 1234
            },
            "members": [
                {
                    "bioguideId": "P000197",
                    "name": "Pelosi, Nancy",
                    "party": "D",
                    "state": "CA",
                    "vote": "Yea"
                },
                {
                    "bioguideId": "M000317",
                    "name": "McCarthy, Kevin",
                    "party": "R",
                    "state": "CA",
                    "vote": "Nay"
                }
            ]
        }
    }
