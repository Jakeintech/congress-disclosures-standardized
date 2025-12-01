"""
Filter parser for Congressional Trading API

Parses API Gateway query parameters into filter dictionaries for query builder.
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def parse_query_params(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and parse query parameters from API Gateway event.
    
    Supports operators via bracket notation:
        ?ticker=AAPL                    → {'ticker': 'AAPL'}
        ?amount[gt]=50000               → {'amount': {'gt': 50000}}
        ?transaction_type[in]=Purchase,Sale → {'transaction_type': {'in': ['Purchase', 'Sale']}}
    
    Args:
        event: API Gateway event dict
    
    Returns:
        Dict of parsed query parameters
    """
    # Get query string parameters (API Gateway v2.0 format)
    query_params = event.get('queryStringParameters') or {}
    
    parsed = {}
    
    for key, value in query_params.items():
        if '[' in key and ']' in key:
            # Operator-based filter: amount[gt]=50000
            column, operator = parse_operator_syntax(key)
            if column and operator:
                # Convert value to appropriate type
                converted_value = convert_value(value, operator)
                
                if column not in parsed:
                    parsed[column] = {}
                parsed[column][operator] = converted_value
        else:
            # Simple filter: ticker=AAPL
            parsed[key] = value
    
    return parsed


def parse_operator_syntax(key: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse operator syntax from query parameter key.
    
    Examples:
        'amount[gt]' → ('amount', 'gt')
        'transaction_type[in]' → ('transaction_type', 'in')
    
    Args:
        key: Query parameter key
    
    Returns:
        Tuple of (column_name, operator) or (None, None) if invalid
    """
    try:
        column, operator_part = key.split('[', 1)
        operator = operator_part.rstrip(']')
        
        # Validate operator
        valid_operators = ['eq', 'ne', 'gt', 'lt', 'gte', 'lte', 'in', 'like']
        if operator not in valid_operators:
            logger.warning(f"Invalid operator: {operator}")
            return None, None
        
        return column, operator
    except ValueError:
        return None, None


def convert_value(value: str, operator: str) -> Any:
    """
    Convert string value to appropriate type based on operator.
    
    Args:
        value: String value from query parameter
        operator: Operator type
    
    Returns:
        Converted value (int, float, list, or str)
    """
    if operator == 'in':
        # Split comma-separated list
        return [v.strip() for v in value.split(',')]
    
    # Try to convert to number
    try:
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        # Keep as string
        return value


def build_sql_where(filters: Dict[str, Any]) -> str:
    """
    Build SQL WHERE clause from filter dictionary.
    
    This is a simplified version - actual SQL building happens in query_builder.py.
    This function is mainly for validation and debugging.
    
    Args:
        filters: Filter dictionary
    
    Returns:
        SQL WHERE clause (without 'WHERE' keyword)
    """
    from api.lib.query_builder import ParquetQueryBuilder
    
    builder = ParquetQueryBuilder()
    return builder._build_where_clause(filters)


def extract_filter_params(query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract only filter-related parameters (exclude limit, offset, etc.).
    
    Args:
        query_params: All query parameters
    
    Returns:
        Dict with only filter parameters
    """
    # Non-filter parameters
    reserved_params = ['limit', 'offset', 'sort', 'order', 'page']
    
    return {
        k: v for k, v in query_params.items()
        if k not in reserved_params
    }


def parse_date_range(query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse common date range parameters.
    
    Converts:
        ?start_date=2025-01-01&end_date=2025-03-31
    
    To:
        {'transaction_date': {'gte': '2025-01-01', 'lte': '2025-03-31'}}
    
    Args:
        query_params: Query parameters
    
    Returns:
        Filters dict with date range filters
    """
    filters = {}
    
    start_date = query_params.get('start_date')
    end_date = query_params.get('end_date')
    
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter['gte'] = start_date
        if end_date:
            date_filter['lte'] = end_date
        
        # Use transaction_date as default, can be overridden
        filters['transaction_date'] = date_filter
    
    return filters


def parse_amount_range(query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse min/max amount parameters.
    
    Converts:
        ?min_amount=10000&max_amount=100000
    
    To:
        {'amount': {'gte': 10000, 'lte': 100000}}
    
    Args:
        query_params: Query parameters
    
    Returns:
        Filters dict with amount range filters
    """
    filters = {}
    
    min_amount = query_params.get('min_amount')
    max_amount = query_params.get('max_amount')
    
    if min_amount or max_amount:
        amount_filter = {}
        if min_amount:
            try:
                amount_filter['gte'] = float(min_amount)
            except ValueError:
                logger.warning(f"Invalid min_amount: {min_amount}")
        if max_amount:
            try:
                amount_filter['lte'] = float(max_amount)
            except ValueError:
                logger.warning(f"Invalid max_amount: {max_amount}")
        
        if amount_filter:
            filters['amount'] = amount_filter
    
    return filters
