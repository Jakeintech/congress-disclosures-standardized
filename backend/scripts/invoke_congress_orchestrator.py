#!/usr/bin/env python3
"""Invoke Congress orchestrator Lambda for bulk data ingestion.

Usage:
    python scripts/invoke_congress_orchestrator.py --entity-type member
    python scripts/invoke_congress_orchestrator.py --entity-type bill --congress 118
    python scripts/invoke_congress_orchestrator.py --entity-type bill --congress 118 --limit 100
"""

import argparse
import json
import os

import boto3


def main():
    parser = argparse.ArgumentParser(description="Invoke Congress orchestrator Lambda")
    parser.add_argument(
        "--entity-type",
        required=True,
        choices=["member", "bill", "committee"],
        help="Entity type to ingest"
    )
    parser.add_argument(
        "--congress",
        type=int,
        help="Congress number (required for bills)"
    )
    parser.add_argument(
        "--bill-type",
        help="Bill type filter (hr, s, hjres, etc.)"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="full",
        help="Ingestion mode (default: full)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of entities (for testing)"
    )
    parser.add_argument(
        "--function-name",
        default=os.environ.get(
            "CONGRESS_ORCHESTRATOR_LAMBDA",
            "congress-disclosures-development-congress-orchestrator"
        ),
        help="Lambda function name"
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", "us-east-1"),
        help="AWS region"
    )
    
    args = parser.parse_args()
    
    # Build payload
    payload = {
        "entity_type": args.entity_type,
        "mode": args.mode
    }
    
    if args.congress:
        payload["congress"] = args.congress
    elif args.entity_type == "bill":
        parser.error("--congress is required for bill entity type")
        
    if args.bill_type:
        payload["bill_type"] = args.bill_type
        
    if args.limit:
        payload["limit"] = args.limit
    
    print(f"Invoking Lambda: {args.function_name}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    # Invoke Lambda
    client = boto3.client("lambda", region_name=args.region)
    
    response = client.invoke(
        FunctionName=args.function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload)
    )
    
    # Parse response
    result = json.loads(response["Payload"].read())
    
    print("\n--- Result ---")
    print(json.dumps(result, indent=2))
    
    # Check for errors
    if result.get("statusCode") != 200:
        print(f"\n⚠️ Error: {result.get('error', 'Unknown error')}")
        return 1
    
    print(f"\n✅ Queued {result.get('queued_count', 0)} jobs in {result.get('duration_seconds', 0)}s")
    return 0


if __name__ == "__main__":
    exit(main())
