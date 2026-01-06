#!/usr/bin/env python3
"""Compute bill-lobbying correlation aggregate.

For each bill, aggregate all lobbying activity and spending.
Shows which bills have the most lobbying pressure.
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


def read_parquet_from_s3(s3_client: boto3.client, key: str) -> pd.DataFrame:
    """Read Parquet file from S3."""
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        df = pd.read_parquet(obj["Body"])
        logger.info(f"Read {len(df)} records from {key}")
        return df
    except Exception as e:
        logger.warning(f"Could not read {key}: {e}")
        return pd.DataFrame()


def compute_correlation(s3_client: boto3.client, year: int) -> pd.DataFrame:
    """Compute bill-lobbying correlations."""

    # Read Silver activity_bills (bill references)
    activity_bills_df = read_parquet_from_s3(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/activity_bills/year={year}/activity_bills.parquet"
    )

    if activity_bills_df.empty:
        logger.warning("No bill references found")
        return pd.DataFrame()

    # Read fact_lobbying_activity from Gold
    fact_df = pd.DataFrame()
    for quarter in ["Q1", "Q2", "Q3", "Q4"]:
        quarter_df = read_parquet_from_s3(
            s3_client,
            f"{S3_GOLD_PREFIX}/lobbying/fact_lobbying_activity/year={year}/quarter={quarter}/data.parquet"
        )
        if not quarter_df.empty:
            fact_df = pd.concat([fact_df, quarter_df], ignore_index=True)

    if fact_df.empty:
        logger.error("No fact_lobbying_activity data found. Run lobbying_build_fact_activity.py first.")
        return pd.DataFrame()

    # Join bill references with fact table
    logger.info("Joining bill references with fact table...")
    bill_activity_df = activity_bills_df.merge(
        fact_df[[
            "activity_id", "filing_uuid", "filing_year", "filing_period",
            "registrant_id", "registrant_name", "client_id", "client_name",
            "general_issue_code", "general_issue_code_display",
            "income", "lobbyist_count", "dt_posted"
        ]],
        on="activity_id",
        how="inner"
    )

    logger.info(f"Matched {len(bill_activity_df)} bill-activity pairs")

    # Aggregate by bill
    logger.info("Aggregating by bill...")
    agg_df = bill_activity_df.groupby("bill_id").agg({
        "client_name": lambda x: list(x.unique()),
        "client_id": "nunique",
        "registrant_name": lambda x: list(x.unique()),
        "registrant_id": "nunique",
        "income": "sum",
        "activity_id": "count",
        "general_issue_code_display": lambda x: list(x.value_counts().head(5).index),
        "filing_period": lambda x: list(sorted(x.unique())),
        "dt_posted": ["min", "max"],
        "lobbyist_count": "sum",
        "confidence": "mean"
    }).reset_index()

    # Flatten column names
    agg_df.columns = [
        "bill_id",
        "client_names",
        "client_count",
        "registrant_names",
        "registrant_count",
        "total_lobbying_spend",
        "activity_count",
        "top_issue_codes",
        "filing_quarters",
        "first_lobbying_date",
        "last_lobbying_date",
        "total_lobbyists",
        "avg_confidence"
    ]

    # Add derived fields
    agg_df["lobbying_intensity_score"] = (
        agg_df["total_lobbying_spend"] / 100000 +  # Spend component
        agg_df["activity_count"] * 5 +              # Activity component
        agg_df["client_count"] * 10                  # Client diversity component
    ).round(2)

    # Parse Congress number from bill_id
    agg_df["congress"] = agg_df["bill_id"].str.extract(r"(\d+)-")[0].astype(int)

    agg_df["year"] = year
    agg_df["dt_computed"] = datetime.utcnow().isoformat()

    # Sort by lobbying spend
    agg_df = agg_df.sort_values("total_lobbying_spend", ascending=False)

    logger.info(f"Computed correlations for {len(agg_df)} bills")
    return agg_df


def write_gold_table(df: pd.DataFrame, year: int) -> None:
    """Write DataFrame to Gold Parquet table."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_GOLD_PREFIX}/lobbying/agg_bill_lobbying_activity/year={year}/agg_bill_lobbying_activity.parquet"
    logger.info(f"Writing Gold table to s3://{S3_BUCKET}/{s3_key}")

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

    logger.info(f"Wrote {len(df)} bill-lobbying correlations to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Compute bill-lobbying correlation aggregate")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    args = parser.parse_args()

    logger.info(f"Computing bill-lobbying correlations for year {args.year}")

    s3_client = boto3.client("s3")
    df = compute_correlation(s3_client, args.year)

    if df.empty:
        logger.warning("No correlations computed")
        sys.exit(0)  # Don't error - might be legitimate

    write_gold_table(df, args.year)

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Bills with lobbying activity: {len(df)}")
    logger.info(f"Total lobbying spend: ${df['total_lobbying_spend'].sum():,.0f}")
    logger.info(f"Unique clients: {df['client_count'].sum()}")
    logger.info(f"Unique registrants: {df['registrant_count'].sum()}")
    logger.info(f"\nTop 10 most lobbied bills:")
    top_bills = df.head(10)[["bill_id", "total_lobbying_spend", "client_count", "activity_count"]]
    for _, row in top_bills.iterrows():
        logger.info(
            f"  {row['bill_id']}: ${row['total_lobbying_spend']:,.0f} "
            f"({row['client_count']} clients, {row['activity_count']} activities)"
        )


if __name__ == "__main__":
    main()
