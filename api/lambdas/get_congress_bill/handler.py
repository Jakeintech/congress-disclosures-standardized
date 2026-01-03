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
import pandas as pd
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    clean_nan_values
)
from api.lib.response_models import (
    BillDetail,
    Bill,
    Member,
    BillAction,
    BillIndustryTag,
    BillTradeCorrelation,
    BillCommittee,
    RelatedBill,
    BillTitle
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def get_cosponsors(qb, bill_id, congress):
    """Get cosponsors for a bill with member details."""
    try:
        try:
            cosponsors_df = qb.query_parquet(
                'gold/congress/fact_member_bill_role',
                filters={'bill_id': bill_id},
                limit=500
            )
        except Exception as e:
            logger.warning(f"Cosponsors table not found or query failed: {e}")
            return []

        if cosponsors_df.empty:
            return []

        # Get member details efficiently with filter
        bioguide_ids = cosponsors_df['bioguide_id'].unique().tolist()
        members_df = qb.query_parquet(
            'silver/congress/dim_member',
            filters={'bioguide_id': {'in': bioguide_ids}},
            limit=len(bioguide_ids)
        )

        members_dict = {}
        if not members_df.empty and 'bioguide_id' in members_df.columns:
            members_dict = {row['bioguide_id']: row for _, row in members_df.iterrows()}

        # Build cosponsor list as Member models
        cosponsors = []
        for _, cosponsor in cosponsors_df.iterrows():
            bioguide_id = cosponsor['bioguide_id']
            member_data = members_dict.get(bioguide_id, {})

            try:
                cosponsors.append(Member(
                    bioguide_id=bioguide_id,
                    name=member_data.get('name', 'Unknown'),
                    first_name=member_data.get('first_name'),
                    last_name=member_data.get('last_name'),
                    party=member_data.get('party', 'Unknown'),
                    state=member_data.get('state', 'Unknown'),
                    chamber=member_data.get('chamber', 'house')
                ))
            except Exception as e:
                logger.warning(f"Error mapping cosponsor {bioguide_id}: {e}")
                continue

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

        try:
            actions_df = qb.query_parquet(
                'silver/congress/bill_actions',
                filters={'bill_id': bill_id},
                order_by='action_date DESC',
                limit=500 if include_all else limit
            )
        except Exception as e:
            logger.warning(f"Actions table not found or query failed: {e}")
            return []

        if actions_df.empty:
            return []

        actions = []
        for _, action in actions_df.iterrows():
            try:
                actions.append(BillAction(
                    action_date=str(action.get('action_date', '')),
                    action_text=action.get('action_text', ''),
                    chamber=action.get('chamber'),
                    action_code=action.get('action_code'),
                    action_type=action.get('action_type')
                ))
            except Exception as e:
                logger.warning(f"Error mapping action: {e}")
                continue

        return actions

    except Exception as e:
        logger.error(f"Error fetching actions: {e}")
        return []


def get_industry_tags(qb, bill_id):
    """Get industry tags for a bill."""
    try:
        filters = {'bill_id': bill_id}
        try:
            tags_df = qb.query_parquet(
                'gold/congress/bill_industry_tags',
                filters=filters,
                order_by='confidence_score DESC',
                limit=10
            )
        except Exception as e:
            logger.warning(f"Industry tags table not found or query failed: {e}")
            return []

        if tags_df.empty:
            return []

        # Group by industry to aggregate tickers
        industry_tags = {}
        for _, tag in tags_df.iterrows():
            industry = tag['industry']
            if industry not in industry_tags:
                industry_tags[industry] = {
                    'industry': industry,
                    'confidence': float(tag.get('confidence_score', 0.0)),
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
        for tag_data in industry_tags.values():
            try:
                result.append(BillIndustryTag(
                    industry=tag_data['industry'],
                    confidence=tag_data['confidence'],
                    tickers=list(set(tag_data['tickers'])),
                    keywords=list(set(tag_data['keywords']))[:10]
                ))
            except Exception as e:
                logger.warning(f"Error mapping industry tag: {e}")
                continue

        return sorted(result, key=lambda x: x.confidence, reverse=True)

    except Exception as e:
        logger.error(f"Error fetching industry tags: {e}")
        return []


def get_trade_correlations(qb, bill_id, limit=20):
    """Get trade correlations for a bill."""
    try:
        filters = {'bill_id': bill_id}
        try:
            corr_df = qb.query_parquet(
                'gold/congress/agg_bill_trade_correlation',
                filters=filters,
                order_by='correlation_score DESC',
                limit=limit
            )
        except Exception as e:
            logger.warning(f"Trade correlation table not found or query failed: {e}")
            return []

        if corr_df.empty:
            return []

        # Get member details efficiently with filter
        bioguide_ids = corr_df['bioguide_id'].unique().tolist()
        members_df = qb.query_parquet(
            'silver/congress/dim_member',
            filters={'bioguide_id': {'in': bioguide_ids}},
            limit=len(bioguide_ids)
        )

        members_dict = {}
        if not members_df.empty and 'bioguide_id' in members_df.columns:
            members_dict = {row['bioguide_id']: row for _, row in members_df.iterrows()}

        # Build correlations list
        correlations = []
        for _, corr in corr_df.iterrows():
            bioguide_id = corr['bioguide_id']
            member_data = members_dict.get(bioguide_id, {})

            try:
                member = Member(
                    bioguide_id=bioguide_id,
                    name=member_data.get('name', 'Unknown'),
                    party=member_data.get('party', 'Unknown'),
                    state=member_data.get('state', 'Unknown'),
                    chamber=member_data.get('chamber', 'house')
                )
                
                correlations.append(BillTradeCorrelation(
                    member=member,
                    ticker=corr.get('ticker', ''),
                    trade_date=str(corr.get('trade_date', '')),
                    trade_type=corr.get('trade_type', ''),
                    amount_range=corr.get('amount_range'),
                    bill_action_date=str(corr.get('bill_action_date', '')),
                    days_offset=int(corr.get('days_offset', 0)),
                    correlation_score=int(corr.get('correlation_score', 0)),
                    role=corr.get('member_role'),
                    committee_overlap=bool(corr.get('committee_overlap', False)),
                    match_type=corr.get('match_type')
                ))
            except Exception as e:
                logger.warning(f"Error mapping trade correlation for {bioguide_id}: {e}")
                continue

        return correlations

    except Exception as e:
        logger.error(f"Error fetching trade correlations: {e}")
        return []


def get_committees(qb, bill_id):
    """Get committee assignments for a bill."""
    try:
        filters = {'bill_id': bill_id}
        # Try Gold first, fall back to Silver
        try:
            committees_df = qb.query_parquet(
                'gold/congress/fact_bill_committees',
                filters=filters
            )
        except Exception:
            try:
                committees_df = qb.query_parquet(
                    'silver/congress/bill_committees',
                    filters=filters
                )
            except Exception as e:
                logger.warning(f"Committees tables not found: {e}")
                return []

        if committees_df.empty:
            return []

        committees = []
        for _, row in committees_df.iterrows():
            try:
                committees.append(BillCommittee(
                    system_code=row.get('system_code', ''),
                    name=row.get('name', ''),
                    chamber=row.get('chamber', ''),
                    activity=row.get('activity', []) if isinstance(row.get('activity'), list) else []
                ))
            except Exception as e:
                logger.warning(f"Error mapping committee: {e}")
                continue
        return committees
    except Exception as e:
        logger.warning(f"Error fetching committees: {e}")
        return []

def get_related_bills(qb, bill_id):
    """Get related bills."""
    try:
        filters = {'bill_id': bill_id}
        try:
            related_df = qb.query_parquet(
                'silver/congress/related_bills',
                filters=filters
            )
        except Exception as e:
            logger.warning(f"Related bills table not found: {e}")
            return []
        
        if related_df.empty:
            return []
            
        related = []
        for _, row in related_df.iterrows():
            try:
                related.append(RelatedBill(
                    related_bill_id=row.get('related_bill_id', ''),
                    title=row.get('title', ''),
                    type=row.get('relationship_type', ''),
                    identified_by=row.get('identified_by')
                ))
            except Exception as e:
                logger.warning(f"Error mapping related bill: {e}")
                continue
        return related
    except Exception as e:
        logger.warning(f"Error fetching related bills: {e}")
        return []

def get_titles(qb, bill_id):
    """Get all titles for a bill."""
    try:
        filters = {'bill_id': bill_id}
        try:
            titles_df = qb.query_parquet(
                'silver/congress/bill_titles',
                filters=filters
            )
        except Exception as e:
            logger.warning(f"Titles table not found: {e}")
            return []
        
        if titles_df.empty:
            return []
            
        titles = []
        for _, row in titles_df.iterrows():
            try:
                titles.append(BillTitle(
                    title=row.get('title', ''),
                    type=row.get('title_type', ''),
                    chamber=row.get('chamber')
                ))
            except Exception as e:
                logger.warning(f"Error mapping title: {e}")
                continue
        return titles
    except Exception as e:
        logger.warning(f"Error fetching titles: {e}")
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
        # Extract params from path
        path_params = event.get('pathParameters') or {}
        
        # Support both formats:
        # 1. /v1/congress/bills/{bill_id} (legacy/internal)
        # 2. /v1/congress/bills/{congress}/{type}/{number} (standardized)
        bill_id = path_params.get('bill_id', '')
        
        if not bill_id:
            congress_str = path_params.get('congress')
            bill_type = path_params.get('type')
            bill_number_str = path_params.get('number')
            
            if congress_str and bill_type and bill_number_str:
                bill_id = f"{congress_str}-{bill_type}-{bill_number_str}"
            else:
                return error_response(
                    message="Missing path parameters",
                    status_code=400
                )

        # Parse bill_id: "118-hr-1" -> congress=118, bill_type=hr, bill_number=1
        parts = bill_id.split('-')
        if len(parts) != 3:
            # Fallback for direct path param usage if somehow not reconstructed
            congress_str = path_params.get('congress')
            bill_type = path_params.get('type')
            bill_number_str = path_params.get('number')
            if congress_str and bill_type and bill_number_str:
                parts = [congress_str, bill_type, bill_number_str]
            else:
                return error_response(
                    message="Invalid bill_id format. Expected: congress-type-number (e.g., 118-hr-1)",
                    status_code=400
                )

        try:
            congress = int(parts[0])
            bill_type = parts[1].lower()
            bill_number = int(parts[2])
            # Reconstruct canonical bill_id
            bill_id = f"{congress}-{bill_type}-{bill_number}"
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

        # Map bill to Pydantic model
        bill_model = Bill(
            bill_id=bill_id,
            congress=int(bill['congress']),
            bill_type=bill['bill_type'],
            bill_number=int(bill['bill_number']),
            title=bill.get('title') or bill.get('short_title', 'Untitled Bill'),
            introduced_date=bill.get('introduced_date'),
            sponsor_bioguide_id=bill.get('sponsor_bioguide_id'),
            sponsor_name=bill.get('sponsor_name'),
            sponsor_party=bill.get('sponsor_party'),
            sponsor_state=bill.get('sponsor_state')
        )

        # Get sponsor details
        sponsor_bioguide = bill.get('sponsor_bioguide_id')
        sponsor_model = None

        if sponsor_bioguide:
            try:
                try:
                    sponsor_df = qb.query_parquet(
                        'silver/congress/dim_member',
                        filters=None,
                        limit=1000
                    )
                except Exception as e:
                    logger.warning(f"Sponsor member table not found: {e}")
                    sponsor_df = pd.DataFrame()
                if not sponsor_df.empty and 'bioguide_id' in sponsor_df.columns:
                    sponsor_row = sponsor_df[sponsor_df['bioguide_id'] == sponsor_bioguide]
                    if not sponsor_row.empty:
                        s = sponsor_row.iloc[0]
                        sponsor_model = Member(
                            bioguide_id=sponsor_bioguide,
                            name=s.get('name', 'Unknown'),
                            first_name=s.get('first_name'),
                            last_name=s.get('last_name'),
                            party=s.get('party', 'Unknown'),
                            state=s.get('state', 'Unknown'),
                            chamber=s.get('chamber', 'house')
                        )
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

        # Build BillDetail response
        bill_detail = BillDetail(
            bill=bill_model,
            sponsor=sponsor_model,
            cosponsors=cosponsors,
            cosponsors_count=cosponsors_count,
            actions_recent=actions_recent,
            actions_count_total=actions_count_total,
            industry_tags=industry_tags,
            trade_correlations=trade_correlations,
            trade_correlations_count=trade_correlations_count,
            committees=get_committees(qb, bill_id),
            related_bills=get_related_bills(qb, bill_id),
            titles=get_titles(qb, bill_id),
            congress_gov_url=congress_gov_url
        )

        # Determine cache duration (archived congresses get longer cache)
        cache_max_age = 86400 if congress <= 118 else 300

        return success_response(
            data=bill_detail.model_dump(),
            metadata={
                'bill_id': bill_id,
                'cached': congress <= 118,
                'cache_max_age': cache_max_age
            }
        )

    except Exception as e:
        logger.error(f"Error fetching bill: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve bill",
            status_code=500,
            details=str(e)
        )
