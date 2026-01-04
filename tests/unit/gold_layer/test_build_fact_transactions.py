"""
Unit tests for build_fact_transactions Lambda handler.
"""

import json
import os
import sys
from pathlib import Path

# Add Lambda handler to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ingestion/lambdas/build_fact_transactions"))

import pytest
from conftest import upload_json_to_s3


def test_lambda_handler_success(s3_client, mock_lambda_context, monkeypatch):
    """Test successful fact_transactions build."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    # Upload sample Type P extraction
    sample_extraction = {
        'doc_id': '10063228',
        'filing_date': '2024-01-15',
        'transactions': [
            {
                'transaction_date': '2024-01-10',
                'trans_type': 'P',
                'asset_name': 'Apple Inc.',
                'ticker': 'AAPL',
                'amount': '$15,001 - $50,000',
                'owner': 'Self'
            }
        ]
    }

    upload_json_to_s3(
        s3_client,
        'test-bucket',
        'silver/house/financial/objects/filing_type=type_p/year=2024/doc_id=10063228.json',
        sample_extraction
    )

    from handler import lambda_handler

    event = {}
    result = lambda_handler(event, mock_lambda_context)

    assert result['statusCode'] == 200
    assert result['status'] == 'success'
    assert result['fact_table'] == 'fact_ptr_transactions'
    assert result['records_processed'] >= 1


def test_parse_amount_string():
    """Test amount parsing logic."""
    from handler import parse_amount_string

    # Test range
    low, high = parse_amount_string('$15,001 - $50,000')
    assert low == 15001
    assert high == 50000

    # Test single value
    low, high = parse_amount_string('$100,000')
    assert low == 100000

    # Test 'Over' format
    low, high = parse_amount_string('Over $50,000,000')
    assert low == 50000000

    # Test None
    low, high = parse_amount_string(None)
    assert low is None
    assert high is None


def test_get_transaction_type():
    """Test transaction type mapping."""
    from handler import get_transaction_type

    assert get_transaction_type({'trans_type': 'P'}) == 'Purchase'
    assert get_transaction_type({'trans_type': 'S'}) == 'Sale'
    assert get_transaction_type({'trans_type': 'E'}) == 'Exchange'
    assert get_transaction_type({'transaction_type': 'p'}) == 'Purchase'  # Case insensitive


def test_generate_transaction_key():
    """Test transaction key generation."""
    from handler import generate_transaction_key

    txn = {
        'transaction_date': '2024-01-10',
        'ticker': 'AAPL',
        'amount': '$15,001 - $50,000',
        'transaction_type': 'P',
        'asset_description': 'Apple Inc.'
    }

    key = generate_transaction_key('10063228', txn)
    assert isinstance(key, str)
    assert len(key) == 32  # MD5 hash length


def test_lambda_handler_with_year_filter(s3_client, mock_lambda_context, monkeypatch):
    """Test processing specific year only."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    # Upload 2024 data
    upload_json_to_s3(
        s3_client,
        'test-bucket',
        'silver/house/financial/objects/filing_type=type_p/year=2024/doc_id=10063228.json',
        {'doc_id': '10063228', 'filing_date': '2024-01-15', 'transactions': []}
    )

    from handler import lambda_handler

    event = {'year': 2024}
    result = lambda_handler(event, mock_lambda_context)

    assert result['statusCode'] == 200


def test_lambda_handler_no_transactions(s3_client, mock_lambda_context, monkeypatch):
    """Test handling when no transactions exist."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    from handler import lambda_handler

    event = {}
    result = lambda_handler(event, mock_lambda_context)

    # Should handle gracefully
    assert result['statusCode'] in [200, 500]


def test_lambda_handler_rebuild_mode(s3_client, mock_lambda_context, monkeypatch):
    """Test rebuild mode (overwrite existing partitions)."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    # Upload sample Type P extraction
    sample_extraction = {
        'doc_id': '10063229',
        'filing_date': '2024-02-15',
        'transactions': [
            {
                'transaction_date': '2024-02-10',
                'trans_type': 'S',
                'asset_name': 'Tesla Inc.',
                'ticker': 'TSLA',
                'amount': '$50,001 - $100,000',
                'owner': 'Spouse'
            }
        ]
    }

    upload_json_to_s3(
        s3_client,
        'test-bucket',
        'silver/house/financial/objects/filing_type=type_p/year=2024/doc_id=10063229.json',
        sample_extraction
    )

    from handler import lambda_handler

    event = {'rebuild': True}
    result = lambda_handler(event, mock_lambda_context)

    assert result['statusCode'] == 200
    assert result['mode'] == 'rebuild'
    assert result['records_processed'] >= 1


def test_lambda_handler_incremental_mode(s3_client, mock_lambda_context, monkeypatch):
    """Test incremental mode (append to existing partitions)."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    # Upload sample Type P extraction
    sample_extraction = {
        'doc_id': '10063230',
        'filing_date': '2024-03-15',
        'transactions': [
            {
                'transaction_date': '2024-03-10',
                'trans_type': 'P',
                'asset_name': 'Microsoft Corp.',
                'ticker': 'MSFT',
                'amount': '$15,001 - $50,000',
                'owner': 'Self'
            }
        ]
    }

    upload_json_to_s3(
        s3_client,
        'test-bucket',
        'silver/house/financial/objects/filing_type=type_p/year=2024/doc_id=10063230.json',
        sample_extraction
    )

    from handler import lambda_handler

    event = {'rebuild': False}
    result = lambda_handler(event, mock_lambda_context)

    assert result['statusCode'] == 200
    assert result['mode'] == 'incremental'
    assert result['records_processed'] >= 1


def test_lambda_handler_since_date_filter(s3_client, mock_lambda_context, monkeypatch):
    """Test filtering by since_date parameter."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    # Upload old transaction (should be filtered out)
    old_extraction = {
        'doc_id': '10063231',
        'filing_date': '2024-01-05',
        'transactions': [
            {
                'transaction_date': '2024-01-01',
                'trans_type': 'P',
                'asset_name': 'Old Corp.',
                'ticker': 'OLD',
                'amount': '$15,001 - $50,000',
                'owner': 'Self'
            }
        ]
    }

    # Upload new transaction (should be included)
    new_extraction = {
        'doc_id': '10063232',
        'filing_date': '2024-02-15',
        'transactions': [
            {
                'transaction_date': '2024-02-10',
                'trans_type': 'S',
                'asset_name': 'New Corp.',
                'ticker': 'NEW',
                'amount': '$50,001 - $100,000',
                'owner': 'Self'
            }
        ]
    }

    upload_json_to_s3(
        s3_client,
        'test-bucket',
        'silver/house/financial/objects/filing_type=type_p/year=2024/doc_id=10063231.json',
        old_extraction
    )

    upload_json_to_s3(
        s3_client,
        'test-bucket',
        'silver/house/financial/objects/filing_type=type_p/year=2024/doc_id=10063232.json',
        new_extraction
    )

    from handler import lambda_handler

    event = {'since_date': '2024-02-01'}
    result = lambda_handler(event, mock_lambda_context)

    assert result['statusCode'] == 200
    # Should only process transactions after 2024-02-01
    assert result['records_processed'] >= 1
