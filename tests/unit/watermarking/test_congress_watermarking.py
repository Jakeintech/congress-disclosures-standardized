"""
Unit tests for check_congress_updates watermarking (STORY-051)

Tests DynamoDB timestamp-based watermarking with Congress.gov API.
"""
import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
from datetime import datetime, timezone
import sys
import os
import importlib.util

# Import handler module with unique name to avoid caching issues
handler_path = os.path.join(
    os.path.dirname(__file__), 
    '../../../ingestion/lambdas/check_congress_updates/handler.py'
)
spec = importlib.util.spec_from_file_location("congress_handler", handler_path)
handler = importlib.util.module_from_spec(spec)
sys.modules["congress_handler"] = handler
spec.loader.exec_module(handler)


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB table resource."""
    with patch.object(handler, 'dynamodb') as mock_db:
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
    
    def test_new_data_available(self, mock_dynamodb):
        """Test handling when new data is available."""
        mock_dynamodb.get_item.return_value = {
            'Item': {'last_update_date': '2025-01-01T00:00:00Z'}
        }
        
        with patch.object(handler, 'check_congress_api', return_value={'pagination': {'count': 50}}):
            result = handler.lambda_handler({'data_type': 'bills'}, {})
        
        assert result['has_new_data'] is True
        assert result['watermark_status'] == 'incremental'
        mock_dynamodb.put_item.assert_called_once()
    
    def test_no_new_data(self, mock_dynamodb):
        """Test handling when no new data is available."""
        mock_dynamodb.get_item.return_value = {
            'Item': {'last_update_date': '2025-01-01T00:00:00Z'}
        }
        
        with patch.object(handler, 'check_congress_api', return_value={'pagination': {'count': 0}}):
            result = handler.lambda_handler({'data_type': 'bills'}, {})
        
        assert result['has_new_data'] is False
    
    def test_first_ingestion_no_watermark(self, mock_dynamodb):
        """Test first ingestion with no existing watermark."""
        mock_dynamodb.get_item.return_value = {}
        
        with patch.object(handler, 'check_congress_api', return_value={'pagination': {'count': 100}}):
            result = handler.lambda_handler({'data_type': 'bills'}, {})
        
        assert result['has_new_data'] is True
        assert result['watermark_status'] == 'new'
        assert result['is_initial_load'] is True  # STORY-004 Scenario 3
        assert result['bills_count'] == 100  # STORY-004 Scenario 2
        # Should use 5-year lookback (current year - 5)
        current_year = datetime.now(timezone.utc).year
        lookback_year = current_year - 5
        assert str(lookback_year) in result['from_date']
    
    def test_no_new_data_scenario_1(self, mock_dynamodb):
        """Test STORY-004 Scenario 1: No new data since last check."""
        # GIVEN: Last fetch timestamp = "2025-12-14T00:00:00Z"
        mock_dynamodb.get_item.return_value = {
            'Item': {'last_update_date': '2025-12-14T00:00:00Z'}
        }
        # AND: Congress.gov API has no new data since that time
        with patch.object(handler, 'check_congress_api', return_value={'pagination': {'count': 0}}):
            # WHEN: check_congress_updates executes
            result = handler.lambda_handler({'data_type': 'bills'}, {})
        
        # THEN: return {"has_new_data": false}
        assert result['has_new_data'] is False
        assert result['is_initial_load'] is False
    
    def test_members_data_type_no_bills_count(self, mock_dynamodb):
        """Test that bills_count is NOT present when data_type is 'members'."""
        mock_dynamodb.get_item.return_value = {}
        
        with patch.object(handler, 'check_congress_api', return_value={'pagination': {'count': 50}}):
            result = handler.lambda_handler({'data_type': 'members'}, {})
        
        assert result['has_new_data'] is True
        assert result['record_count'] == 50
        assert 'bills_count' not in result  # Should not have bills_count for members
    
    def test_rate_limiting_handled_gracefully(self, mock_dynamodb):
        """Test that HTTP 429 rate limiting is handled gracefully."""
        mock_dynamodb.get_item.return_value = {
            'Item': {'last_update_date': '2025-01-01T00:00:00Z'}
        }
        # Simulate rate limiting by returning empty count
        with patch.object(handler, 'check_congress_api', return_value={'pagination': {'count': 0}}):
            result = handler.lambda_handler({'data_type': 'bills'}, {})
        
        assert result['has_new_data'] is False
        # Should not fail the pipeline
        assert 'error' not in result or result.get('error') != 'rate_limited'
    
    def test_check_congress_api_handles_429(self):
        """Test that check_congress_api handles HTTP 429 gracefully."""
        # Simulate HTTP 429 error
        from urllib.error import HTTPError
        with patch.object(handler.urllib.request, 'urlopen') as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(None, 429, 'Too Many Requests', {}, None)
            
            result = handler.check_congress_api('bill', {'fromDateTime': '2025-01-01T00:00:00Z'})
        
        # Should return empty result, not raise exception
        assert result == {'pagination': {'count': 0}}
    
    def test_check_congress_api_success(self):
        """Test successful API call."""
        # Mock successful response
        with patch.object(handler.urllib.request, 'urlopen') as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b'{"pagination": {"count": 42}, "bills": []}'
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response
            
            result = handler.check_congress_api('bill', {'fromDateTime': '2025-01-01T00:00:00Z'})
        
        assert result['pagination']['count'] == 42
