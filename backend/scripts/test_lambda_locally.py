#!/usr/bin/env python3
"""
Local Lambda execution simulator for testing API handlers.
Injects mock events and captures responses.
"""

import importlib.util
import json
import os
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

@dataclass
class LambdaContext:
    function_name: str = "local_test"
    function_version: str = "local"
    aws_request_id: str = "local-uuid"
    memory_limit_in_mb: int = 128

def simulate_lambda(handler_path: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """Dynamically load and run a Lambda handler."""
    abs_path = Path(handler_path).absolute()
    if not abs_path.exists():
        raise FileNotFoundError(f"Handler not found: {handler_path}")

    # Load module
    module_name = abs_path.stem
    spec = importlib.util.spec_from_file_location(module_name, str(abs_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Context mock
    context = LambdaContext()
    
    # Run handler
    if hasattr(module, 'handler'):
        return module.handler(event, context)
    else:
        raise AttributeError(f"No 'handler' function in {handler_path}")

def main():
    parser = argparse.ArgumentParser(description="Test Lambda handlers locally")
    parser.add_argument("--handler", help="Path to handler.py or handler name (e.g. get_trades)")
    parser.add_argument("--path", help="Mock request path (e.g. /v1/trades)")
    parser.add_argument("--query", help="Query string (e.g. ticker=AAPL&limit=10)")
    parser.add_argument("--all", action="store_true", help="Run smoke test on all handlers")

    args = parser.parse_args()

    # Set required environment variables
    os.environ['S3_BUCKET_NAME'] = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
    os.environ['CONGRESS_GOV_API_KEY'] = os.environ.get('CONGRESS_GOV_API_KEY', 'mock-key')

    if args.all:
        print("Running smoke tests on all handlers...")
        lambdas_dir = Path("api/lambdas")
        results = []
        for handler_file in lambdas_dir.glob("**/handler.py"):
            print(f"Testing {handler_file.parent.name}...", end=" ")
            try:
                # Basic health check event
                event = {
                    "httpMethod": "GET",
                    "path": "/health",
                    "queryStringParameters": {},
                    "pathParameters": {}
                }
                resp = simulate_lambda(str(handler_file), event)
                status = resp.get('statusCode', 500)
                if status < 400:
                    print("✅")
                else:
                    print(f"❌ (Status {status})")
                results.append({"name": handler_file.parent.name, "status": status})
            except Exception as e:
                print(f"💥 (Error: {e})")
                results.append({"name": handler_file.parent.name, "status": "Error", "error": str(e)})
        
        print("\nSummary:")
        for r in results:
            print(f"{r['name']}: {r['status']}")
        return

    if not args.handler:
        parser.print_help()
        return

    # Map name to path
    handler_path = args.handler
    if not handler_path.endswith(".py"):
        handler_path = f"api/lambdas/{args.handler}/handler.py"

    # Build event
    query_params = {}
    if args.query:
        for pair in args.query.split('&'):
            if '=' in pair:
                k, v = pair.split('=', 1)
                query_params[k] = v

    # Simple path parameter extraction if path provided
    path_params = {}
    if args.path:
        parts = args.path.split('/')
        if 'bills' in parts:
            idx = parts.index('bills')
            if len(parts) > idx + 3:
                 path_params['congress'] = parts[idx+1]
                 path_params['type'] = parts[idx+2]
                 path_params['number'] = parts[idx+3]

    event = {
        "httpMethod": "GET",
        "path": args.path or "/",
        "queryStringParameters": query_params,
        "pathParameters": path_params
    }

    print(f"Simulating {handler_path}...")
    try:
        response = simulate_lambda(handler_path, event)
        print("\nResponse Status:", response.get('statusCode'))
        print("Response Body:")
        body = json.loads(response.get('body', '{}'))
        print(json.dumps(body, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
