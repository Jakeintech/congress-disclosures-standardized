#!/usr/bin/env python3
"""Build Gold dim_client dimension table with aggregated metrics.

SCD Type 2 dimension for lobbying clients with historical spend tracking.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "congress-disclosures-standardized")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver")
S3_GOLD_PREFIX = os.environ.get("S3_GOLD_PREFIX", "gold")


def read_silver_parquet(s3_client: boto3.client, key: str) -> pd.DataFrame:
    """Read Parquet file from S3 into pandas via pyarrow."""
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        data = obj["Body"].read()
        table = pq.read_table(pa.BufferReader(data))
        df = table.to_pandas()
        logger.info(f"Read {len(df)} records from {key}")
        return df
    except Exception as e:
        logger.warning(f"Could not read {key}: {e}")
        return pd.DataFrame()


def build_dimension(s3_client: boto3.client, year: int) -> pd.DataFrame:
    """Build client dimension with aggregated metrics."""

    # Read Silver tables
    clients_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/clients/clients.parquet"
    )

    filings_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/filings/year={year}/filings.parquet"
    )

    activities_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/activities/year={year}/activities.parquet"
    )

    if clients_df.empty or filings_df.empty:
        logger.error("Required Silver tables not found")
        return pd.DataFrame()

    # Calculate metrics per client
    logger.info("Calculating client metrics...")

    # Total spend by client
    client_spend = filings_df.groupby("client_id").agg({
        "income": "sum",
        "expenses": "sum",
        "filing_uuid": "count"
    }).reset_index()
    client_spend.columns = ["client_id", "total_income", "total_expenses", "filing_count"]

    # Top issue codes per client
    if not activities_df.empty:
        activity_filings = activities_df.merge(
            filings_df[["filing_uuid", "client_id"]],
            on="filing_uuid"
        )

        top_issues = activity_filings.groupby("client_id")["general_issue_code_display"].apply(
            lambda x: x.value_counts().head(3).index.tolist()
        ).reset_index()
        top_issues.columns = ["client_id", "top_issue_codes"]
    else:
        top_issues = pd.DataFrame(columns=["client_id", "top_issue_codes"])

    # Join with base dimension
    dim_df = clients_df.merge(client_spend, on="client_id", how="left")

    if not top_issues.empty:
        dim_df = dim_df.merge(top_issues, on="client_id", how="left")
    else:
        dim_df["top_issue_codes"] = [[] for _ in range(len(dim_df))]

    # Fill NaN values
    dim_df["total_income"] = pd.to_numeric(dim_df["total_income"], errors="coerce").fillna(0.0)
    dim_df["total_expenses"] = pd.to_numeric(dim_df["total_expenses"], errors="coerce").fillna(0.0)
    dim_df["filing_count"] = pd.to_numeric(dim_df["filing_count"], errors="coerce").fillna(0).astype(int)
    dim_df["top_issue_codes"] = dim_df["top_issue_codes"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    # Add derived fields
    dim_df["total_spend"] = dim_df["total_income"] + dim_df["total_expenses"]
    dim_df["year"] = year

    # SCD Type 2 fields
    dim_df["effective_date"] = datetime.utcnow().date().isoformat()
    dim_df["end_date"] = None
    dim_df["is_current"] = True

    dim_df["dt_updated"] = datetime.utcnow().isoformat()

    logger.info(f"Built dimension with {len(dim_df)} clients")
    return dim_df


def write_gold_table(df: pd.DataFrame) -> None:
    """Write DataFrame to Gold Parquet table."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_GOLD_PREFIX}/lobbying/dim_client/dim_client.parquet"
    logger.info(f"Writing Gold table to s3://{S3_BUCKET}/{s3_key}")

    # Ensure numeric types for Arrow conversion
    for col in ["total_income", "total_expenses", "filing_count", "total_spend"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    table = pa.Table.from_pandas(df)

    with pa.BufferOutputStream() as out_stream:
        pq.write_table(table, out_stream, compression="snappy")
        buffer = out_stream.getvalue()

        s3_client = boto3.client("s3")
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=buffer.to_pybytes(),
            ContentType="application/x-parquet",
        )

    logger.info(f"Wrote {len(df)} client records to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Build Gold dim_client table")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    args = parser.parse_args()

    logger.info(f"Building Gold dim_client for year {args.year}")

    s3_client = boto3.client("s3")
    df = build_dimension(s3_client, args.year)

    if df.empty:
        logger.error("No dimension data generated")
        sys.exit(1)

    write_gold_table(df)

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total clients: {len(df)}")
    logger.info(f"Total spend: ${df['total_spend'].sum():,.0f}")
    logger.info(f"Average spend per client: ${df['total_spend'].mean():,.0f}")
    logger.info(f"\nTop 10 clients by spend:")
    top_clients = df.nlargest(10, "total_spend")[["name", "total_spend"]]
    for _, row in top_clients.iterrows():
        logger.info(f"  {row['name']}: ${row['total_spend']:,.0f}")


if __name__ == "__main__":
    main()
