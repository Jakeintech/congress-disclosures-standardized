#!/usr/bin/env python3
"""Build Gold fact_lobbying_activity table from Silver lobbying data.

Joins Silver tables to create comprehensive fact table for analytics.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

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
    """Read Parquet file from S3."""
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        df = pd.read_parquet(obj["Body"])
        logger.info(f"Read {len(df)} records from {key}")
        return df
    except Exception as e:
        logger.warning(f"Could not read {key}: {e}")
        return pd.DataFrame()


def build_fact_table(s3_client: boto3.client, year: int) -> pd.DataFrame:
    """Build fact table by joining Silver tables."""

    # Read Silver tables
    logger.info("Reading Silver tables...")

    filings_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/filings/year={year}/filings.parquet"
    )

    activities_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/activities/year={year}/activities.parquet"
    )

    govt_entities_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/government_entities/year={year}/government_entities.parquet"
    )

    activity_bills_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/activity_bills/year={year}/activity_bills.parquet"
    )

    lobbyists_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/lobbyists/year={year}/lobbyists.parquet"
    )

    if activities_df.empty:
        logger.error("No activities data found")
        return pd.DataFrame()

    # Aggregate government entities per activity
    logger.info("Aggregating government entities...")
    if not govt_entities_df.empty:
        govt_agg = govt_entities_df.groupby("activity_id")["entity_name"].apply(list).reset_index()
        govt_agg.columns = ["activity_id", "government_entities_contacted"]
    else:
        govt_agg = pd.DataFrame(columns=["activity_id", "government_entities_contacted"])

    # Aggregate bills per activity
    logger.info("Aggregating bill references...")
    if not activity_bills_df.empty:
        bills_agg = activity_bills_df.groupby("activity_id").agg({
            "bill_id": list,
            "confidence": "mean"
        }).reset_index()
        bills_agg.columns = ["activity_id", "bills_referenced", "bill_confidence_avg"]
    else:
        bills_agg = pd.DataFrame(columns=["activity_id", "bills_referenced", "bill_confidence_avg"])

    # Count lobbyists per filing
    logger.info("Counting lobbyists...")
    if not lobbyists_df.empty:
        lobbyist_counts = lobbyists_df.groupby("filing_uuid").size().reset_index()
        lobbyist_counts.columns = ["filing_uuid", "lobbyist_count"]
    else:
        lobbyist_counts = pd.DataFrame(columns=["filing_uuid", "lobbyist_count"])

    # Join activities with filings
    logger.info("Joining tables...")
    fact_df = activities_df.merge(
        filings_df[["filing_uuid", "registrant_id", "registrant_name", "client_id",
                    "client_name", "income", "expenses", "dt_posted"]],
        on="filing_uuid",
        how="left"
    )

    # Add government entities
    fact_df = fact_df.merge(govt_agg, on="activity_id", how="left")

    # Add bill references
    fact_df = fact_df.merge(bills_agg, on="activity_id", how="left")

    # Add lobbyist counts
    fact_df = fact_df.merge(lobbyist_counts, on="filing_uuid", how="left")

    # Fill NaN values
    fact_df["government_entities_contacted"] = fact_df["government_entities_contacted"].apply(
        lambda x: x if isinstance(x, list) else []
    )
    fact_df["bills_referenced"] = fact_df["bills_referenced"].apply(
        lambda x: x if isinstance(x, list) else []
    )
    fact_df["lobbyist_count"] = fact_df["lobbyist_count"].fillna(0).astype(int)
    fact_df["bill_confidence_avg"] = fact_df["bill_confidence_avg"].fillna(0.0)
    fact_df["income"] = fact_df["income"].fillna(0.0)
    fact_df["expenses"] = fact_df["expenses"].fillna(0.0)

    # Calculate derived fields
    fact_df["has_bill_references"] = fact_df["bills_referenced"].apply(len) > 0
    fact_df["bill_reference_count"] = fact_df["bills_referenced"].apply(len)
    fact_df["government_entity_count"] = fact_df["government_entities_contacted"].apply(len)

    # Add quarter for partitioning
    period_to_quarter = {"Q1": "Q1", "Q2": "Q2", "Q3": "Q3", "Q4": "Q4",
                         "MID-YEAR": "Q2", "YEAR-END": "Q4"}
    fact_df["quarter"] = fact_df["filing_period"].map(period_to_quarter).fillna("Q4")

    # Add timestamp
    fact_df["dt_transformed"] = datetime.utcnow().isoformat()

    # Select final columns
    fact_df = fact_df[[
        "activity_id",
        "filing_uuid",
        "filing_year",
        "filing_period",
        "quarter",
        "registrant_id",
        "registrant_name",
        "client_id",
        "client_name",
        "general_issue_code",
        "general_issue_code_display",
        "description",
        "income",
        "expenses",
        "lobbyist_count",
        "government_entities_contacted",
        "government_entity_count",
        "bills_referenced",
        "bill_reference_count",
        "bill_confidence_avg",
        "has_bill_references",
        "dt_posted",
        "dt_transformed"
    ]]

    logger.info(f"Built fact table with {len(fact_df)} records")
    return fact_df


def write_gold_table(df: pd.DataFrame, year: int) -> None:
    """Write DataFrame to Gold Parquet table with partitioning."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_client = boto3.client("s3")

    # Write partitioned by year and quarter
    for quarter in df["quarter"].unique():
        quarter_df = df[df["quarter"] == quarter].copy()

        # Drop partition columns before writing
        quarter_df = quarter_df.drop(columns=["quarter"])

        s3_key = f"{S3_GOLD_PREFIX}/lobbying/fact_lobbying_activity/year={year}/quarter={quarter}/data.parquet"
        logger.info(f"Writing {len(quarter_df)} records to {s3_key}")

        table = pa.Table.from_pandas(quarter_df)

        with pa.BufferOutputStream() as out_stream:
            pq.write_table(table, out_stream, compression="snappy")
            buffer = out_stream.getvalue()

            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=buffer.to_pybytes(),
                ContentType="application/x-parquet",
            )

    logger.info(f"Wrote fact table for year {year}")


def main():
    parser = argparse.ArgumentParser(description="Build Gold fact_lobbying_activity table")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    args = parser.parse_args()

    logger.info(f"Building Gold fact_lobbying_activity for year {args.year}")

    s3_client = boto3.client("s3")
    df = build_fact_table(s3_client, args.year)

    if df.empty:
        logger.error("No fact data generated")
        sys.exit(1)

    write_gold_table(df, args.year)

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total activities: {len(df)}")
    logger.info(f"With bill references: {df['has_bill_references'].sum()} ({df['has_bill_references'].mean():.1%})")
    logger.info(f"Total bills referenced: {df['bill_reference_count'].sum()}")
    logger.info(f"Total lobbying income: ${df['income'].sum():,.0f}")
    logger.info(f"Unique clients: {df['client_id'].nunique()}")
    logger.info(f"Unique registrants: {df['registrant_id'].nunique()}")
    logger.info(f"\nTop issue codes:")
    for code, count in df['general_issue_code_display'].value_counts().head(10).items():
        logger.info(f"  {code}: {count}")


if __name__ == "__main__":
    main()
