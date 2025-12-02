#!/usr/bin/env python3
"""
Fix all API Lambda handlers to use S3_BUCKET instead of None.
"""
import os
import re
from pathlib import Path

API_LAMBDAS_DIR = Path("api/lambdas")

# List of Lambda functions that need fixing (from grep results)
LAMBDAS_TO_FIX = [
    "get_top_traders",
    "get_stock_activity",
    "get_member_trades",
    "get_filing",
    "get_trending_stocks",
    "get_compliance",
    "get_summary",
    "get_member_portfolio",
    "search",
    "get_stocks",
    "get_sector_activity",
    "get_trading_timeline",
    "get_trades",
    "get_members",
    "get_stock",
    "get_member",
]

def fix_handler(lambda_name):
    """Fix a single handler file."""
    handler_path = API_LAMBDAS_DIR / lambda_name / "handler.py"
    
    if not handler_path.exists():
        print(f"❌ Handler not found: {handler_path}")
        return False
    
    with open(handler_path, 'r') as f:
        content = f.read()
    
    # Check if it needs fixing
    if 's3_bucket=None' not in content:
        print(f"✓ {lambda_name}: Already fixed or doesn't need fixing")
        return False
    
    # Replace s3_bucket=None with s3_bucket=S3_BUCKET
    new_content = content.replace('s3_bucket=None', 's3_bucket=S3_BUCKET')
    
    # Ensure S3_BUCKET is defined at module level
    if 'S3_BUCKET = ' not in new_content:
        # Find where to insert it (after imports, before handler function)
        lines = new_content.split('\n')
        insert_index = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('#') and not line.startswith('import') and not line.startswith('from'):
                insert_index = i
                break
        
        lines.insert(insert_index, "S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')\n")
        new_content = '\n'.join(lines)
    
    with open(handler_path, 'w') as f:
        f.write(new_content)
    
    print(f"✅ {lambda_name}: Fixed")
    return True

def main():
    print("Fixing API Lambda handlers...")
    fixed_count = 0
    
    for lambda_name in LAMBDAS_TO_FIX:
        if fix_handler(lambda_name):
            fixed_count += 1
    
    print(f"\n✅ Fixed {fixed_count} handlers")

if __name__ == "__main__":
    main()
