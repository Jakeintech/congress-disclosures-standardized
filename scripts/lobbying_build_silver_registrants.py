#!/usr/bin/env python3
"""Build Silver lobbying registrants (firms) dimension table from Bronze LDA data.

Transforms raw LDA registrant data into normalized dimension table.
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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Environment variables
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


def extract_registrants(s3_client: boto3.client, year: int) -> pd.DataFrame:
    """Extract unique registrants from all filings."""
    filing_keys = list_bronze_filings(s3_client, year)

    if not filing_keys:
        logger.warning(f"No filings found for year {year}")
        return pd.DataFrame()

    registrants_dict = {}

    for idx, key in enumerate(filing_keys, 1):
        if idx % 100 == 0:
            logger.info(f"Processing filing {idx}/{len(filing_keys)}")

        try:
            obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            compressed_data = obj["Body"].read()
            json_data = gzip.decompress(compressed_data)
            filing_data = json.loads(json_data)

            registrant = filing_data.get("registrant", {})
            if not registrant or not registrant.get("id"):
                continue

            registrant_id = registrant["id"]

            # Keep most recent/complete record
            if registrant_id not in registrants_dict:
                registrants_dict[registrant_id] = {
                    "registrant_id": registrant_id,
                    "name": registrant.get("name"),
                    "description": registrant.get("description"),
                    "address": registrant.get("address"),
                    "address_2": registrant.get("address_2"),
                    "city": registrant.get("city"),
                    "state": registrant.get("state"),
                    "zip": registrant.get("zip"),
                    "country": registrant.get("country"),
                    "ppb_country": registrant.get("ppb_country"),
                    "contact_name": registrant.get("contact_name"),
                    "contact_phone": registrant.get("contact_phone"),
                    "dt_updated": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error processing {key}: {e}")
            continue

    df = pd.DataFrame(list(registrants_dict.values()))
    logger.info(f"Extracted {len(df)} unique registrants")
    return df


def write_silver_table(df: pd.DataFrame) -> None:
    """Write DataFrame to Silver Parquet table."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_SILVER_PREFIX}/lobbying/registrants/registrants.parquet"
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

    logger.info(f"Wrote {len(df)} registrants to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Build Silver lobbying registrants table")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    args = parser.parse_args()

    logger.info(f"Building Silver registrants table for year {args.year}")

    s3_client = boto3.client("s3")
    df = extract_registrants(s3_client, args.year)

    if df.empty:
        logger.error("No registrants extracted")
        sys.exit(1)

    write_silver_table(df)

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total registrants: {len(df)}")
    logger.info(f"States: {df['state'].value_counts().head(10).to_dict()}")
    logger.info(f"Countries: {df['country'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
