#!/usr/bin/env python3
"""
Build static JSON profiles for every Congress member.
ISR (Incremental Static Regeneration) style for website performance.

Reads:
- Silver: dim_member (bio, terms), dim_bill (titles)
- Gold: fact_member_bill_role (sponsorships), fact_member_bill_trade_window (trades)

Writes:
- S3: website/data/member_profiles/{bioguide_id}.json
"""

import sys
import os
import json
import logging
import boto3
import pandas as pd
from io import BytesIO
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def read_parquet_s3(s3_client, prefix):
    """Read all parquet files from prefix into DataFrame."""
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    if 'Contents' not in response:
        return pd.DataFrame()
    
    dfs = []
    for obj in response['Contents']:
        if obj['Key'].endswith('.parquet'):
            resp = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
            dfs.append(pd.read_parquet(BytesIO(resp['Body'].read())))
            
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def build_profiles():
    s3 = boto3.client('s3')
    
    logger.info("📦 Loading data for profile generation...")
    
    # 1. Load Members
    members_df = read_parquet_s3(s3, 'silver/congress/dim_member/')
    if members_df.empty:
        logger.error("No members found")
        return

    # 2. Load Bills (for titles)
    bills_df = read_parquet_s3(s3, 'silver/congress/dim_bill/')
    bill_titles = {}
    if not bills_df.empty:
        # Create fallback ID if bill_id missing
        if 'bill_id' not in bills_df.columns:
            bills_df['bill_id'] = bills_df.apply(lambda x: f"{x.get('congress')}-{x.get('bill_type')}-{x.get('bill_number')}", axis=1)
            
        bill_titles = bills_df.set_index('bill_id')[['title', 'introduced_date', 'policy_area']].to_dict('index')
    
    # 3. Load Roles (Sponsorships)
    roles_df = read_parquet_s3(s3, 'gold/congress/fact_member_bill_role/')
    
    # 4. Load Trade Windows
    trades_df = read_parquet_s3(s3, 'gold/analytics/fact_member_bill_trade_window/')
    
    logger.info(f"Loaded: {len(members_df)} members, {len(bills_df)} bills, {len(roles_df)} roles")
    
    # Group roles by member
    member_roles = {}
    if not roles_df.empty:
        for mid, group in roles_df.groupby('bioguide_id'):
            member_roles[mid] = group.to_dict('records')
            
    # Group trades by bill
    bill_trades = {}
    if not trades_df.empty:
        for bid, group in trades_df.groupby('bill_id'):
            bill_trades[bid] = group.to_dict('records')

    def generate_profile(member):
        mid = member['bioguide_id']
        
        # Get bills
        roles = member_roles.get(mid, [])
        my_bills = []
        
        for r in roles:
            bid = r.get('bill_id')
            bill_info = bill_titles.get(bid, {})
            
            # Check for trades on this bill (by anyone, or just this member? Context implies member's trades)
            # Actually fact_member_bill_trade_window is per member-bill-trade.
            # We want trades *by this member* on *this bill*.
            # The trade window table has bioguide_id.
            
            member_bill_trades = []
            if not trades_df.empty:
                # Optimized filtering later, for now simple:
                member_bill_trades = [t for t in bill_trades.get(bid, []) if t.get('bioguide_id') == mid]

            if not bill_info.get('title'):
                continue # Skip bills without titles (bad data)

            my_bills.append({
                'bill_id': bid,
                'title': bill_info.get('title'),
                'introduced_date': bill_info.get('introduced_date'),
                'policy_area': bill_info.get('policy_area'),
                'role': r.get('role'),
                'action_date': r.get('action_date'),
                'trade_windows': member_bill_trades
            })
            
        # Sort bills by date desc
        my_bills.sort(key=lambda x: str(x.get('action_date') or ''), reverse=True)
        
        # Parse terms data
        terms_history = []
        if member.get('terms_data'):
            try:
                terms_history = json.loads(member['terms_data'])
                # Sort terms reverse chrono
                terms_history.sort(key=lambda x: x.get('start_year') or 0, reverse=True)
            except:
                pass

        profile = {
            'member': {
                'bioguide_id': mid,
                'first_name': member.get('first_name'),
                'last_name': member.get('last_name'),
                'party': member.get('party'),
                'state': member.get('state'),
                'district': member.get('district'),
                'chamber': member.get('chamber'),
                'image_url': member.get('image_url'),
                'official_url': member.get('official_url'),
                'sponsored_count': member.get('sponsored_legislation_count', 0),
                'cosponsored_count': member.get('cosponsored_legislation_count', 0),
                'terms': terms_history
            },
            'bills': my_bills[:500], # Limit to 500 most recent
            'stats': {
                'bills_sponsored': len([b for b in my_bills if b['role'] == 'sponsor']),
                'bills_cosponsored': len([b for b in my_bills if b['role'] == 'cosponsor']),
                'trades_in_windows': sum(len(b['trade_windows']) for b in my_bills)
            },
            'generated_at': pd.Timestamp.now().isoformat()
        }
        
        return mid, profile

    # Generate all profiles
    profiles_to_upload = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(generate_profile, members_df.to_dict('records')))
        profiles_to_upload = results

    # Upload to S3
    logger.info(f" uploading {len(profiles_to_upload)} profiles to S3...")
    
    def upload_s3(item):
        mid, data = item
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=f"website/data/member_profiles/{mid}.json",
            Body=json.dumps(data, default=str),
            ContentType='application/json',
            CacheControl='public, max-age=3600'
        )
        
    with ThreadPoolExecutor(max_workers=20) as executor:
        list(executor.map(upload_s3, profiles_to_upload))
        
    logger.info("✅ All profiles generated and uploaded!")

if __name__ == '__main__':
    build_profiles()
