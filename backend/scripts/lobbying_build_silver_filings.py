#!/usr/bin/env python3
"""Build Silver lobbying filings table from Bronze LDA data.

Transforms raw LDA filings JSON into normalized Parquet table.
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
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.lib.ingestion.s3_utils import download_s3_file, upload_parquet_to_s3

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
    """List all filing JSON files in Bronze for a given year.

    Args:
        s3_client: Boto3 S3 client
        year: Filing year

    Returns:
        List of S3 keys
    """
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


def parse_filing(filing_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse filing JSON into Silver schema.

    Args:
        filing_data: Raw filing dict from LDA API

    Returns:
        Parsed filing dict
    """
    return {
        "filing_uuid": filing_data.get("filing_uuid"),
        "filing_type": filing_data.get("filing_type"),
        "filing_year": filing_data.get("filing_year"),
        "filing_period": filing_data.get("filing_period"),
        "dt_posted": filing_data.get("dt_posted"),
        "amount_reported": filing_data.get("amount_reported"),
        "amount": filing_data.get("amount"),
        "income": filing_data.get("income"),
        "expenses": filing_data.get("expenses"),
        "registrant_id": filing_data.get("registrant", {}).get("id"),
        "registrant_name": filing_data.get("registrant", {}).get("name"),
        "client_id": filing_data.get("client", {}).get("id"),
        "client_name": filing_data.get("client", {}).get("name"),
        "client_status": filing_data.get("client", {}).get("status"),
        "client_state": filing_data.get("client", {}).get("state"),
        "client_country": filing_data.get("client", {}).get("country"),
        "lobbying_activities_count": len(filing_data.get("lobbying_activities", [])),
        "lobbyists_count": len(filing_data.get("lobbyists", [])),
        "conviction_disclosures_count": len(
            filing_data.get("conviction_disclosures", [])
        ),
        "dt_ingested": datetime.utcnow().isoformat(),
    }


def process_filings(s3_client: boto3.client, year: int) -> pd.DataFrame:
    """Process all filings for a year into a DataFrame.

    Args:
        s3_client: Boto3 S3 client
        year: Filing year

    Returns:
        DataFrame with parsed filings
    """
    filing_keys = list_bronze_filings(s3_client, year)

    if not filing_keys:
        logger.warning(f"No filings found for year {year}")
        return pd.DataFrame()

    filings = []

    for idx, key in enumerate(filing_keys, 1):
        if idx % 100 == 0:
            logger.info(f"Processing filing {idx}/{len(filing_keys)}")

        try:
            # Download and decompress
            obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            compressed_data = obj["Body"].read()
            json_data = gzip.decompress(compressed_data)
            filing_data = json.loads(json_data)

            # Parse filing
            parsed = parse_filing(filing_data)
            filings.append(parsed)

        except Exception as e:
            logger.error(f"Error processing {key}: {e}")
            continue

    df = pd.DataFrame(filings)

    logger.info(f"Processed {len(df)} filings")
    return df


def write_silver_table(df: pd.DataFrame, year: int) -> None:
    """Write DataFrame to Silver Parquet table.

    Args:
        df: DataFrame with filing data
        year: Filing year
    """
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_SILVER_PREFIX}/lobbying/filings/year={year}/filings.parquet"

    logger.info(f"Writing Silver table to s3://{S3_BUCKET}/{s3_key}")

    # Convert to Parquet and upload
    table = pa.Table.from_pandas(df)

    # Upload to S3
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

    logger.info(f"Wrote {len(df)} records to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Build Silver lobbying filings table")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    parser.add_argument(
        "--output-path",
        help="Local output path (for testing). If not set, uploads to S3",
    )

    args = parser.parse_args()

    logger.info(f"Building Silver filings table for year {args.year}")

    # Create S3 client
    s3_client = boto3.client("s3")

    # Process filings
    df = process_filings(s3_client, args.year)

    if df.empty:
        logger.error("No filings processed")
        sys.exit(1)

    # Write to Silver
    if args.output_path:
        # Write locally for testing
        df.to_parquet(args.output_path, compression="snappy", index=False)
        logger.info(f"Wrote {len(df)} records to {args.output_path}")
    else:
        # Write to S3
        write_silver_table(df, args.year)

    # Coerce numeric fields for safe aggregation
    for col in ["income", "expenses", "amount", "amount_reported"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total filings: {len(df)}")
    logger.info(f"Filing types: {df['filing_type'].value_counts().to_dict()}")
    logger.info(f"Total income: ${df['income'].sum():,.0f}")
    logger.info(f"Total expenses: ${df['expenses'].sum():,.0f}")
    logger.info(f"Unique clients: {df['client_id'].nunique()}")
    logger.info(f"Unique registrants: {df['registrant_id'].nunique()}")


if __name__ == "__main__":
    main()
