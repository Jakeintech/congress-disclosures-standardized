#!/usr/bin/env python3
"""
Backfill S3 Object Tags for Bronze PDFs.

Tags applied per PDF:
- cd:doc_id
- cd:year
- cd:filing_type
- cd:member_name ("First Last" if available)
- cd:state_district

Sources:
- Reads filings from s3://{bucket}/manifest.json (website manifest built from Silver index)
- Locates Bronze PDFs using both layouts:
  * bronze/house/financial/year={YEAR}/pdfs/{YEAR}/{DOC_ID}.pdf
  * bronze/house/financial/disclosures/year={YEAR}/doc_id={DOC_ID}/{DOC_ID}.pdf

Usage:
  python3 scripts/backfill_bronze_tags.py [--limit N] [--year 2025]

Requires AWS creds and permissions: s3:GetObject, s3:PutObjectTagging, s3:HeadObject on bucket.
"""
import argparse
import json
import sys
from typing import Dict, Any, List, Optional

import boto3
from botocore.exceptions import ClientError

try:
    from lib.terraform_config import get_aws_config
except Exception:
    # Fallback if import path differs when run directly
    from scripts.lib.terraform_config import get_aws_config  # type: ignore


def load_manifest(bucket: str) -> Dict[str, Any]:
    s3 = boto3.client("s3")
    resp = s3.get_object(Bucket=bucket, Key="manifest.json")
    return json.loads(resp["Body"].read())


def head_object_exists(bucket: str, key: str) -> bool:
    s3 = boto3.client("s3")
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def put_tags(bucket: str, key: str, tagset: List[Dict[str, str]]) -> None:
    s3 = boto3.client("s3")
    s3.put_object_tagging(
        Bucket=bucket,
        Key=key,
        Tagging={"TagSet": tagset},
    )


def build_tags(rec: Dict[str, Any]) -> List[Dict[str, str]]:
    first = rec.get("first_name") or ""
    last = rec.get("last_name") or ""
    member_name = (f"{first} {last}").strip()
    tags = [
        {"Key": "cd:doc_id", "Value": str(rec.get("doc_id", "")).strip()},
        {"Key": "cd:year", "Value": str(rec.get("year", "")).strip()},
        {"Key": "cd:filing_type", "Value": str(rec.get("filing_type", "")).strip()},
    ]
    if member_name:
        tags.append({"Key": "cd:member_name", "Value": member_name})
    if rec.get("state_district"):
        tags.append({"Key": "cd:state_district", "Value": str(rec["state_district"])})
    return tags


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--year", type=int, default=None)
    args = ap.parse_args()

    cfg = get_aws_config()
    bucket = cfg.s3_bucket_id
    data = load_manifest(bucket)
    filings: List[Dict[str, Any]] = data.get("filings", [])
    if args.year:
        filings = [f for f in filings if int(f.get("year") or 0) == args.year]
    if args.limit:
        filings = filings[: args.limit]

    total = 0
    tagged = 0
    missing = 0
    for rec in filings:
        doc_id = str(rec.get("doc_id", "")).strip()
        year = rec.get("year")
        if not doc_id or not year:
            continue
        total += 1
        key_candidates = [
            f"bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf",
            f"bronze/house/financial/disclosures/year={year}/doc_id={doc_id}/{doc_id}.pdf",
        ]
        target_key: Optional[str] = None
        for k in key_candidates:
            if head_object_exists(bucket, k):
                target_key = k
                break
        if not target_key:
            missing += 1
            continue
        tags = build_tags(rec)
        put_tags(bucket, target_key, tags)
        tagged += 1

    print(f"Processed filings: {total}")
    print(f"Tagged PDFs: {tagged}")
    print(f"Missing PDFs: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

