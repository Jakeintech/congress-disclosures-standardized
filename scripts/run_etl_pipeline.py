#!/usr/bin/env python3
"""
ETL Pipeline Orchestration Script

This script orchestrates the execution of the ETL pipeline in different modes:
- full: Ingest Bronze (download zips) -> Silver -> Gold -> Website
- silver_gold: Index to Silver (parse XML) -> Gold -> Website
- gold_only: Rebuild Gold tables -> Website

Usage:
    python3 scripts/run_etl_pipeline.py --mode [full|silver_gold|gold_only] --years 2024,2025 --environment [development|production]
"""

import argparse
import boto3
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def get_lambda_client():
    """Get boto3 Lambda client."""
    return boto3.client('lambda')

def invoke_lambda(function_name: str, payload: dict, synchronous: bool = True) -> dict:
    """Invoke a Lambda function."""
    client = get_lambda_client()
    invocation_type = 'RequestResponse' if synchronous else 'Event'
    
    logger.info(f"Invoking Lambda: {function_name} (Sync: {synchronous})")
    
    try:
        response = client.invoke(
            FunctionName=function_name,
            InvocationType=invocation_type,
            Payload=json.dumps(payload)
        )
        
        if synchronous:
            response_payload = json.loads(response['Payload'].read())
            if response.get('StatusCode') != 200:
                logger.error(f"Lambda invocation failed: {response_payload}")
                raise Exception(f"Lambda {function_name} failed")
            return response_payload
        else:
            return {"status": "async_invocation_sent"}
            
    except Exception as e:
        logger.error(f"Failed to invoke Lambda {function_name}: {e}")
        raise

def run_bronze_ingestion(years: List[int], environment: str):
    """Run Bronze ingestion (Full ETL start)."""
    logger.info("=== Starting Bronze Ingestion ===")
    function_name = f"congress-disclosures-{environment}-house-fd-ingest-zip"
    
    for year in years:
        logger.info(f"Triggering ingestion for year {year}...")
        # Ingest zip is long-running, usually async invocation is safer if it takes > 15m, 
        # but here we might want to wait or just trigger. 
        # The ingest lambda triggers index-to-silver itself at the end.
        # However, for 'full' mode in this script, if we want to control the flow, 
        # we should know that ingest-zip -> SQS -> Extract -> (async)
        # ingest-zip also triggers index-to-silver synchronously at the end.
        
        # We'll invoke synchronously to wait for the download and index extraction.
        # The PDF extraction happens asynchronously via SQS.
        invoke_lambda(function_name, {"year": year}, synchronous=True)
        
    logger.info("Bronze ingestion triggered. PDF extraction will continue in background.")

def run_silver_generation(years: List[int], environment: str):
    """Run Silver generation (Index to Silver)."""
    logger.info("=== Starting Silver Generation ===")
    function_name = f"congress-disclosures-{environment}-index-to-silver"
    
    for year in years:
        logger.info(f"Triggering index-to-silver for year {year}...")
        invoke_lambda(function_name, {"year": year}, synchronous=True)
        
    logger.info("Silver generation complete.")

def run_gold_rebuild(environment: str):
    """Run Gold layer rebuild."""
    logger.info("=== Starting Gold Layer Rebuild ===")
    
    # We can run the rebuild script directly if we are in an environment with access,
    # or trigger a Lambda if we had one for this. 
    # Currently we have scripts/rebuild_gold_incremental.py
    
    # Assuming this script runs in CI/CD or local with credentials
    import subprocess
    
    cmd = [sys.executable, "scripts/rebuild_gold_incremental.py"]
    
    # Pass environment variables if needed
    env = os.environ.copy()
    if environment == 'production':
        env['S3_BUCKET_NAME'] = 'congress-disclosures-standardized' # Prod bucket
    else:
        # Dev bucket might be different or same? 
        # Based on infra, it seems we use same bucket but different prefixes or just same bucket?
        # The terraform seems to use 'congress-disclosures-standardized' for both but keys might differ?
        # Actually, looking at backend.tf, it's the same bucket.
        # The environment separation is usually in resource names or prefixes.
        # But the scripts seem to assume S3_BUCKET_NAME.
        pass

    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error(f"Gold rebuild failed:\n{result.stderr}")
        raise Exception("Gold rebuild failed")
        
    logger.info(f"Gold rebuild output:\n{result.stdout}")
    logger.info("Gold layer rebuild complete.")

def update_website(environment: str):
    """Regenerate manifests and upload website."""
    logger.info("=== Updating Website ===")
    
    # 1. Regenerate document quality manifest
    # This is actually done in rebuild_gold_incremental.py usually, 
    # but let's ensure it's done or do other manifest updates.
    # scripts/generate_document_quality_manifest.py
    
    # 2. Upload to S3
    # We can use aws cli for this
    bucket_name = "congress-disclosures-standardized"
    
    logger.info("Uploading website files to S3...")
    files_to_upload = [
        ("website/index.html", "text/html"),
        ("website/app.js", "application/javascript"),
        ("website/document_quality.js", "application/javascript"),
        ("website/style.css", "text/css")
    ]
    
    s3 = boto3.client('s3')
    
    for local_path, content_type in files_to_upload:
        if os.path.exists(local_path):
            key = f"website/{os.path.basename(local_path)}"
            logger.info(f"Uploading {local_path} to s3://{bucket_name}/{key}")
            with open(local_path, 'rb') as f:
                s3.put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=f,
                    ContentType=content_type,
                    CacheControl="no-cache, no-store, must-revalidate"
                )
        else:
            logger.warning(f"File not found: {local_path}")

    logger.info("Website update complete.")

def main():
    parser = argparse.ArgumentParser(description="Run ETL Pipeline")
    parser.add_argument("--mode", required=True, choices=['full', 'silver_gold', 'gold_only'], help="ETL Mode")
    parser.add_argument("--years", default=f"{datetime.now().year}", help="Comma-separated years (e.g. 2024,2025)")
    parser.add_argument("--environment", default="development", choices=['development', 'production'], help="Environment")
    
    args = parser.parse_args()
    
    years = [int(y.strip()) for y in args.years.split(',')]
    mode = args.mode
    env = args.environment
    
    logger.info(f"Starting ETL Pipeline | Mode: {mode} | Env: {env} | Years: {years}")
    
    try:
        if mode == 'full':
            run_bronze_ingestion(years, env)
            # Bronze ingestion triggers index-to-silver automatically in the lambda
            # But we might want to wait or ensure it runs.
            # The lambda handler for ingest calls trigger_index_to_silver at the end.
            # So we don't strictly need to call run_silver_generation explicitly 
            # UNLESS we want to be sure or if ingest fails to trigger it.
            # For robustness, we can rely on the chain.
            
            # Wait a bit for silver to process? 
            # Silver processing is fast (XML parsing).
            # But PDF extraction is slow and async.
            # Gold rebuild depends on Silver data.
            time.sleep(10) # Give it a moment
            
            run_gold_rebuild(env)
            update_website(env)
            
        elif mode == 'silver_gold':
            run_silver_generation(years, env)
            run_gold_rebuild(env)
            update_website(env)
            
        elif mode == 'gold_only':
            run_gold_rebuild(env)
            update_website(env)
            
        logger.info("✅ ETL Pipeline execution completed successfully.")
        
    except Exception as e:
        logger.error(f"❌ ETL Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
