"""
Unit tests for check_lobbying_updates watermarking (STORY-051)

Tests S3 existence-based watermarking for lobbying data.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import sys
import os

# Add ingestion path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../ingestion/lambdas/check_lobbying_updates'))

import handler


@pytest.fixture
def mock_s3():
    """Mock S3 client."""
    with patch('handler.s3') as mock_s3_client:
        yield mock_s3_client


class TestLobbyingWatermarking:
    """Test lobbying watermarking functions."""
    
    def test_check_bronze_exists_true(self, mock_s3):
        """Test Bronze data exists."""
        mock_s3.list_objects_v2.return_value = {'KeyCount': 5}
        
        result = handler.check_bronze_exists(2025, 'Q1')
        
        assert result is True
        mock_s3.list_objects_v2.assert_called_once()
    
    def test_check_bronze_exists_false(self, mock_s3):
        """Test Bronze data does not exist."""
        mock_s3.list_objects_v2.return_value = {'KeyCount': 0}
        
        result = handler.check_bronze_exists(2025, 'Q1')
        
        assert result is False
    
    @patch('handler.check_bronze_exists')
    def test_all_quarters_exist(self, mock_check):
        """Test when all quarters already exist."""
        mock_check.return_value = True
        
        result = handler.lambda_handler({'year': 2025, 'quarter': 'all'}, {})
        
        assert result['has_new_filings'] is False
        assert len(result['quarters_to_process']) == 0
    
    @patch('handler.check_bronze_exists')
    def test_some_quarters_missing(self, mock_check):
        """Test when some quarters are missing."""
        # Q1 and Q3 exist, Q2 and Q4 missing
        mock_check.side_effect = [True, False, True, False]
        
        result = handler.lambda_handler({'year': 2025, 'quarter': 'all'}, {})
        
        assert result['has_new_filings'] is True
        assert len(result['quarters_to_process']) == 2
        assert 'Q2' in result['quarters_to_process']
        assert 'Q4' in result['quarters_to_process']
    
    def test_year_outside_lookback_window(self):
        """Test year validation outside lookback window."""
        current_year = datetime.now().year
        old_year = current_year - 10
        
        result = handler.lambda_handler({'year': old_year, 'quarter': 'Q1'}, {})
        
        assert result['has_new_filings'] is False
        assert 'error' in result
    
    def test_invalid_quarter(self):
        """Test invalid quarter validation."""
        result = handler.lambda_handler({'year': 2025, 'quarter': 'Q5'}, {})
        
        assert result['has_new_filings'] is False
        assert 'error' in result
