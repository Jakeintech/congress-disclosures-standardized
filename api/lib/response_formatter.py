"""
Response formatting utilities for Congressional Trading API

Provides consistent JSON response structure with CORS headers.
"""

from typing import Dict, Any, Optional, List, Union
import json
import math


def clean_nan_values(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Recursively clean NaN/Inf values from data structures.
    This should be called on dataframe.to_dict('records') output before serialization.
    
    Args:
        data: Dict, list, or scalar value to clean
        
    Returns:
        Cleaned data with NaN/Inf replaced by None
    """
    if isinstance(data, dict):
        return {k: clean_nan_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(item) for item in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    elif hasattr(data, '__class__') and 'numpy' in str(data.__class__):
        # Handle numpy types
        try:
            float_val = float(data)
            if math.isnan(float_val) or math.isinf(float_val):
                return None
            return float_val
        except (TypeError, ValueError):
            return data
    return data

class NaNToNoneEncoder(json.JSONEncoder):
    """Encodes NaN/Inf floats as null for valid JSON output."""
    def encode(self, obj):
        def replace_nan(o):
            # Check for NaN/Inf in any numeric type (including numpy.float64)
            # Use try-except to handle types that might not have math.isnan support
            try:
                if isinstance(o, (float, int)) or (hasattr(o, '__class__') and 'numpy' in str(o.__class__)):
                    if math.isnan(o) or math.isinf(o):
                        return None
            except (TypeError, ValueError):
                pass

            if isinstance(o, dict):
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
