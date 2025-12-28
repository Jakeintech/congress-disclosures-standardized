#!/usr/bin/env python3
"""Build Silver lobbying contributions table from Bronze LDA data.

Transforms LD-203 political contributions data (lobbyist → candidate donations).
"""

import argparse
import gzip
import json
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
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver")


def list_bronze_contributions(s3_client: boto3.client, year: int) -> List[str]:
    """List all contribution JSON files in Bronze for a given year."""
    prefix = f"{S3_BRONZE_PREFIX}/lobbying/contributions/year={year}/"
    logger.info(f"Listing Bronze contributions from s3://{S3_BUCKET}/{prefix}")

    contributions = []
    paginator = s3_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".json.gz"):
                contributions.append(key)

    logger.info(f"Found {len(contributions)} contribution files")
    return contributions


def parse_contribution(contribution_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse contribution JSON into Silver schema."""
    return {
        "contribution_id": contribution_data.get("id"),
        "filing_uuid": contribution_data.get("filing_uuid"),
        "filing_year": contribution_data.get("filing_year"),
        "filing_period": contribution_data.get("filing_period"),
        "lobbyist_id": contribution_data.get("lobbyist", {}).get("id"),
        "lobbyist_name": contribution_data.get("lobbyist_name"),
        "payee_name": contribution_data.get("payee_name"),
        "recipient_name": contribution_data.get("recipient_name"),  # The honoree (candidate)
        "honoree_name": contribution_data.get("honoree_name"),
        "amount": contribution_data.get("amount"),
        "contribution_type": contribution_data.get("contribution_type"),
        "contribution_type_display": contribution_data.get("contribution_type_display"),
        "date": contribution_data.get("date"),
        "dt_posted": contribution_data.get("dt_posted"),
        "dt_ingested": datetime.utcnow().isoformat(),
    }


def process_contributions(s3_client: boto3.client, year: int) -> pd.DataFrame:
    """Process all contributions for a year into a DataFrame."""
    contribution_keys = list_bronze_contributions(s3_client, year)

    if not contribution_keys:
        logger.warning(f"No contributions found for year {year}")
        return pd.DataFrame()

    contributions = []

    for idx, key in enumerate(contribution_keys, 1):
        if idx % 100 == 0:
            logger.info(f"Processing contribution {idx}/{len(contribution_keys)}")

        try:
            obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            compressed_data = obj["Body"].read()
            json_data = gzip.decompress(compressed_data)
            contribution_data = json.loads(json_data)

            parsed = parse_contribution(contribution_data)
            contributions.append(parsed)

        except Exception as e:
            logger.error(f"Error processing {key}: {e}")
            continue

    df = pd.DataFrame(contributions)
    logger.info(f"Processed {len(df)} contributions")
    return df


def write_silver_table(df: pd.DataFrame, year: int) -> None:
    """Write DataFrame to Silver Parquet table."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_SILVER_PREFIX}/lobbying/contributions/year={year}/contributions.parquet"
    logger.info(f"Writing Silver table to s3://{S3_BUCKET}/{s3_key}")

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

    logger.info(f"Wrote {len(df)} contribution records to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Build Silver lobbying contributions table")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    args = parser.parse_args()

    logger.info(f"Building Silver contributions table for year {args.year}")

    s3_client = boto3.client("s3")
    df = process_contributions(s3_client, args.year)

    if df.empty:
        logger.warning("No contributions processed")
        # Don't error - some years might have no contribution data
    else:
        write_silver_table(df, args.year)

        logger.info(f"\n{'='*60}")
        logger.info("SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total contributions: {len(df)}")
        logger.info(f"Total amount: ${df['amount'].sum():,.2f}")
        logger.info(f"Average amount: ${df['amount'].mean():,.2f}")
        logger.info(f"Unique lobbyists: {df['lobbyist_id'].nunique()}")
        logger.info(f"Unique recipients: {df['honoree_name'].nunique()}")
        logger.info(f"\nTop recipients:")
        for recipient, amount in df.groupby('honoree_name')['amount'].sum().nlargest(10).items():
            logger.info(f"  {recipient}: ${amount:,.2f}")


if __name__ == "__main__":
    main()
