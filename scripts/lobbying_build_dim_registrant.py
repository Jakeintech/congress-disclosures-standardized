#!/usr/bin/env python3
"""Build Gold dim_registrant dimension table with aggregated metrics.

Dimension for lobbying firms (registrants) with business metrics.
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
    """Read Parquet file from S3."""
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        df = pd.read_parquet(obj["Body"])
        logger.info(f"Read {len(df)} records from {key}")
        return df
    except Exception as e:
        logger.warning(f"Could not read {key}: {e}")
        return pd.DataFrame()


def build_dimension(s3_client: boto3.client, year: int) -> pd.DataFrame:
    """Build registrant dimension with aggregated metrics."""

    # Read Silver tables
    registrants_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/registrants/registrants.parquet"
    )

    filings_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/filings/year={year}/filings.parquet"
    )

    lobbyists_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/lobbyists/year={year}/lobbyists.parquet"
    )

    activities_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/activities/year={year}/activities.parquet"
    )

    if registrants_df.empty or filings_df.empty:
        logger.error("Required Silver tables not found")
        return pd.DataFrame()

    # Calculate metrics per registrant
    logger.info("Calculating registrant metrics...")

    # Total revenue and client count
    registrant_metrics = filings_df.groupby("registrant_id").agg({
        "income": "sum",
        "expenses": "sum",
        "client_id": "nunique",
        "filing_uuid": "count"
    }).reset_index()
    registrant_metrics.columns = [
        "registrant_id", "total_revenue", "total_expenses",
        "client_count", "filing_count"
    ]

    # Lobbyist count (unique lobbyists per firm)
    if not lobbyists_df.empty:
        lobbyist_count = lobbyists_df.groupby("registrant_id")["lobbyist_id"].nunique().reset_index()
        lobbyist_count.columns = ["registrant_id", "lobbyist_count"]

        # Revolving door percentage
        revolving_door = lobbyists_df.groupby("registrant_id")["has_covered_position"].mean().reset_index()
        revolving_door.columns = ["registrant_id", "revolving_door_pct"]
    else:
        lobbyist_count = pd.DataFrame(columns=["registrant_id", "lobbyist_count"])
        revolving_door = pd.DataFrame(columns=["registrant_id", "revolving_door_pct"])

    # Top issue codes (specialization)
    if not activities_df.empty:
        activity_filings = activities_df.merge(
            filings_df[["filing_uuid", "registrant_id"]],
            on="filing_uuid"
        )

        top_issues = activity_filings.groupby("registrant_id")["general_issue_code_display"].apply(
            lambda x: x.value_counts().head(5).index.tolist()
        ).reset_index()
        top_issues.columns = ["registrant_id", "specialization_issues"]
    else:
        top_issues = pd.DataFrame(columns=["registrant_id", "specialization_issues"])

    # Join all metrics
    dim_df = registrants_df.merge(registrant_metrics, on="registrant_id", how="left")

    if not lobbyist_count.empty:
        dim_df = dim_df.merge(lobbyist_count, on="registrant_id", how="left")
    else:
        dim_df["lobbyist_count"] = 0

    if not revolving_door.empty:
        dim_df = dim_df.merge(revolving_door, on="registrant_id", how="left")
    else:
        dim_df["revolving_door_pct"] = 0.0

    if not top_issues.empty:
        dim_df = dim_df.merge(top_issues, on="registrant_id", how="left")
    else:
        dim_df["specialization_issues"] = [[]]

    # Fill NaN values
    dim_df["total_revenue"] = dim_df["total_revenue"].fillna(0.0)
    dim_df["total_expenses"] = dim_df["total_expenses"].fillna(0.0)
    dim_df["client_count"] = dim_df["client_count"].fillna(0).astype(int)
    dim_df["filing_count"] = dim_df["filing_count"].fillna(0).astype(int)
    dim_df["lobbyist_count"] = dim_df["lobbyist_count"].fillna(0).astype(int)
    dim_df["revolving_door_pct"] = dim_df["revolving_door_pct"].fillna(0.0)
    dim_df["specialization_issues"] = dim_df["specialization_issues"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    # Add derived fields
    dim_df["firm_size"] = pd.cut(
        dim_df["lobbyist_count"],
        bins=[0, 5, 20, 50, 1000],
        labels=["small", "medium", "large", "enterprise"]
    ).astype(str)

    dim_df["year"] = year
    dim_df["dt_updated"] = datetime.utcnow().isoformat()

    logger.info(f"Built dimension with {len(dim_df)} registrants")
    return dim_df


def write_gold_table(df: pd.DataFrame) -> None:
    """Write DataFrame to Gold Parquet table."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_GOLD_PREFIX}/lobbying/dim_registrant/dim_registrant.parquet"
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

    logger.info(f"Wrote {len(df)} registrant records to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Build Gold dim_registrant table")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    args = parser.parse_args()

    logger.info(f"Building Gold dim_registrant for year {args.year}")

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
    logger.info(f"Total registrants: {len(df)}")
    logger.info(f"Total revenue: ${df['total_revenue'].sum():,.0f}")
    logger.info(f"Total lobbyists: {df['lobbyist_count'].sum()}")
    logger.info(f"Average revolving door rate: {df['revolving_door_pct'].mean():.1%}")
    logger.info(f"\nFirm sizes:")
    logger.info(df['firm_size'].value_counts().to_dict())
    logger.info(f"\nTop 10 firms by revenue:")
    top_firms = df.nlargest(10, "total_revenue")[["name", "total_revenue", "client_count"]]
    for _, row in top_firms.iterrows():
        logger.info(f"  {row['name']}: ${row['total_revenue']:,.0f} ({row['client_count']} clients)")


if __name__ == "__main__":
    main()
