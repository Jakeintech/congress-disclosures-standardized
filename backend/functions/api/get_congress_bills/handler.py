"""
Lambda handler: GET /v1/congress/bills

List Congress bills with enhanced sorting, filtering, and enriched data.
Supports industry filters, trade correlation filters, and multiple sort options.
"""

import os
import json
import logging
from urllib.parse import urlencode
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    parse_pagination_params
)
from backend.lib.api.response_models import Bill, PaginationMetadata, PaginatedResponse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def enrich_bills_with_aggregates(qb, bills_df):
    """Enrich bills with cosponsors count, trade correlations, industry tags, and latest action."""
    if bills_df.empty:
        return bills_df

    bill_ids = bills_df['bill_id'].unique().tolist() if 'bill_id' in bills_df.columns else []

    if not bill_ids:
        # Generate bill_ids if not present
        bills_df['bill_id'] = bills_df.apply(
            lambda row: f"{row.get('congress', '')}-{row.get('bill_type', '')}-{row.get('bill_number', '')}",
            axis=1
        )
        bill_ids = bills_df['bill_id'].tolist()

    # Initialize enrichment columns
    bills_df['cosponsors_count'] = 0
    bills_df['trade_correlations_count'] = 0
    bills_df['top_industry_tags'] = None
    bills_df['latest_action_date'] = None
    bills_df['latest_action_text'] = None
    bills_df['days_since_action'] = None

    try:
        # Get cosponsors counts
        cosponsors_df = qb.query_parquet(
            'gold/congress/fact_member_bill_role',
            filters={'is_cosponsor': True},
            limit=10000
        )

        if not cosponsors_df.empty and 'bill_id' in cosponsors_df.columns:
            cosponsors_counts = cosponsors_df[cosponsors_df['bill_id'].isin(bill_ids)].groupby('bill_id').size()
            bills_df['cosponsors_count'] = bills_df['bill_id'].map(cosponsors_counts).fillna(0).astype(int)

    except Exception as e:
        logger.warning(f"Could not load cosponsors: {e}")

    try:
        # Get trade correlation counts
        corr_df = qb.query_parquet(
            'gold/congress/agg_bill_trade_correlation',
            filters=None,
            limit=10000
        )

        if not corr_df.empty and 'bill_id' in corr_df.columns:
            corr_counts = corr_df[corr_df['bill_id'].isin(bill_ids)].groupby('bill_id').size()
            bills_df['trade_correlations_count'] = bills_df['bill_id'].map(corr_counts).fillna(0).astype(int)

    except Exception as e:
        logger.warning(f"Could not load trade correlations: {e}")

    try:
        # Get top 2 industry tags per bill
        industry_df = qb.query_parquet(
            'gold/congress/bill_industry_tags',
            filters=None,
            limit=10000
        )

        if not industry_df.empty and 'bill_id' in industry_df.columns:
            # Filter to our bills and sort by confidence
            industry_df = industry_df[industry_df['bill_id'].isin(bill_ids)]
            industry_df = industry_df.sort_values('confidence_score', ascending=False)

            # Get top 2 per bill
            top_industries = industry_df.groupby('bill_id').head(2).groupby('bill_id')['industry'].apply(list)
            bills_df['top_industry_tags'] = bills_df['bill_id'].map(top_industries).apply(
                lambda x: x if isinstance(x, list) else []
            )

    except Exception as e:
        logger.warning(f"Could not load industry tags: {e}")

    try:
        # Get latest action per bill
        latest_action_df = qb.query_parquet(
            'gold/congress/agg_bill_latest_action',
            filters=None,
            limit=5000
        )

        if not latest_action_df.empty and 'bill_id' in latest_action_df.columns:
            latest_action_df = latest_action_df[latest_action_df['bill_id'].isin(bill_ids)]
            latest_action_dict = latest_action_df.set_index('bill_id').to_dict('index')

            for idx, row in bills_df.iterrows():
                bill_id = row['bill_id']
                if bill_id in latest_action_dict:
                    action = latest_action_dict[bill_id]
                    bills_df.at[idx, 'latest_action_date'] = str(action.get('latest_action_date', ''))
                    bills_df.at[idx, 'latest_action_text'] = action.get('latest_action_text', '')
                    bills_df.at[idx, 'days_since_action'] = int(action.get('days_since_action', 0))

    except Exception as e:
        logger.warning(f"Could not load latest actions: {e}")

    return bills_df


def handler(event, context):
    """
    GET /v1/congress/bills
    """
    try:
        query_params = event.get('queryStringParameters') or {}
        limit, offset = parse_pagination_params(query_params)

        # Parse filters
        filters = {}
        if 'congress' in query_params:
            filters['congress'] = int(query_params['congress'])
        if 'bill_type' in query_params:
            filters['bill_type'] = query_params['bill_type'].lower()
        if 'sponsor_bioguide' in query_params:
            filters['sponsor_bioguide_id'] = query_params['sponsor_bioguide']

        # Parse sorting
        sort_by = query_params.get('sort_by', 'latest_action_date')
        sort_order = query_params.get('sort_order', 'desc').lower()

        logger.info(f"Fetching bills: limit={limit}, offset={offset}, filters={filters}, sort_by={sort_by}")

        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        s3_prefix = 'gold/congress/dim_bill'

        # Determine base ordering
        if sort_by == 'introduced_date':
            base_order = 'introduced_date DESC' if sort_order == 'desc' else 'introduced_date ASC'
        else:
            base_order = 'congress DESC, bill_number DESC'

        # Query bills
        query_limit = min(limit * 3, 1500)
        try:
            bills_df = qb.query_parquet(
                s3_prefix,
                filters=filters if filters else None,
                order_by=base_order,
                limit=query_limit,
                offset=0 
            )
        except Exception as e:
            logger.warning(f"No bills data available: {e}")
            bills_df = None

        if bills_df is None or bills_df.empty:
            return success_response({
                'items': [],
                'pagination': {
                    'total': 0, 'count': 0, 'limit': limit, 'offset': offset,
                    'has_next': False, 'has_prev': False, 'next': None, 'prev': None
                }
            })

        # Apply post-query filters
        if 'sponsor' in query_params:
            sponsor_filter = query_params['sponsor'].lower()
            if 'sponsor_name' in bills_df.columns:
                bills_df = bills_df[bills_df['sponsor_name'].str.lower().str.contains(sponsor_filter, na=False)]

        bills_df = enrich_bills_with_aggregates(qb, bills_df)

        if 'industry' in query_params:
            industry_filter = query_params['industry']
            bills_df = bills_df[bills_df['top_industry_tags'].apply(
                lambda tags: industry_filter in tags if isinstance(tags, list) else False
            )]

        if 'has_trade_correlations' in query_params:
            has_corr = query_params['has_trade_correlations'].lower() == 'true'
            if has_corr:
                bills_df = bills_df[bills_df['trade_correlations_count'] > 0]

        if 'min_cosponsors' in query_params:
            min_cosponsors = int(query_params['min_cosponsors'])
            bills_df = bills_df[bills_df['cosponsors_count'] >= min_cosponsors]

        # Apply final sorting
        if sort_by == 'latest_action_date':
            bills_df = bills_df.sort_values('latest_action_date', ascending=(sort_order == 'asc'))
        elif sort_by == 'cosponsors_count':
            bills_df = bills_df.sort_values('cosponsors_count', ascending=(sort_order == 'asc'))
        elif sort_by == 'trade_correlation_score':
            bills_df = bills_df.sort_values('trade_correlations_count', ascending=(sort_order == 'asc'))

        total_count = len(bills_df)
        paged_df = bills_df.iloc[offset:offset + limit]
        bills_data = paged_df.to_dict('records')

        # Map to Pydantic
        bills = []
        for row in bills_data:
            try:
                bills.append(Bill(
                    bill_id=row['bill_id'],
                    congress=int(row['congress']),
                    bill_type=row['bill_type'],
                    bill_number=int(row['bill_number']),
                    title=row.get('title') or row.get('short_title', 'Untitled Bill'),
                    introduced_date=row.get('introduced_date'),
                    sponsor_bioguide_id=row.get('sponsor_bioguide_id'),
                    sponsor_name=row.get('sponsor_name'),
                    sponsor_party=row.get('sponsor_party'),
                    sponsor_state=row.get('sponsor_state'),
                    cosponsors_count=int(row.get('cosponsors_count', 0)),
                    trade_correlations_count=int(row.get('trade_correlations_count', 0)),
                    top_industry_tags=row.get('top_industry_tags'),
                    latest_action_date=row.get('latest_action_date'),
                    latest_action_text=row.get('latest_action_text'),
                    days_since_action=row.get('days_since_action'),
                    congress_gov_url=row.get('congress_gov_url')
                ))
            except Exception as e:
                logger.warning(f"Error mapping bill {row.get('bill_id')}: {e}")
                continue

        # Pagination metadata
        has_next = (offset + len(bills)) < total_count
        has_prev = offset > 0
        
        base_url = "/v1/congress/bills"
        other_params = {k: v for k, v in query_params.items() if k not in ['limit', 'offset']}
        
        next_url = None
        if has_next:
            next_params = {**other_params, 'limit': limit, 'offset': offset + limit}
            next_url = f"{base_url}?{urlencode(next_params)}"
            
        prev_url = None
        if has_prev:
            prev_offset = max(0, offset - limit)
            prev_params = {**other_params, 'limit': limit, 'offset': prev_offset}
            prev_url = f"{base_url}?{urlencode(prev_params)}"

        pagination = PaginationMetadata(
            total=total_count,
            count=len(bills),
            limit=limit,
            offset=offset,
            has_next=has_next,
            has_prev=has_prev,
            next=next_url,
            prev=prev_url
        )
        
        paginated = PaginatedResponse(
            items=bills,
            pagination=pagination
        )
        
        return success_response(paginated.model_dump(), metadata={'cache_seconds': 300})

    except Exception as e:
        logger.error(f"Error fetching bills: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve bills",
            status_code=500,
            details=str(e)
        )

    except Exception as e:
        logger.error(f"Error fetching bills: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve bills",
            status_code=500,
            details=str(e)
        )
