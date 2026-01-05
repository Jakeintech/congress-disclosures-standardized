"""
Unit tests for build_fact_lobbying Lambda handler.
"""

import gzip
import json
import os
import sys
from pathlib import Path

# Add Lambda handler to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ingestion/lambdas/build_fact_lobbying"))

import pytest
from conftest import upload_json_to_s3


def test_lambda_handler_success(s3_client, mock_lambda_context, monkeypatch):
    """Test successful fact_lobbying build."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    # Upload sample lobbying disclosure to Bronze
    sample_disclosure = {
        'filing_uuid': 'test-uuid-123',
        'filing_year': 2024,
        'filing_period': 'Q1',
        'filing_date': '2024-03-31',
        'client_name': 'Tech Corp',
        'registrant_name': 'Lobbying Firm LLC',
        'lobbyist_name': 'John Lobbyist',
        'amount': '$50,000',
        'issue_code': 'TEC',
        'issue_description': 'Technology and telecommunications',
        'government_entity': 'Senate'
    }

    upload_json_to_s3(
        s3_client,
        'test-bucket',
        'bronze/lobbying/filings/2024/test-filing.json',
        sample_disclosure
    )

    from handler import lambda_handler

    event = {}
    result = lambda_handler(event, mock_lambda_context)

    assert result['statusCode'] == 200
    assert result['status'] == 'success'
    assert result['fact_table'] == 'fact_lobbying'
    assert result['records_processed'] >= 1


def test_lambda_handler_with_gzipped_data(s3_client, mock_lambda_context, monkeypatch):
    """Test handling of gzipped JSON files."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    sample_disclosure = {
        'filing_uuid': 'test-uuid-456',
        'filing_year': 2025,
        'filing_period': 'Q2',
        'filing_date': '2025-06-30',
        'client_name': 'Finance Inc',
        'registrant_name': 'Policy Advisors',
        'amount': '$100,000',
        'issue_code': 'FIN',
        'issue_description': 'Financial services'
    }

    # Upload gzipped JSON
    json_bytes = json.dumps(sample_disclosure).encode('utf-8')
    gzipped = gzip.compress(json_bytes)
    
    s3_client.put_object(
        Bucket='test-bucket',
        Key='bronze/lobbying/filings/2025/test-filing.json.gz',
        Body=gzipped
    )

    from handler import lambda_handler

    event = {}
    result = lambda_handler(event, mock_lambda_context)

    assert result['statusCode'] == 200
    assert result['records_processed'] >= 1


def test_lambda_handler_with_bucket_override(s3_client, mock_lambda_context, monkeypatch):
    """Test bucket name override via event."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'default-bucket')

    # Create the test bucket
    s3_client.create_bucket(Bucket='custom-bucket')

    sample_disclosure = {
        'filing_uuid': 'test-uuid-789',
        'filing_year': 2024,
        'filing_period': 'Q3',
        'amount': '$25,000'
    }

    upload_json_to_s3(
        s3_client,
        'custom-bucket',
        'bronze/lobbying/filings/2024/test.json',
        sample_disclosure
    )

    from handler import lambda_handler

    event = {'bucket_name': 'custom-bucket'}
    result = lambda_handler(event, mock_lambda_context)

    assert result['statusCode'] == 200


def test_lambda_handler_no_data(s3_client, mock_lambda_context, monkeypatch):
    """Test handling when no lobbying data exists."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    from handler import lambda_handler

    event = {}
    result = lambda_handler(event, mock_lambda_context)

    # Should handle gracefully
    assert result['statusCode'] == 200
    assert result['records_processed'] == 0


def test_load_lobbying_from_bronze(s3_client, monkeypatch):
    """Test loading lobbying data from Bronze layer."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    # Upload multiple filings
    for i in range(3):
        disclosure = {
            'filing_uuid': f'uuid-{i}',
            'filing_year': 2024,
            'filing_period': 'Q1',
            'client_name': f'Client {i}',
            'amount': f'${(i+1)*10000}'
        }
        upload_json_to_s3(
            s3_client,
            'test-bucket',
            f'bronze/lobbying/filings/2024/filing-{i}.json',
            disclosure
        )

    from handler import load_lobbying_from_bronze

    df = load_lobbying_from_bronze('test-bucket')

    assert len(df) == 3
    assert 'filing_uuid' in df.columns
    assert 'amount' in df.columns


def test_build_fact_lobbying(monkeypatch):
    """Test fact table building logic."""
    import pandas as pd
    from handler import build_fact_lobbying

    lobbying_data = {
        'filing_uuid': ['uuid-1', 'uuid-2'],
        'filing_year': [2024, 2024],
        'filing_period': ['Q1', 'Q2'],
        'client_name': ['Client A', 'Client B'],
        'amount': ['$50,000', '$100,000']
    }
    
    df = pd.DataFrame(lobbying_data)
    result = build_fact_lobbying(df)

    assert len(result) == 2
    assert 'load_timestamp' in result.columns
    assert 'amount_numeric' in result.columns
    assert result['amount_numeric'].iloc[0] == 50000.0
    assert result['amount_numeric'].iloc[1] == 100000.0


def test_parse_amounts():
    """Test amount parsing logic."""
    from handler import build_fact_lobbying
    import pandas as pd

    test_cases = {
        'filing_uuid': ['a', 'b', 'c', 'd', 'e'],
        'amount': ['$50,000', '$1,000,000', '100000', None, '']
    }
    
    df = pd.DataFrame(test_cases)
    result = build_fact_lobbying(df)

    assert result['amount_numeric'].iloc[0] == 50000.0
    assert result['amount_numeric'].iloc[1] == 1000000.0
    assert result['amount_numeric'].iloc[2] == 100000.0
    assert pd.isna(result['amount_numeric'].iloc[3])
    assert pd.isna(result['amount_numeric'].iloc[4])


def test_write_to_gold_partitioned_by_year(s3_client, monkeypatch):
    """Test writing fact table partitioned by year."""
    import pandas as pd
    from handler import write_to_gold

    data = {
        'filing_uuid': ['a', 'b', 'c'],
        'filing_year': [2023, 2024, 2024],
        'client_name': ['Client 1', 'Client 2', 'Client 3']
    }
    
    df = pd.DataFrame(data)
    result = write_to_gold(df, 'test-bucket')

    assert result['total_records'] == 3
    assert len(result['files_written']) == 2  # 2 years
    assert 2023 in result['years']
    assert 2024 in result['years']

    # Check S3 objects were created
    objects = s3_client.list_objects_v2(Bucket='test-bucket', Prefix='gold/lobbying/facts/fact_lobbying/')
    assert 'Contents' in objects
    assert len(objects['Contents']) == 2  # One file per year


def test_lambda_handler_error_handling(s3_client, mock_lambda_context, monkeypatch):
    """Test error handling in Lambda handler."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'non-existent-bucket')

    from handler import lambda_handler

    # Use a bucket that doesn't exist to trigger an error during processing
    event = {'bucket_name': 'non-existent-bucket'}
    result = lambda_handler(event, mock_lambda_context)
    
    # Should handle error gracefully
    assert result['statusCode'] in [200, 500]  # May succeed with 0 records or fail
    if result['statusCode'] == 500:
        assert result['status'] == 'error'
        assert 'error' in result


def test_skip_non_filing_files(s3_client, monkeypatch):
    """Test that non-filing files are skipped."""
    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')

    # Upload constant file (should be skipped)
    upload_json_to_s3(
        s3_client,
        'test-bucket',
        'bronze/lobbying/constants/issue_codes.json',
        {'TEC': 'Technology'}
    )

    # Upload valid filing
    upload_json_to_s3(
        s3_client,
        'test-bucket',
        'bronze/lobbying/filings/2024/valid.json',
        {'filing_uuid': 'valid-123', 'filing_year': 2024}
    )

    from handler import load_lobbying_from_bronze

    df = load_lobbying_from_bronze('test-bucket')

    # Should only have 1 record (constants file skipped)
    assert len(df) == 1
    assert df['filing_uuid'].iloc[0] == 'valid-123'


def test_empty_dataframe_handling():
    """Test handling of empty dataframes."""
    import pandas as pd
    from handler import build_fact_lobbying, write_to_gold

    empty_df = pd.DataFrame()
    
    # build_fact_lobbying should handle empty input
    result = build_fact_lobbying(empty_df)
    assert result.empty

    # write_to_gold should handle empty input
    write_result = write_to_gold(empty_df, 'test-bucket')
    assert write_result['total_records'] == 0
    assert write_result['files_written'] == []
