import os
import json
import logging
import duckdb
from api.lib import success_response, error_response

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

# Global connection (reused across warm invocations)
_conn = None

def get_duckdb_connection():
    """Get or create DuckDB connection with S3 support."""
    global _conn
    if _conn is None:
        logger.info("Creating new DuckDB connection (cold start)")
        _conn = duckdb.connect(':memory:')
        _conn.execute("SET home_directory='/tmp';")
        _conn.execute("INSTALL httpfs; LOAD httpfs;")
        _conn.execute("SET enable_http_metadata_cache=true;")
        _conn.execute("SET s3_region='us-east-1';")
        _conn.execute("SET s3_use_ssl=true;")
    return _conn

def handler(event, context):
    """
    GET /v1/congress/members
    
    Query parameters:
    - limit: Records per page (default 50, max 500)
    - offset: Records to skip (default 0)
    - chamber: Filter by chamber ('House', 'Senate')
    - state: Filter by state (e.g., 'CA')
    - party: Filter by party ('D', 'R', 'I')
    - sort_by: Sort column ('total_trades', 'total_volume', 'name', 'last_name')
    - sort_order: 'asc' or 'desc' (default desc for numeric, asc for name)
    """
    try:
        query_params = event.get('queryStringParameters') or {}
        limit = min(int(query_params.get('limit', 50)), 500)
        offset = int(query_params.get('offset', 0))
        
        chamber = query_params.get('chamber')
        state = query_params.get('state')
        party = query_params.get('party')
        sort_by = query_params.get('sort_by', 'total_volume')
        sort_order = query_params.get('sort_order', 'desc')
        
        conn = get_duckdb_connection()
        
        # Build WHERE clauses
        where_clauses = ["1=1"]
        if chamber:
            val = 'house' if chamber.lower() in ['house', 'h'] else 'senate'
            where_clauses.append(f"m.chamber = '{val}'")
        if state:
            where_clauses.append(f"m.state = '{state.upper()}'")
        if party:
            where_clauses.append(f"m.party = '{party.upper()}'")
            
        where_sql = " AND ".join(where_clauses)
        
        # Determine sort column
        if sort_by == 'name' or sort_by == 'last_name':
            order_sql = f"m.last_name {sort_order}, m.first_name {sort_order}"
        elif sort_by == 'total_trades':
            order_sql = f"COALESCE(t.total_trades, 0) {sort_order}"
        else:  # Default total_volume
            order_sql = f"COALESCE(t.total_volume, 0) {sort_order}"
            
        # Standardize search paths for DuckDB
        members_path = f"s3://{S3_BUCKET}/gold/house/financial/dimensions/dim_members/**/*.parquet"
        stats_path = f"s3://{S3_BUCKET}/gold/aggregates/agg_member_trading_stats/**/*.parquet"
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) FROM read_parquet('{members_path}') m
            WHERE {where_sql}
        """
        total_count = conn.execute(count_query).fetchone()[0]
        
        # Main query with resilient JOIN
        # Note: We use union_by_name=True to handle schema differences between years in aggregates
        # Main query with resilient JOIN
        # Note: We use union_by_name=True to handle schema differences between years in aggregates
        # We also handle files that might only have 'name' or only 'first_name'/'last_name'
        query = f"""
            WITH raw_stats AS (
                SELECT * FROM read_parquet('{stats_path}', union_by_name=True)
            ),
            normalized_stats AS (
                SELECT 
                    COALESCE(first_name, split_part(name, ' ', 1)) as f_name,
                    COALESCE(last_name, split_part(name, ' ', -1)) as l_name,
                    total_trades,
                    total_volume,
                    unique_stocks,
                    CAST(period_end AS VARCHAR) as last_trade_date
                FROM raw_stats
            ),
            agg_stats AS (
                SELECT 
                    f_name, 
                    l_name, 
                    MAX(total_trades) as total_trades, 
                    SUM(total_volume) as total_volume, 
                    MAX(unique_stocks) as unique_stocks,
                    MAX(last_trade_date) as last_trade_date
                FROM normalized_stats
                GROUP BY f_name, l_name
            )
            SELECT 
                m.bioguide_id,
                m.first_name,
                m.last_name,
                m.full_name,
                m.party,
                m.state,
                m.district,
                m.chamber as chamber,
                m.is_current,
                COALESCE(t.total_trades, 0) as total_trades,
                COALESCE(t.total_volume, 0) as total_volume,
                COALESCE(t.unique_stocks, 0) as unique_stocks,
                t.last_trade_date
            FROM read_parquet('{members_path}') m
            LEFT JOIN agg_stats t 
                ON LOWER(m.first_name) = LOWER(t.f_name) 
                AND LOWER(m.last_name) = LOWER(t.l_name)
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT {limit} OFFSET {offset}
        """
        
        logger.info(f"Querying members: sort_by={sort_by}, limit={limit}, offset={offset}")
        result_df = conn.execute(query).fetchdf()
        members_list = result_df.to_dict('records')
        
        response = {
            'data': members_list,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_next': (offset + limit) < total_count,
                'has_prev': offset > 0
            },
            'filters': {
                'chamber': chamber,
                'state': state,
                'party': party,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
        }
        
        return success_response(response, metadata={'cache_seconds': 300})

    except Exception as e:
        logger.error(f"Error fetching Congress members: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve Congress members",
            status_code=500,
            details=str(e)
        )
