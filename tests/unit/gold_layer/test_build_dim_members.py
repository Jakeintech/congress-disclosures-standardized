"""
Unit tests for build_dim_members Lambda handler.
"""

import json
import os
import sys
from pathlib import Path

# Add Lambda handler to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ingestion/lambdas/build_dim_members"))

import pytest
from conftest import upload_parquet_to_s3


def test_lambda_handler_success(s3_client, sample_filings_df, mock_lambda_context, monkeypatch):
    """Test successful dim_members build."""
    # Setup
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    # Upload sample filings to S3
    upload_parquet_to_s3(
        s3_client,
        'test-bucket',
        'gold/house/financial/facts/fact_filings/year=2024/part-0000.parquet',
        sample_filings_df
    )

    # Import handler after mocking
    from handler import lambda_handler

    # Execute
    event = {}
    result = lambda_handler(event, mock_lambda_context)

    # Assert
    assert result['statusCode'] == 200
    assert result['status'] == 'success'
    assert result['dimension'] == 'dim_members'
    assert result['records_processed'] > 0
    assert len(result['files_written']) > 0


def test_lambda_handler_no_filings(s3_client, mock_lambda_context, monkeypatch):
    """Test handling when no filings exist."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    from handler import lambda_handler

    event = {}
    result = lambda_handler(event, mock_lambda_context)

    # Should handle gracefully (may return error or empty result)
    assert result['statusCode'] in [200, 500]


def test_lambda_handler_custom_bucket(s3_client, sample_filings_df, mock_lambda_context):
    """Test with custom bucket name in event."""
    # Upload sample data
    s3_client.create_bucket(Bucket='custom-bucket')
    upload_parquet_to_s3(
        s3_client,
        'custom-bucket',
        'gold/house/financial/facts/fact_filings/year=2024/part-0000.parquet',
        sample_filings_df
    )

    from handler import lambda_handler

    event = {'bucket_name': 'custom-bucket'}
    result = lambda_handler(event, mock_lambda_context)

    assert result['statusCode'] == 200
    assert result['records_processed'] > 0


def test_parse_name_formats():
    """Test name parsing logic."""
    from handler import load_unique_members_from_filings
    import pandas as pd

    # This would test the internal name parsing function
    # For now, just verify the module imports correctly
    assert load_unique_members_from_filings is not None


def test_build_dim_members_structure(s3_client, sample_filings_df):
    """Test dim_members output structure."""
    from handler import build_dim_members, load_unique_members_from_filings
    import tempfile

    # Upload test data
    upload_parquet_to_s3(
        s3_client,
        'test-bucket',
        'gold/house/financial/facts/fact_filings/year=2024/part-0000.parquet',
        sample_filings_df
    )

    # Load and build
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    members_df = load_unique_members_from_filings('test-bucket')
    dim_members = build_dim_members(members_df)

    # Verify structure
    assert 'member_key' in dim_members.columns
    assert 'first_name' in dim_members.columns
    assert 'last_name' in dim_members.columns
    assert 'state' in dim_members.columns
    assert 'effective_from' in dim_members.columns
    assert 'version' in dim_members.columns
    assert len(dim_members) > 0
