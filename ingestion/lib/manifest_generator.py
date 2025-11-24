"""Generate manifest.json for the public website.

This module creates a lightweight manifest file that the static website
can fetch to display filing data without direct S3 queries.
"""

import json
import gzip
from datetime import datetime
from typing import List, Dict, Any
from io import BytesIO

import boto3


def generate_manifest(
    filings: List[Dict[str, Any]],
    s3_bucket: str,
    s3_key: str = "manifest.json",
) -> Dict[str, Any]:
    """Generate and upload manifest.json to S3.

    Args:
        filings: List of filing records from silver layer
        s3_bucket: S3 bucket name
        s3_key: S3 key for manifest (default: manifest.json in root)

    Returns:
        dict: Manifest metadata

    Example:
        >>> filings = [
        ...     {"doc_id": "123", "year": 2025, "first_name": "John", ...},
        ...     ...
        ... ]
        >>> result = generate_manifest(filings, "my-bucket")
        >>> print(result["filings_count"])
        150
    """
    # Calculate statistics
    stats = {
        "total_filings": len(filings),
        "total_members": len(set(f.get("doc_id") for f in filings if f.get("doc_id"))),
        "latest_year": max((f.get("year") for f in filings if f.get("year")), default=None),
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
    }

    # Simplify filings for frontend (remove unnecessary fields)
    simplified_filings = []
    for filing in filings:
        simplified = {
            "doc_id": filing.get("doc_id"),
            "year": filing.get("year"),
            "filing_date": filing.get("filing_date"),
            "filing_type": filing.get("filing_type"),
            "prefix": filing.get("prefix"),
            "first_name": filing.get("first_name"),
            "last_name": filing.get("last_name"),
            "suffix": filing.get("suffix"),
            "state_district": filing.get("state_district"),
        }
        simplified_filings.append(simplified)

    # Create manifest
    manifest = {
        "version": "1.0.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "stats": stats,
        "filings": simplified_filings,
    }

    # Upload to S3 (uncompressed for direct browser access)
    s3_client = boto3.client("s3")

    manifest_json = json.dumps(manifest, separators=(",", ":"))  # Compact JSON

    s3_client.put_object(
        Bucket=s3_bucket,
        Key=s3_key,
        Body=manifest_json.encode("utf-8"),
        ContentType="application/json",
        CacheControl="max-age=300",  # Cache for 5 minutes
        Metadata={
            "filings-count": str(len(simplified_filings)),
            "generated-at": manifest["generated_at"],
        },
    )

    # Also upload a gzipped version for bandwidth savings
    gzipped_buffer = BytesIO()
    with gzip.GzipFile(fileobj=gzipped_buffer, mode="wb") as gz_file:
        gz_file.write(manifest_json.encode("utf-8"))

    s3_client.put_object(
        Bucket=s3_bucket,
        Key=f"{s3_key}.gz",
        Body=gzipped_buffer.getvalue(),
        ContentType="application/json",
        ContentEncoding="gzip",
        CacheControl="max-age=300",
    )

    return {
        "manifest_s3_key": s3_key,
        "filings_count": len(simplified_filings),
        "manifest_size_bytes": len(manifest_json.encode("utf-8")),
        "manifest_size_compressed": len(gzipped_buffer.getvalue()),
        "compression_ratio": len(gzipped_buffer.getvalue()) / len(manifest_json.encode("utf-8")),
    }


def update_manifest_incremental(
    new_filings: List[Dict[str, Any]],
    s3_bucket: str,
    s3_key: str = "manifest.json",
) -> Dict[str, Any]:
    """Update manifest incrementally (fetch existing, merge, re-upload).

    Args:
        new_filings: New filings to add
        s3_bucket: S3 bucket name
        s3_key: S3 key for manifest

    Returns:
        dict: Update metadata
    """
    s3_client = boto3.client("s3")

    try:
        # Fetch existing manifest
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        existing_manifest = json.loads(response["Body"].read().decode("utf-8"))
        existing_filings = existing_manifest.get("filings", [])
    except s3_client.exceptions.NoSuchKey:
        # Manifest doesn't exist yet
        existing_filings = []

    # Merge filings (deduplicate by doc_id)
    filing_map = {f["doc_id"]: f for f in existing_filings}
    for filing in new_filings:
        doc_id = filing.get("doc_id")
        if doc_id:
            # Simplify filing
            simplified = {
                "doc_id": filing.get("doc_id"),
                "year": filing.get("year"),
                "filing_date": filing.get("filing_date"),
                "filing_type": filing.get("filing_type"),
                "prefix": filing.get("prefix"),
                "first_name": filing.get("first_name"),
                "last_name": filing.get("last_name"),
                "suffix": filing.get("suffix"),
                "state_district": filing.get("state_district"),
            }
            filing_map[doc_id] = simplified

    # Regenerate manifest
    all_filings = list(filing_map.values())
    return generate_manifest(all_filings, s3_bucket, s3_key)
