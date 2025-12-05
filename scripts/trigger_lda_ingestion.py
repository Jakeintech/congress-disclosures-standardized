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
        choices=["filings", "contributions", "all"],
        default="filings",
        help="Type of data to ingest"
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
        ingestion_types.append("FILING")
    if args.type in ["contributions", "all"]:
        ingestion_types.append("CONTRIBUTION")

    # Invoke Lambda for each type
    results = []
    for ingestion_type in ingestion_types:
        payload = {
            "filing_year": args.year,
            "filing_type": ingestion_type,
            "skip_existing": args.skip_existing
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"Ingesting {ingestion_type} for year {args.year}")
        logger.info(f"{'='*60}\n")

        try:
            result = invoke_lambda(lambda_client, function_name, payload)
            results.append({
                "type": ingestion_type,
                "result": result
            })

            if result.get("status") == "error":
                logger.error(f"Ingestion failed for {ingestion_type}")
                sys.exit(1)

        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            sys.exit(1)

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
        logger.info("")

    logger.info("Ingestion complete!")


if __name__ == "__main__":
    main()
