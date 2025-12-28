"""
Unit tests for API shared libraries

Tests for query_builder, pagination, response_formatter, filter_parser, and cache.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from api.lib.query_builder import ParquetQueryBuilder
from api.lib.pagination import paginate, build_pagination_response, parse_pagination_params
from api.lib.response_formatter import success_response, error_response, add_cors_headers
from api.lib.filter_parser import (
    parse_query_params,
    parse_operator_syntax,
    convert_value,
    parse_date_range,
    parse_amount_range
)
from api.lib.cache import cache_response, get_cached, invalidate_cache, cleanup_expired
import json
import time


# ============================================================================
# Query Builder Tests
# ============================================================================

class TestParquetQueryBuilder:
    """Tests for ParquetQueryBuilder."""
    
    def test_build_where_clause_simple_equality(self):
        """Test simple equality filter."""
        builder = ParquetQueryBuilder()
        filters = {'ticker': 'AAPL'}
        where_clause = builder._build_where_clause(filters)
        assert where_clause == "ticker = 'AAPL'"
    
    def test_build_where_clause_multiple_filters(self):
        """Test multiple filters with AND."""
        builder = ParquetQueryBuilder()
        filters = {
            'ticker': 'AAPL',
            'transaction_type': 'Purchase'
        }
        where_clause = builder._build_where_clause(filters)
        assert "ticker = 'AAPL'" in where_clause
        assert "transaction_type = 'Purchase'" in where_clause
        assert " AND " in where_clause
    
    def test_build_condition_operators(self):
        """Test various operators."""
        builder = ParquetQueryBuilder()
        
        # Greater than
        assert builder._build_condition('amount', 'gt', 50000) == "amount > 50000"
        
        # Less than or equal
        assert builder._build_condition('amount', 'lte', 100000) == "amount <= 100000"
        
        # Not equal
        assert builder._build_condition('status', 'ne', 'archived') == "status != 'archived'"
        
        # IN operator
        assert builder._build_condition('ticker', 'in', ['AAPL', 'GOOGL', 'MSFT']) == \
               "ticker IN ('AAPL', 'GOOGL', 'MSFT')"
        
        # LIKE operator
        assert builder._build_condition('name', 'like', '%Smith%') == "name LIKE '%Smith%'"
    
    def test_escape_string(self):
        """Test SQL injection protection."""
        builder = ParquetQueryBuilder()
        # Test single quote escaping
        escaped = builder._escape_string("O'Reilly")
        assert escaped == "O''Reilly"
       
        # Test in WHERE clause
        condition = builder._build_condition('name', 'eq', "O'Reilly")
        assert condition == "name = 'O''Reilly'"
    
    def test_build_where_with_operator_dict(self):
        """Test filter with operator dictionary."""
        builder = ParquetQueryBuilder()
        filters = {
            'amount': {'gt': 50000, 'lte': 100000},
            'transaction_date': {'gte': '2025-01-01'}
        }
        where_clause = builder._build_where_clause(filters)
        assert "amount > 50000" in where_clause
        assert "amount <= 100000" in where_clause
        assert "transaction_date >= '2025-01-01'" in where_clause
    
    def test_null_handling(self):
        """Test NULL value handling."""
        builder = ParquetQueryBuilder()
        
        # IS NULL
        assert builder._build_condition('notes', 'eq', None) == "notes IS NULL"
        
        # IS NOT NULL
        assert builder._build_condition('notes', 'ne', None) == "notes IS NOT NULL"


# ============================================================================
# Pagination Tests
# ============================================================================

class TestPagination:
    """Tests for pagination utilities."""
    
    def test_paginate_basic(self):
        """Test basic pagination."""
        df = pd.DataFrame({'id': range(100)})
        
        # First page
        page1 = paginate(df, limit=10, offset=0)
        assert len(page1) == 10
        assert page1['id'].tolist() == list(range(10))
        
        # Second page
        page2 = paginate(df, limit=10, offset=10)
        assert len(page2) == 10
        assert page2['id'].tolist() == list(range(10, 20))
    
    def test_paginate_last_page(self):
        """Test pagination on last page with fewer items."""
        df = pd.DataFrame({'id': range(25)})
        
        last_page = paginate(df, limit=10, offset=20)
        assert len(last_page) == 5
        assert last_page['id'].tolist() == list(range(20, 25))
    
    def test_paginate_max_limit(self):
        """Test that limit is capped at 500."""
        df = pd.DataFrame({'id': range(1000)})
        
        page = paginate(df, limit=1000, offset=0)
        assert len(page) == 500  # Should be capped
    
    def test_build_pagination_response(self):
        """Test pagination response building."""
        data = [{'id': i} for i in range(50)]
        response = build_pagination_response(
            data=data,
            total_count=435,
            limit=50,
            offset=0,
            base_url='/v1/members'
        )
        
        assert response['success'] is True
        assert len(response['data']) == 50
        assert response['pagination']['total'] == 435
        assert response['pagination']['count'] == 50
        assert response['pagination']['has_next'] is True
        assert response['pagination']['has_prev'] is False
        assert '/v1/members?limit=50&offset=50' in response['pagination']['next']
        assert response['pagination']['prev'] is None
    
    def test_parse_pagination_params(self):
        """Test pagination parameter parsing."""
        # Valid params
        limit, offset = parse_pagination_params({'limit': '20', 'offset': '40'})
        assert limit == 20
        assert offset == 40
        
        # Defaults
        limit, offset = parse_pagination_params({})
        assert limit == 50
        assert offset == 0
        
        # Invalid values
        limit, offset = parse_pagination_params({'limit': 'invalid', 'offset': '-5'})
        assert limit == 50  # Default
        assert offset == 0  # Clamped to 0


# ============================================================================
# Response Formatter Tests
# ============================================================================

class TestResponseFormatter:
    """Tests for response formatting."""
    
    def test_success_response(self):
        """Test success response formatting."""
        response = success_response(
            data={'members': [{'id': 1}]},
            metadata={'total': 435}
        )
        
        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'members' in body['data']
        assert body['metadata']['total'] == 435
    
    def test_error_response(self):
        """Test error response formatting."""
        response = error_response(
            message="Member not found",
            status_code=404,
            details={'bioguide_id': 'C999999'}
        )
        
        assert response['statusCode'] == 404
        
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error']['message'] == "Member not found"
        assert body['error']['code'] == 404
        assert body['error']['details']['bioguide_id'] == 'C999999'
    
    def test_cors_headers(self):
        """Test CORS headers are added."""
        response = success_response(data={})
        
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert 'GET' in response['headers']['Access-Control-Allow-Methods']
        assert 'Content-Type' in response['headers']


# ============================================================================
# Filter Parser Tests
# ============================================================================

class TestFilterParser:
    """Tests for filter parameter parsing."""
    
    def test_parse_query_params_simple(self):
        """Test simple query parameter parsing."""
        event = {
            'queryStringParameters': {
                'ticker': 'AAPL',
                'transaction_type': 'Purchase'
            }
        }
        
        parsed = parse_query_params(event)
        assert parsed == {'ticker': 'AAPL', 'transaction_type': 'Purchase'}
    
    def test_parse_query_params_with_operators(self):
        """Test operator syntax parsing."""
        event = {
            'queryStringParameters': {
                'amount[gt]': '50000',
                'amount[lte]': '100000',
                'ticker': 'AAPL'
            }
        }
        
        parsed = parse_query_params(event)
        assert parsed['amount']['gt'] == 50000  # Converted to int
        assert parsed['amount']['lte'] == 100000
        assert parsed['ticker'] == 'AAPL'
    
    def test_parse_query_params_in_operator(self):
        """Test IN operator with comma-separated list."""
        event = {
            'queryStringParameters': {
                'transaction_type[in]': 'Purchase,Sale,Exchange'
            }
        }
        
        parsed = parse_query_params(event)
        assert parsed['transaction_type']['in'] == ['Purchase', 'Sale', 'Exchange']
    
    def test_parse_operator_syntax(self):
        """Test operator syntax extraction."""
        column, op = parse_operator_syntax('amount[gt]')
        assert column == 'amount'
        assert op == 'gt'
        
        column, op = parse_operator_syntax('invalid_syntax')
        assert column is None
        assert op is None
    
    def test_convert_value(self):
        """Test value type conversion."""
        # Integer
        assert convert_value('42', 'eq') == 42
        
        # Float
        assert convert_value('99.99', 'eq') == 99.99
        
        # List (for IN operator)
        assert convert_value('AAPL,GOOGL,MSFT', 'in') == ['AAPL', 'GOOGL', 'MSFT']
        
        # String
        assert convert_value('text', 'like') == 'text'
    
    def test_parse_date_range(self):
        """Test date range parsing."""
        params = {
            'start_date': '2025-01-01',
            'end_date': '2025-03-31'
        }
        
        filters = parse_date_range(params)
        assert filters['transaction_date']['gte'] == '2025-01-01'
        assert filters['transaction_date']['lte'] == '2025-03-31'
    
    def test_parse_amount_range(self):
        """Test amount range parsing."""
        params = {
            'min_amount': '10000',
            'max_amount': '100000'
        }
        
        filters = parse_amount_range(params)
        assert filters['amount']['gte'] == 10000.0
        assert filters['amount']['lte'] == 100000.0


# ============================================================================
# Cache Tests
# ============================================================================

class TestCache:
    """Tests for caching utilities."""
    
    def test_cache_set_and_get(self):
        """Test cache set and retrieval."""
        cache_response('test_key', {'data': 'test'}, ttl=60)
        
        cached = get_cached('test_key')
        assert cached == {'data': 'test'}
    
    def test_cache_miss(self):
        """Test cache miss."""
        result = get_cached('nonexistent_key')
        assert result is None
    
    def test_cache_ttl_expiry(self):
        """Test cache TTL expiration."""
        # Cache with 1 second TTL
        cache_response('short_ttl', 'data', ttl=1)
        
        # Should exist immediately
        assert get_cached('short_ttl') == 'data'
        
        # Wait for expiry
        time.sleep(1.1)
        
        # Should be expired
        assert get_cached('short_ttl') is None
    
    def test_invalidate_all(self):
        """Test clearing all cache."""
        cache_response('key1', 'data1')
        cache_response('key2', 'data2')
        
        count = invalidate_cache()
        assert count == 2
        
        assert get_cached('key1') is None
        assert get_cached('key2') is None
    
    def test_invalidate_pattern(self):
        """Test pattern-based cache invalidation."""
        cache_response('members_list', 'data1')
        cache_response('members_detail_1', 'data2')
        cache_response('trades_list', 'data3')
        
        # Invalidate only members-related caches
        count = invalidate_cache('members')
        assert count == 2
        
        assert get_cached('members_list') is None
        assert get_cached('members_detail_1') is None
        assert get_cached('trades_list') == 'data3'  # Still exists
