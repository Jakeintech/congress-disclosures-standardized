"""
Response formatting utilities for Congressional Trading API

Provides consistent JSON response structure with CORS headers.
"""

from typing import Dict, Any, Optional, List, Union
import json
import math
import logging
from pathlib import Path

try:
    from pydantic import BaseModel

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

logger = logging.getLogger(__name__)


# Load version at module initialization (cached for all Lambda invocations)
_VERSION_CACHE = None


def _load_version() -> str:
    """
    Load version string from version.json file.

    Searches multiple possible locations in Lambda environment.
    Falls back to hardcoded version if file not found.

    Returns:
        str: Version string (e.g., "v20251220-33a4c83")
    """
    global _VERSION_CACHE

    if _VERSION_CACHE is not None:
        return _VERSION_CACHE

    # Try multiple potential locations for version.json
    possible_paths = [
        Path("/var/task/version.json"),  # Lambda task root
        Path("/opt/python/version.json"),  # Layer location
        Path(__file__).parent.parent / "version.json",  # Relative to lib
        Path("version.json"),  # Current directory
    ]

    for version_path in possible_paths:
        try:
            if version_path.exists():
                with open(version_path, "r") as f:
                    version_data = json.load(f)
                    _VERSION_CACHE = version_data.get("version", "unknown")
                    logger.info(f"Loaded version {_VERSION_CACHE} from {version_path}")
                    return _VERSION_CACHE
        except Exception as e:
            logger.warning(f"Failed to load version from {version_path}: {e}")
            continue

    # Fallback to hardcoded version
    _VERSION_CACHE = "v20251219-fallback"
    logger.warning("version.json not found, using fallback version")
    return _VERSION_CACHE


def clean_nan_values(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Recursively clean NaN/Inf values from data structures.
    """
    if isinstance(data, dict):
        return {k: clean_nan_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(item) for item in data]

    # Robust numeric check
    try:
        # Handle string representations of NaN/Inf that might leak from data layer
        if isinstance(data, str):
            data_lower = data.lower().strip()
            if data_lower in (
                "nan",
                "inf",
                "infinity",
                "-inf",
                "-infinity",
                "none",
                "null",
            ):
                return None

        # Check for NaN/Inf in any numeric type (including numpy)
        # We check for __class__ name to avoid direct numpy dependency if not present
        class_name = str(data.__class__).lower()
        if "numpy" in class_name or "pandas" in class_name:
            import numpy as np

            if np.isnan(data) or np.isinf(data):
                return None

        if data is not None and isinstance(data, (float, int)):
            val = float(data)
            if math.isnan(val) or math.isinf(val):
                return None
    except (TypeError, ValueError, ImportError):
        pass
    return data


class NaNToNoneEncoder(json.JSONEncoder):
    """Encodes NaN/Inf floats as null for valid JSON output."""

    def encode(self, obj):
        return super().encode(clean_nan_values(obj))


def success_response(
    data: Any, status_code: int = 200, metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build success response with consistent structure.

    Args:
        data: Response data (dict, list, or Pydantic model)
        status_code: HTTP status code (default 200)
        metadata: Optional metadata dict

    Returns:
        API Gateway response dict with CORS headers

    Example:
        # Legacy dict usage (still supported)
        success_response({"member": {...}})

        # New Pydantic model usage
        from api.lib.response_models import Member, APIResponse
        member = Member(bioguide_id="C001117", name="Crockett, Jasmine", ...)
        success_response(member.model_dump())
    """
    # Convert Pydantic models to dict
    if PYDANTIC_AVAILABLE and isinstance(data, BaseModel):
        data = data.model_dump(mode="json", exclude_none=False)

    body = {
        "success": True,
        "data": data,
        "version": _load_version(),  # Load version from version.json
    }

    if metadata:
        body["metadata"] = metadata

    return {
        "statusCode": status_code,
        "headers": _get_cors_headers(),
        "body": json.dumps(body, cls=NaNToNoneEncoder, default=str, allow_nan=False),
    }


def error_response(
    message: str, status_code: int = 400, details: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Build error response with consistent structure.

    Args:
        message: Error message
        status_code: HTTP status code (400, 404, 500, etc.)
        details: Optional error details (stack trace, validation errors, etc.)

    Returns:
        API Gateway response dict

    Example:
        error_response(
            "Member not found",
            status_code=404,
            details={'bioguide_id': 'C999999'}
        )
    """
    body = {"success": False, "error": {"message": message, "code": status_code}}

    if details:
        body["error"]["details"] = details

    return {
        "statusCode": status_code,
        "headers": _get_cors_headers(),
        "body": json.dumps(body, cls=NaNToNoneEncoder, default=str, allow_nan=False),
    }


def _get_cors_headers() -> Dict[str, str]:
    """
    Get CORS headers for API responses.

    Returns:
        Dict of CORS headers
    """
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Content-Type": "application/json",
    }


def add_cors_headers(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add CORS headers to existing response dict.

    Args:
        response: API Gateway response dict

    Returns:
        Response dict with CORS headers added
    """
    if "headers" not in response:
        response["headers"] = {}

    response["headers"].update(_get_cors_headers())
    return response
