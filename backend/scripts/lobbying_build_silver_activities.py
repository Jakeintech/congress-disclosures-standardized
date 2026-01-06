#!/usr/bin/env python3
"""Build Silver lobbying activities table from Bronze LDA data.

Extracts lobbying activity records (what was lobbied on, which issues, descriptions).
"""

import argparse
import gzip
import hashlib
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


def list_bronze_filings(s3_client: boto3.client, year: int) -> List[str]:
    """List all filing JSON files in Bronze for a given year."""
    prefix = f"{S3_BRONZE_PREFIX}/lobbying/filings/year={year}/"
    logger.info(f"Listing Bronze filings from s3://{S3_BUCKET}/{prefix}")

    filings = []
    paginator = s3_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".json.gz"):
                filings.append(key)

    logger.info(f"Found {len(filings)} filing files")
    return filings


def extract_activities(s3_client: boto3.client, year: int) -> pd.DataFrame:
    """Extract all lobbying activity records from filings."""
    filing_keys = list_bronze_filings(s3_client, year)

    if not filing_keys:
        logger.warning(f"No filings found for year {year}")
        return pd.DataFrame()

    activities = []

    for idx, key in enumerate(filing_keys, 1):
        if idx % 100 == 0:
            logger.info(f"Processing filing {idx}/{len(filing_keys)}")

        try:
            obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            compressed_data = obj["Body"].read()
            json_data = gzip.decompress(compressed_data)
            filing_data = json.loads(json_data)

            filing_uuid = filing_data.get("filing_uuid")
            filing_year = filing_data.get("filing_year")
            filing_period = filing_data.get("filing_period")

            for idx, activity in enumerate(filing_data.get("lobbying_activities", [])):
                # Activities don't have IDs in the API, so we generate one
                # using filing_uuid + index to ensure uniqueness
                activity_id = f"{filing_uuid}_{idx}"

                # Alternative: hash-based ID for deterministic regeneration
                # activity_hash = hashlib.sha256(
                #     f"{filing_uuid}_{activity.get('general_issue_code')}_{activity.get('description', '')[:100]}".encode()
                # ).hexdigest()[:16]

                activities.append({
                    "activity_id": activity_id,
                    "filing_uuid": filing_uuid,
                    "filing_year": filing_year,
                    "filing_period": filing_period,
                    "general_issue_code": activity.get("general_issue_code"),
                    "general_issue_code_display": activity.get("general_issue_code_display"),
                    "description": activity.get("description", "")[:5000],  # Truncate long descriptions
                    "foreign_entity_issues": activity.get("foreign_entity_issues"),
                    "foreign_entity_ppb_country": activity.get("foreign_entity_ppb_country"),
                    "dt_updated": datetime.utcnow().isoformat(),
                })

        except Exception as e:
            logger.error(f"Error processing {key}: {e}")
            continue

    df = pd.DataFrame(activities)
    logger.info(f"Extracted {len(df)} activity records")
    return df


def write_silver_table(df: pd.DataFrame, year: int) -> None:
    """Write DataFrame to Silver Parquet table."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_SILVER_PREFIX}/lobbying/activities/year={year}/activities.parquet"
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

    logger.info(f"Wrote {len(df)} activity records to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Build Silver lobbying activities table")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    args = parser.parse_args()

    logger.info(f"Building Silver activities table for year {args.year}")

    s3_client = boto3.client("s3")
    df = extract_activities(s3_client, args.year)

    if df.empty:
        logger.error("No activities extracted")
        sys.exit(1)

    write_silver_table(df, args.year)

    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total activities: {len(df)}")
    logger.info(f"Top issue codes:")
    for code, count in df['general_issue_code_display'].value_counts().head(10).items():
        logger.info(f"  {code}: {count}")


if __name__ == "__main__":
    main()
