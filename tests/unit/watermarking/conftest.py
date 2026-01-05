"""Shared test fixtures for watermarking tests."""
import pytest
import os
from unittest.mock import Mock

# Set AWS region to avoid NoRegionError during imports
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def sample_watermark_item():
    """Sample DynamoDB watermark item."""
    return {
        'table_name': 'house_fd',
        'watermark_type': '2025',
        'sha256': 'abc123def456',
        'last_modified': '2025-01-01T00:00:00Z',
        'content_length': 1000000,
        'updated_at': '2025-01-01T10:00:00Z'
    }


@pytest.fixture
def sample_http_headers():
    """Sample HTTP response headers."""
    return {
        'Last-Modified': 'Mon, 01 Jan 2025 00:00:00 GMT',
        'Content-Length': '1000000',
        'Content-Type': 'application/zip'
    }


@pytest.fixture
def mock_lambda_context():
    """Mock Lambda context object."""
    context = Mock()
    context.function_name = 'test-function'
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test'
    context.aws_request_id = 'test-request-id'
    return context
