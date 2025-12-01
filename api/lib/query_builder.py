"""
DuckDB-based Parquet Query Builder for Congressional Trading API

Provides fast SQL-based queries against Gold layer Parquet files using DuckDB.
DuckDB offers zero-copy Parquet access and is 10-100x faster than pandas for analytical queries.
"""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ParquetQueryBuilder:
    """Build and execute DuckDB queries against Parquet files."""
    
    def __init__(self, s3_bucket: Optional[str] = None):
        """
        Initialize query builder.
        
        Args:
            s3_bucket: Optional S3 bucket name. If provided, will query S3 directly.
                      If None, assumes local filesystem access.
        """
        self.s3_bucket = s3_bucket
        self.conn = duckdb.connect(database=':memory:')
        
        # Install and load httpfs extension for S3 access if needed
        if s3_bucket:
            self.conn.execute("INSTALL httpfs;")
            self.conn.execute("LOAD httpfs;")
    
    def query_parquet(
        self,
        table_path: str,
        filters: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Query Parquet files with filters, pagination, and column selection.
        
        Args:
            table_path: Path to Parquet table (e.g., 'gold/dimensions/dim_members')
            filters: Dict of filters {column: value} or {column: {operator: value}}
            columns: List of columns to select (None = all)
            limit: Max rows to return
            offset: Rows to skip
            order_by: Column to sort by (e.g., 'transaction_date DESC')
        
        Returns:
            pandas DataFrame with query results
        
        Examples:
            # Simple filter
            query_parquet('gold/facts/fact_ptr_transactions', 
                         filters={'ticker': 'AAPL'}, limit=100)
            
            # Complex filters with operators
            query_parquet('gold/facts/fact_ptr_transactions',
                         filters={
                             'transaction_date': {'gte': '2025-01-01'},
                             'amount': {'gt': 50000}
                         })
        """
        # Build parquet path
        if self.s3_bucket:
            parquet_path = f"s3://{self.s3_bucket}/{table_path}/**/*.parquet"
        else:
            parquet_path = f"data/{table_path}/**/*.parquet"
        
        # Build SQL query
        select_clause = ", ".join(columns) if columns else "*"
        query = f"SELECT {select_clause} FROM read_parquet('{parquet_path}')"
        
        # Add WHERE clause if filters provided
        if filters:
            where_clause = self._build_where_clause(filters)
            if where_clause:
                query += f" WHERE {where_clause}"
        
        # Add ORDER BY
        if order_by:
            query += f" ORDER BY {order_by}"
        
        # Add pagination
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
        
        logger.info(f "Executing query: {query}")
        
        try:
            result = self.conn.execute(query).df()
            logger.info(f"Query returned {len(result)} rows")
            return result
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    def _build_where_clause(self, filters: Dict[str, Any]) -> str:
        """
        Build SQL WHERE clause from filter dictionary.
        
        Supports operators: eq, ne, gt, lt, gte, lte, in, like
        
        Args:
            filters: {column: value} or {column: {operator: value}}
        
        Returns:
            SQL WHERE clause (without 'WHERE' keyword)
        """
        conditions = []
        
        for column, filter_value in filters.items():
            if isinstance(filter_value, dict):
                # Operator-based filter: {'amount': {'gt': 50000}}
                for operator, value in filter_value.items():
                    condition = self._build_condition(column, operator, value)
                    if condition:
                        conditions.append(condition)
            else:
                # Simple equality filter: {'ticker': 'AAPL'}
                condition = self._build_condition(column, 'eq', filter_value)
                if condition:
                    conditions.append(condition)
        
        return " AND ".join(conditions)
    
    def _build_condition(self, column: str, operator: str, value: Any) -> str:
        """Build a single SQL condition."""
        # Sanitize column name (basic protection)
        column = column.replace("'", "").replace(";", "")
        
        if operator == 'eq':
            if isinstance(value, str):
                return f"{column} = '{self._escape_string(value)}'"
            elif value is None:
                return f"{column} IS NULL"
            else:
                return f"{column} = {value}"
        
        elif operator == 'ne':
            if isinstance(value, str):
                return f"{column} != '{self._escape_string(value)}'"
            elif value is None:
                return f"{column} IS NOT NULL"
            else:
                return f"{column} != {value}"
        
        elif operator == 'gt':
            if isinstance(value, str):
                return f"{column} > '{self._escape_string(value)}'"
            else:
                return f"{column} > {value}"
        
        elif operator == 'lt':
            if isinstance(value, str):
                return f"{column} < '{self._escape_string(value)}'"
            else:
                return f"{column} < {value}"
        
        elif operator == 'gte':
            if isinstance(value, str):
                return f"{column} >= '{self._escape_string(value)}'"
            else:
                return f"{column} >= {value}"
        
        elif operator == 'lte':
            if isinstance(value, str):
                return f"{column} <= '{self._escape_string(value)}'"
            else:
                return f"{column} <= {value}"
        
        elif operator == 'in':
            if isinstance(value, list):
                # Convert list to SQL IN clause
                if all(isinstance(v, str) for v in value):
                    values_str = ", ".join([f"'{self._escape_string(v)}'" for v in value])
                else:
                    values_str = ", ".join([str(v) for v in value])
                return f"{column} IN ({values_str})"
            else:
                logger.warning(f"'in' operator requires list value, got {type(value)}")
                return ""
        
        elif operator == 'like':
            if isinstance(value, str):
                return f"{column} LIKE '{self._escape_string(value)}'"
            else:
                logger.warning(f"'like' operator requires string value, got {type(value)}")
                return ""
        
        else:
            logger.warning(f"Unknown operator: {operator}")
            return ""
    
    def _escape_string(self, value: str) -> str:
        """Escape string for SQL (prevent injection)."""
        return value.replace("'", "''")
    
    def aggregate_parquet(
        self,
        table_path: str,
        group_by: List[str],
        aggregations: Dict[str, str],
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Run aggregation query on Parquet files.
        
        Args:
            table_path: Path to Parquet table
            group_by: Columns to group by
            aggregations: Dict of {result_column: sql_expression}
                         e.g., {'total_trades': 'COUNT(*)', 'avg_amount': 'AVG(amount)'}
            filters: Optional filters to apply before aggregation
            order_by: Column to sort results
            limit: Max rows to return
        
        Returns:
            pandas DataFrame with aggregated results
        
        Example:
            aggregate_parquet(
                'gold/facts/fact_ptr_transactions',
                group_by=['ticker'],
                aggregations={
                    'trade_count': 'COUNT(*)',
                    'total_volume': 'SUM(amount)',
                    'avg_amount': 'AVG(amount)'
                },
                order_by='trade_count DESC',
                limit=20
            )
        """
        # Build parquet path
        if self.s3_bucket:
            parquet_path = f"s3://{self.s3_bucket}/{table_path}/**/*.parquet"
        else:
            parquet_path = f"data/{table_path}/**/*.parquet"
        
        # Build aggregation expressions
        agg_exprs = [f"{expr} AS {col}" for col, expr in aggregations.items()]
        select_clause = ", ".join(group_by + agg_exprs)
        
        query = f"SELECT {select_clause} FROM read_parquet('{parquet_path}')"
        
        # Add WHERE clause if filters provided
        if filters:
            where_clause = self._build_where_clause(filters)
            if where_clause:
                query += f" WHERE {where_clause}"
        
        # Add GROUP BY
        query += f" GROUP BY {', '.join(group_by)}"
        
        # Add ORDER BY
        if order_by:
            query += f" ORDER BY {order_by}"
        
        # Add LIMIT
        if limit:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing aggregation: {query}")
        
        try:
            result = self.conn.execute(query).df()
            logger.info(f"Aggregation returned {len(result)} rows")
            return result
        except Exception as e:
            logger.error(f"Aggregation failed: {e}")
            raise
    
    def count_records(self, table_path: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records in Parquet table with optional filters.
        
        Args:
            table_path: Path to Parquet table
            filters: Optional filters
        
        Returns:
            Record count
        """
        if self.s3_bucket:
            parquet_path = f"s3://{self.s3_bucket}/{table_path}/**/*.parquet"
        else:
            parquet_path = f"data/{table_path}/**/*.parquet"
        
        query = f"SELECT COUNT(*) as count FROM read_parquet('{parquet_path}')"
        
        if filters:
            where_clause = self._build_where_clause(filters)
            if where_clause:
                query += f" WHERE {where_clause}"
        
        result = self.conn.execute(query).df()
        return int(result['count'].iloc[0])
    
    def close(self):
        """Close DuckDB connection."""
        if self.conn:
            self.conn.close()
