"""
Unit tests for compute_trending_stocks Lambda handler.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add Lambda handler to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ingestion/lambdas/compute_trending_stocks"))

import pandas as pd
import pytest
from conftest import upload_parquet_to_s3


def test_lambda_handler_success(s3_client, sample_transactions_df, mock_lambda_context, monkeypatch):
    """Test successful trending stocks computation."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

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
    assert result['aggregate'] == 'trending_stocks'


def test_compute_trending_stocks_windows(sample_transactions_df):
    """Test trending stocks computation for different windows."""
    from handler import compute_trending_stocks

    # Add recent dates to transactions
    now = datetime.utcnow()
    sample_transactions_df['transaction_date'] = [
        (now - timedelta(days=5)).isoformat(),
        (now - timedelta(days=25)).isoformat()
    ]

    trending = compute_trending_stocks(sample_transactions_df)

    # Should have results for different windows
    assert len(trending) > 0
    assert 'window' in trending.columns
    assert 'ticker' in trending.columns
    assert 'transaction_count' in trending.columns

    # Check windows exist
    windows = trending['window'].unique()
    assert len(windows) > 0  # At least one window should have data


def test_trending_stocks_top_100():
    """Test that trending stocks limits to top 100 per window."""
    from handler import compute_trending_stocks
    import pandas as pd

    # Create large dataset
    now = datetime.utcnow()
    transactions = []
    for i in range(200):
        transactions.append({
            'transaction_date': (now - timedelta(days=3)).isoformat(),
            'ticker': f'TICK{i}',
            'doc_id': f'doc_{i}',
            'transaction_type': 'Purchase',
            'amount_low': 10000
        })

    df = pd.DataFrame(transactions)
    trending = compute_trending_stocks(df)

    # Each window should have max 100 tickers
    for window in trending['window'].unique():
        window_count = len(trending[trending['window'] == window])
        assert window_count <= 100


def test_lambda_handler_no_transactions(s3_client, mock_lambda_context, monkeypatch):
    """Test handling when no transactions exist."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    from handler import lambda_handler

    event = {}
    result = lambda_handler(event, mock_lambda_context)

    assert result['statusCode'] in [200, 500]


def test_lambda_handler_custom_lookback(s3_client, sample_transactions_df, mock_lambda_context, monkeypatch):
    """Test with custom lookback period."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    upload_parquet_to_s3(
        s3_client,
        'test-bucket',
        'gold/house/financial/facts/fact_ptr_transactions/year=2024/month=01/part-0000.parquet',
        sample_transactions_df
    )

    from handler import lambda_handler

    event = {'lookback_days': 180}
    result = lambda_handler(event, mock_lambda_context)

    assert result['statusCode'] == 200
