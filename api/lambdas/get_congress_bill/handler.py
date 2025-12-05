"""
Lambda handler: GET /v1/congress/bills/{bill_id}

Get single bill details by ID with full enhancements:
- Cosponsors list with member details
- Recent actions timeline
- Industry tags and tickers
- Trade correlations
- Committee assignments
"""

import os
import json
import logging
import math
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def clean_nan(obj):
    """Replace NaN/Inf values with None for JSON serialization."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    elif isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    return obj


def get_cosponsors(qb, bill_id, congress):
    """Get cosponsors for a bill with member details."""
    try:
        # Get cosponsor relationships from fact table
        filters = {'bill_id': bill_id, 'is_cosponsor': True}
        cosponsors_df = qb.query_parquet(
            'gold/congress/fact_member_bill_role',
            filters=filters,
            limit=500  # Max 500 cosponsors
        )

        if cosponsors_df.empty:
            return []

        # Get member details
        bioguide_ids = cosponsors_df['bioguide_id'].unique().tolist()
        members_df = qb.query_parquet(
            'silver/congress/dim_member',
            filters=None,  # Read all, filter in memory
            limit=1000
        )

        # Filter to requested bioguides
        if not members_df.empty and 'bioguide_id' in members_df.columns:
            members_df = members_df[members_df['bioguide_id'].isin(bioguide_ids)]
            members_dict = {row['bioguide_id']: row for _, row in members_df.iterrows()}
        else:
            members_dict = {}

        # Build cosponsor list with member details
        cosponsors = []
        for _, cosponsor in cosponsors_df.iterrows():
            bioguide_id = cosponsor['bioguide_id']
            member = members_dict.get(bioguide_id, {})

            cosponsors.append({
                'bioguide_id': bioguide_id,
                'name': member.get('name', 'Unknown'),
                'party': member.get('party', 'Unknown'),
                'state': member.get('state', 'Unknown'),
                'sponsored_date': str(cosponsor.get('action_date', '')),
                'is_original': False  # TODO: Add is_original_cosponsor field
            })

        # Sort by sponsored date
        cosponsors.sort(key=lambda x: x['sponsored_date'], reverse=True)

        return cosponsors

    except Exception as e:
        logger.error(f"Error fetching cosponsors: {e}")
        return []


def get_recent_actions(qb, bill_id, limit=10, include_all=False):
    """Get recent actions for a bill."""
    try:
        # Parse bill_id to get congress
        parts = bill_id.split('-')
        if len(parts) != 3:
            return []
        congress = int(parts[0])

        # Query bill actions
        filters = {'bill_id': bill_id}
        actions_df = qb.query_parquet(
            'silver/congress/bill_actions',
            filters=filters,
            order_by='action_date DESC',
            limit=500 if include_all else limit
        )

        if actions_df.empty:
            return []

        actions = []
        for _, action in actions_df.iterrows():
            actions.append({
                'action_date': str(action.get('action_date', '')),
                'action_text': action.get('action_text', ''),
                'chamber': action.get('chamber', ''),
                'action_code': action.get('action_code', ''),
                'action_type': action.get('action_type', '')
            })

        return actions

    except Exception as e:
        logger.error(f"Error fetching actions: {e}")
        return []


def get_industry_tags(qb, bill_id):
    """Get industry tags for a bill."""
    try:
        filters = {'bill_id': bill_id}
        tags_df = qb.query_parquet(
            'gold/congress/bill_industry_tags',
            filters=filters,
            order_by='confidence_score DESC',
            limit=10
        )

        if tags_df.empty:
            return []

        # Group by industry to aggregate tickers
        industry_tags = {}
        for _, tag in tags_df.iterrows():
            industry = tag['industry']
            if industry not in industry_tags:
                industry_tags[industry] = {
                    'industry': industry,
                    'confidence': tag.get('confidence_score', 0.0),
                    'tickers': [],
                    'keywords': tag.get('matched_keywords', '').split(',') if tag.get('matched_keywords') else []
                }

            # Add tickers
            tickers_str = tag.get('tickers', '')
            if tickers_str:
                tickers = [t.strip() for t in tickers_str.split(',') if t.strip()]
                industry_tags[industry]['tickers'].extend(tickers)

        # Convert to list and dedupe tickers
        result = []
        for tag in industry_tags.values():
            tag['tickers'] = list(set(tag['tickers']))
            tag['keywords'] = list(set(tag['keywords']))[:10]  # Limit keywords
            result.append(tag)

        return sorted(result, key=lambda x: x['confidence'], reverse=True)

    except Exception as e:
        logger.error(f"Error fetching industry tags: {e}")
        return []


def get_trade_correlations(qb, bill_id, limit=20):
    """Get trade correlations for a bill."""
    try:
        filters = {'bill_id': bill_id}
        corr_df = qb.query_parquet(
            'gold/congress/agg_bill_trade_correlation',
            filters=filters,
            order_by='correlation_score DESC',
            limit=limit
        )

        if corr_df.empty:
            return []

        # Get member details for correlations
        bioguide_ids = corr_df['bioguide_id'].unique().tolist()
        members_df = qb.query_parquet(
            'silver/congress/dim_member',
            filters=None,
            limit=1000
        )

        members_dict = {}
        if not members_df.empty and 'bioguide_id' in members_df.columns:
            members_df = members_df[members_df['bioguide_id'].isin(bioguide_ids)]
            members_dict = {row['bioguide_id']: row for _, row in members_df.iterrows()}

        # Build correlations list
        correlations = []
        for _, corr in corr_df.iterrows():
            bioguide_id = corr['bioguide_id']
            member = members_dict.get(bioguide_id, {})

            correlations.append({
                'member': {
                    'bioguide_id': bioguide_id,
                    'name': member.get('name', 'Unknown'),
                    'party': member.get('party', 'Unknown'),
                    'state': member.get('state', 'Unknown')
                },
                'ticker': corr.get('ticker', ''),
                'trade_date': str(corr.get('trade_date', '')),
                'trade_type': corr.get('trade_type', ''),
                'amount_range': corr.get('amount_range', ''),
                'bill_action_date': str(corr.get('bill_action_date', '')),
                'days_offset': int(corr.get('days_offset', 0)),
                'correlation_score': int(corr.get('correlation_score', 0)),
                'role': corr.get('member_role', ''),
                'committee_overlap': bool(corr.get('committee_overlap', False)),
                'match_type': corr.get('match_type', ''),
                'matched_industries': corr.get('matched_industries', '').split(',') if corr.get('matched_industries') else []
            })

        return correlations

    except Exception as e:
        logger.error(f"Error fetching trade correlations: {e}")
        return []


def handler(event, context):
    """
    GET /v1/congress/bills/{bill_id}

    Path parameter:
    - bill_id: Bill ID in format "congress-type-number" (e.g., "118-hr-1")

    Query parameters:
    - include_all_actions: If true, return all actions (default: false, returns 10)

    Returns comprehensive bill details including:
    - Bill metadata
    - Sponsor info
    - Cosponsors list
    - Recent actions
    - Industry tags
    - Trade correlations
    - Committee assignments
    """
    try:
        # Extract bill_id from path
        path_params = event.get('pathParameters') or {}
        bill_id = path_params.get('bill_id', '')

        if not bill_id:
            return error_response(
                message="Missing bill_id parameter",
                status_code=400
            )

        # Parse bill_id: "118-hr-1" -> congress=118, bill_type=hr, bill_number=1
        parts = bill_id.split('-')
        if len(parts) != 3:
            return error_response(
                message="Invalid bill_id format. Expected: congress-type-number (e.g., 118-hr-1)",
                status_code=400
            )

        try:
            congress = int(parts[0])
            bill_type = parts[1].lower()
            bill_number = int(parts[2])
        except ValueError:
            return error_response(
                message="Invalid bill_id format",
                status_code=400
            )

        # Query parameters
        query_params = event.get('queryStringParameters') or {}
        include_all_actions = query_params.get('include_all_actions', '').lower() == 'true'

        logger.info(f"Fetching bill: {bill_id}, include_all_actions={include_all_actions}")

        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)

        # Query bill metadata
        filters = {
            'congress': congress,
            'bill_type': bill_type,
            'bill_number': bill_number
        }

        bills_df = qb.query_parquet(
            'gold/congress/dim_bill',
            filters=filters,
            limit=1
        )

        if bills_df.empty:
            return error_response(
                message=f"Bill not found: {bill_id}",
                status_code=404
            )

        bill = bills_df.iloc[0].to_dict()
        bill['bill_id'] = bill_id

        # Get sponsor details
        sponsor_bioguide = bill.get('sponsor_bioguide_id')
        sponsor = {'bioguide_id': sponsor_bioguide, 'name': 'Unknown', 'party': 'Unknown', 'state': 'Unknown'}

        if sponsor_bioguide:
            try:
                sponsor_df = qb.query_parquet(
                    'silver/congress/dim_member',
                    filters=None,
                    limit=1000
                )
                if not sponsor_df.empty and 'bioguide_id' in sponsor_df.columns:
                    sponsor_row = sponsor_df[sponsor_df['bioguide_id'] == sponsor_bioguide]
                    if not sponsor_row.empty:
                        s = sponsor_row.iloc[0]
                        sponsor = {
                            'bioguide_id': sponsor_bioguide,
                            'name': s.get('name', 'Unknown'),
                            'party': s.get('party', 'Unknown'),
                            'state': s.get('state', 'Unknown')
                        }
            except Exception as e:
                logger.error(f"Error fetching sponsor: {e}")

        # Get cosponsors
        cosponsors = get_cosponsors(qb, bill_id, congress)
        cosponsors_count = len(cosponsors)

        # Get actions
        actions_recent = get_recent_actions(qb, bill_id, limit=10, include_all=include_all_actions)
        actions_count_total = len(actions_recent) if include_all_actions else 0

        # Get industry tags
        industry_tags = get_industry_tags(qb, bill_id)

        # Get trade correlations
        trade_correlations = get_trade_correlations(qb, bill_id, limit=20)
        trade_correlations_count = len(trade_correlations)

        # Build Congress.gov URL
        bill_type_map = {
            'hr': 'house-bill',
            's': 'senate-bill',
            'hjres': 'house-joint-resolution',
            'sjres': 'senate-joint-resolution',
            'hconres': 'house-concurrent-resolution',
            'sconres': 'senate-concurrent-resolution',
            'hres': 'house-resolution',
            'sres': 'senate-resolution'
        }
        bill_type_url = bill_type_map.get(bill_type, bill_type)
        congress_gov_url = f"https://www.congress.gov/bill/{congress}th-congress/{bill_type_url}/{bill_number}"

        # Build response
        response_data = {
            'bill': bill,
            'sponsor': sponsor,
            'cosponsors': cosponsors,
            'cosponsors_count': cosponsors_count,
            'actions_recent': actions_recent,
            'actions_count_total': actions_count_total,
            'industry_tags': industry_tags,
            'trade_correlations': trade_correlations,
            'trade_correlations_count': trade_correlations_count,
            'committees': [],  # TODO: Add committee data when available
            'related_bills': [],  # TODO: Add related bills when available
            'congress_gov_url': congress_gov_url
        }

        # Determine cache duration (archived congresses get longer cache)
        cache_max_age = 86400 if congress <= 118 else 300  # 24h for archived, 5min for current

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': f'public, max-age={cache_max_age}'
            },
            'body': json.dumps(clean_nan(response_data), default=str)
        }

    except Exception as e:
        logger.error(f"Error fetching bill: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve bill",
            status_code=500,
            details=str(e)
        )
