#!/usr/bin/env python3
"""
Download complete Congress member list and save as reference data in Bronze layer.
Run this script periodically to update the member roster.

This is MDM Master Data Management for member reference data.
"""

import os
import json
import requests
import boto3
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get('CONGRESS_GOV_API_KEY') or os.environ.get('CONGRESS_API_KEY')
BASE_URL = "https://api.congress.gov/v3"
BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

# Store in Bronze layer as reference data
S3_KEY = "bronze/reference/congress_members.json"
LOCAL_FILE = Path(__file__).parent.parent / "ingestion/lib/congress_members.json"

def fetch_all_members():
    """Fetch all members from Congress API with pagination."""
    if not API_KEY:
        raise ValueError("API key required (CONGRESS_GOV_API_KEY)")
    
    all_members = []
    offset = 0
    limit = 250
    
    print(f"Fetching members from Congress.gov API...")
    
    while True:
        response = requests.get(
            f"{BASE_URL}/member",
            params={'api_key': API_KEY, 'format': 'json', 'limit': limit, 'offset': offset},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        members = data.get('members', [])
        if not members:
            break
            
        all_members.extend(members)
        print(f"  Fetched {len(members)} members (total: {len(all_members)})")
        
        if len(members) < limit:
            break
            
        offset += limit
    
    return all_members

def main():
    members = fetch_all_members()
    
    reference_data = {
        'updated_at': datetime.utcnow().isoformat(),
        'count': len(members),
        'members': members
    }
    
    # Save locally
    LOCAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCAL_FILE, 'w') as f:
        json.dump(reference_data, f, indent=2)
    print(f"\n✅ Saved {len(members)} members to {LOCAL_FILE}")
    
    # Upload to Bronze layer in S3
    s3 = boto3.client('s3')
    s3.put_object(
        Bucket=BUCKET,
        Key=S3_KEY,
        Body=json.dumps(reference_data),
        ContentType='application/json'
    )
    print(f"✅ Uploaded reference data to s3://{BUCKET}/{S3_KEY}")

if __name__ == '__main__':
    main()
