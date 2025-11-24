"""S3 utility functions for data lake operations."""

import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union
from io import BytesIO
import gzip

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

logger = logging.getLogger(__name__)

# Configure boto3 with retries and timeouts optimized for Lambda
BOTO_CONFIG = Config(
    retries={"max_attempts": 3, "mode": "adaptive"},
    read_timeout=300,
    connect_timeout=10,
)

# Initialize S3 client (reused across invocations in Lambda)
s3_client = None


def get_s3_client():
    """Get or create S3 client with optimal configuration.

    Returns:
        boto3 S3 client
    """
    global s3_client
    if s3_client is None:
        s3_client = boto3.client("s3", config=BOTO_CONFIG)
    return s3_client


def calculate_sha256(file_path: Union[str, Path]) -> str:
    """Calculate SHA256 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        Hex-encoded SHA256 hash
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def calculate_sha256_bytes(data: bytes) -> str:
    """Calculate SHA256 hash of bytes.

    Args:
        data: Bytes to hash

    Returns:
        Hex-encoded SHA256 hash
    """
    return hashlib.sha256(data).hexdigest()


def upload_file_to_s3(
    local_path: Union[str, Path],
    bucket: str,
    s3_key: str,
    metadata: Optional[Dict[str, str]] = None,
    content_type: Optional[str] = None,
    storage_class: str = "STANDARD",
) -> Dict[str, Any]:
    """Upload a file to S3 with metadata and retry logic.

    Args:
        local_path: Path to local file
        bucket: S3 bucket name
        s3_key: S3 object key
        metadata: Optional metadata dict
        content_type: Optional content type (auto-detected if not provided)
        storage_class: S3 storage class (STANDARD, INTELLIGENT_TIERING, etc.)

    Returns:
        Dict with upload details (s3_key, bucket, size, sha256, etag)

    Raises:
        ClientError: If upload fails after retries
    """
    local_path = Path(local_path)
    if not local_path.exists():
        raise FileNotFoundError(f"File not found: {local_path}")

    # Calculate file hash for integrity
    file_hash = calculate_sha256(local_path)
    file_size = local_path.stat().st_size

    # Auto-detect content type if not provided
    if content_type is None:
        content_type = get_content_type(local_path)

    # Build metadata
    upload_metadata = {
        "sha256": file_hash,
        "upload_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_file": local_path.name,
    }
    if metadata:
        upload_metadata.update(metadata)

    # Upload with retry logic (handled by boto3 config)
    s3 = get_s3_client()
    try:
        logger.info(f"Uploading {local_path} to s3://{bucket}/{s3_key} ({file_size} bytes)")

        response = s3.upload_file(
            str(local_path),
            bucket,
            s3_key,
            ExtraArgs={
                "Metadata": upload_metadata,
                "ContentType": content_type,
                "StorageClass": storage_class,
            },
        )

        # Get ETag from HEAD request
        head_response = s3.head_object(Bucket=bucket, Key=s3_key)
        etag = head_response.get("ETag", "").strip('"')

        logger.info(f"Upload successful: s3://{bucket}/{s3_key} (ETag: {etag})")

        return {
            "s3_key": s3_key,
            "bucket": bucket,
            "size_bytes": file_size,
            "sha256": file_hash,
            "etag": etag,
            "storage_class": storage_class,
        }

    except ClientError as e:
        logger.error(f"Failed to upload {local_path} to S3: {e}")
        raise


def upload_bytes_to_s3(
    data: bytes,
    bucket: str,
    s3_key: str,
    metadata: Optional[Dict[str, str]] = None,
    content_type: str = "application/octet-stream",
    storage_class: str = "STANDARD",
) -> Dict[str, Any]:
    """Upload bytes directly to S3.

    Args:
        data: Bytes to upload
        bucket: S3 bucket name
        s3_key: S3 object key
        metadata: Optional metadata dict
        content_type: Content type
        storage_class: S3 storage class

    Returns:
        Dict with upload details

    Raises:
        ClientError: If upload fails
    """
    data_hash = calculate_sha256_bytes(data)
    data_size = len(data)

    upload_metadata = {
        "sha256": data_hash,
        "upload_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if metadata:
        upload_metadata.update(metadata)

    s3 = get_s3_client()
    try:
        logger.info(f"Uploading {data_size} bytes to s3://{bucket}/{s3_key}")

        response = s3.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=data,
            Metadata=upload_metadata,
            ContentType=content_type,
            StorageClass=storage_class,
        )

        etag = response.get("ETag", "").strip('"')

        logger.info(f"Upload successful: s3://{bucket}/{s3_key} (ETag: {etag})")

        return {
            "s3_key": s3_key,
            "bucket": bucket,
            "size_bytes": data_size,
            "sha256": data_hash,
            "etag": etag,
            "storage_class": storage_class,
        }

    except ClientError as e:
        logger.error(f"Failed to upload bytes to S3: {e}")
        raise


def download_file_from_s3(
    bucket: str,
    s3_key: str,
    local_path: Union[str, Path],
) -> Dict[str, Any]:
    """Download a file from S3.

    Args:
        bucket: S3 bucket name
        s3_key: S3 object key
        local_path: Path to save file locally

    Returns:
        Dict with download details (local_path, size, etag, metadata)

    Raises:
        ClientError: If download fails
    """
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    s3 = get_s3_client()
    try:
        logger.info(f"Downloading s3://{bucket}/{s3_key} to {local_path}")

        # Get object metadata first
        head_response = s3.head_object(Bucket=bucket, Key=s3_key)

        # Download file
        s3.download_file(bucket, s3_key, str(local_path))

        file_size = local_path.stat().st_size
        etag = head_response.get("ETag", "").strip('"')
        metadata = head_response.get("Metadata", {})

        logger.info(f"Download successful: {local_path} ({file_size} bytes)")

        return {
            "local_path": str(local_path),
            "size_bytes": file_size,
            "etag": etag,
            "metadata": metadata,
            "last_modified": head_response.get("LastModified"),
        }

    except ClientError as e:
        logger.error(f"Failed to download s3://{bucket}/{s3_key}: {e}")
        raise


def download_bytes_from_s3(bucket: str, s3_key: str) -> bytes:
    """Download S3 object as bytes.

    Args:
        bucket: S3 bucket name
        s3_key: S3 object key

    Returns:
        Object data as bytes

    Raises:
        ClientError: If download fails
    """
    s3 = get_s3_client()
    try:
        logger.info(f"Downloading s3://{bucket}/{s3_key} as bytes")

        response = s3.get_object(Bucket=bucket, Key=s3_key)
        data = response["Body"].read()

        logger.info(f"Downloaded {len(data)} bytes from s3://{bucket}/{s3_key}")

        return data

    except ClientError as e:
        logger.error(f"Failed to download s3://{bucket}/{s3_key}: {e}")
        raise


def upload_text_gzipped(
    text: str,
    bucket: str,
    s3_key: str,
    metadata: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Upload text as gzipped file to S3.

    Useful for storing extracted text efficiently.

    Args:
        text: Text content to upload
        bucket: S3 bucket name
        s3_key: S3 object key (should end with .gz)
        metadata: Optional metadata

    Returns:
        Dict with upload details
    """
    # Gzip compress the text
    text_bytes = text.encode("utf-8")
    compressed_buffer = BytesIO()

    with gzip.GzipFile(fileobj=compressed_buffer, mode="wb") as gz_file:
        gz_file.write(text_bytes)

    compressed_data = compressed_buffer.getvalue()

    # Add compression info to metadata
    upload_metadata = {
        "original_size_bytes": str(len(text_bytes)),
        "compressed_size_bytes": str(len(compressed_data)),
        "compression_ratio": f"{len(text_bytes) / len(compressed_data):.2f}",
    }
    if metadata:
        upload_metadata.update(metadata)

    return upload_bytes_to_s3(
        data=compressed_data,
        bucket=bucket,
        s3_key=s3_key,
        metadata=upload_metadata,
        content_type="application/gzip",
    )


def download_text_gzipped(bucket: str, s3_key: str) -> str:
    """Download and decompress gzipped text from S3.

    Args:
        bucket: S3 bucket name
        s3_key: S3 object key

    Returns:
        Decompressed text content
    """
    compressed_data = download_bytes_from_s3(bucket, s3_key)

    with gzip.GzipFile(fileobj=BytesIO(compressed_data)) as gz_file:
        text_bytes = gz_file.read()

    return text_bytes.decode("utf-8")


def s3_object_exists(bucket: str, s3_key: str) -> bool:
    """Check if an S3 object exists.

    Args:
        bucket: S3 bucket name
        s3_key: S3 object key

    Returns:
        True if object exists, False otherwise
    """
    s3 = get_s3_client()
    try:
        s3.head_object(Bucket=bucket, Key=s3_key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


def get_content_type(file_path: Union[str, Path]) -> str:
    """Get content type based on file extension.

    Args:
        file_path: Path to file

    Returns:
        MIME content type
    """
    suffix = Path(file_path).suffix.lower()

    content_types = {
        ".pdf": "application/pdf",
        ".xml": "application/xml",
        ".txt": "text/plain",
        ".json": "application/json",
        ".parquet": "application/octet-stream",
        ".zip": "application/zip",
        ".gz": "application/gzip",
        ".csv": "text/csv",
    }

    return content_types.get(suffix, "application/octet-stream")


def build_s3_uri(bucket: str, key: str) -> str:
    """Build S3 URI from bucket and key.

    Args:
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        S3 URI (s3://bucket/key)
    """
    return f"s3://{bucket}/{key}"
