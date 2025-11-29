#!/usr/bin/env python3
"""
Smart Pipeline Runner

Orchestrates the end-to-end pipeline with intelligent options:
1. Full Reset: Purge data, ingest from scratch (overwrite)
2. Incremental: Ingest only new files (skip existing)
3. Reprocess: Re-run extraction on existing Bronze files
4. Aggregate Only: Run aggregation scripts

Usage:
    python scripts/run_smart_pipeline.py [--year 2025] [--mode auto|full|incremental|reprocess|aggregate]
"""

import boto3
import argparse
import sys
import json
import time
import subprocess
import importlib
from datetime import datetime
from pathlib import Path

# Configuration
BUCKET = "congress-disclosures-standardized"
INGEST_FUNCTION = "congress-disclosures-development-ingest-zip"
DEFAULT_YEAR = 2025

# Add parent directory to path to allow importing from scripts package
sys.path.append(str(Path(__file__).parent.parent))

s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')
sqs = boto3.client('sqs')

def check_bronze_exists(year):
    """Check if Bronze data exists for the year."""
    prefix = f"bronze/house/financial/year={year}/"
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix, MaxKeys=1)
    return 'Contents' in response

def get_queue_url():
    """Get extraction queue URL."""
    try:
        # Try common name
        return sqs.get_queue_url(QueueName="congress-disclosures-development-extract-queue")['QueueUrl']
    except:
        return None

def purge_queue():
    """Purge extraction queue."""
    url = get_queue_url()
    if not url:
        print("⚠️  Could not find extraction queue to purge.")
        return
    
    print(f"Purging queue: {url}...")
    try:
        sqs.purge_queue(QueueUrl=url)
        print("✓ Queue purged. Waiting 60s for stabilization...")
        time.sleep(60)
    except Exception as e:
        print(f"⚠️  Purge failed (might be empty): {e}")

def run_ingestion(year, skip_existing=False):
    """Trigger ingestion Lambda."""
    print(f"Triggering ingestion for {year} (skip_existing={skip_existing})...")
    
    payload = {
        "year": year,
        "skip_existing": skip_existing
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=INGEST_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        if response.get('StatusCode') != 200 or response_payload.get('status') == 'error':
            print(f"❌ Ingestion failed: {response_payload}")
            return False
            
        print(f"✓ Ingestion complete: {json.dumps(response_payload, indent=2)}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to invoke ingestion lambda: {e}")
        return False

def run_silver_pipeline(limit=None):
    """Run Silver pipeline (re-extraction)."""
    cmd = ["python3", "scripts/run_silver_pipeline.py", "--yes"]
    if limit:
        cmd.extend(["--limit", str(limit)])
        
    print(f"Running Silver pipeline: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0

def run_module(module_name):
    """Run a script module's main function."""
    print(f"Running {module_name}...")
    try:
        # Dynamic import to avoid circular dependencies or load issues
        module = importlib.import_module(f"scripts.{module_name}")
        # Reload to ensure fresh state if run multiple times in same process (though unlikely here)
        importlib.reload(module)
        
        if hasattr(module, 'main'):
            result = module.main()
            if result != 0 and result is not None:
                print(f"❌ {module_name} failed with code {result}")
                return False
        else:
            print(f"⚠️  {module_name} has no main() function")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Failed to run {module_name}: {e}")
        return False

def run_aggregation():
    """Run aggregation scripts directly."""
    print("\nRunning Aggregation (Gold Layer)...")
    
    # List of modules to run in order (without .py extension)
    modules = [
        "build_bronze_manifest",
        "generate_type_p_transactions",    # Type P (PTR) - Periodic transactions
        "generate_type_a_assets",          # Type A/N (Annual/New) - Assets & income
        "generate_type_t_terminations",    # Type T (Termination) - Termination reports
        "sync_parquet_to_dynamodb",
        "rebuild_silver_manifest",
        "build_silver_manifest_api",
        "build_fact_filings",
        "compute_agg_document_quality",
        "compute_agg_member_trading_stats",
        "compute_agg_trending_stocks",
        "compute_agg_network_graph",
        "generate_document_quality_manifest",
        "generate_all_gold_manifests"
    ]
    
    for module_name in modules:
        if not run_module(module_name):
            return False
            
    print("✓ Aggregation complete")
    return True

def reset_data(year):
    """Reset data for specific year (optional)."""
    # For now, we rely on ingestion overwrite or manual reset
    # Implementing full S3 delete is risky without explicit confirmation
    pass

def main():
    parser = argparse.ArgumentParser(description="Smart Pipeline Runner")
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR, help="Year to process")
    parser.add_argument("--mode", choices=["auto", "full", "incremental", "reprocess", "aggregate"], default="auto", help="Execution mode")
    args = parser.parse_args()
    
    print("="*60)
    print(f"Smart Pipeline Runner - Year {args.year}")
    print("="*60)
    
    mode = args.mode
    
    # Auto-detect mode
    if mode == "auto":
        if check_bronze_exists(args.year):
            print(f"Found existing data for {args.year}.")
            print("Select mode:")
            print("  1. Incremental Update (Download & process only new files)")
            print("  2. Full Reset (Overwrite everything)")
            print("  3. Reprocess (Re-run extraction on existing files)")
            print("  4. Aggregate Only (Update stats/tables)")
            
            choice = input("Enter choice [1-4]: ")
            if choice == "1": mode = "incremental"
            elif choice == "2": mode = "full"
            elif choice == "3": mode = "reprocess"
            elif choice == "4": mode = "aggregate"
            else:
                print("Invalid choice. Exiting.")
                return 1
        else:
            print(f"No data found for {args.year}. Defaulting to Full Ingestion.")
            mode = "full"
            
    print(f"\nExecuting mode: {mode.upper()}\n")
    
    if mode == "full":
        # Purge queue first
        purge_queue()
        # Run ingestion (overwrite)
        if not run_ingestion(args.year, skip_existing=False):
            return 1
        # Ingestion triggers extraction automatically
        
    elif mode == "incremental":
        # Run ingestion (skip existing)
        if not run_ingestion(args.year, skip_existing=True):
            return 1
        # Ingestion triggers extraction ONLY for new files
        
    elif mode == "reprocess":
        # Run Silver pipeline script
        if not run_silver_pipeline():
            return 1
            
    elif mode == "aggregate":
        pass # Just skip to aggregation
        
    # Always run aggregation at the end (unless failed)
    if not run_aggregation():
        return 1
        
    print("\n✓ Pipeline execution successful!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
