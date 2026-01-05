"""
Shared pytest fixtures for Gold layer Lambda tests.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock

import boto3
import pandas as pd
import pytest
from moto import mock_aws


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'


@pytest.fixture
def s3_client(aws_credentials):
    """Create mock S3 client."""
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        yield s3


@pytest.fixture
def dynamodb_client(aws_credentials):
    """Create mock DynamoDB client."""
    with mock_aws():
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')
        yield dynamodb


@pytest.fixture
def sample_filings_df():
    """Sample filings dataframe."""
    return pd.DataFrame([
        {
            'doc_id': '10063228',
            'filing_date': '2024-01-15',
            'filing_type': 'P',
            'filer_name': 'Smith, John',
            'state_district': 'CA-12',
            'year': 2024
        },
        {
            'doc_id': '10078945',
            'filing_date': '2024-02-20',
            'filing_type': 'P',
            'filer_name': 'Doe, Jane',
            'state_district': 'NY-10',
            'year': 2024
        }
    ])


@pytest.fixture
def sample_transactions_df():
    """Sample transactions dataframe."""
    return pd.DataFrame([
        {
            'transaction_key': 'abc123',
            'doc_id': '10063228',
            'filing_date': '2024-01-15',
            'transaction_date': '2024-01-10',
            'transaction_type': 'Purchase',
            'asset_name': 'Apple Inc.',
            'ticker': 'AAPL',
            'amount_low': 15000,
            'amount_high': 50000
        },
        {
            'transaction_key': 'def456',
            'doc_id': '10078945',
            'filing_date': '2024-02-20',
            'transaction_date': '2024-02-15',
            'transaction_type': 'Sale',
            'asset_name': 'Tesla Inc.',
            'ticker': 'TSLA',
            'amount_low': 50000,
            'amount_high': 100000
        }
    ])


@pytest.fixture
def mock_lambda_context():
    """Mock Lambda context object."""
    context = MagicMock()
    context.get_remaining_time_in_millis.return_value = 300000  # 5 minutes
    context.function_name = 'test-function'
    context.function_version = '$LATEST'
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test'
    context.memory_limit_in_mb = 512
    context.aws_request_id = 'test-request-id'
    return context


def upload_parquet_to_s3(s3_client, bucket: str, key: str, df: pd.DataFrame):
    """Helper to upload DataFrame as Parquet to S3."""
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        df.to_parquet(tmp.name, engine='pyarrow', index=False)
        s3_client.upload_file(tmp.name, bucket, key)
        os.unlink(tmp.name)


def upload_json_to_s3(s3_client, bucket: str, key: str, data: dict):
    """Helper to upload JSON data to S3."""
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data).encode('utf-8')
    )
