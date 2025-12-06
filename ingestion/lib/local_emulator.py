"""Local Emulator for Pipeline Development

This module provides local filesystem-based alternatives to AWS services
for local development and testing.

Usage:
    export USE_LOCAL_EMULATOR=true
    export LOCAL_DATA_DIR=./local_data

    python3 scripts/run_smart_pipeline.py --mode full
"""

import os
import json
import gzip
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LocalS3Client:
    """Local filesystem-based S3 client emulator."""

    def __init__(self, base_dir: str = "./local_data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalS3Client initialized at: {self.base_dir.absolute()}")

    def _get_path(self, bucket: str, key: str) -> Path:
        """Convert S3 bucket/key to local filesystem path."""
        return self.base_dir / bucket / key

    def get_object(self, Bucket: str, Key: str) -> Dict[str, Any]:
        """Emulate S3 get_object."""
        path = self._get_path(Bucket, Key)

        if not path.exists():
            raise FileNotFoundError(f"Key does not exist: {Key}")

        with open(path, 'rb') as f:
            body_bytes = f.read()

        # Read metadata from adjacent .metadata.json file
        metadata_path = path.parent / f"{path.name}.metadata.json"
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

        return {
            'Body': _BytesIO(body_bytes),
            'Metadata': metadata.get('Metadata', {}),
            'ContentLength': len(body_bytes),
            'LastModified': datetime.fromtimestamp(path.stat().st_mtime),
        }

    def put_object(self, Bucket: str, Key: str, Body: Union[bytes, str],
                   Metadata: Optional[Dict[str, str]] = None,
                   ContentType: Optional[str] = None,
                   **kwargs) -> Dict[str, Any]:
        """Emulate S3 put_object."""
        path = self._get_path(Bucket, Key)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write the object
        if isinstance(Body, str):
            Body = Body.encode('utf-8')

        with open(path, 'wb') as f:
            f.write(Body)

        # Write metadata to adjacent file
        if Metadata or ContentType:
            metadata_path = path.parent / f"{path.name}.metadata.json"
            metadata_data = {
                'Metadata': Metadata or {},
                'ContentType': ContentType,
            }
            with open(metadata_path, 'w') as f:
                json.dump(metadata_data, f, indent=2)

        logger.debug(f"Wrote {len(Body)} bytes to {path}")

        return {
            'ETag': f'"{hash(Body)}"',
            'VersionId': None,
        }

    def head_object(self, Bucket: str, Key: str) -> Dict[str, Any]:
        """Emulate S3 head_object."""
        path = self._get_path(Bucket, Key)

        if not path.exists():
            raise FileNotFoundError(f"Key does not exist: {Key}")

        # Read metadata
        metadata_path = path.parent / f"{path.name}.metadata.json"
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

        return {
            'ContentLength': path.stat().st_size,
            'LastModified': datetime.fromtimestamp(path.stat().st_mtime),
            'Metadata': metadata.get('Metadata', {}),
        }

    def copy_object(self, CopySource: Dict[str, str], Bucket: str, Key: str,
                    Metadata: Optional[Dict[str, str]] = None,
                    MetadataDirective: str = 'COPY',
                    **kwargs) -> Dict[str, Any]:
        """Emulate S3 copy_object (used for updating metadata)."""
        source_bucket = CopySource['Bucket']
        source_key = CopySource['Key']

        source_path = self._get_path(source_bucket, source_key)
        dest_path = self._get_path(Bucket, Key)

        # Copy file
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest_path)

        # Handle metadata
        if MetadataDirective == 'REPLACE' and Metadata:
            metadata_path = dest_path.parent / f"{dest_path.name}.metadata.json"
            metadata_data = {'Metadata': Metadata}
            with open(metadata_path, 'w') as f:
                json.dump(metadata_data, f, indent=2)

        return {'CopyObjectResult': {'ETag': '"copied"'}}

    def list_objects_v2(self, Bucket: str, Prefix: str = '',
                        MaxKeys: int = 1000,
                        ContinuationToken: Optional[str] = None) -> Dict[str, Any]:
        """Emulate S3 list_objects_v2."""
        bucket_path = self.base_dir / Bucket

        if not bucket_path.exists():
            return {'Contents': [], 'KeyCount': 0}

        prefix_path = bucket_path / Prefix if Prefix else bucket_path

        contents = []

        # Walk the directory tree
        if prefix_path.exists():
            for item in prefix_path.rglob('*'):
                if item.is_file() and not item.name.endswith('.metadata.json'):
                    relative_path = item.relative_to(bucket_path)
                    key = str(relative_path)

                    contents.append({
                        'Key': key,
                        'Size': item.stat().st_size,
                        'LastModified': datetime.fromtimestamp(item.stat().st_mtime),
                    })

        return {
            'Contents': contents[:MaxKeys],
            'KeyCount': len(contents[:MaxKeys]),
            'IsTruncated': len(contents) > MaxKeys,
        }

    def get_paginator(self, operation_name: str):
        """Return a paginator."""
        return LocalS3Paginator(self, operation_name)


class LocalS3Paginator:
    """Paginator for local S3 operations."""

    def __init__(self, client: LocalS3Client, operation_name: str):
        self.client = client
        self.operation_name = operation_name

    def paginate(self, **kwargs):
        """Paginate through results."""
        if self.operation_name == 'list_objects_v2':
            # For simplicity, return all results in one page
            result = self.client.list_objects_v2(**kwargs)
            yield result


class LocalSQSClient:
    """Local filesystem-based SQS client emulator."""

    def __init__(self, base_dir: str = "./local_data"):
        self.base_dir = Path(base_dir) / "sqs_queues"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalSQSClient initialized at: {self.base_dir.absolute()}")

    def _get_queue_dir(self, queue_url: str) -> Path:
        """Get directory for a queue."""
        queue_name = queue_url.split('/')[-1]
        return self.base_dir / queue_name

    def send_message(self, QueueUrl: str, MessageBody: str,
                     MessageAttributes: Optional[Dict] = None,
                     **kwargs) -> Dict[str, Any]:
        """Emulate SQS send_message."""
        queue_dir = self._get_queue_dir(QueueUrl)
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Generate message ID and filename
        message_id = f"msg_{datetime.now().timestamp()}_{hash(MessageBody) % 10000}"
        message_file = queue_dir / f"{message_id}.json"

        message_data = {
            'MessageId': message_id,
            'Body': MessageBody,
            'Attributes': MessageAttributes or {},
            'Timestamp': datetime.now().isoformat(),
        }

        with open(message_file, 'w') as f:
            json.dump(message_data, f, indent=2)

        logger.debug(f"Sent message to queue: {QueueUrl}")

        return {'MessageId': message_id}

    def get_queue_attributes(self, QueueUrl: str, AttributeNames: List[str]) -> Dict[str, Any]:
        """Emulate SQS get_queue_attributes."""
        queue_dir = self._get_queue_dir(QueueUrl)

        if not queue_dir.exists():
            return {'Attributes': {'ApproximateNumberOfMessages': '0'}}

        # Count messages in queue
        message_count = len(list(queue_dir.glob('*.json')))

        return {
            'Attributes': {
                'ApproximateNumberOfMessages': str(message_count),
                'ApproximateNumberOfMessagesNotVisible': '0',
                'ApproximateNumberOfMessagesDelayed': '0',
            }
        }

    def purge_queue(self, QueueUrl: str) -> Dict[str, Any]:
        """Emulate SQS purge_queue."""
        queue_dir = self._get_queue_dir(QueueUrl)

        if queue_dir.exists():
            shutil.rmtree(queue_dir)
            queue_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Purged queue: {QueueUrl}")
        return {}


class LocalLambdaClient:
    """Local Lambda client emulator - runs functions locally."""

    def invoke(self, FunctionName: str, InvocationType: str = 'RequestResponse',
               Payload: Union[str, bytes] = '', **kwargs) -> Dict[str, Any]:
        """Emulate Lambda invoke by importing and running the handler locally."""
        logger.info(f"Local Lambda invoke: {FunctionName} (type: {InvocationType})")

        # For now, just log the invocation
        # In a full implementation, you'd import the Lambda handler and run it
        if InvocationType == 'Event':
            # Async invoke - just log and return
            return {'StatusCode': 202}
        else:
            # Sync invoke - return success
            return {
                'StatusCode': 200,
                'Payload': _BytesIO(b'{"status": "success", "message": "Local execution"}'),
            }


class _BytesIO:
    """Simple BytesIO wrapper to match boto3 response format."""

    def __init__(self, data: bytes):
        self.data = data

    def read(self) -> bytes:
        return self.data


def get_client(service_name: str, **kwargs):
    """Get a client - returns local emulator if USE_LOCAL_EMULATOR is set."""
    use_local = os.environ.get('USE_LOCAL_EMULATOR', 'false').lower() == 'true'
    local_data_dir = os.environ.get('LOCAL_DATA_DIR', './local_data')

    if use_local:
        if service_name == 's3':
            return LocalS3Client(local_data_dir)
        elif service_name == 'sqs':
            return LocalSQSClient(local_data_dir)
        elif service_name == 'lambda':
            return LocalLambdaClient()
        else:
            raise ValueError(f"Local emulator not implemented for: {service_name}")
    else:
        # Use real boto3
        import boto3
        return boto3.client(service_name, **kwargs)
