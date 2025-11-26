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
        "latest_year": max(
            (f.get("year") for f in filings if f.get("year")), default=None
        ),
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
        "compression_ratio": len(gzipped_buffer.getvalue())
        / len(manifest_json.encode("utf-8")),
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


def generate_silver_documents_json(
    documents: List[Dict[str, Any]],
    s3_bucket: str,
    s3_key: str = "silver_documents.json",
) -> Dict[str, Any]:
    """Generate and upload silver documents data as JSON to S3.

    Args:
        documents: List of document records from silver layer
        s3_bucket: S3 bucket name
        s3_key: S3 key for documents JSON (default: silver_documents.json in root)

    Returns:
        dict: Upload metadata

    Example:
        >>> documents = [
        ...     {"doc_id": "123", "year": 2025, "extraction_status": "success", ...},
        ...     ...
        ... ]
        >>> result = generate_silver_documents_json(documents, "my-bucket")
        >>> print(result["documents_count"])
        150
    """
    # Calculate statistics
    stats = {
        "total_documents": len(documents),
        "extraction_stats": {
            "success": sum(
                1 for d in documents if d.get("extraction_status") == "success"
            ),
            "pending": sum(
                1 for d in documents if d.get("extraction_status") == "pending"
            ),
            "failed": sum(
                1 for d in documents if d.get("extraction_status") == "failed"
            ),
        },
        "extraction_methods": {},
        "total_pages": sum(d.get("pages", 0) for d in documents),
        "total_chars": sum(
            d.get("char_count", 0) for d in documents if d.get("char_count")
        ),
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
    }

    # Count extraction methods
    for doc in documents:
        method = doc.get("extraction_method", "unknown")
        stats["extraction_methods"][method] = (
            stats["extraction_methods"].get(method, 0) + 1
        )

    # Simplify documents for frontend
    simplified_documents = []
    for doc in documents:
        simplified = {
            "doc_id": doc.get("doc_id"),
            "year": doc.get("year"),
            "pdf_s3_key": doc.get("pdf_s3_key"),
            "pdf_file_size_bytes": doc.get("pdf_file_size_bytes"),
            "pages": doc.get("pages"),
            "has_embedded_text": doc.get("has_embedded_text"),
            "extraction_method": doc.get("extraction_method"),
            "extraction_status": doc.get("extraction_status"),
            "extraction_timestamp": doc.get("extraction_timestamp"),
            "extraction_error": doc.get("extraction_error"),
            "char_count": doc.get("char_count"),
            "text_s3_key": doc.get("text_s3_key"),
            "json_s3_key": doc.get("json_s3_key"),
        }
        simplified_documents.append(simplified)

    # Create documents JSON
    documents_data = {
        "version": "1.0.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "stats": stats,
        "documents": simplified_documents,
    }

    # Upload to S3
    s3_client = boto3.client("s3")
    documents_json = json.dumps(documents_data, separators=(",", ":"))

    s3_client.put_object(
        Bucket=s3_bucket,
        Key=s3_key,
        Body=documents_json.encode("utf-8"),
        ContentType="application/json",
        CacheControl="max-age=300",
        Metadata={
            "documents-count": str(len(simplified_documents)),
            "generated-at": documents_data["generated_at"],
        },
    )

    # Also upload a gzipped version
    gzipped_buffer = BytesIO()
    with gzip.GzipFile(fileobj=gzipped_buffer, mode="wb") as gz_file:
        gz_file.write(documents_json.encode("utf-8"))

    s3_client.put_object(
        Bucket=s3_bucket,
        Key=f"{s3_key}.gz",
        Body=gzipped_buffer.getvalue(),
        ContentType="application/json",
        ContentEncoding="gzip",
        CacheControl="max-age=300",
    )

    return {
        "documents_s3_key": s3_key,
        "documents_count": len(simplified_documents),
        "documents_size_bytes": len(documents_json.encode("utf-8")),
        "documents_size_compressed": len(gzipped_buffer.getvalue()),
        "compression_ratio": len(gzipped_buffer.getvalue())
        / len(documents_json.encode("utf-8")),
    }


def update_silver_documents_json_incremental(
    new_documents: List[Dict[str, Any]],
    s3_bucket: str,
    s3_key: str = "silver_documents.json",
) -> Dict[str, Any]:
    """Update silver documents JSON incrementally.

    Args:
        new_documents: New documents to add/update
        s3_bucket: S3 bucket name
        s3_key: S3 key for documents JSON

    Returns:
        dict: Update metadata
    """
    s3_client = boto3.client("s3")

    try:
        # Fetch existing documents
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        existing_data = json.loads(response["Body"].read().decode("utf-8"))
        existing_documents = existing_data.get("documents", [])
    except s3_client.exceptions.NoSuchKey:
        # Documents JSON doesn't exist yet
        existing_documents = []

    # Merge documents (deduplicate by doc_id)
    doc_map = {d["doc_id"]: d for d in existing_documents}
    for doc in new_documents:
        doc_id = doc.get("doc_id")
        if doc_id:
            # Simplify document
            simplified = {
                "doc_id": doc.get("doc_id"),
                "year": doc.get("year"),
                "pdf_s3_key": doc.get("pdf_s3_key"),
                "pdf_file_size_bytes": doc.get("pdf_file_size_bytes"),
                "pages": doc.get("pages"),
                "has_embedded_text": doc.get("has_embedded_text"),
                "extraction_method": doc.get("extraction_method"),
                "extraction_status": doc.get("extraction_status"),
                "extraction_timestamp": doc.get("extraction_timestamp"),
                "extraction_error": doc.get("extraction_error"),
                "char_count": doc.get("char_count"),
                "text_s3_key": doc.get("text_s3_key"),
                "json_s3_key": doc.get("json_s3_key"),
            }
            doc_map[doc_id] = simplified


    # Regenerate documents JSON
    all_documents = list(doc_map.values())
    return generate_silver_documents_json(all_documents, s3_bucket, s3_key)
