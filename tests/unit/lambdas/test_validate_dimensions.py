"""
Unit tests for validate_dimensions Lambda handler.
"""

import json
import os
import sys
from pathlib import Path
from io import BytesIO
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
import pyarrow as pa
import pyarrow.parquet as pq

# Add Lambda handler to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ingestion/lambdas/validate_dimensions"))


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client."""
    with patch('boto3.client') as mock_client:
        yield mock_client.return_value


@pytest.fixture
def mock_lambda_context():
    """Mock Lambda context."""
    context = Mock()
    context.function_name = 'validate-dimensions'
    context.aws_request_id = 'test-request-id'
    return context


@pytest.fixture
def sample_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')
    monkeypatch.setenv('LOG_LEVEL', 'INFO')


def create_mock_parquet_buffer(rows: dict, schema: pa.Schema) -> BytesIO:
    """Create a mock Parquet file in memory."""
    table = pa.Table.from_pydict(rows, schema=schema)
    buffer = BytesIO()
    pq.write_table(table, buffer)
    buffer.seek(0)  # Reset to beginning for reading
    return buffer


def create_fresh_buffer(data: dict, schema: pa.Schema):
    """Create a fresh BytesIO buffer with parquet data."""
    table = pa.Table.from_pydict(data, schema=schema)
    buffer = BytesIO()
    pq.write_table(table, buffer)
    buffer.seek(0)
    
    class MockBody:
        def __init__(self, buf):
            self._data = buf.read()
        
        def read(self):
            return self._data
    
    return MockBody(buffer)


def test_all_dimensions_exist_and_valid(mock_s3_client, mock_lambda_context, sample_env):
    """Test that all dimensions pass validation."""
    # Mock S3 responses
    mock_s3_client.head_object.return_value = {}
    
    # Create different parquet data for each dimension based on their primary key
    def get_object_side_effect(Bucket, Key):
        # Determine which dimension based on path
        if 'dim_members' in Key:
            schema = pa.schema([('member_key', pa.string()), ('name', pa.string())])
            data = {'member_key': ['M001', 'M002', 'M003'], 'name': ['Member 1', 'Member 2', 'Member 3']}
        elif 'dim_assets' in Key:
            schema = pa.schema([('asset_key', pa.string()), ('asset_name', pa.string())])
            data = {'asset_key': ['A001', 'A002'], 'asset_name': ['Asset 1', 'Asset 2']}
        elif 'dim_bills' in Key:
            schema = pa.schema([('bill_key', pa.string()), ('bill_number', pa.string())])
            data = {'bill_key': ['B001', 'B002'], 'bill_number': ['HR1', 'HR2']}
        elif 'dim_lobbyists' in Key:
            schema = pa.schema([('lobbyist_key', pa.string()), ('lobbyist_name', pa.string())])
            data = {'lobbyist_key': ['L001'], 'lobbyist_name': ['Lobbyist 1']}
        else:  # dim_dates
            schema = pa.schema([('date_key', pa.string()), ('date', pa.string())])
            data = {'date_key': ['D001', 'D002', 'D003'], 'date': ['2024-01-01', '2024-01-02', '2024-01-03']}
        
        return {'Body': create_fresh_buffer(data, schema)}
    
    mock_s3_client.get_object.side_effect = get_object_side_effect
    
    # Import handler after mocking
    from handler import lambda_handler
    
    # Execute
    result = lambda_handler({}, mock_lambda_context)
    
    # Assert
    assert result['validation_passed'] is True
    assert result['dimensions_validated'] == 5
    assert result['dimensions_passed'] == 5
    assert result['dimensions_failed'] == 0
    assert len(result['failures']) == 0
    assert all(d['passed'] for d in result['details'])


def test_missing_dimension_fails_validation(mock_s3_client, mock_lambda_context, sample_env):
    """Test that missing dimension file fails validation."""
    # Mock S3 to raise NoSuchKey for first dimension
    mock_s3_client.head_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}},
        'HeadObject'
    )
    
    from handler import lambda_handler
    
    result = lambda_handler({}, mock_lambda_context)
    
    # Assert - all dimensions should fail as head_object fails for all
    assert result['validation_passed'] is False
    assert result['dimensions_failed'] == 5
    assert len(result['failures']) == 5
    assert all('not found' in failure.lower() for failure in result['failures'])


def test_empty_dimension_fails_validation(mock_s3_client, mock_lambda_context, sample_env):
    """Test that dimension with 0 rows fails validation."""
    # Mock S3 responses
    mock_s3_client.head_object.return_value = {}
    
    # Create different empty parquet data for each dimension based on their primary key
    def get_object_side_effect(Bucket, Key):
        # Determine which dimension based on path and create appropriate empty schema
        if 'dim_members' in Key:
            schema = pa.schema([('member_key', pa.string()), ('name', pa.string())])
            data = {'member_key': [], 'name': []}
        elif 'dim_assets' in Key:
            schema = pa.schema([('asset_key', pa.string()), ('asset_name', pa.string())])
            data = {'asset_key': [], 'asset_name': []}
        elif 'dim_bills' in Key:
            schema = pa.schema([('bill_key', pa.string()), ('bill_number', pa.string())])
            data = {'bill_key': [], 'bill_number': []}
        elif 'dim_lobbyists' in Key:
            schema = pa.schema([('lobbyist_key', pa.string()), ('lobbyist_name', pa.string())])
            data = {'lobbyist_key': [], 'lobbyist_name': []}
        else:  # dim_dates
            schema = pa.schema([('date_key', pa.string()), ('date', pa.string())])
            data = {'date_key': [], 'date': []}
        
        return {'Body': create_fresh_buffer(data, schema)}
    
    mock_s3_client.get_object.side_effect = get_object_side_effect
    
    from handler import lambda_handler
    
    result = lambda_handler({}, mock_lambda_context)
    
    # Assert - all dimensions fail because they're all empty
    assert result['validation_passed'] is False
    assert result['dimensions_failed'] == 5
    assert all('empty' in failure.lower() or '0 rows' in failure.lower() 
               for failure in result['failures'])


def test_duplicate_primary_keys_fails_validation(mock_s3_client, mock_lambda_context, sample_env):
    """Test that duplicate primary keys fail validation."""
    # Mock S3 responses
    mock_s3_client.head_object.return_value = {}
    
    # Create parquet with duplicate keys for each dimension
    def get_object_side_effect(Bucket, Key):
        if 'dim_members' in Key:
            schema = pa.schema([('member_key', pa.string()), ('name', pa.string())])
            data = {'member_key': ['M001', 'M002', 'M001'], 'name': ['Member 1', 'Member 2', 'Member 3']}
        elif 'dim_assets' in Key:
            schema = pa.schema([('asset_key', pa.string()), ('asset_name', pa.string())])
            data = {'asset_key': ['A001', 'A001'], 'asset_name': ['Asset 1', 'Asset 2']}
        elif 'dim_bills' in Key:
            schema = pa.schema([('bill_key', pa.string()), ('bill_number', pa.string())])
            data = {'bill_key': ['B001', 'B002', 'B001'], 'bill_number': ['HR1', 'HR2', 'HR3']}
        elif 'dim_lobbyists' in Key:
            schema = pa.schema([('lobbyist_key', pa.string()), ('lobbyist_name', pa.string())])
            data = {'lobbyist_key': ['L001', 'L001'], 'lobbyist_name': ['Lobbyist 1', 'Lobbyist 2']}
        else:  # dim_dates
            schema = pa.schema([('date_key', pa.string()), ('date', pa.string())])
            data = {'date_key': ['D001', 'D002', 'D001'], 'date': ['2024-01-01', '2024-01-02', '2024-01-03']}
        
        return {'Body': create_fresh_buffer(data, schema)}
    
    mock_s3_client.get_object.side_effect = get_object_side_effect
    
    from handler import lambda_handler
    
    result = lambda_handler({}, mock_lambda_context)
    
    # Assert - all dimensions fail due to duplicates
    assert result['validation_passed'] is False
    assert result['dimensions_failed'] == 5
    assert any('duplicate' in failure.lower() for failure in result['failures'])


def test_partial_failure_reports_correctly(mock_s3_client, mock_lambda_context, sample_env):
    """Test that partial failures are reported correctly."""
    call_count = [0]
    
    # Create valid and empty parquet files
    valid_schema = pa.schema([
        ('key', pa.string()),
        ('value', pa.string())
    ])
    
    empty_schema = pa.schema([
        ('key', pa.string()),
        ('value', pa.string())
    ])
    
    def head_object_side_effect(Bucket, Key):
        """Some dimensions exist, some don't."""
        if 'dim_lobbyists' in Key or 'dim_dates' in Key:
            raise ClientError(
                {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}},
                'HeadObject'
            )
        return {}
    
    def get_object_side_effect(Bucket, Key):
        """Return valid or empty parquet based on dimension."""
        call_count[0] += 1
        # First call (dim_members) - valid, second (dim_assets) - empty, third (dim_bills) - valid
        if call_count[0] % 2 == 0:
            return {'Body': create_fresh_buffer({'key': [], 'value': []}, empty_schema)}
        else:
            return {'Body': create_fresh_buffer({'key': ['K001', 'K002'], 'value': ['Value 1', 'Value 2']}, valid_schema)}
    
    mock_s3_client.head_object.side_effect = head_object_side_effect
    mock_s3_client.get_object.side_effect = get_object_side_effect
    
    from handler import lambda_handler
    
    result = lambda_handler({}, mock_lambda_context)
    
    # Assert - partial failure
    assert result['validation_passed'] is False
    assert result['dimensions_validated'] == 5
    assert result['dimensions_passed'] < 5
    assert result['dimensions_failed'] > 0
    assert len(result['failures']) > 0
    assert len(result['failures']) == result['dimensions_failed']


def test_validate_dimension_missing_primary_key_column(mock_s3_client, sample_env):
    """Test validation when primary key column doesn't exist in parquet."""
    # Mock S3 responses
    mock_s3_client.head_object.return_value = {}
    
    # Create parquet WITHOUT the expected primary key column
    schema = pa.schema([
        ('wrong_key', pa.string()),
        ('name', pa.string())
    ])
    data = {
        'wrong_key': ['W001', 'W002'],
        'name': ['Name 1', 'Name 2']
    }
    
    mock_s3_client.get_object.return_value = {'Body': create_fresh_buffer(data, schema)}
    
    from handler import validate_dimension
    
    # Test dimension with primary_key that doesn't exist
    dim = {
        'name': 'dim_test',
        'path': 'gold/dimensions/test.parquet',
        'primary_key': 'expected_key'
    }
    
    result = validate_dimension(dim)
    
    # Assert
    assert result['passed'] is False
    assert 'not found in table' in result['error']
    # Row count should still be 2 since the table exists and has 2 rows
    assert result.get('row_count') == 2
