"""
Lambda handler: GET /v1/version

Returns API version information including Git commit, build timestamp,
and deployment metadata.
"""

import json
import logging
import os
from pathlib import Path

from api.lib import success_response, error_response
from backend.lib.api.response_models import (
    VersionData,
    GitInfo,
    BuildInfo,
    RuntimeInfo
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def load_version_file() -> dict:
    """
    Load version.json from Lambda package.

    Returns:
        dict: Version metadata including git hash, build timestamp, etc.
    """
    # Try multiple potential locations
    possible_paths = [
        Path(__file__).parent / "version.json",  # Same directory as handler
        Path("/opt/python/version.json"),        # Layer location
        Path("/var/task/version.json"),          # Lambda task root
        Path("version.json")                      # Current directory
    ]

    for version_path in possible_paths:
        if version_path.exists():
            logger.info(f"Loading version from {version_path}")
            with open(version_path, 'r') as f:
                return json.load(f)

    # Fallback if version.json not found
    logger.warning("version.json not found, using fallback")
    return {
        "version": "unknown",
        "git": {
            "commit": "unknown",
            "commit_short": "unknown",
            "branch": "unknown",
            "dirty": False
        },
        "build": {
            "timestamp": "unknown",
            "date": "unknown"
        },
        "api_version": "v1"
    }


def handler(event, context):
    """
    GET /v1/version

    Returns API version metadata and deployment information.

    Response includes:
    - version: Human-readable version string (e.g., v20251220-33a4c83)
    - git: Git commit hash, branch, and dirty status
    - build: Build timestamp and date
    - api_version: API version (v1)
    - runtime: Lambda runtime information
    """
    try:
        # Load version from bundled file
        version_file_data = load_version_file()

        # Build Pydantic models for type safety
        git_info = GitInfo(**version_file_data.get('git', {}))
        build_info = BuildInfo(**version_file_data.get('build', {}))
        runtime_info = RuntimeInfo(
            function_name=context.function_name if context else "local",
            function_version=context.function_version if context else "local",
            aws_request_id=context.aws_request_id if context else None,
            memory_limit_mb=context.memory_limit_in_mb if context else None,
        )

        # Create type-safe version response
        version_response = VersionData(
            version=version_file_data.get('version', 'unknown'),
            git=git_info,
            build=build_info,
            api_version=version_file_data.get('api_version', 'v1'),
            runtime=runtime_info,
            status="healthy"
        )

        logger.info(f"Version: {version_response.version}")

        # Convert Pydantic model to dict for response_formatter
        return success_response(
            version_response.model_dump(),
            metadata={
                "cache_seconds": 60  # Cache for 1 minute
            }
        )

    except Exception as e:
        logger.error(f"Error retrieving version: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve version information",
            status_code=500,
            details=str(e)
        )
