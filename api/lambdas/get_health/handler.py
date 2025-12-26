"""
Lambda handler: GET /v1/health
Health check endpoint with comprehensive service validation
"""

import json
import logging
import os
import sys
import time
from typing import Dict, Any, List

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def check_duckdb() -> Dict[str, Any]:
    """Check DuckDB availability and version."""
    try:
        import duckdb

        # Test basic query
        conn = duckdb.connect(':memory:')

        # Set home directory to /tmp for Lambda
        conn.execute("SET home_directory='/tmp';")

        result = conn.execute("SELECT version()").fetchone()
        version = result[0] if result else "unknown"

        # Test S3 access via DuckDB
        conn.execute("INSTALL httpfs; LOAD httpfs;")
        conn.execute("SET s3_region='us-east-1';")

        return {
            "status": "healthy",
            "version": version,
            "s3_enabled": True
        }
    except Exception as e:
        logger.error(f"DuckDB check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_s3() -> Dict[str, Any]:
    """Check S3 bucket access."""
    try:
        import boto3
        from botocore.exceptions import ClientError

        s3 = boto3.client('s3')

        # Test bucket access with list operation
        start_time = time.time()
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix='gold/',
            MaxKeys=1
        )
        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "status": "healthy",
            "bucket": S3_BUCKET,
            "accessible": True,
            "latency_ms": latency_ms,
            "objects_found": response.get('KeyCount', 0)
        }
    except ClientError as e:
        logger.error(f"S3 check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "bucket": S3_BUCKET,
            "error": str(e),
            "error_code": e.response.get('Error', {}).get('Code', 'Unknown')
        }
    except Exception as e:
        logger.error(f"S3 check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "bucket": S3_BUCKET,
            "error": str(e)
        }


def check_dependencies() -> Dict[str, Any]:
    """Check Python dependency versions."""
    dependencies = {}

    try:
        import duckdb
        dependencies['duckdb'] = duckdb.__version__
    except ImportError:
        dependencies['duckdb'] = "not installed"

    try:
        import pyarrow
        dependencies['pyarrow'] = pyarrow.__version__
    except ImportError:
        dependencies['pyarrow'] = "not installed"

    try:
        import boto3
        dependencies['boto3'] = boto3.__version__
    except ImportError:
        dependencies['boto3'] = "not installed"

    dependencies['python'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    return dependencies


def check_lambda_runtime() -> Dict[str, Any]:
    """Check Lambda runtime information."""
    return {
        "function_name": os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'unknown'),
        "function_version": os.environ.get('AWS_LAMBDA_FUNCTION_VERSION', 'unknown'),
        "memory_limit_mb": os.environ.get('AWS_LAMBDA_FUNCTION_MEMORY_SIZE', 'unknown'),
        "log_group": os.environ.get('AWS_LAMBDA_LOG_GROUP_NAME', 'unknown'),
        "region": os.environ.get('AWS_REGION', 'unknown')
    }


def handler(event, context):
    """GET /v1/health - Comprehensive health check."""
    try:
        logger.info("Running health checks...")

        # Run all checks
        start_time = time.time()

        duckdb_health = check_duckdb()
        s3_health = check_s3()
        dependencies = check_dependencies()
        runtime_info = check_lambda_runtime()

        total_time_ms = int((time.time() - start_time) * 1000)

        # Determine overall health status
        checks_passed = [
            duckdb_health['status'] == 'healthy',
            s3_health['status'] == 'healthy'
        ]

        overall_status = 'healthy' if all(checks_passed) else 'degraded'

        response = {
            'status': overall_status,
            'timestamp': int(time.time()),
            'checks': {
                'duckdb': duckdb_health,
                's3': s3_health
            },
            'dependencies': dependencies,
            'runtime': runtime_info,
            'response_time_ms': total_time_ms
        }

        # Return 200 for healthy/degraded, 503 for critical failures
        status_code = 200 if overall_status in ['healthy', 'degraded'] else 503

        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,OPTIONS',
                'Cache-Control': 'no-cache, no-store, must-revalidate'
            },
            'body': json.dumps(response, indent=2)
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)

        error_response = {
            'status': 'unhealthy',
            'timestamp': int(time.time()),
            'error': str(e),
            'error_type': type(e).__name__
        }

        return {
            'statusCode': 503,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(error_response, indent=2)
        }
