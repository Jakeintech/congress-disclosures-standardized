#!/usr/bin/env python3
"""Trigger LDA (Lobbying Disclosure Act) ingestion Lambda.

Usage:
    python3 scripts/trigger_lda_ingestion.py --year 2024 --type filings
    python3 scripts/trigger_lda_ingestion.py --year 2024 --type contributions
    python3 scripts/trigger_lda_ingestion.py --year 2024 --type all
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError
import concurrent.futures as futures
import math
import requests
import threading
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_lambda_function_name() -> str:
    """Get the LDA ingestion Lambda function name from environment or Terraform."""
    function_name = os.environ.get("LDA_INGEST_LAMBDA_NAME")

    if not function_name:
        # Try to read from Terraform outputs
        try:
            import subprocess
            result = subprocess.run(
                ["terraform", "-chdir=infra/terraform", "output", "-json"],
                capture_output=True,
                text=True,
                check=True
            )
            outputs = json.loads(result.stdout)
            function_name = outputs.get("lda_ingest_lambda_name", {}).get("value")
        except Exception as e:
            logger.warning(f"Could not read from Terraform outputs: {e}")

    if not function_name:
        # Use default naming convention
        project_name = os.environ.get("PROJECT_NAME", "congress-disclosures")
        environment = os.environ.get("ENVIRONMENT", "development")
        function_name = f"{project_name}-{environment}-lda-ingest-filings"

    return function_name


def invoke_lambda(
    lambda_client: boto3.client,
    function_name: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke Lambda function with given payload.

    Args:
        lambda_client: Boto3 Lambda client
        function_name: Lambda function name
        payload: Event payload

    Returns:
        Lambda response
    """
    try:
        logger.info(f"Invoking Lambda: {function_name}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload)
        )

        # Parse response
        response_payload = json.loads(response["Payload"].read())

        if response["StatusCode"] == 200:
            logger.info("Lambda invocation successful")
            logger.info(f"Response: {json.dumps(response_payload, indent=2)}")
            return response_payload
        else:
            logger.error(f"Lambda invocation failed with status {response['StatusCode']}")
            logger.error(f"Response: {json.dumps(response_payload, indent=2)}")
            return response_payload

    except ClientError as e:
        logger.error(f"Error invoking Lambda: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Trigger LDA ingestion Lambda"
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Filing year to ingest (e.g., 2024)"
    )
    parser.add_argument(
        "--type",
        choices=[
            "filings", "contributions",
            "registrants", "clients", "lobbyists", "constants",
            "all", "all-entities"
        ],
        default="filings",
        help="Type of data to ingest"
    )
    parser.add_argument(
        "--chunked",
        action="store_true",
        help="Run in chunked mode: split pages across multiple Lambda invocations"
    )
    parser.add_argument(
        "--pages-per-invoke",
        type=int,
        default=25,
        help="Number of pages each Lambda invocation should process"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Maximum concurrent Lambda invocations when chunked"
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="API page size (typically 100)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip files that already exist in S3"
    )
    parser.add_argument(
        "--function-name",
        help="Override Lambda function name"
    )

    args = parser.parse_args()

    # Get Lambda function name
    function_name = args.function_name or get_lambda_function_name()
    logger.info(f"Using Lambda function: {function_name}")

    # Create Lambda client
    lambda_client = boto3.client("lambda")

    # Determine which ingestion types to run
    ingestion_types = []
    if args.type in ["filings", "all"]:
        ingestion_types.append(("filing_type", "FILING"))
    if args.type in ["contributions", "all"]:
        ingestion_types.append(("filing_type", "CONTRIBUTION"))
    if args.type in ["registrants", "clients", "lobbyists", "constants", "all-entities", "all"]:
        if args.type in ["registrants", "all-entities", "all"]:
            ingestion_types.append(("entity_type", "REGISTRANT"))
        if args.type in ["clients", "all-entities", "all"]:
            ingestion_types.append(("entity_type", "CLIENT"))
        if args.type in ["lobbyists", "all-entities", "all"]:
            ingestion_types.append(("entity_type", "LOBBYIST"))
        if args.type in ["constants", "all-entities", "all"]:
            ingestion_types.append(("entity_type", "CONSTANTS"))

    # Helpers for chunked mode
    LDA_API_BASE_URL = os.environ.get("LDA_API_BASE_URL", "https://lda.senate.gov/api/v1")

    def get_total_pages(entity: str) -> int:
        # entity: "filings" or "contributions"
        url = f"{LDA_API_BASE_URL}/{entity}/"
        params = {"filing_year": args.year, "page_size": args.page_size}
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        count = int(data.get("count", 0))
        total_pages = max(1, math.ceil(count / args.page_size))
        return total_pages

    # Simple cross-thread rate limiter to avoid Lambda Invoke 'Rate Exceeded'
    _rl_lock = threading.Lock()
    _rl_last = {"t": 0.0}
    _rl_min_interval = 0.5  # seconds between invokes (~2 TPS overall)

    def _rate_limited_invoke(fn):
        with _rl_lock:
            now = time.time()
            elapsed = now - _rl_last["t"]
            if elapsed < _rl_min_interval:
                time.sleep(_rl_min_interval - elapsed)
            _rl_last["t"] = time.time()
        return fn()

    def invoke_async_chunk(entity_type: str, page_start: int, page_end: int):
        payload = {
            "filing_year": args.year,
            "filing_type": entity_type,
            "skip_existing": args.skip_existing,
            "page_start": page_start,
            "page_end": page_end,
            "page_size": args.page_size,
        }
        logger.info(f"Invoking chunk {entity_type} pages {page_start}-{page_end}")
        def _do():
            return boto3.client("lambda").invoke(
                FunctionName=function_name,
                InvocationType="Event",
                Payload=json.dumps(payload)
            )
        _rate_limited_invoke(_do)

    # Invoke Lambda for each type
    results = []
    for key_type, value in ingestion_types:
        logger.info(f"\n{'='*60}")
        if key_type == "filing_type":
            logger.info(f"Ingesting {value} for year {args.year}")
        else:
            logger.info(f"Ingesting entity {value}")
        logger.info(f"{'='*60}\n")

        if args.chunked and key_type == "filing_type":
            # Discover total pages then invoke chunks asynchronously
            entity = "filings" if value == "FILING" else "contributions"
            try:
                total_pages = get_total_pages(entity)
            except Exception as e:
                logger.error(f"Failed to discover total pages: {e}")
                sys.exit(1)

            logger.info(f"Total pages ({entity}): {total_pages}")

            chunks = []
            p = 1
            while p <= total_pages:
                start = p
                end = min(total_pages, p + args.pages_per_invoke - 1)
                chunks.append((start, end))
                p = end + 1

            logger.info(f"Dispatching {len(chunks)} Lambda chunks with concurrency={args.concurrency}")
            with futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                list(pool.map(lambda rng: invoke_async_chunk(value, rng[0], rng[1]), chunks))

            # In chunked mode we don't wait for completion; return a queued summary
            results.append({
                "type": value,
                "result": {"status": "queued", "chunks": len(chunks)}
            })
        else:
            # Single invocation path
            payload = {"skip_existing": args.skip_existing}
            if key_type == "filing_type":
                payload.update({"filing_year": args.year, "filing_type": value})
                try:
                    result = invoke_lambda(lambda_client, function_name, payload)
                    results.append({"type": value, "result": result})
                    if result.get("status") == "error":
                        logger.error(f"Ingestion failed for {value}")
                        sys.exit(1)
                except Exception as e:
                    logger.error(f"Error during ingestion: {e}")
                    sys.exit(1)
            else:
                # Entity types: use async invoke to avoid API throttling after chunk bursts
                payload.update({"entity_type": value})
                def _do():
                    return boto3.client("lambda").invoke(
                        FunctionName=function_name,
                        InvocationType="Event",
                        Payload=json.dumps(payload)
                    )
                # brief cooldown
                time.sleep(3)
                _rate_limited_invoke(_do)
                results.append({"type": value, "result": {"status": "queued"}})

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("INGESTION SUMMARY")
    logger.info(f"{'='*60}\n")

    for item in results:
        logger.info(f"{item['type']}:")
        result = item['result']
        if result.get("status") == "success":
            if item['type'] == "FILING":
                logger.info(f"  Filings ingested: {result.get('filings_ingested', 0)}")
                logger.info(f"  Filings skipped: {result.get('filings_skipped', 0)}")
                logger.info(f"  SQS messages sent: {result.get('sqs_messages_sent', 0)}")
            elif item['type'] == "CONTRIBUTION":
                logger.info(f"  Contributions ingested: {result.get('contributions_ingested', 0)}")
                logger.info(f"  Contributions skipped: {result.get('contributions_skipped', 0)}")
            elif item['type'] in ("REGISTRANT","CLIENT","LOBBYIST"):
                logger.info(f"  Ingested: {result.get('ingested', 0)}  Skipped: {result.get('skipped', 0)}  Pages: {result.get('pages_processed', 0)}")
            elif item['type'] == "CONSTANTS":
                logger.info(f"  Constants ingested: {result.get('constants_ingested', 0)}")
        elif result.get("status") == "queued":
            chunks = result.get('chunks')
            if chunks is not None:
                logger.info(f"  Queued {chunks} chunks for asynchronous ingestion")
            else:
                logger.info("  Queued (async invoke)")
        logger.info("")

    logger.info("Ingestion complete!")


if __name__ == "__main__":
    main()
