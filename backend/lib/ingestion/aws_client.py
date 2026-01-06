"""AWS Client Factory

Provides boto3 clients with automatic local emulator support.

Usage:
    Instead of:
        import boto3
        s3 = boto3.client('s3')

    Use:
        from backend.lib.ingestion.aws_client import get_client
        s3 = get_client('s3')

When USE_LOCAL_EMULATOR=true, this will return a local emulator client.
Otherwise, it returns a regular boto3 client.
"""

import os
from typing import Any


def get_client(service_name: str, **kwargs) -> Any:
    """Get an AWS client - uses local emulator if USE_LOCAL_EMULATOR is set.

    Args:
        service_name: AWS service name ('s3', 'sqs', 'lambda', etc.)
        **kwargs: Additional arguments to pass to boto3.client()

    Returns:
        Either a local emulator client or a boto3 client
    """
    use_local = os.environ.get('USE_LOCAL_EMULATOR', 'false').lower() == 'true'

    if use_local:
        # Use local emulator
        from backend.lib.ingestion.local_emulator import (
            LocalS3Client, LocalSQSClient, LocalLambdaClient
        )

        local_data_dir = os.environ.get('LOCAL_DATA_DIR', './local_data')

        if service_name == 's3':
            return LocalS3Client(local_data_dir)
        elif service_name == 'sqs':
            return LocalSQSClient(local_data_dir)
        elif service_name == 'lambda':
            return LocalLambdaClient()
        else:
            # Fallback to real boto3 for services without local emulator
            import boto3
            return boto3.client(service_name, **kwargs)
    else:
        # Use real boto3
        import boto3
        return boto3.client(service_name, **kwargs)


# Convenience function for scripts
def is_local_mode() -> bool:
    """Check if running in local emulator mode."""
    return os.environ.get('USE_LOCAL_EMULATOR', 'false').lower() == 'true'
