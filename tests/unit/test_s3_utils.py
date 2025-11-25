"""Unit tests for s3_utils module."""

import gzip
import io
from pathlib import Path
from unittest.mock import patch, MagicMock

from botocore.exceptions import ClientError

# Add ingestion/lib to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ingestion"))

from lib import s3_utils  # noqa: E402


class TestS3Utils:
    """Tests for S3 utility functions."""

    def test_calculate_sha256_bytes(self):
        """Test SHA256 calculation from bytes."""
        data = b"test data"
        expected_hash = (
            "916f0027a575074ce72a331777c3478d6513f786a591bd892da1a577bf2335f9"
        )

        result = s3_utils.calculate_sha256_bytes(data)

        assert result == expected_hash

    def test_build_s3_uri(self):
        """Test S3 URI construction."""
        bucket = "test-bucket"
        key = "path/to/file.txt"

        result = s3_utils.build_s3_uri(bucket, key)

        assert result == "s3://test-bucket/path/to/file.txt"

    def test_get_content_type_pdf(self):
        """Test content type detection for PDF."""
        result = s3_utils.get_content_type("document.pdf")
        assert result == "application/pdf"

    def test_get_content_type_xml(self):
        """Test content type detection for XML."""
        result = s3_utils.get_content_type("index.xml")
        assert result == "application/xml"

    def test_get_content_type_unknown(self):
        """Test content type detection for unknown type."""
        result = s3_utils.get_content_type("file.unknown")
        assert result == "application/octet-stream"

    @patch("lib.s3_utils.get_s3_client")
    def test_upload_bytes_to_s3_success(self, mock_get_client):
        """Test successful bytes upload to S3."""
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        mock_s3.put_object.return_value = {"ETag": '"abc123"'}

        data = b"test data"
        bucket = "test-bucket"
        s3_key = "test-key.txt"

        result = s3_utils.upload_bytes_to_s3(
            data=data,
            bucket=bucket,
            s3_key=s3_key,
        )

        # Verify S3 client was called correctly
        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Bucket"] == bucket
        assert call_kwargs["Key"] == s3_key
        assert call_kwargs["Body"] == data

        # Verify result
        assert result["s3_key"] == s3_key
        assert result["bucket"] == bucket
        assert result["size_bytes"] == len(data)
        assert "sha256" in result
        assert result["etag"] == "abc123"

    @patch("lib.s3_utils.get_s3_client")
    def test_s3_object_exists_true(self, mock_get_client):
        """Test s3_object_exists when object exists."""
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        mock_s3.head_object.return_value = {}

        result = s3_utils.s3_object_exists("bucket", "key")

        assert result is True
        mock_s3.head_object.assert_called_once_with(Bucket="bucket", Key="key")

    @patch("lib.s3_utils.get_s3_client")
    def test_s3_object_exists_false(self, mock_get_client):
        """Test s3_object_exists when object doesn't exist."""
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3

        # Simulate 404 error
        error_response = {"Error": {"Code": "404"}}
        mock_s3.head_object.side_effect = ClientError(error_response, "HeadObject")

        result = s3_utils.s3_object_exists("bucket", "key")

        assert result is False

    def test_upload_text_gzipped_compression(self):
        """Test text is properly gzipped when uploading."""
        with patch("lib.s3_utils.upload_bytes_to_s3") as mock_upload:
            mock_upload.return_value = {
                "s3_key": "test.gz",
                "bucket": "test-bucket",
                "size_bytes": 100,
            }

            text = "This is test text that should be compressed"
            bucket = "test-bucket"
            s3_key = "test.txt.gz"

            s3_utils.upload_text_gzipped(text, bucket, s3_key)

            # Verify upload was called
            mock_upload.assert_called_once()
            call_args = mock_upload.call_args[1]

            # Verify data is gzipped
            compressed_data = call_args["data"]
            with gzip.GzipFile(fileobj=io.BytesIO(compressed_data)) as gz:
                decompressed = gz.read().decode("utf-8")
                assert decompressed == text

            # Verify metadata includes compression info
            metadata = call_args["metadata"]
            assert "original_size_bytes" in metadata
            assert "compressed_size_bytes" in metadata
            assert "compression_ratio" in metadata
