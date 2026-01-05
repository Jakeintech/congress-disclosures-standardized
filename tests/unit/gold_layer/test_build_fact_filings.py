"""
Unit tests for build_fact_filings Lambda handler.
"""

import sys
from pathlib import Path

# Add Lambda handler to path
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent.parent
        / "ingestion/lambdas/build_fact_filings"
    ),
)

from conftest import upload_parquet_to_s3  # noqa: E402


def test_lambda_handler_success(
    s3_client, mock_lambda_context, sample_filings_df, monkeypatch
):
    """Test successful fact_filings build."""
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")

    # Upload sample filings to Silver layer
    upload_parquet_to_s3(
        s3_client,
        "test-bucket",
        "silver/house/financial/filings/year=2024/part-0000.parquet",
        sample_filings_df,
    )

    from handler import lambda_handler

    event = {}
    result = lambda_handler(event, mock_lambda_context)

    assert result["statusCode"] == 200
    assert result["status"] == "success"
    assert result["fact_table"] == "fact_filings"
    assert result["records_processed"] >= 1


def test_lambda_handler_with_bucket_override(
    s3_client, mock_lambda_context, sample_filings_df, monkeypatch
):
    """Test Lambda with bucket name in event."""
    monkeypatch.setenv("S3_BUCKET_NAME", "default-bucket")

    # Upload to test-bucket
    upload_parquet_to_s3(
        s3_client,
        "test-bucket",
        "silver/house/financial/filings/year=2024/part-0000.parquet",
        sample_filings_df,
    )

    from handler import lambda_handler

    event = {"bucket_name": "test-bucket"}
    result = lambda_handler(event, mock_lambda_context)

    assert result["statusCode"] == 200
    assert result["status"] == "success"


def test_load_filings_from_silver(s3_client, sample_filings_df, monkeypatch):
    """Test loading filings from Silver layer."""
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")

    # Upload sample data
    upload_parquet_to_s3(
        s3_client,
        "test-bucket",
        "silver/house/financial/filings/year=2024/part-0000.parquet",
        sample_filings_df,
    )

    from handler import load_filings_from_silver

    df = load_filings_from_silver("test-bucket")

    assert not df.empty
    assert len(df) == len(sample_filings_df)
    assert "doc_id" in df.columns
    assert "filing_date" in df.columns


def test_load_filings_from_silver_no_data(s3_client, monkeypatch):
    """Test loading when no filings exist."""
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")

    from handler import load_filings_from_silver

    df = load_filings_from_silver("test-bucket")

    assert df.empty


def test_build_fact_filings(sample_filings_df):
    """Test building fact table from filings."""
    from handler import build_fact_filings

    result = build_fact_filings(sample_filings_df)

    assert not result.empty
    assert len(result) == len(sample_filings_df)
    assert "doc_id" in result.columns
    assert "filing_date" in result.columns
    assert "filing_type" in result.columns
    assert "load_timestamp" in result.columns
    assert "state" in result.columns  # Derived field


def test_build_fact_filings_creates_filer_name(sample_filings_df):
    """Test filer_name creation from first_name + last_name."""
    from handler import build_fact_filings

    # Add first_name and last_name, remove filer_name
    df = sample_filings_df.copy()
    df["first_name"] = ["John", "Jane"]
    df["last_name"] = ["Smith", "Doe"]
    df = df.drop(columns=["filer_name"])

    result = build_fact_filings(df)

    assert "filer_name" in result.columns
    assert result.iloc[0]["filer_name"] == "John Smith"
    assert result.iloc[1]["filer_name"] == "Jane Doe"


def test_build_fact_filings_empty():
    """Test building fact table with empty input."""
    from handler import build_fact_filings
    import pandas as pd

    result = build_fact_filings(pd.DataFrame())

    assert result.empty


def test_write_to_gold(s3_client, sample_filings_df, monkeypatch):
    """Test writing fact table to Gold layer."""
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")

    from handler import write_to_gold

    result = write_to_gold(sample_filings_df, "test-bucket")

    assert result["total_records"] == len(sample_filings_df)
    assert len(result["files_written"]) > 0
    assert len(result["years"]) > 0
    assert 2024 in result["years"]

    # Verify file exists in S3
    response = s3_client.list_objects_v2(
        Bucket="test-bucket", Prefix="gold/house/financial/facts/fact_filings/"
    )
    assert "Contents" in response
    assert any("year=2024" in obj["Key"] for obj in response["Contents"])


def test_write_to_gold_empty():
    """Test writing empty dataframe."""
    from handler import write_to_gold
    import pandas as pd

    result = write_to_gold(pd.DataFrame(), "test-bucket")

    assert result["total_records"] == 0
    assert len(result["files_written"]) == 0
    assert len(result["years"]) == 0


def test_lambda_handler_error(s3_client, mock_lambda_context, monkeypatch):
    """Test Lambda handler error handling."""
    monkeypatch.setenv("S3_BUCKET_NAME", "nonexistent-bucket")

    from handler import lambda_handler

    event = {}
    result = lambda_handler(event, mock_lambda_context)

    assert result["statusCode"] == 500
    assert result["status"] == "error"
    assert "error" in result
    assert "error_type" in result


def test_state_district_parsing(sample_filings_df):
    """Test state and district parsing from state_district."""
    from handler import build_fact_filings

    result = build_fact_filings(sample_filings_df)

    assert "state" in result.columns
    assert "district" in result.columns
    assert result.iloc[0]["state"] == "CA"
    assert result.iloc[1]["state"] == "NY"
