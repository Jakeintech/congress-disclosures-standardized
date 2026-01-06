#!/usr/bin/env python3
"""
Build Silver manifest API endpoint.
Copies silver_documents_v2.json to the API v1 structure for consistency.
"""
import boto3
import json
from datetime import datetime

S3_BUCKET = "congress-disclosures-standardized"
SOURCE_KEY = "website/data/silver_documents_v2.json"
DEST_KEY = "website/api/v1/documents/silver/manifest.json"

def main():
    s3 = boto3.client("s3", region_name="us-east-1")
    
    try:
        print(f"📥 Reading {SOURCE_KEY}...")
        response = s3.get_object(Bucket=S3_BUCKET, Key=SOURCE_KEY)
        data = json.loads(response["Body"].read().decode("utf-8"))
        
        # Ensure API structure matches expected format
        manifest = {
            "generated_at": data.get("generated_at", datetime.utcnow().isoformat() + "Z"),
            "total_documents": data.get("total_documents", len(data.get("documents", []))),
            "stats": data.get("stats", {}),
            "documents": data.get("documents", [])
        }
        
        print(f"✅ Loaded {manifest['total_documents']} documents")
        print(f"📤 Uploading to {DEST_KEY}...")
        
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=DEST_KEY,
            Body=json.dumps(manifest, indent=2, default=str),
            ContentType="application/json",
            CacheControl="max-age=300"
        )
        
        print(f"✅ Silver manifest API endpoint created")
        print(f"📍 URL: https://{S3_BUCKET}.s3.us-east-1.amazonaws.com/{DEST_KEY}")
        print(f"📊 Stats: {manifest['stats']}")
        
    except s3.exceptions.NoSuchKey:
        print(f"⚠️  Source file {SOURCE_KEY} not found")
        print("   Run 'python3 scripts/rebuild_silver_manifest.py' first")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
