#!/usr/bin/env python3
"""Validate that LDA samples exist in Bronze and corresponding Silver/Gold outputs exist.

Usage:
  python3 scripts/validate_lda_pipeline.py --year 2025
"""

import argparse
import os
import sys
from pathlib import Path

import boto3

S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "congress-disclosures-standardized")
BRONZE = os.environ.get("S3_BRONZE_PREFIX", "bronze")
SILVER = os.environ.get("S3_SILVER_PREFIX", "silver")
GOLD = os.environ.get("S3_GOLD_PREFIX", "gold")


def s3_has_prefix(s3, prefix: str) -> bool:
    resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix, MaxKeys=1)
    return bool(resp.get("Contents"))


def main():
    ap = argparse.ArgumentParser(description="Validate LDA Bronze/Silver/Gold presence")
    ap.add_argument("--year", type=int, required=True)
    args = ap.parse_args()

    s3 = boto3.client("s3")
    ok = True

    checks = [
        ("bronze filings", f"{BRONZE}/lobbying/filings/year={args.year}/"),
        ("bronze contributions", f"{BRONZE}/lobbying/contributions/year={args.year}/"),
        ("bronze registrants", f"{BRONZE}/lobbying/registrants/"),
        ("bronze clients", f"{BRONZE}/lobbying/clients/"),
        ("bronze lobbyists", f"{BRONZE}/lobbying/lobbyists/"),
        ("silver filings", f"{SILVER}/lobbying/filings/year={args.year}/filings.parquet"),
        ("silver registrants", f"{SILVER}/lobbying/registrants/registrants.parquet"),
        ("silver clients", f"{SILVER}/lobbying/clients/clients.parquet"),
        ("gold dim_registrant", f"{GOLD}/lobbying/dim_registrant/dim_registrant.parquet"),
        ("gold dim_client", f"{GOLD}/lobbying/dim_client/dim_client.parquet"),
    ]

    print("LDA PIPELINE VALIDATION")
    for name, prefix in checks:
        exists = s3_has_prefix(s3, prefix)
        status = "✓" if exists else "✗"
        print(f"  {status} {name}: s3://{S3_BUCKET}/{prefix}")
        ok = ok and exists

    if not ok:
        print("\nSome expected paths are missing. If this is expected (e.g., no activities/lobbyists for this year), you can ignore those.")
        sys.exit(1)
    else:
        print("\nAll required LDA paths present.")


if __name__ == "__main__":
    main()

