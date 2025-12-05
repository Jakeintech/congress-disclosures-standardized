#!/usr/bin/env python3
"""Build Silver lobbying lobbyists dimension table from Bronze LDA data.

Extracts individual lobbyist records with covered position info (revolving door).
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


def extract_lobbyists(s3_client: boto3.client, year: int) -> pd.DataFrame:
    """Extract all lobbyist records from filings."""
    filing_keys = list_bronze_filings(s3_client, year)

    if not filing_keys:
        logger.warning(f"No filings found for year {year}")
        return pd.DataFrame()

    lobbyists = []

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
            registrant_id = filing_data.get("registrant", {}).get("id")
            client_id = filing_data.get("client", {}).get("id")

            for lobbyist in filing_data.get("lobbyists", []):
                lobbyist_id = lobbyist.get("id")
                if not lobbyist_id:
                    continue

                # Extract covered positions (revolving door)
                covered_positions = lobbyist.get("covered_positions", [])
                covered_position = None
                former_agency = None

                if covered_positions:
                    # Take most recent covered position
                    covered_positions.sort(
                        key=lambda x: x.get("dt_posted", ""), reverse=True
                    )
                    latest_position = covered_positions[0]
                    covered_position = latest_position.get("position")
                    former_agency = latest_position.get("agency")

                lobbyists.append({
                    "lobbyist_id": lobbyist_id,
                    "filing_uuid": filing_uuid,
                    "filing_year": filing_year,
                    "registrant_id": registrant_id,
                    "client_id": client_id,
                    "first_name": lobbyist.get("first_name"),
                    "last_name": lobbyist.get("last_name"),
                    "suffix": lobbyist.get("suffix"),
                    "covered_position": covered_position,
                    "former_agency": former_agency,
                    "has_covered_position": len(covered_positions) > 0,
                    "covered_positions_count": len(covered_positions),
                    "dt_updated": datetime.utcnow().isoformat(),
                })

        except Exception as e:
            logger.error(f"Error processing {key}: {e}")
            continue

    df = pd.DataFrame(lobbyists)
    logger.info(f"Extracted {len(df)} lobbyist records")
    return df


def write_silver_table(df: pd.DataFrame, year: int) -> None:
    """Write DataFrame to Silver Parquet table."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_SILVER_PREFIX}/lobbying/lobbyists/year={year}/lobbyists.parquet"
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

    logger.info(f"Wrote {len(df)} lobbyist records to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Build Silver lobbying lobbyists table")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    args = parser.parse_args()

    logger.info(f"Building Silver lobbyists table for year {args.year}")

    s3_client = boto3.client("s3")
    df = extract_lobbyists(s3_client, args.year)

    if df.empty:
        logger.error("No lobbyists extracted")
        sys.exit(1)

    write_silver_table(df, args.year)

    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total lobbyist records: {len(df)}")
    logger.info(f"Unique lobbyists: {df['lobbyist_id'].nunique()}")
    logger.info(f"With covered positions: {df['has_covered_position'].sum()}")
    logger.info(f"Revolving door rate: {df['has_covered_position'].mean():.1%}")


if __name__ == "__main__":
    main()
