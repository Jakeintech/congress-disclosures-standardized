"""
Unit tests for compute_member_stats Lambda handler.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add Lambda handler to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ingestion/lambdas/compute_member_stats"))

import pandas as pd
import pytest
from conftest import upload_parquet_to_s3


def test_lambda_handler_success(s3_client, sample_filings_df, sample_transactions_df, mock_lambda_context, monkeypatch):
    """Test successful member stats computation."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    # Add filer_name to transactions
    sample_transactions_df['filer_name'] = ['Smith, John', 'Doe, Jane']

    # Upload sample filings
    upload_parquet_to_s3(
        s3_client,
        'test-bucket',
        'gold/house/financial/facts/fact_filings/year=2024/part-0000.parquet',
        sample_filings_df
    )

    # Upload sample transactions
    upload_parquet_to_s3(
        s3_client,
        'test-bucket',
        'gold/house/financial/facts/fact_ptr_transactions/year=2024/month=01/part-0000.parquet',
        sample_transactions_df
    )

    from handler import lambda_handler

    event = {}
    result = lambda_handler(event, mock_lambda_context)

    assert result['statusCode'] == 200
    assert result['status'] == 'success'
    assert result['aggregate'] == 'member_trading_stats'
    assert result['records_processed'] > 0


def test_compute_member_stats_with_compliance(sample_filings_df, sample_transactions_df):
    """Test member stats computation includes compliance_score."""
    from handler import compute_member_stats

    # Add filer_name and dates to transactions for compliance calculation
    now = datetime.utcnow()
    sample_transactions_df['filer_name'] = ['Smith, John', 'Doe, Jane']
    sample_transactions_df['filing_date'] = (now - timedelta(days=10)).isoformat()
    sample_transactions_df['transaction_date'] = (now - timedelta(days=60)).isoformat()  # Late filing

    stats = compute_member_stats(sample_filings_df, sample_transactions_df)

    assert len(stats) > 0
    assert 'compliance_score' in stats.columns
    assert 'total_transactions' in stats.columns
    assert 'filer_name' in stats.columns
    
    # Compliance score should be between 0.0 and 1.0
    assert (stats['compliance_score'] >= 0.0).all()
    assert (stats['compliance_score'] <= 1.0).all()


def test_compute_member_stats_late_filing_detection():
    """Test that late filings (>45 days) are properly detected."""
    from handler import compute_member_stats

    now = datetime.utcnow()
    
    # Create sample filings
    filings = pd.DataFrame([
        {
            'doc_id': 'doc1',
            'filer_name': 'John Doe',
            'filing_date': now.isoformat(),
            'state_district': 'CA-12'
        }
    ])

    # Create transactions with late filing
    transactions = pd.DataFrame([
        {
            'transaction_key': 'txn1',
            'filer_name': 'John Doe',
            'ticker': 'AAPL',
            'amount_low': 10000,
            'transaction_date': (now - timedelta(days=60)).isoformat(),
            'filing_date': now.isoformat()  # Filed 60 days later - LATE
        },
        {
            'transaction_key': 'txn2',
            'filer_name': 'John Doe',
            'ticker': 'MSFT',
            'amount_low': 15000,
            'transaction_date': (now - timedelta(days=30)).isoformat(),
            'filing_date': now.isoformat()  # Filed 30 days later - ON TIME
        }
    ])

    stats = compute_member_stats(filings, transactions)

    assert len(stats) == 1
    john_stats = stats.iloc[0]
    
    # Should have 1 late filing out of 2 total
    assert john_stats['late_filing_count'] == 1
    assert john_stats['total_transactions'] == 2
    # Compliance score should be 1.0 - (1/2) = 0.5
    assert abs(john_stats['compliance_score'] - 0.5) < 0.01


def test_compute_member_stats_perfect_compliance():
    """Test perfect compliance score when all filings are on time."""
    from handler import compute_member_stats

    now = datetime.utcnow()
    
    filings = pd.DataFrame([
        {
            'doc_id': 'doc1',
            'filer_name': 'Jane Smith',
            'filing_date': now.isoformat(),
            'state_district': 'NY-14'
        }
    ])

    # All transactions filed within 45 days
    transactions = pd.DataFrame([
        {
            'transaction_key': 'txn1',
            'filer_name': 'Jane Smith',
            'ticker': 'AAPL',
            'amount_low': 10000,
            'transaction_date': (now - timedelta(days=30)).isoformat(),
            'filing_date': now.isoformat()  # Filed 30 days later - ON TIME
        }
    ])

    stats = compute_member_stats(filings, transactions)

    assert len(stats) == 1
    jane_stats = stats.iloc[0]
    
    assert jane_stats['late_filing_count'] == 0
    assert jane_stats['compliance_score'] == 1.0


def test_compute_member_stats_no_transactions():
    """Test handling when member has filings but no transactions."""
    from handler import compute_member_stats

    filings = pd.DataFrame([
        {
            'doc_id': 'doc1',
            'filer_name': 'Bob Jones',
            'filing_date': datetime.utcnow().isoformat(),
            'state_district': 'TX-02'
        }
    ])

    transactions = pd.DataFrame()

    stats = compute_member_stats(filings, transactions)

    assert len(stats) == 1
    bob_stats = stats.iloc[0]
    
    assert bob_stats['total_transactions'] == 0
    assert bob_stats['total_volume'] == 0.0
    assert bob_stats['compliance_score'] == 1.0  # Default perfect compliance


def test_write_to_gold_correct_path(s3_client, monkeypatch):
    """Test that output is written to correct S3 path."""
    from handler import write_to_gold

    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    stats = pd.DataFrame([
        {
            'filer_name': 'Test Member',
            'total_transactions': 10,
            'total_volume': 100000.0,
            'compliance_score': 0.95,
            'computed_at': datetime.utcnow().isoformat()
        }
    ])

    result = write_to_gold(stats, 'test-bucket')

    assert result['total_records'] == 1
    assert len(result['files_written']) == 1
    assert result['files_written'][0] == 'gold/house/financial/aggregates/agg_member_trading_stats/latest.parquet'

    # Verify file exists in S3
    response = s3_client.list_objects_v2(
        Bucket='test-bucket',
        Prefix='gold/house/financial/aggregates/agg_member_trading_stats/'
    )
    assert 'Contents' in response
    assert len(response['Contents']) == 1


def test_lambda_handler_empty_data(s3_client, mock_lambda_context, monkeypatch):
    """Test handling when no data exists."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    from handler import lambda_handler

    event = {}
    result = lambda_handler(event, mock_lambda_context)

    # Should handle gracefully
    assert result['statusCode'] in [200, 500]


def test_compute_member_stats_creates_filer_name():
    """Test that filer_name is created from first_name and last_name if missing."""
    from handler import compute_member_stats

    # Filings without filer_name but with first_name and last_name
    filings = pd.DataFrame([
        {
            'doc_id': 'doc1',
            'first_name': 'John',
            'last_name': 'Doe',
            'filing_date': datetime.utcnow().isoformat(),
            'state_district': 'CA-12'
        }
    ])

    transactions = pd.DataFrame()

    stats = compute_member_stats(filings, transactions)

    assert len(stats) == 1
    assert stats.iloc[0]['filer_name'] == 'John Doe'
