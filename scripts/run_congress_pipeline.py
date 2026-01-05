#!/usr/bin/env python3
"""
Congress Pipeline Orchestrator

Master script to run the end-to-end Congress.gov pipeline.
Supports full, incremental, and aggregate-only modes.

Usage:
    python run_congress_pipeline.py --mode full --congress 118
    python run_congress_pipeline.py --mode incremental
    python run_congress_pipeline.py --mode aggregate
"""

import sys
import os
import json
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
import logging

import boto3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
SCRIPTS_DIR = Path(__file__).parent

# Validate required environment variables
if not AWS_ACCOUNT_ID:
    raise ValueError("AWS_ACCOUNT_ID environment variable is required")


def get_lambda_client():
    """Get boto3 Lambda client."""
    return boto3.client('lambda', region_name=AWS_REGION)


def get_sqs_client():
    """Get boto3 SQS client."""
    return boto3.client('sqs', region_name=AWS_REGION)


def get_queue_message_count(queue_url: str) -> int:
    """Get approximate number of messages in SQS queue."""
    sqs = get_sqs_client()
    try:
        response = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
        )
        visible = int(response['Attributes'].get('ApproximateNumberOfMessages', 0))
        in_flight = int(response['Attributes'].get('ApproximateNumberOfMessagesNotVisible', 0))
        return visible + in_flight
    except Exception as e:
        logger.warning(f"Could not get queue count: {e}")
        return -1


def invoke_orchestrator(entity_type: str, congress: int = None, mode: str = 'full') -> dict:
    """Invoke the Congress API ingest orchestrator Lambda."""
    lambda_client = get_lambda_client()
    function_name = f"congress-disclosures-development-congress-orchestrator"
    
    payload = {
        'entity_type': entity_type,
        'mode': mode,
    }
    if congress:
        payload['congress'] = congress
    
    logger.info(f"Invoking orchestrator: {entity_type} (congress={congress}, mode={mode})")
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event',  # Async
            Payload=json.dumps(payload)
        )
        return {'status': 'queued', 'entity_type': entity_type}
    except Exception as e:
        logger.error(f"Failed to invoke orchestrator: {e}")
        return {'status': 'error', 'error': str(e)}


def wait_for_queue_drain(queue_url: str, timeout_seconds: int = 3600, poll_interval: int = 30) -> bool:
    """Wait for SQS queue to drain (message count = 0)."""
    logger.info(f"Waiting for queue to drain (timeout: {timeout_seconds}s)...")
    start_time = time.time()
    last_count = -1
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            logger.warning(f"Timeout waiting for queue to drain after {elapsed:.0f}s")
            return False
        
        count = get_queue_message_count(queue_url)
        if count == 0:
            logger.info("Queue drained successfully!")
            return True
        
        if count != last_count:
            logger.info(f"Queue messages: {count} (elapsed: {elapsed:.0f}s)")
            last_count = count
        
        time.sleep(poll_interval)


def run_script(script_name: str) -> bool:
    """Run a Python script and return success status."""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return False
    
    logger.info(f"Running {script_name}...")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(SCRIPTS_DIR.parent),
            capture_output=True,
            text=True,
            timeout=600  # 10 min timeout per script
        )
        if result.returncode != 0:
            logger.error(f"Script failed: {result.stderr}")
            return False
        logger.info(f"Script completed: {script_name}")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"Script timed out: {script_name}")
        return False
    except Exception as e:
        logger.error(f"Script error: {e}")
        return False


def run_full_pipeline(congress: int = None, wait: bool = True):
    """Run full pipeline: Bronze ingestion → Silver → Gold → Analytics."""
    logger.info("=" * 80)
    logger.info("RUNNING FULL CONGRESS PIPELINE")
    logger.info(f"Congress: {congress or 'all'}, Wait: {wait}")
    logger.info("=" * 80)
    
    # Step 1: Trigger Bronze ingestion for all entity types
    entity_types = ['member', 'bill']  # Core entities to ingest
    
    logger.info("\n📥 STEP 1: Bronze Ingestion")
    for entity_type in entity_types:
        result = invoke_orchestrator(entity_type, congress=congress, mode='full')
        logger.info(f"  {entity_type}: {result['status']}")
    
    # Step 2: Wait for fetch queue to drain (optional)
    if wait:
        logger.info("\n⏳ STEP 2: Waiting for ingestion to complete...")
        fetch_queue_url = f"https://sqs.{AWS_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/congress-disclosures-{ENVIRONMENT}-congress-fetch-queue"
        wait_for_queue_drain(fetch_queue_url, timeout_seconds=7200)  # 2 hours max
        
        # Also wait for Silver queue
        silver_queue_url = f"https://sqs.{AWS_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/congress-disclosures-{ENVIRONMENT}-congress-silver-queue"
        wait_for_queue_drain(silver_queue_url, timeout_seconds=1800)  # 30 min max
    
    # Step 3: Build Gold layer
    logger.info("\n🏆 STEP 3: Building Gold Layer")
    gold_scripts = [
        'congress_build_dim_member.py',
        'congress_build_dim_bill.py',
        'congress_build_fact_member_bill_role.py',
        'congress_build_agg_bill_latest_action.py',  # Epic 1: Bill latest action aggregate
    ]
    for script in gold_scripts:
        run_script(script)

    # Step 4: Build Analytics (Epic 2: Bill Industry Analysis & Correlation)
    logger.info("\n📊 STEP 4: Building Analytics")
    analytics_scripts = [
        'congress_build_analytics_trade_windows.py',
        'congress_build_analytics_stock_activity.py',
        'congress_compute_agg_member_stats.py',
        'analyze_bill_industry_impact.py',  # Epic 2: Industry classification for bills
        'compute_agg_bill_trade_correlation.py',  # Epic 2: Bill-trade correlation scores
    ]
    for script in analytics_scripts:
        run_script(script)
    
    logger.info("\n✅ FULL PIPELINE COMPLETE!")


def run_incremental_pipeline():
    """Run incremental pipeline: fetch updates since last run."""
    logger.info("=" * 80)
    logger.info("RUNNING INCREMENTAL CONGRESS PIPELINE")
    logger.info("=" * 80)
    
    # Step 1: Trigger incremental ingestion
    logger.info("\n📥 STEP 1: Incremental Ingestion")
    entity_types = ['member', 'bill']
    for entity_type in entity_types:
        result = invoke_orchestrator(entity_type, mode='incremental')
        logger.info(f"  {entity_type}: {result['status']}")
    
    # Step 2: Wait briefly for processing
    logger.info("\n⏳ STEP 2: Waiting for processing (5 min max)...")
    silver_queue_url = f"https://sqs.{AWS_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/congress-disclosures-{ENVIRONMENT}-congress-silver-queue"
    wait_for_queue_drain(silver_queue_url, timeout_seconds=300, poll_interval=15)
    
    # Step 3: Rebuild Gold & Analytics
    run_aggregate_pipeline()


def run_aggregate_pipeline():
    """Run aggregate-only pipeline: rebuild Gold + Analytics from existing Silver."""
    logger.info("=" * 80)
    logger.info("RUNNING AGGREGATE PIPELINE (Gold + Analytics)")
    logger.info("=" * 80)

    # Gold layer
    logger.info("\n🏆 Building Gold Layer...")
    gold_scripts = [
        'congress_build_dim_member.py',
        'congress_build_dim_bill.py',
        'congress_build_fact_member_bill_role.py',
        'congress_build_agg_bill_latest_action.py',  # Epic 1: Bill latest action aggregate
    ]
    for script in gold_scripts:
        run_script(script)

    # Analytics
    logger.info("\n📊 Building Analytics...")
    analytics_scripts = [
        'congress_build_analytics_trade_windows.py',
        'congress_build_analytics_stock_activity.py',
        'congress_compute_agg_member_stats.py',
        'analyze_bill_industry_impact.py',  # Epic 2: Industry classification for bills
        'compute_agg_bill_trade_correlation.py',  # Epic 2: Bill-trade correlation scores
    ]
    for script in analytics_scripts:
        run_script(script)

    logger.info("\n✅ AGGREGATE PIPELINE COMPLETE!")


def main():
    parser = argparse.ArgumentParser(description='Congress Pipeline Orchestrator')
    parser.add_argument('--mode', choices=['full', 'incremental', 'aggregate'], 
                        default='aggregate', help='Pipeline mode')
    parser.add_argument('--congress', type=int, default=None,
                        help='Congress number (e.g., 118, 119)')
    parser.add_argument('--no-wait', action='store_true',
                        help='Do not wait for queue processing')
    args = parser.parse_args()
    
    logger.info(f"Congress Pipeline Orchestrator v1.0")
    logger.info(f"Mode: {args.mode}, Congress: {args.congress or 'all'}")
    
    if args.mode == 'full':
        run_full_pipeline(congress=args.congress, wait=not args.no_wait)
    elif args.mode == 'incremental':
        run_incremental_pipeline()
    elif args.mode == 'aggregate':
        run_aggregate_pipeline()


if __name__ == '__main__':
    main()
