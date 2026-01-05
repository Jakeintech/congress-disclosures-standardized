"""
Unit tests for build_dim_bills Lambda handler.
"""

import json
import os
import sys
from pathlib import Path

# Add Lambda handler to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ingestion/lambdas/build_dim_bills"))

import pytest
from conftest import upload_json_to_s3


@pytest.fixture
def sample_bills_data():
    """Sample bill data from Congress.gov."""
    return [
        {
            "number": "1",
            "type": "HR",
            "congress": 119,
            "title": "Infrastructure Investment and Jobs Act",
            "introducedDate": "2024-01-03",
            "sponsors": [
                {
                    "bioguideId": "S000185",
                    "fullName": "Rep. Scott, Robert C. 'Bobby' [D-VA-3]"
                }
            ],
            "policyArea": {
                "name": "Transportation and Public Works"
            },
            "latestAction": {
                "actionDate": "2024-01-15",
                "text": "Referred to the Committee on Transportation and Infrastructure"
            }
        },
        {
            "number": "2",
            "type": "S",
            "congress": 119,
            "title": "Climate Action Now Act",
            "introducedDate": "2024-01-05",
            "sponsors": [
                {
                    "bioguideId": "W000817",
                    "fullName": "Sen. Warren, Elizabeth [D-MA]"
                }
            ],
            "policyArea": {
                "name": "Environmental Protection"
            },
            "latestAction": {
                "actionDate": "2024-01-20",
                "text": "Read twice and referred to the Committee on Environment and Public Works"
            }
        },
        {
            "number": "100",
            "type": "HR",
            "congress": 118,
            "title": "Defense Authorization Act",
            "introducedDate": "2023-01-10",
            "sponsors": [],  # No sponsors
            "policyArea": {
                "name": "Armed Forces and National Security"
            },
            "latestAction": {
                "actionDate": "2023-12-15",
                "text": "Became Public Law No: 118-31"
            }
        }
    ]


def test_lambda_handler_success(s3_client, sample_bills_data, mock_lambda_context, monkeypatch):
    """Test successful dim_bills build."""
    # Setup
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')
    
    # Upload sample bills to Bronze layer
    for i, bill_data in enumerate(sample_bills_data):
        congress = bill_data.get('congress')
        bill_type = bill_data.get('type', '').lower()
        number = bill_data.get('number')
        key = f'bronze/congress/bills/{congress}/{bill_type}/{number}/data.json'
        upload_json_to_s3(s3_client, 'test-bucket', key, bill_data)
    
    # Import handler after mocking
    from handler import lambda_handler
    
    # Execute
    event = {}
    result = lambda_handler(event, mock_lambda_context)
    
    # Assert
    assert result['statusCode'] == 200
    assert result['status'] == 'success'
    assert result['dimension'] == 'dim_bills'
    assert result['records_processed'] == 3
    assert len(result['files_written']) > 0
    assert result['congresses'] == [118, 119]


def test_lambda_handler_no_bills(s3_client, mock_lambda_context, monkeypatch):
    """Test handling when no bills exist."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')
    
    from handler import lambda_handler
    
    event = {}
    result = lambda_handler(event, mock_lambda_context)
    
    # Should handle gracefully
    assert result['statusCode'] == 200
    assert result['status'] == 'success'
    assert result['records_processed'] == 0


def test_lambda_handler_custom_bucket(s3_client, sample_bills_data, mock_lambda_context):
    """Test with custom bucket name in event."""
    # Create custom bucket and upload data
    s3_client.create_bucket(Bucket='custom-bucket')
    
    for i, bill_data in enumerate(sample_bills_data):
        congress = bill_data.get('congress')
        bill_type = bill_data.get('type', '').lower()
        number = bill_data.get('number')
        key = f'bronze/congress/bills/{congress}/{bill_type}/{number}/data.json'
        upload_json_to_s3(s3_client, 'custom-bucket', key, bill_data)
    
    from handler import lambda_handler
    
    event = {'bucket_name': 'custom-bucket'}
    result = lambda_handler(event, mock_lambda_context)
    
    assert result['statusCode'] == 200
    assert result['records_processed'] == 3


def test_lambda_handler_malformed_bill(s3_client, mock_lambda_context, monkeypatch):
    """Test handling of malformed bill data."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')
    
    # Upload malformed bill (missing required fields)
    malformed_bill = {"number": "999"}  # Missing type, congress, etc.
    upload_json_to_s3(
        s3_client,
        'test-bucket',
        'bronze/congress/bills/119/hr/999/data.json',
        malformed_bill
    )
    
    # Also upload valid bill
    valid_bill = {
        "number": "1",
        "type": "HR",
        "congress": 119,
        "title": "Test Bill",
        "introducedDate": "2024-01-01",
        "sponsors": []
    }
    upload_json_to_s3(
        s3_client,
        'test-bucket',
        'bronze/congress/bills/119/hr/1/data.json',
        valid_bill
    )
    
    from handler import lambda_handler
    
    event = {}
    result = lambda_handler(event, mock_lambda_context)
    
    # Should process valid bill, skip malformed one (or process it with nulls)
    assert result['statusCode'] == 200
    assert result['records_processed'] >= 1  # At least the valid bill


def test_load_bills_from_bronze(s3_client, sample_bills_data):
    """Test bill loading from Bronze layer."""
    from handler import load_bills_from_bronze
    
    # Upload bills
    for bill_data in sample_bills_data:
        congress = bill_data.get('congress')
        bill_type = bill_data.get('type', '').lower()
        number = bill_data.get('number')
        key = f'bronze/congress/bills/{congress}/{bill_type}/{number}/data.json'
        upload_json_to_s3(s3_client, 'test-bucket', key, bill_data)
    
    # Load bills
    bills_df = load_bills_from_bronze('test-bucket')
    
    # Verify
    assert len(bills_df) == 3
    assert 'bill_number' in bills_df.columns
    assert 'bill_type' in bills_df.columns
    assert 'congress' in bills_df.columns
    assert 'title' in bills_df.columns
    assert 'sponsor_bioguide_id' in bills_df.columns
    assert 'policy_area' in bills_df.columns


def test_build_dim_bills_structure(s3_client, sample_bills_data):
    """Test dim_bills output structure."""
    from handler import load_bills_from_bronze, build_dim_bills
    
    # Upload test data
    for bill_data in sample_bills_data:
        congress = bill_data.get('congress')
        bill_type = bill_data.get('type', '').lower()
        number = bill_data.get('number')
        key = f'bronze/congress/bills/{congress}/{bill_type}/{number}/data.json'
        upload_json_to_s3(s3_client, 'test-bucket', key, bill_data)
    
    # Load and build
    bills_df = load_bills_from_bronze('test-bucket')
    dim_bills = build_dim_bills(bills_df)
    
    # Verify structure
    assert 'bill_key' in dim_bills.columns
    assert 'bill_id' in dim_bills.columns
    assert 'bill_number' in dim_bills.columns
    assert 'bill_type' in dim_bills.columns
    assert 'congress' in dim_bills.columns
    assert 'title' in dim_bills.columns
    assert 'introduced_date' in dim_bills.columns
    assert 'sponsor_bioguide_id' in dim_bills.columns
    assert 'sponsor_name' in dim_bills.columns
    assert 'policy_area' in dim_bills.columns
    assert 'effective_from' in dim_bills.columns
    assert 'effective_to' in dim_bills.columns
    assert 'version' in dim_bills.columns
    assert len(dim_bills) == 3
    
    # Verify bill_id format
    assert dim_bills[dim_bills['bill_number'] == '1']['bill_id'].values[0] == '119-hr-1'
    assert dim_bills[dim_bills['bill_number'] == '2']['bill_id'].values[0] == '119-s-2'
    
    # Verify surrogate keys are sequential
    assert set(dim_bills['bill_key'].values) == {1, 2, 3}


def test_write_to_gold(s3_client, sample_bills_data):
    """Test writing to Gold layer."""
    from handler import load_bills_from_bronze, build_dim_bills, write_to_gold
    
    # Upload and process
    for bill_data in sample_bills_data:
        congress = bill_data.get('congress')
        bill_type = bill_data.get('type', '').lower()
        number = bill_data.get('number')
        key = f'bronze/congress/bills/{congress}/{bill_type}/{number}/data.json'
        upload_json_to_s3(s3_client, 'test-bucket', key, bill_data)
    
    bills_df = load_bills_from_bronze('test-bucket')
    dim_bills = build_dim_bills(bills_df)
    result = write_to_gold(dim_bills, 'test-bucket')
    
    # Verify result
    assert result['total_records'] == 3
    assert result['congresses'] == [118, 119]
    assert len(result['files_written']) == 2  # 2 congresses
    
    # Verify files exist in S3
    for congress in [118, 119]:
        key = f'gold/congress/dimensions/dim_bills/congress={congress}/part-0000.parquet'
        response = s3_client.list_objects_v2(Bucket='test-bucket', Prefix=key)
        assert 'Contents' in response
        assert any(obj['Key'] == key for obj in response['Contents'])


def test_empty_bills_dataframe():
    """Test handling of empty bills dataframe."""
    from handler import build_dim_bills
    import pandas as pd
    
    empty_df = pd.DataFrame()
    result = build_dim_bills(empty_df)
    
    assert result.empty


def test_bills_without_sponsors(s3_client):
    """Test handling of bills without sponsors."""
    from handler import load_bills_from_bronze, build_dim_bills
    
    # Bill with no sponsors list
    bill_data = {
        "number": "999",
        "type": "HR",
        "congress": 119,
        "title": "Test Bill Without Sponsor",
        "introducedDate": "2024-01-01"
    }
    upload_json_to_s3(
        s3_client,
        'test-bucket',
        'bronze/congress/bills/119/hr/999/data.json',
        bill_data
    )
    
    bills_df = load_bills_from_bronze('test-bucket')
    dim_bills = build_dim_bills(bills_df)
    
    assert len(dim_bills) == 1
    assert dim_bills.iloc[0]['sponsor_bioguide_id'] is None
    assert dim_bills.iloc[0]['sponsor_name'] is None
