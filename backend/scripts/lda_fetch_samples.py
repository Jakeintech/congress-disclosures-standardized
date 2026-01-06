#!/usr/bin/env python3
"""Fetch and store sample LDA API payloads to S3 Bronze and local samples.

Usage:
  python3 scripts/lda_fetch_samples.py --year 2025 --limit 5 --upload-s3

Stores to:
  - Local: analysis/samples/lda/{endpoint}/...
  - S3 Bronze (if --upload-s3):
      filings:      bronze/lobbying/filings/year=YYYY/filing_uuid={uuid}.json.gz
      contributions: bronze/lobbying/contributions/year=YYYY/contribution_id={id}.json.gz
      registrants:  bronze/lobbying/registrants/registrant_id={id}.json.gz
      clients:      bronze/lobbying/clients/client_id={id}.json.gz
      lobbyists:    bronze/lobbying/lobbyists/lobbyist_id={id}.json.gz
      constants:    bronze/lobbying/constants/{name}/snapshot_date=YYYY-MM-DD/snapshot.json.gz
"""

import argparse
import gzip
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import boto3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Make ingestion lib importable
sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion"))
from lib.s3_utils import upload_bytes_to_s3  # type: ignore

S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "congress-disclosures-standardized")
BRONZE = os.environ.get("S3_BRONZE_PREFIX", "bronze")

BASE_URL = os.environ.get("LDA_API_BASE_URL", "https://lda.senate.gov/api/v1")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, */*;q=0.8",
}


def session_with_retries() -> requests.Session:
    s = requests.Session()
    retries = Retry(total=6, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update(HEADERS)
    return s


def write_local(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2))


def upload_json_gz(obj: Any, key: str) -> None:
    data = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    buf = gzip.compress(data)
    upload_bytes_to_s3(
        data=buf,
        bucket=S3_BUCKET,
        s3_key=key,
        metadata={
            "source_system": "lda.senate.gov",
            "snapshot_ts": datetime.now(timezone.utc).isoformat(),
        },
        content_type="application/gzip",
    )


def fetch_list(sess: requests.Session, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    r = sess.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser(description="Fetch sample LDA payloads and store to Bronze")
    ap.add_argument("--year", type=int, required=True, help="Filing year for filings/contributions")
    ap.add_argument("--limit", type=int, default=5, help="Max items per collection to store")
    ap.add_argument("--upload-s3", action="store_true", help="Upload samples to S3 Bronze as well")
    args = ap.parse_args()

    sess = session_with_retries()

    # Output dir
    root = Path("analysis/samples/lda")

    # Collections: filings, contributions (year-bound)
    print("Fetching filings...")
    filings = fetch_list(sess, f"{BASE_URL}/filings/", {"filing_year": args.year, "page_size": args.limit})
    for item in filings.get("results", [])[: args.limit]:
        fid = item.get("filing_uuid")
        if not fid:
            continue
        write_local(item, root / "filings" / f"{fid}.json")
        if args.upload_s3:
            key = f"{BRONZE}/lobbying/filings/year={args.year}/filing_uuid={fid}.json.gz"
            upload_json_gz(item, key)

    print("Fetching contributions...")
    contribs = fetch_list(sess, f"{BASE_URL}/contributions/", {"filing_year": args.year, "page_size": args.limit})
    for item in contribs.get("results", [])[: args.limit]:
        cid = item.get("id")
        if cid is None:
            continue
        write_local(item, root / "contributions" / f"{cid}.json")
        if args.upload_s3:
            key = f"{BRONZE}/lobbying/contributions/year={args.year}/contribution_id={cid}.json.gz"
            upload_json_gz(item, key)

    # Directories: registrants, clients, lobbyists (first page)
    print("Fetching registrants...")
    regs = fetch_list(sess, f"{BASE_URL}/registrants/", {"page_size": args.limit})
    for item in regs.get("results", [])[: args.limit]:
        rid = item.get("id")
        if rid is None:
            continue
        write_local(item, root / "registrants" / f"{rid}.json")
        if args.upload_s3:
            key = f"{BRONZE}/lobbying/registrants/registrant_id={rid}.json.gz"
            upload_json_gz(item, key)

    print("Fetching clients...")
    clis = fetch_list(sess, f"{BASE_URL}/clients/", {"page_size": args.limit})
    for item in clis.get("results", [])[: args.limit]:
        cid = item.get("id")
        if cid is None:
            continue
        write_local(item, root / "clients" / f"{cid}.json")
        if args.upload_s3:
            key = f"{BRONZE}/lobbying/clients/client_id={cid}.json.gz"
            upload_json_gz(item, key)

    print("Fetching lobbyists...")
    lobs = fetch_list(sess, f"{BASE_URL}/lobbyists/", {"page_size": args.limit})
    for item in lobs.get("results", [])[: args.limit]:
        lid = item.get("id")
        if lid is None:
            continue
        write_local(item, root / "lobbyists" / f"{lid}.json")
        if args.upload_s3:
            key = f"{BRONZE}/lobbying/lobbyists/lobbyist_id={lid}.json.gz"
            upload_json_gz(item, key)

    # Constants (full snapshot into a single file per resource)
    snapshot = datetime.now(timezone.utc).date().isoformat()
    constants = {
        "filingtypes": f"{BASE_URL}/constants/filing/filingtypes/",
        "lobbyingactivityissues": f"{BASE_URL}/constants/filing/lobbyingactivityissues/",
        "governmententities": f"{BASE_URL}/constants/filing/governmententities/",
        "countries": f"{BASE_URL}/constants/general/countries/",
        "states": f"{BASE_URL}/constants/general/states/",
        "prefixes": f"{BASE_URL}/constants/lobbyist/prefixes/",
        "suffixes": f"{BASE_URL}/constants/lobbyist/suffixes/",
    }
    for name, url in constants.items():
        print(f"Fetching constants: {name}...")
        obj = fetch_list(sess, url, {})
        write_local(obj, root / "constants" / f"{name}.json")
        if args.upload_s3:
            key = f"{BRONZE}/lobbying/constants/{name}/snapshot_date={snapshot}/snapshot.json.gz"
            upload_json_gz(obj, key)

    print("Done. Samples written locally and to S3 Bronze (if enabled).")


if __name__ == "__main__":
    main()

