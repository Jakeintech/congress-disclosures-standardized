"""
Unit tests for validate_dimensions Lambda (STORY-049)

Tests dimension validation logic including file existence checks,
row count validation, and primary key uniqueness checks.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json
import sys
import os
import pyarrow as pa
import pyarrow.parquet as pq
from io import BytesIO
from botocore.exceptions import ClientError

# Add ingestion directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../ingestion'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../ingestion/lambdas/validate_dimensions'))

# Mock environment variables before importing handler
os.environ['S3_BUCKET_NAME'] = 'test-bucket'
os.environ['LOG_LEVEL'] = 'INFO'

from handler import (
    lambda_handler,
    validate_dimension,
    REQUIRED_DIMENSIONS
)


def create_mock_parquet_with_rows(num_rows: int, primary_key: str = 'test_key', has_duplicates: bool = False):
    """Create a mock Parquet file in BytesIO for testing."""
    if has_duplicates:
        # Create data with duplicate keys
        data = {
            primary_key: [f'key_{i % (num_rows // 2)}' for i in range(num_rows)],
            'name': [f'name_{i}' for i in range(num_rows)]
        }
    else:
        # Create data with unique keys
        data = {
            primary_key: [f'key_{i}' for i in range(num_rows)],
            'name': [f'name_{i}' for i in range(num_rows)]
        }
    
    table = pa.table(data)
    buffer = BytesIO()
    pq.write_table(table, buffer)
    buffer.seek(0)
    return buffer


class TestValidateDimension:
    """Test validate_dimension function."""
    
    @patch('handler.s3_client')
    def test_valid_dimension_passes(self, mock_s3):
        """Test that valid dimension with unique keys passes."""
        # Arrange
        mock_s3.head_object.return_value = {}
        mock_parquet = create_mock_parquet_with_rows(100, 'member_key')
        mock_s3.get_object.return_value = {'Body': mock_parquet}
        
        dim = {
            'name': 'dim_members',
            'path': 'gold/house/financial/dimensions/dim_members/dim_members.parquet',
            'primary_key': 'member_key'
        }
        
        # Act
        result = validate_dimension(dim)
        
        # Assert
        assert result['passed'] is True
        assert result['dimension'] == 'dim_members'
        assert result['row_count'] == 100
        assert result['has_duplicates'] is False
        assert result['error'] is None
    
    @patch('handler.s3_client')
    def test_missing_dimension_fails(self, mock_s3):
        """Test that missing dimension file fails validation."""
        # Arrange
        error = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}},
            'HeadObject'
        )
        mock_s3.head_object.side_effect = error
        mock_s3.exceptions.NoSuchKey = ClientError
        
        dim = {
            'name': 'dim_members',
            'path': 'missing/path.parquet',
            'primary_key': 'member_key'
        }
        
        # Act
        result = validate_dimension(dim)
        
        # Assert
        assert result['passed'] is False
        assert result['dimension'] == 'dim_members'
        assert 'not found' in result['error'].lower()
    
    @patch('handler.s3_client')
    def test_empty_dimension_fails(self, mock_s3):
        """Test that dimension with 0 rows fails validation."""
        # Arrange
        mock_s3.head_object.return_value = {}
        mock_parquet = create_mock_parquet_with_rows(0, 'asset_key')
        mock_s3.get_object.return_value = {'Body': mock_parquet}
        
        dim = {
            'name': 'dim_assets',
            'path': 'gold/house/financial/dimensions/assets.parquet',
            'primary_key': 'asset_key'
        }
        
        # Act
        result = validate_dimension(dim)
        
        # Assert
        assert result['passed'] is False
        assert result['dimension'] == 'dim_assets'
        assert result['row_count'] == 0
        assert 'empty' in result['error'].lower()
    
    @patch('handler.s3_client')
    def test_duplicate_primary_keys_fails(self, mock_s3):
        """Test that duplicate primary keys fail validation."""
        # Arrange
        mock_s3.head_object.return_value = {}
        mock_parquet = create_mock_parquet_with_rows(100, 'bill_key', has_duplicates=True)
        mock_s3.get_object.return_value = {'Body': mock_parquet}
        
        dim = {
            'name': 'dim_bills',
            'path': 'gold/congress/dimensions/bills.parquet',
            'primary_key': 'bill_key'
        }
        
        # Act
        result = validate_dimension(dim)
        
        # Assert
        assert result['passed'] is False
        assert result['dimension'] == 'dim_bills'
        assert result['has_duplicates'] is True
        assert 'duplicate' in result['error'].lower()
    
    @patch('handler.s3_client')
    def test_missing_primary_key_column_fails(self, mock_s3):
        """Test that missing primary key column fails validation."""
        # Arrange
        mock_s3.head_object.return_value = {}
        mock_parquet = create_mock_parquet_with_rows(50, 'wrong_key')
        mock_s3.get_object.return_value = {'Body': mock_parquet}
        
        dim = {
            'name': 'dim_dates',
            'path': 'gold/house/financial/dimensions/dates.parquet',
            'primary_key': 'date_key'  # This column doesn't exist in the mock
        }
        
        # Act
        result = validate_dimension(dim)
        
        # Assert
        assert result['passed'] is False
        assert result['dimension'] == 'dim_dates'
        assert 'not found' in result['error'].lower()


class TestLambdaHandler:
    """Test lambda_handler function."""
    
    @patch('handler.s3_client')
    def test_all_dimensions_valid_passes(self, mock_s3):
        """Test that all dimensions passing validation returns success."""
        # Arrange
        mock_s3.head_object.return_value = {}
        
        def get_object_side_effect(Bucket, Key):
            # Determine primary key based on path
            if 'dim_members' in Key:
                pk = 'member_key'
            elif 'dim_assets' in Key:
                pk = 'asset_key'
            elif 'dim_bills' in Key:
                pk = 'bill_key'
            elif 'dim_lobbyists' in Key:
                pk = 'lobbyist_key'
            else:  # dim_dates
                pk = 'date_key'
            
            return {'Body': create_mock_parquet_with_rows(100, pk)}
        
        mock_s3.get_object.side_effect = get_object_side_effect
        
        # Act
        result = lambda_handler({}, None)
        
        # Assert
        assert result['validation_passed'] is True
        assert result['dimensions_validated'] == 5
        assert result['dimensions_passed'] == 5
        assert result['dimensions_failed'] == 0
        assert len(result['failures']) == 0
    
    @patch('handler.s3_client')
    def test_partial_failure_reports_correctly(self, mock_s3):
        """Test that partial failures are reported correctly."""
        # Arrange: 3 dimensions pass, 2 fail
        def head_object_side_effect(Bucket, Key):
            if 'dim_lobbyists' in Key or 'dim_dates' in Key:
                raise ClientError(
                    {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}},
                    'HeadObject'
                )
            return {}
        
        def get_object_side_effect(Bucket, Key):
            if 'dim_members' in Key:
                pk = 'member_key'
            elif 'dim_assets' in Key:
                pk = 'asset_key'
            else:  # dim_bills
                pk = 'bill_key'
            
            return {'Body': create_mock_parquet_with_rows(50, pk)}
        
        mock_s3.head_object.side_effect = head_object_side_effect
        mock_s3.get_object.side_effect = get_object_side_effect
        mock_s3.exceptions.NoSuchKey = ClientError
        
        # Act
        result = lambda_handler({}, None)
        
        # Assert
        assert result['validation_passed'] is False
        assert result['dimensions_validated'] == 5
        assert result['dimensions_passed'] == 3
        assert result['dimensions_failed'] == 2
        assert len(result['failures']) == 2
        assert any('dim_lobbyists' in f for f in result['failures'])
        assert any('dim_dates' in f for f in result['failures'])
    
    @patch('handler.s3_client')
    def test_all_dimensions_fail_returns_failure(self, mock_s3):
        """Test that all dimensions failing validation returns failure."""
        # Arrange - all dimensions missing
        error = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}},
            'HeadObject'
        )
        mock_s3.head_object.side_effect = error
        mock_s3.exceptions.NoSuchKey = ClientError
        
        # Act
        result = lambda_handler({}, None)
        
        # Assert
        assert result['validation_passed'] is False
        assert result['dimensions_validated'] == 5
        assert result['dimensions_passed'] == 0
        assert result['dimensions_failed'] == 5
        assert len(result['failures']) == 5


class TestRequiredDimensions:
    """Test REQUIRED_DIMENSIONS constant."""
    
    def test_required_dimensions_count(self):
        """Test that all 5 dimensions are defined."""
        assert len(REQUIRED_DIMENSIONS) == 5
    
    def test_required_dimensions_have_all_fields(self):
        """Test that all dimensions have required fields."""
        for dim in REQUIRED_DIMENSIONS:
            assert 'name' in dim
            assert 'path' in dim
            assert 'primary_key' in dim
    
    def test_required_dimension_names(self):
        """Test that all expected dimensions are present."""
        expected_names = {'dim_members', 'dim_assets', 'dim_bills', 'dim_lobbyists', 'dim_dates'}
        actual_names = {dim['name'] for dim in REQUIRED_DIMENSIONS}
        assert actual_names == expected_names
