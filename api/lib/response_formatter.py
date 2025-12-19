"""
Response formatting utilities for Congressional Trading API

Provides consistent JSON response structure with CORS headers.
"""

from typing import Dict, Any, Optional
import json
import math

class NaNToNoneEncoder(json.JSONEncoder):
    """Encodes NaN/Inf floats as null for valid JSON output."""
    def encode(self, obj):
        def replace_nan(o):
            if isinstance(o, float):
                if math.isnan(o) or math.isinf(o):
                    return None
            elif isinstance(o, dict):
                return {k: replace_nan(v) for k, v in o.items()}
            elif isinstance(o, (list, tuple)):
                return [replace_nan(x) for x in o]
            return o
        return super().encode(replace_nan(obj))


def success_response(
    data: Any,
    status_code: int = 200,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build success response with consistent structure.
    
    Args:
        data: Response data (will be JSON serialized)
        status_code: HTTP status code (default 200)
        metadata: Optional metadata dict
    
    Returns:
        API Gateway response dict with statusCode, headers, body
    
    Example:
        success_response(
            data={'members': [...] },
            metadata={'total': 435, 'query_time_ms': 42}
        )
    """
    body = {
        "success": True,
        "data": data
    }
    
    if metadata:
        body["metadata"] = metadata
    
    return {
        "statusCode": status_code,
        "headers": _get_cors_headers(),
        "body": json.dumps(body, cls=NaNToNoneEncoder, default=str)  # default=str handles dates
    }


def error_response(
    message: str,
    status_code: int = 400,
    details: Optional[Any] = None
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
    body = {
        "success": False,
        "error": {
            "message": message,
            "code": status_code
        }
    }
    
    if details:
        body["error"]["details"] = details
    
    return {
        "statusCode": status_code,
        "headers": _get_cors_headers(),
        "body": json.dumps(body, cls=NaNToNoneEncoder, default=str)
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
        "Content-Type": "application/json"
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
