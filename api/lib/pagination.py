"""
Pagination utilities for Congressional Trading API

Provides limit/offset pagination with next/prev links.
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode


def paginate(df: pd.DataFrame, limit: int = 50, offset: int = 0) -> pd.DataFrame:
    """
    Apply limit/offset pagination to DataFrame.
    
    Args:
        df: DataFrame to paginate
        limit: Max rows to return (default 50, max 500)
        offset: Rows to skip (default 0)
    
    Returns:
        Paginated DataFrame
    """
    # Enforce max limit
    limit = min(limit, 500)
    
    # Handle negative values
    limit = max(limit, 1)
    offset = max(offset, 0)
    
    return df.iloc[offset:offset + limit]


def build_pagination_response(
    data: List[Dict[str, Any]],
    total_count: int,
    limit: int,
    offset: int,
    base_url: str,
    query_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build paginated API response with metadata and next/prev links.
    
    Args:
        data: List of data items for current page
        total_count: Total number of records (before pagination)
        limit: Records per page
        offset: Current offset
        base_url: Base URL for pagination links (e.g., '/v1/members')
        query_params: Additional query parameters to preserve in links
    
    Returns:
        Dict with data and pagination metadata
    
    Example:
        {
            "success": true,
            "data": [...],
            "pagination": {
                "total": 435,
                "count": 50,
                "limit": 50,
                "offset": 0,
                "has_next": true,
                "has_prev": false,
                "next": "/v1/members?limit=50&offset=50",
                "prev": null
            }
        }
    """
    query_params = query_params or {}
    count = len(data)
    has_next = (offset + count) < total_count
    has_prev = offset > 0
    
    # Build next/prev URLs
    next_url = None
    prev_url = None
    
    if has_next:
        next_params = {**query_params, 'limit': limit, 'offset': offset + limit}
        next_url = f"{base_url}?{urlencode(next_params)}"
    
    if has_prev:
        prev_offset = max(0, offset - limit)
        prev_params = {**query_params, 'limit': limit, 'offset': prev_offset}
        prev_url = f"{base_url}?{urlencode(prev_params)}"
    
    return {
        "success": True,
        "data": data,
        "pagination": {
            "total": total_count,
            "count": count,
            "limit": limit,
            "offset": offset,
            "has_next": has_next,
            "has_prev": has_prev,
            "next": next_url,
            "prev": prev_url
        }
    }


def parse_pagination_params(query_params: Dict[str, Any]) -> tuple[int, int]:
    """
    Extract and validate limit/offset from query parameters.
    
    Args:
        query_params: Query parameters dict
    
    Returns:
        Tuple of (limit, offset) with validated values
    """
    try:
        limit = int(query_params.get('limit', 50))
    except (ValueError, TypeError):
        limit = 50
    
    try:
        offset = int(query_params.get('offset', 0))
    except (ValueError, TypeError):
        offset = 0
    
    # Enforce constraints
    limit = max(1, min(limit, 500))  # Between 1 and 500
    offset = max(0, offset)          # Non-negative
    
    return limit, offset
