"""
Unit tests for check_congress_updates watermarking (STORY-051)

Tests DynamoDB timestamp-based watermarking with Congress.gov API.
"""
import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
from datetime import datetime
import sys
import os

# Add ingestion path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../ingestion/lambdas/check_congress_updates'))

import handler


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB table resource."""
    with patch('handler.dynamodb') as mock_db:
        mock_table = Mock()
        mock_db.Table.return_value = mock_table
        yield mock_table


class TestCongressWatermarking:
    """Test Congress.gov watermarking functions."""
    
    def test_get_watermark_exists(self, mock_dynamodb):
        """Test retrieving existing watermark."""
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'table_name': 'congress_gov',
                'watermark_type': 'bills',
                'last_update_date': '2025-01-01T00:00:00Z',
                'record_count': Decimal('150')
            }
        }
        
        result = handler.get_watermark('bills')
        
        assert result['last_update_date'] == '2025-01-01T00:00:00Z'
        assert result['record_count'] == Decimal('150')
    
    def test_update_watermark_success(self, mock_dynamodb):
        """Test successful watermark update."""
        handler.update_watermark('bills', '2025-01-15T10:00:00Z', 50)
        
        mock_dynamodb.put_item.assert_called_once()
        call_args = mock_dynamodb.put_item.call_args[1]
        item = call_args['Item']
        
        assert item['table_name'] == 'congress_gov'
        assert item['watermark_type'] == 'bills'
        assert item['last_update_date'] == '2025-01-15T10:00:00Z'
    
    @patch('handler.check_congress_api')
    @patch('handler.get_watermark')
    @patch('handler.update_watermark')
    def test_new_data_available(self, mock_update, mock_get, mock_api):
        """Test handling when new data is available."""
        mock_get.return_value = {'last_update_date': '2025-01-01T00:00:00Z'}
        mock_api.return_value = {'pagination': {'count': 50}}
        
        result = handler.lambda_handler({'data_type': 'bills'}, {})
        
        assert result['has_new_data'] is True
        assert result['watermark_status'] == 'incremental'
        mock_update.assert_called_once()
    
    @patch('handler.check_congress_api')
    @patch('handler.get_watermark')
    def test_no_new_data(self, mock_get, mock_api):
        """Test handling when no new data is available."""
        mock_get.return_value = {'last_update_date': '2025-01-01T00:00:00Z'}
        mock_api.return_value = {'pagination': {'count': 0}}
        
        result = handler.lambda_handler({'data_type': 'bills'}, {})
        
        assert result['has_new_data'] is False
    
    @patch('handler.check_congress_api')
    @patch('handler.get_watermark')
    @patch('handler.update_watermark')
    def test_first_ingestion_no_watermark(self, mock_update, mock_get, mock_api):
        """Test first ingestion with no existing watermark."""
        mock_get.return_value = {}
        mock_api.return_value = {'pagination': {'count': 100}}
        
        result = handler.lambda_handler({'data_type': 'bills'}, {})
        
        assert result['has_new_data'] is True
        assert result['watermark_status'] == 'new'
        assert result['is_initial_load'] is True  # STORY-004 Scenario 3
        assert result['bills_count'] == 100  # STORY-004 Scenario 2
        # Should use 5-year lookback (current year - 5)
        from datetime import timezone
        current_year = datetime.now(timezone.utc).year
        lookback_year = current_year - 5
        assert str(lookback_year) in result['from_date']
    
    @patch('handler.check_congress_api')
    @patch('handler.get_watermark')
    def test_no_new_data_scenario_1(self, mock_get, mock_api):
        """Test STORY-004 Scenario 1: No new data since last check."""
        # GIVEN: Last fetch timestamp = "2025-12-14T00:00:00Z"
        mock_get.return_value = {'last_update_date': '2025-12-14T00:00:00Z'}
        # AND: Congress.gov API has no new data since that time
        mock_api.return_value = {'pagination': {'count': 0}}
        
        # WHEN: check_congress_updates executes
        result = handler.lambda_handler({'data_type': 'bills'}, {})
        
        # THEN: return {"has_new_data": false}
        assert result['has_new_data'] is False
        assert result['is_initial_load'] is False
    
    @patch('handler.check_congress_api')
    @patch('handler.get_watermark')
    @patch('handler.update_watermark')
    def test_members_data_type_no_bills_count(self, mock_update, mock_get, mock_api):
        """Test that bills_count is NOT present when data_type is 'members'."""
        mock_get.return_value = {}
        mock_api.return_value = {'pagination': {'count': 50}}
        
        result = handler.lambda_handler({'data_type': 'members'}, {})
        
        assert result['has_new_data'] is True
        assert result['record_count'] == 50
        assert 'bills_count' not in result  # Should not have bills_count for members
    
    @patch('handler.check_congress_api')
    @patch('handler.get_watermark')
    def test_rate_limiting_handled_gracefully(self, mock_get, mock_api):
        """Test that HTTP 429 rate limiting is handled gracefully."""
        mock_get.return_value = {'last_update_date': '2025-01-01T00:00:00Z'}
        # Simulate rate limiting by returning empty count
        mock_api.return_value = {'pagination': {'count': 0}}
        
        result = handler.lambda_handler({'data_type': 'bills'}, {})
        
        assert result['has_new_data'] is False
        # Should not fail the pipeline
        assert 'error' not in result or result.get('error') != 'rate_limited'
    
    @patch('handler.urllib.request.urlopen')
    def test_check_congress_api_handles_429(self, mock_urlopen):
        """Test that check_congress_api handles HTTP 429 gracefully."""
        # Simulate HTTP 429 error
        from urllib.error import HTTPError
        mock_response = Mock()
        mock_response.code = 429
        mock_urlopen.side_effect = HTTPError(None, 429, 'Too Many Requests', {}, None)
        
        result = handler.check_congress_api('bill', {'fromDateTime': '2025-01-01T00:00:00Z'})
        
        # Should return empty result, not raise exception
        assert result == {'pagination': {'count': 0}}
    
    @patch('handler.urllib.request.urlopen')
    def test_check_congress_api_success(self, mock_urlopen):
        """Test successful API call."""
        # Mock successful response
        mock_response = Mock()
        mock_response.read.return_value = b'{"pagination": {"count": 42}, "bills": []}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        result = handler.check_congress_api('bill', {'fromDateTime': '2025-01-01T00:00:00Z'})
        
        assert result['pagination']['count'] == 42
