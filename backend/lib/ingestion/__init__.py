"""
Backend ingestion library - shared utilities for data ingestion and processing.

This module provides common utilities for:
- S3 operations (s3_utils, s3_path_registry)
- PDF extraction (extraction pipeline, extractors)
- Data transformation (parquet_writer, manifest_generator)
- Member lookup and reference data
"""

__version__ = "2.0.0"

# Re-export commonly used utilities
try:
    from backend.lib.ingestion.s3_utils import (
        get_s3_client,
        upload_file_to_s3,
        download_file_from_s3,
        s3_object_exists,
    )
    from backend.lib.ingestion.s3_path_registry import S3Paths, S3PathConfig
except ImportError:
    # For backward compatibility during migration
    pass

__all__ = [
    "get_s3_client",
    "upload_file_to_s3", 
    "download_file_from_s3",
    "s3_object_exists",
    "S3Paths",
    "S3PathConfig",
]
