#!/usr/bin/env python3
"""Build Gold dim_lobbyist dimension table with aggregated metrics.

Dimension for individual lobbyists with revolving door tracking.
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
    """Build lobbyist dimension with aggregated metrics."""

    # Read Silver tables
    lobbyists_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/lobbyists/year={year}/lobbyists.parquet"
    )

    contributions_df = read_silver_parquet(
        s3_client, f"{S3_SILVER_PREFIX}/lobbying/contributions/year={year}/contributions.parquet"
    )

    if lobbyists_df.empty:
        logger.error("Lobbyists Silver table not found")
        return pd.DataFrame()

    # Get most recent record for each lobbyist (with most complete info)
    logger.info("Deduplicating lobbyist records...")
    lobbyist_base = lobbyists_df.sort_values("dt_updated", ascending=False).groupby("lobbyist_id").first().reset_index()

    # Count filings per lobbyist
    filing_counts = lobbyists_df.groupby("lobbyist_id").agg({
        "filing_uuid": "nunique",
        "client_id": "nunique",
        "registrant_id": "nunique"
    }).reset_index()
    filing_counts.columns = ["lobbyist_id", "filing_count", "client_count", "registrant_count"]

    # Calculate contribution totals
    if not contributions_df.empty:
        contribution_totals = contributions_df.groupby("lobbyist_id")["amount"].sum().reset_index()
        contribution_totals.columns = ["lobbyist_id", "contribution_total"]

        contribution_counts = contributions_df.groupby("lobbyist_id").size().reset_index()
        contribution_counts.columns = ["lobbyist_id", "contribution_count"]
    else:
        contribution_totals = pd.DataFrame(columns=["lobbyist_id", "contribution_total"])
        contribution_counts = pd.DataFrame(columns=["lobbyist_id", "contribution_count"])

    # Determine active years
    active_years = lobbyists_df.groupby("lobbyist_id")["filing_year"].apply(
        lambda x: sorted(x.unique())
    ).reset_index()
    active_years.columns = ["lobbyist_id", "active_years"]

    # Join all metrics
    dim_df = lobbyist_base.merge(filing_counts, on="lobbyist_id", how="left")

    if not contribution_totals.empty:
        dim_df = dim_df.merge(contribution_totals, on="lobbyist_id", how="left")
    else:
        dim_df["contribution_total"] = 0.0

    if not contribution_counts.empty:
        dim_df = dim_df.merge(contribution_counts, on="lobbyist_id", how="left")
    else:
        dim_df["contribution_count"] = 0

    dim_df = dim_df.merge(active_years, on="lobbyist_id", how="left")

    # Fill NaN values
    dim_df["filing_count"] = dim_df["filing_count"].fillna(0).astype(int)
    dim_df["client_count"] = dim_df["client_count"].fillna(0).astype(int)
    dim_df["registrant_count"] = dim_df["registrant_count"].fillna(0).astype(int)
    dim_df["contribution_total"] = dim_df["contribution_total"].fillna(0.0)
    dim_df["contribution_count"] = dim_df["contribution_count"].fillna(0).astype(int)
    dim_df["active_years"] = dim_df["active_years"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    # Add derived fields
    dim_df["full_name"] = (
        dim_df["first_name"].fillna("") + " " +
        dim_df["last_name"].fillna("") + " " +
        dim_df["suffix"].fillna("")
    ).str.strip()

    dim_df["years_active"] = dim_df["active_years"].apply(len)
    dim_df["is_revolving_door"] = dim_df["has_covered_position"].fillna(False)

    dim_df["year"] = year
    dim_df["dt_updated"] = datetime.utcnow().isoformat()

    # Select final columns
    dim_df = dim_df[[
        "lobbyist_id",
        "full_name",
        "first_name",
        "last_name",
        "suffix",
        "covered_position",
        "former_agency",
        "is_revolving_door",
        "filing_count",
        "client_count",
        "registrant_count",
        "contribution_total",
        "contribution_count",
        "active_years",
        "years_active",
        "year",
        "dt_updated"
    ]]

    logger.info(f"Built dimension with {len(dim_df)} lobbyists")
    return dim_df


def write_gold_table(df: pd.DataFrame) -> None:
    """Write DataFrame to Gold Parquet table."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_GOLD_PREFIX}/lobbying/dim_lobbyist/dim_lobbyist.parquet"
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

    logger.info(f"Wrote {len(df)} lobbyist records to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Build Gold dim_lobbyist table")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    args = parser.parse_args()

    logger.info(f"Building Gold dim_lobbyist for year {args.year}")

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
    logger.info(f"Total lobbyists: {len(df)}")
    logger.info(f"With revolving door: {df['is_revolving_door'].sum()} ({df['is_revolving_door'].mean():.1%})")
    logger.info(f"Total contributions: ${df['contribution_total'].sum():,.2f}")
    logger.info(f"Average contributions per lobbyist: ${df['contribution_total'].mean():,.2f}")
    logger.info(f"\nTop former agencies (revolving door):")
    top_agencies = df[df['is_revolving_door']]['former_agency'].value_counts().head(10)
    for agency, count in top_agencies.items():
        if agency:
            logger.info(f"  {agency}: {count}")


if __name__ == "__main__":
    main()
