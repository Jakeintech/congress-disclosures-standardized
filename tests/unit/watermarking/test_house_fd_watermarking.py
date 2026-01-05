"""
Unit tests for check_house_fd_updates watermarking (STORY-051)

Tests SHA256-based watermarking with DynamoDB storage.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime
import sys
import os
import importlib.util

# Import handler module with unique name to avoid caching issues
handler_path = os.path.join(
    os.path.dirname(__file__), 
    '../../../ingestion/lambdas/check_house_fd_updates/handler.py'
)
spec = importlib.util.spec_from_file_location("house_fd_handler", handler_path)
handler = importlib.util.module_from_spec(spec)
sys.modules["house_fd_handler"] = handler
spec.loader.exec_module(handler)


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB table resource."""
    with patch.object(handler, 'dynamodb') as mock_db:
        mock_table = Mock()
        mock_db.Table.return_value = mock_table
        yield mock_table


@pytest.fixture
def mock_urllib():
    """Mock urllib for HTTP requests."""
    with patch.object(handler.urllib.request, 'urlopen') as mock_urlopen:
        yield mock_urlopen


class TestGetWatermark:
    """Test get_watermark function."""
    
    def test_get_watermark_exists(self, mock_dynamodb):
        """Test retrieving existing watermark."""
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'table_name': 'house_fd',
                'watermark_type': '2025',
                'sha256': 'abc123',
                'last_modified': '2025-01-01T00:00:00Z',
                'content_length': Decimal('1000000')
            }
        }
        
        result = handler.get_watermark(2025)
        
        assert result['sha256'] == 'abc123'
        assert result['content_length'] == Decimal('1000000')
        mock_dynamodb.get_item.assert_called_once()
    
    def test_get_watermark_not_exists(self, mock_dynamodb):
        """Test retrieving non-existent watermark."""
        mock_dynamodb.get_item.return_value = {}
        
        result = handler.get_watermark(2025)
        
        assert result == {}
    
    def test_get_watermark_error(self, mock_dynamodb):
        """Test error handling in get_watermark."""
        mock_dynamodb.get_item.side_effect = Exception("DynamoDB error")
        
        result = handler.get_watermark(2025)
        
        assert result == {}


class TestUpdateWatermark:
    """Test update_watermark function."""
    
    def test_update_watermark_success(self, mock_dynamodb):
        """Test successful watermark update."""
        handler.update_watermark(2025, 'abc123', '2025-01-01T00:00:00Z', 1000000)
        
        mock_dynamodb.put_item.assert_called_once()
        call_args = mock_dynamodb.put_item.call_args[1]
        item = call_args['Item']
        
        assert item['table_name'] == 'house_fd'
        assert item['watermark_type'] == 'year_2025'
        assert item['sha256'] == 'abc123'
        assert item['content_length'] == Decimal('1000000')
    
    def test_update_watermark_error(self, mock_dynamodb):
        """Test error handling in update_watermark."""
        mock_dynamodb.put_item.side_effect = Exception("DynamoDB error")
        
        with pytest.raises(Exception):
            handler.update_watermark(2025, 'abc123', '2025-01-01T00:00:00Z', 1000000)


class TestComputeSHA256:
    """Test compute_sha256_from_url function."""
    
    def test_compute_sha256_success(self, mock_urllib):
        """Test successful SHA256 computation."""
        mock_response = Mock()
        mock_response.read.side_effect = [b'test data chunk 1', b'test data chunk 2', b'']
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urllib.return_value = mock_response
        
        result = handler.compute_sha256_from_url('https://example.com/file.zip')
        
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex digest length
    
    def test_compute_sha256_http_error(self, mock_urllib):
        """Test HTTP error handling."""
        from urllib.error import HTTPError
        mock_urllib.side_effect = HTTPError(None, 404, 'Not Found', {}, None)
        
        with pytest.raises(HTTPError):
            handler.compute_sha256_from_url('https://example.com/file.zip')


class TestLambdaHandler:
    """Test lambda_handler function."""
    
    def test_new_filing_no_watermark(self):
        """Test handling of new filing (no existing watermark)."""
        with patch.object(handler, 'get_watermark', return_value={}), \
             patch.object(handler, 'update_watermark') as mock_update, \
             patch.object(handler.urllib.request, 'urlopen') as mock_urlopen:
            
            # Mock HTTP HEAD request
            mock_head_response = Mock()
            mock_head_response.headers = {
                'Last-Modified': 'Mon, 01 Jan 2025 00:00:00 GMT',
                'Content-Length': '1000000'
            }
            mock_head_response.__enter__ = Mock(return_value=mock_head_response)
            mock_head_response.__exit__ = Mock(return_value=False)
            
            # Mock SHA256 computation
            mock_sha_response = Mock()
            mock_sha_response.read.side_effect = [b'test data', b'']
            mock_sha_response.__enter__ = Mock(return_value=mock_sha_response)
            mock_sha_response.__exit__ = Mock(return_value=False)
            
            mock_urlopen.side_effect = [mock_head_response, mock_sha_response]
            
            result = handler.lambda_handler({'year': 2025}, {})
            
            assert result['has_new_filings'] is True
            assert result['watermark_status'] == 'new'
            mock_update.assert_called_once()
    
    def test_unchanged_filing_same_sha256(self):
        """Test handling of unchanged filing (same SHA256)."""
        with patch.object(handler, 'get_watermark', return_value={
            'sha256': 'abc123',
            'content_length': Decimal('1000000')
        }), \
             patch.object(handler, 'update_watermark') as mock_update, \
             patch.object(handler, 'compute_sha256_from_url', return_value='abc123'), \
             patch.object(handler.urllib.request, 'urlopen') as mock_urlopen:
            
            # Mock HTTP HEAD request
            mock_head_response = Mock()
            mock_head_response.headers = {
                'Last-Modified': 'Mon, 01 Jan 2025 00:00:00 GMT',
                'Content-Length': '1000000'
            }
            mock_head_response.__enter__ = Mock(return_value=mock_head_response)
            mock_head_response.__exit__ = Mock(return_value=False)
            
            mock_urlopen.return_value = mock_head_response
            
            result = handler.lambda_handler({'year': 2025}, {})
        
            assert result['has_new_filings'] is False
            assert result['watermark_status'] == 'unchanged'
            mock_update.assert_not_called()
    
    def test_updated_filing_different_sha256(self):
        """Test handling of updated filing (different SHA256)."""
        with patch.object(handler, 'get_watermark', return_value={
            'sha256': 'old_hash',
            'content_length': Decimal('1000000')
        }), \
             patch.object(handler, 'update_watermark') as mock_update, \
             patch.object(handler, 'compute_sha256_from_url', return_value='new_hash'), \
             patch.object(handler.urllib.request, 'urlopen') as mock_urlopen:
            
            # Mock HTTP HEAD request
            mock_head_response = Mock()
            mock_head_response.headers = {
                'Last-Modified': 'Mon, 01 Jan 2025 00:00:00 GMT',
                'Content-Length': '1000000'
            }
            mock_head_response.__enter__ = Mock(return_value=mock_head_response)
            mock_head_response.__exit__ = Mock(return_value=False)
            
            mock_urlopen.return_value = mock_head_response
            
            result = handler.lambda_handler({'year': 2025}, {})
        
            assert result['has_new_filings'] is True
            assert result['watermark_status'] == 'updated'
            mock_update.assert_called_once()
    
    def test_file_not_found_404(self):
        """Test handling of 404 error (file not found)."""
        from urllib.error import HTTPError
        with patch.object(handler.urllib.request, 'urlopen') as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(None, 404, 'Not Found', {}, None)
            
            result = handler.lambda_handler({'year': 2025}, {})
            
            assert result['has_new_filings'] is False
            assert 'error' in result
    
    def test_year_outside_lookback_window(self):
        """Test validation of year outside lookback window."""
        current_year = datetime.now().year
        old_year = current_year - 10  # Outside 5-year window
        
        result = handler.lambda_handler({'year': old_year}, {})
        
        assert result['has_new_filings'] is False
        assert 'error' in result
        assert 'lookback window' in result['error']
