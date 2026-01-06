#!/usr/bin/env python3
"""
Build static ISR (Incremental Static Regeneration) JSON files for bill detail pages.

Pre-generates bill detail JSON files for archived congresses (115-118) to enable
instant page loads without API calls. The output matches the API response schema
from GET /v1/congress/bills/{bill_id}.

Usage:
    python scripts/build_bill_detail_pages.py --congress 115 116 117 118
    python scripts/build_bill_detail_pages.py --congress 118 --limit 10  # Test mode
    python scripts/build_bill_detail_pages.py --dry-run  # Show what would be generated
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
import math
import pandas as pd
import boto3
from io import BytesIO
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def clean_nan(obj):
    """Replace NaN/Inf values with None for JSON serialization."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    elif isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    return obj


def read_parquet_from_s3(s3_client, prefix: str) -> pd.DataFrame:
    """Read all Parquet files from an S3 prefix."""
    logger.info(f"  Reading from s3://{BUCKET_NAME}/{prefix}")
    
    dfs = []
    paginator = s3_client.get_paginator('list_objects_v2')
    
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.parquet'):
                response = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
                df = pd.read_parquet(BytesIO(response['Body'].read()))
                dfs.append(df)
    
    if not dfs:
        return pd.DataFrame()
    
    return pd.concat(dfs, ignore_index=True)


class BillDetailBuilder:
    """Builds bill detail JSON files for ISR."""
    
    def __init__(self, s3_client):
        self.s3 = s3_client
        self._members_cache = None
        self._latest_actions_cache = None
    
    def get_members_df(self) -> pd.DataFrame:
        """Get cached member dimension table."""
        if self._members_cache is None:
            self._members_cache = read_parquet_from_s3(self.s3, 'silver/congress/dim_member/')
            if self._members_cache.empty:
                # Fallback to gold
                self._members_cache = read_parquet_from_s3(self.s3, 'gold/congress/dim_member/')
            logger.info(f"  Loaded {len(self._members_cache)} members")
        return self._members_cache
    
    def get_latest_actions_df(self) -> pd.DataFrame:
        """Get cached latest actions aggregate."""
        if self._latest_actions_cache is None:
            self._latest_actions_cache = read_parquet_from_s3(
                self.s3, 'gold/congress/agg_bill_latest_action/'
            )
        return self._latest_actions_cache
    
    def get_cosponsors(self, bill_id: str, congress: int) -> list:
        """Get cosponsors for a bill with member details."""
        try:
            # Read fact table for this bill
            fact_df = read_parquet_from_s3(
                self.s3, f'gold/congress/fact_member_bill_role/congress={congress}/'
            )
            
            if fact_df.empty:
                return []
            
            # Filter to cosponsors for this bill
            cosponsors_df = fact_df[
                (fact_df['bill_id'] == bill_id) & 
                (fact_df['is_cosponsor'] == True)
            ]
            
            if cosponsors_df.empty:
                return []
            
            # Get member details
            members_df = self.get_members_df()
            members_dict = {}
            if not members_df.empty and 'bioguide_id' in members_df.columns:
                members_dict = {row['bioguide_id']: row for _, row in members_df.iterrows()}
            
            # Build cosponsor list
            cosponsors = []
            for _, cosponsor in cosponsors_df.iterrows():
                bioguide_id = cosponsor['bioguide_id']
                member = members_dict.get(bioguide_id, {})
                
                cosponsors.append({
                    'bioguide_id': bioguide_id,
                    'name': member.get('name', 'Unknown') if hasattr(member, 'get') else 'Unknown',
                    'party': member.get('party', 'Unknown') if hasattr(member, 'get') else 'Unknown',
                    'state': member.get('state', 'Unknown') if hasattr(member, 'get') else 'Unknown',
                    'sponsored_date': str(cosponsor.get('action_date', '')),
                    'is_original': False
                })
            
            cosponsors.sort(key=lambda x: x['sponsored_date'], reverse=True)
            return cosponsors[:500]  # Max 500 cosponsors
            
        except Exception as e:
            logger.warning(f"Error fetching cosponsors for {bill_id}: {e}")
            return []
    
    def get_actions(self, bill_id: str, congress: int) -> list:
        """Get all actions for a bill."""
        try:
            actions_df = read_parquet_from_s3(
                self.s3, f'silver/congress/bill_actions/congress={congress}/'
            )
            
            if actions_df.empty:
                return []
            
            # Filter to this bill
            bill_actions = actions_df[actions_df['bill_id'] == bill_id].copy()
            
            if bill_actions.empty:
                return []
            
            # Sort by date descending
            if 'action_date' in bill_actions.columns:
                bill_actions['action_date'] = pd.to_datetime(bill_actions['action_date'], errors='coerce')
                bill_actions = bill_actions.sort_values('action_date', ascending=False)
            
            actions = []
            for _, action in bill_actions.iterrows():
                actions.append({
                    'action_date': str(action.get('action_date', ''))[:10] if pd.notna(action.get('action_date')) else '',
                    'action_text': str(action.get('action_text', '')),
                    'chamber': str(action.get('chamber', '')),
                    'action_code': str(action.get('action_code', '')),
                    'action_type': str(action.get('action_type', ''))
                })
            
            return actions
            
        except Exception as e:
            logger.warning(f"Error fetching actions for {bill_id}: {e}")
            return []
    
    def get_industry_tags(self, bill_id: str, congress: int) -> list:
        """Get industry tags for a bill."""
        try:
            tags_df = read_parquet_from_s3(
                self.s3, f'gold/congress/bill_industry_tags/congress={congress}/'
            )
            
            if tags_df.empty:
                return []
            
            # Filter to this bill
            bill_tags = tags_df[tags_df['bill_id'] == bill_id]
            
            if bill_tags.empty:
                return []
            
            # Group by industry
            industry_tags = {}
            for _, tag in bill_tags.iterrows():
                industry = tag['industry']
                if industry not in industry_tags:
                    industry_tags[industry] = {
                        'industry': industry,
                        'confidence': float(tag.get('confidence_score', 0.0)),
                        'tickers': [],
                        'keywords': []
                    }
                
                # Add tickers
                tickers_str = tag.get('tickers', '')
                if pd.notna(tickers_str) and tickers_str:
                    tickers = [t.strip() for t in str(tickers_str).split(',') if t.strip()]
                    industry_tags[industry]['tickers'].extend(tickers)
                
                # Add keywords
                keywords_str = tag.get('matched_keywords', '')
                if pd.notna(keywords_str) and keywords_str:
                    keywords = [k.strip() for k in str(keywords_str).split(',') if k.strip()]
                    industry_tags[industry]['keywords'].extend(keywords)
            
            # Dedupe and sort
            result = []
            for tag in industry_tags.values():
                tag['tickers'] = list(set(tag['tickers']))
                tag['keywords'] = list(set(tag['keywords']))[:10]
                result.append(tag)
            
            return sorted(result, key=lambda x: x['confidence'], reverse=True)
            
        except Exception as e:
            logger.warning(f"Error fetching industry tags for {bill_id}: {e}")
            return []
    
    def get_trade_correlations(self, bill_id: str, congress: int) -> list:
        """Get trade correlations for a bill."""
        try:
            corr_df = read_parquet_from_s3(
                self.s3, f'gold/congress/agg_bill_trade_correlation/congress={congress}/'
            )
            
            if corr_df.empty:
                return []
            
            # Filter to this bill
            bill_corr = corr_df[corr_df['bill_id'] == bill_id].copy()
            
            if bill_corr.empty:
                return []
            
            # Sort by score descending
            if 'correlation_score' in bill_corr.columns:
                bill_corr = bill_corr.sort_values('correlation_score', ascending=False)
            
            # Get member details
            members_df = self.get_members_df()
            members_dict = {}
            if not members_df.empty and 'bioguide_id' in members_df.columns:
                members_dict = {row['bioguide_id']: row for _, row in members_df.iterrows()}
            
            correlations = []
            for _, corr in bill_corr.head(20).iterrows():
                bioguide_id = corr.get('bioguide_id', '')
                member = members_dict.get(bioguide_id, {})
                
                correlations.append({
                    'member': {
                        'bioguide_id': bioguide_id,
                        'name': member.get('name', 'Unknown') if hasattr(member, 'get') else 'Unknown',
                        'party': member.get('party', 'Unknown') if hasattr(member, 'get') else 'Unknown',
                        'state': member.get('state', 'Unknown') if hasattr(member, 'get') else 'Unknown'
                    },
                    'ticker': str(corr.get('ticker', '')),
                    'trade_date': str(corr.get('trade_date', ''))[:10] if pd.notna(corr.get('trade_date')) else '',
                    'trade_type': str(corr.get('trade_type', '')),
                    'amount_range': str(corr.get('amount_range', '')),
                    'bill_action_date': str(corr.get('bill_action_date', ''))[:10] if pd.notna(corr.get('bill_action_date')) else '',
                    'days_offset': int(corr.get('days_offset', 0)) if pd.notna(corr.get('days_offset')) else 0,
                    'correlation_score': int(corr.get('correlation_score', 0)) if pd.notna(corr.get('correlation_score')) else 0,
                    'role': str(corr.get('member_role', '')),
                    'committee_overlap': bool(corr.get('committee_overlap', False)),
                    'match_type': str(corr.get('match_type', '')),
                    'matched_industries': str(corr.get('matched_industries', '')).split(',') if pd.notna(corr.get('matched_industries')) else []
                })
            
            return correlations
            
        except Exception as e:
            logger.warning(f"Error fetching trade correlations for {bill_id}: {e}")
            return []
    
    def build_bill_detail(self, bill: pd.Series) -> dict:
        """Build complete bill detail JSON for a single bill."""
        congress = int(bill['congress'])
        bill_type = str(bill['bill_type']).lower()
        bill_number = int(bill['bill_number'])
        bill_id = f"{congress}-{bill_type}-{bill_number}"
        
        # Get member details for sponsor
        sponsor_bioguide = bill.get('sponsor_bioguide_id', '')
        sponsor = {'bioguide_id': sponsor_bioguide, 'name': 'Unknown', 'party': 'Unknown', 'state': 'Unknown'}
        
        if sponsor_bioguide and pd.notna(sponsor_bioguide):
            members_df = self.get_members_df()
            if not members_df.empty and 'bioguide_id' in members_df.columns:
                sponsor_row = members_df[members_df['bioguide_id'] == sponsor_bioguide]
                if not sponsor_row.empty:
                    s = sponsor_row.iloc[0]
                    sponsor = {
                        'bioguide_id': sponsor_bioguide,
                        'name': s.get('name', 'Unknown') if hasattr(s, 'get') else str(s['name']) if 'name' in s.index else 'Unknown',
                        'party': s.get('party', 'Unknown') if hasattr(s, 'get') else str(s['party']) if 'party' in s.index else 'Unknown',
                        'state': s.get('state', 'Unknown') if hasattr(s, 'get') else str(s['state']) if 'state' in s.index else 'Unknown'
                    }
        
        # Get cosponsors
        cosponsors = self.get_cosponsors(bill_id, congress)
        
        # Get actions
        actions = self.get_actions(bill_id, congress)
        
        # Get industry tags
        industry_tags = self.get_industry_tags(bill_id, congress)
        
        # Get trade correlations
        trade_correlations = self.get_trade_correlations(bill_id, congress)
        
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
        
        # Build response matching API schema
        bill_dict = bill.to_dict()
        bill_dict['bill_id'] = bill_id
        
        response = {
            'bill': bill_dict,
            'sponsor': sponsor,
            'cosponsors': cosponsors,
            'cosponsors_count': len(cosponsors),
            'actions_recent': actions[:10],  # First 10 for display
            'actions': actions,  # Full list for ISR
            'actions_count_total': len(actions),
            'industry_tags': industry_tags,
            'trade_correlations': trade_correlations,
            'trade_correlations_count': len(trade_correlations),
            'committees': [],
            'related_bills': [],
            'congress_gov_url': congress_gov_url,
            'isr_generated_at': datetime.utcnow().isoformat()
        }
        
        return clean_nan(response)


def main():
    parser = argparse.ArgumentParser(description='Build ISR JSON files for bill detail pages')
    parser.add_argument('--congress', type=int, nargs='+', default=[115, 116, 117, 118],
                        help='Congress numbers to process (default: 115 116 117 118)')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limit bills per congress (0 = no limit)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be generated without writing')
    parser.add_argument('--output-dir', type=str, default='website/data/bill_details',
                        help='Output directory for JSON files')
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("Building ISR Bill Detail Pages")
    logger.info("=" * 80)
    logger.info(f"Congresses: {args.congress}")
    logger.info(f"Limit per congress: {args.limit if args.limit else 'none'}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("")
    
    s3 = boto3.client('s3')
    builder = BillDetailBuilder(s3)
    
    output_base = Path(args.output_dir)
    total_generated = 0
    total_errors = 0
    
    for congress in args.congress:
        logger.info(f"\n📋 Processing Congress {congress}...")
        
        # Read bills for this congress
        bills_df = read_parquet_from_s3(s3, f'gold/congress/dim_bill/congress={congress}/')
        
        if bills_df.empty:
            logger.warning(f"  No bills found for Congress {congress}")
            continue
        
        logger.info(f"  Found {len(bills_df)} bills")
        
        # Apply limit if specified
        if args.limit > 0:
            bills_df = bills_df.head(args.limit)
            logger.info(f"  Limited to {len(bills_df)} bills")
        
        congress_generated = 0
        congress_errors = 0
        
        for idx, bill in bills_df.iterrows():
            bill_type = str(bill['bill_type']).lower()
            bill_number = int(bill['bill_number'])
            bill_id = f"{congress}-{bill_type}-{bill_number}"
            
            try:
                if args.dry_run:
                    output_path = output_base / str(congress) / bill_type / f"{bill_number}.json"
                    logger.info(f"  [DRY RUN] Would generate: {output_path}")
                    congress_generated += 1
                else:
                    # Build bill detail
                    detail = builder.build_bill_detail(bill)
                    
                    # Create output directory
                    output_dir = output_base / str(congress) / bill_type
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Write JSON file
                    output_path = output_dir / f"{bill_number}.json"
                    with open(output_path, 'w') as f:
                        json.dump(detail, f, default=str, separators=(',', ':'))
                    
                    congress_generated += 1
                    
                    if congress_generated % 100 == 0:
                        logger.info(f"  Generated {congress_generated} bills...")
                        
            except Exception as e:
                logger.error(f"  Error processing {bill_id}: {e}")
                congress_errors += 1
        
        logger.info(f"  ✅ Congress {congress}: {congress_generated} generated, {congress_errors} errors")
        total_generated += congress_generated
        total_errors += congress_errors
    
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"✅ ISR Generation Complete!")
    logger.info(f"   Total generated: {total_generated}")
    logger.info(f"   Total errors: {total_errors}")
    logger.info(f"   Output directory: {args.output_dir}")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
