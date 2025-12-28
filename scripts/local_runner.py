#!/usr/bin/env python3
"""
Local Pipeline Runner

Run the entire pipeline locally using filesystem storage instead of AWS.
Perfect for testing and debugging without AWS costs or complexity.

Usage:
    python3 scripts/local_runner.py --mode full --year 2025
    python3 scripts/local_runner.py --mode incremental
    python3 scripts/local_runner.py --mode aggregate

This sets up the local environment and runs run_smart_pipeline.py
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Set up local environment variables
LOCAL_DATA_DIR = Path(__file__).parent.parent / "local_data"


def setup_local_environment():
    """Set environment variables for local execution."""
    # Enable local emulator
    os.environ['USE_LOCAL_EMULATOR'] = 'true'
    os.environ['LOCAL_DATA_DIR'] = str(LOCAL_DATA_DIR)

    # Set standard environment variables
    os.environ['S3_BUCKET_NAME'] = 'congress-disclosures-standardized'
    os.environ['AWS_REGION'] = 'us-east-1'
    os.environ['AWS_ACCOUNT_ID'] = 'local'
    os.environ['PROJECT_NAME'] = 'congress-disclosures'
    os.environ['ENVIRONMENT'] = 'local'
    os.environ['LOG_LEVEL'] = 'INFO'

    # Create local data directory
    LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("🏠 LOCAL PIPELINE RUNNER")
    print("=" * 80)
    print(f"📁 Data directory: {LOCAL_DATA_DIR.absolute()}")
    print(f"🔧 Mode: Local Emulator")
    print("=" * 80)
    print()


def view_local_data():
    """Show the local data directory structure."""
    import subprocess

    print("\n" + "=" * 80)
    print("📊 LOCAL DATA STRUCTURE")
    print("=" * 80)

    # Use tree if available, otherwise use find
    try:
        subprocess.run(['tree', '-L', '3', str(LOCAL_DATA_DIR)], check=False)
    except FileNotFoundError:
        # Fallback to find
        subprocess.run(['find', str(LOCAL_DATA_DIR), '-maxdepth', '3', '-type', 'd'], check=False)

    print()


def start_local_viewer():
    """Start a simple HTTP server to browse local data."""
    import http.server
    import socketserver
    import threading

    PORT = 8000

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(LOCAL_DATA_DIR), **kwargs)

    def serve():
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"\n📡 Local data viewer started at http://localhost:{PORT}")
            print(f"   Press Ctrl+C to stop")
            httpd.serve_forever()

    viewer_thread = threading.Thread(target=serve, daemon=True)
    viewer_thread.start()


def main():
    parser = argparse.ArgumentParser(
        description="Run the pipeline locally with filesystem storage"
    )
    parser.add_argument(
        '--mode',
        choices=['full', 'incremental', 'reprocess', 'aggregate'],
        default='incremental',
        help='Pipeline mode'
    )
    parser.add_argument(
        '--year',
        type=int,
        default=2025,
        help='Year to process'
    )
    parser.add_argument(
        '--view-data',
        action='store_true',
        help='Show local data structure after completion'
    )
    parser.add_argument(
        '--start-viewer',
        action='store_true',
        help='Start HTTP server to browse local data'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean local data directory before running'
    )

    args = parser.parse_args()

    # Setup local environment
    setup_local_environment()

    # Clean if requested
    if args.clean:
        import shutil
        print(f"🧹 Cleaning local data directory...")
        if LOCAL_DATA_DIR.exists():
            shutil.rmtree(LOCAL_DATA_DIR)
        LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✅ Cleaned\n")

    # Start viewer if requested
    if args.start_viewer:
        start_local_viewer()

    # Run the pipeline
    print(f"🚀 Starting pipeline (mode: {args.mode}, year: {args.year})\n")

    # Import and run the smart pipeline
    sys.path.insert(0, str(Path(__file__).parent.parent))

    # Run the pipeline script
    cmd = [
        sys.executable,
        'scripts/run_smart_pipeline.py',
        '--mode', args.mode,
        '--year', str(args.year)
    ]

    result = subprocess.run(cmd, env=os.environ.copy())

    # View data if requested
    if args.view_data:
        view_local_data()

    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
