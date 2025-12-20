"""
Lambda handler: GET /v1/congress/bills

List Congress bills with enhanced sorting, filtering, and enriched data.
Supports industry filters, trade correlation filters, and multiple sort options.
"""

import os
import json
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    parse_pagination_params,
    build_pagination_response
)

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

    Query parameters:
    - limit: Records per page (default 50, max 500)
    - offset: Records to skip (default 0)
    - congress: Filter by congress number (e.g., '118', '119')
    - bill_type: Filter by bill type (e.g., 'hr', 's', 'hres')
    - sponsor: Filter by sponsor name (partial match)
    - industry: Filter by industry tag (e.g., 'Defense', 'Healthcare')
    - has_trade_correlations: Boolean, only show bills with correlations (true/false)
    - min_cosponsors: Minimum number of cosponsors (integer)
    - sponsor_bioguide: Filter by sponsor bioguide_id
    - cosponsor_bioguide: Filter by cosponsor bioguide_id
    - sort_by: Sort field (latest_action_date, cosponsors_count, trade_correlation_score, introduced_date)
    - sort_order: Sort direction (asc/desc, default desc)

    Returns paginated list of bills with enriched data.
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

        # Build S3 prefix for partition pruning
        s3_prefix = 'gold/congress/dim_bill'

        # Determine base ordering
        if sort_by == 'introduced_date':
            base_order = 'introduced_date DESC' if sort_order == 'desc' else 'introduced_date ASC'
        else:
            base_order = 'congress DESC, bill_number DESC'

        # Query bills (get more than needed for post-filtering)
        query_limit = min(limit * 3, 1500)  # Get extra for filtering

        try:
            bills_df = qb.query_parquet(
                s3_prefix,
                filters=filters if filters else None,
                order_by=base_order,
                limit=query_limit,
                offset=0  # Don't apply offset yet, do it after enrichment
            )
        except Exception as e:
            # Handle missing dim_bill data gracefully (e.g., during initial setup)
            logger.warning(f"No bills data available: {e}")
            bills_df = None

        if bills_df is None or bills_df.empty:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Cache-Control': 'public, max-age=300'
                },
                'body': json.dumps({
                    'bills': [],
                    'total_count': 0,
                    'limit': limit,
                    'offset': offset,
                    'has_next': False,
                    'has_previous': False
                })
            }

        # Filter by sponsor name if specified (text search)
        if 'sponsor' in query_params:
            sponsor_filter = query_params['sponsor'].lower()
            if 'sponsor_name' in bills_df.columns:
                bills_df = bills_df[
                    bills_df['sponsor_name'].str.lower().str.contains(sponsor_filter, na=False)
                ]

        # Enrich bills with aggregates
        bills_df = enrich_bills_with_aggregates(qb, bills_df)

        # Apply post-enrichment filters
        if 'industry' in query_params:
            industry_filter = query_params['industry']
            bills_df = bills_df[
                bills_df['top_industry_tags'].apply(
                    lambda tags: industry_filter in tags if isinstance(tags, list) else False
                )
            ]

        if 'has_trade_correlations' in query_params:
            has_corr = query_params['has_trade_correlations'].lower() == 'true'
            if has_corr:
                bills_df = bills_df[bills_df['trade_correlations_count'] > 0]

        if 'min_cosponsors' in query_params:
            min_cosponsors = int(query_params['min_cosponsors'])
            bills_df = bills_df[bills_df['cosponsors_count'] >= min_cosponsors]

        if 'cosponsor_bioguide' in query_params:
            # Need to query fact table for this
            cosponsor_bioguide = query_params['cosponsor_bioguide']
            try:
                cosponsor_bills_df = qb.query_parquet(
                    'gold/congress/fact_member_bill_role',
                    filters={'bioguide_id': cosponsor_bioguide, 'is_cosponsor': True},
                    limit=1000
                )
                if not cosponsor_bills_df.empty:
                    cosponsor_bill_ids = cosponsor_bills_df['bill_id'].unique()
                    bills_df = bills_df[bills_df['bill_id'].isin(cosponsor_bill_ids)]
            except Exception as e:
                logger.warning(f"Could not filter by cosponsor: {e}")

        # Apply sorting
        if sort_by == 'latest_action_date':
            bills_df = bills_df.sort_values('latest_action_date', ascending=(sort_order == 'asc'))
        elif sort_by == 'cosponsors_count':
            bills_df = bills_df.sort_values('cosponsors_count', ascending=(sort_order == 'asc'))
        elif sort_by == 'trade_correlation_score':
            bills_df = bills_df.sort_values('trade_correlations_count', ascending=(sort_order == 'asc'))
        elif sort_by == 'introduced_date':
            # Already sorted in base query
            pass

        # Get total count before pagination
        total_count = len(bills_df)

        # Apply pagination
        bills_df = bills_df.iloc[offset:offset + limit]

        bills_list = bills_df.to_dict('records')

        response = build_pagination_response(
            data=bills_list,
            total_count=total_count,
            limit=limit,
            offset=offset,
            base_url='/v1/congress/bills',
            query_params={k: v for k, v in query_params.items() if k not in ['limit', 'offset']}
        )

        return success_response(response, metadata={'cache_seconds': 300})

    except Exception as e:
        logger.error(f"Error fetching bills: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve bills",
            status_code=500,
            details=str(e)
        )
