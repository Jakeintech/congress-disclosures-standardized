import os
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    parse_pagination_params
)
from backend.lib.api.response_models import (
    Member,
    PaginationMetadata,
    PaginatedResponse,
    MembersPaginatedResponse
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def handler(event, context):
    """
    GET /v1/members
    
    Query parameters:
    - limit: Records per page (default 50, max 500)
    - offset: Records to skip (default 0)
    - state: Filter by state (e.g., 'CA')
    - district: Filter by district (e.g., '12')
    - party: Filter by party ('D', 'R', 'I')
    
    Returns paginated list of members with summary stats.
    """
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        limit, offset = parse_pagination_params(query_params)
        
        # Parse filters
        filters = {}
        if 'state' in query_params:
            filters['state'] = query_params['state'].upper()
        if 'district' in query_params:
            filters['district'] = query_params['district']
        if 'party' in query_params:
            filters['party'] = query_params['party'].upper()
        
        logger.info(f"Fetching members: limit={limit}, offset={offset}, filters={filters}")
        
        # Initialize query builder
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Count total matching records
        total_count = qb.count_records(
            'gold/house/financial/dimensions/dim_members',
            filters=filters if filters else None
        )
        
        # Query members with pagination
        members_df = qb.query_parquet(
            'gold/house/financial/dimensions/dim_members',
            filters=filters if filters else None,
            order_by='last_name ASC, first_name ASC',
            limit=limit,
            offset=offset
        )
        
        # Convert to list of dicts
        members_data = members_df.to_dict('records')
        
        if members_data:
            logger.info(f"Sample row keys: {list(members_data[0].keys())}")
            logger.info(f"Sample row: {members_data[0]}")
            
        # Build type-safe Member objects
        members = []
        for row in members_data:
            try:
                member = Member(
                    bioguide_id=row.get('bioguide_id'),
                    name=row.get('full_name') or row.get('name', 'Unknown'),
                    first_name=row.get('first_name'),
                    last_name=row.get('last_name'),
                    party=row.get('party'),
                    state=row.get('state'),
                    chamber=row.get('chamber').lower() if row.get('chamber') else 'house',
                    district=str(row.get('district')) if row.get('district') is not None else None,
                    in_office=bool(row.get('in_office', True))
                )
                members.append(member)
            except Exception as e:
                logger.warning(f"Error mapping member {row.get('bioguide_id')}: {e}")
                # Fallback for minimal data if possible, or skip
                continue

        # Build pagination metadata
        has_next = (offset + len(members)) < total_count
        has_prev = offset > 0
        
        # Build next/prev URLs
        base_url = "/v1/members"
        other_params = {k: v for k, v in query_params.items() if k not in ['limit', 'offset']}
        
        next_url = None
        if has_next:
            next_params = {**other_params, 'limit': limit, 'offset': offset + limit}
            from urllib.parse import urlencode
            next_url = f"{base_url}?{urlencode(next_params)}"
            
        prev_url = None
        if has_prev:
            prev_offset = max(0, offset - limit)
            prev_params = {**other_params, 'limit': limit, 'offset': prev_offset}
            from urllib.parse import urlencode
            prev_url = f"{base_url}?{urlencode(prev_params)}"

        pagination = PaginationMetadata(
            total=total_count,
            count=len(members),
            limit=limit,
            offset=offset,
            has_next=has_next,
            has_prev=has_prev,
            next=next_url,
            prev=prev_url
        )
        
        # Build paginated response
        paginated = PaginatedResponse(
            items=members,
            pagination=pagination
        )
        
        return success_response(paginated.model_dump())
    
    except Exception as e:
        logger.error(f"Error fetching members: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve members",
            status_code=500,
            details=str(e)
        )
