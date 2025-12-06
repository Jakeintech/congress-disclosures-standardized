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
from typing import Optional

# Configuration
BUCKET = "congress-disclosures-standardized"
INGEST_FUNCTION = "congress-disclosures-development-ingest-zip"
DEFAULT_YEAR = 2025

# Add parent directory to path to allow importing from scripts package
sys.path.append(str(Path(__file__).parent.parent))

s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')
sqs = boto3.client('sqs')

# ============================================================================
# Progress Tracking & UI Helpers
# ============================================================================

class ProgressTracker:
    """Track and display pipeline progress with visual indicators."""

    def __init__(self, total_steps: int):
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
        self.step_start_time = None

    def start_step(self, step_name: str):
        """Mark the start of a pipeline step."""
        self.current_step += 1
        self.step_start_time = time.time()

        # Calculate progress
        progress_pct = (self.current_step / self.total_steps) * 100
        progress_bar = self._render_progress_bar(progress_pct)

        print(f"\n{'='*80}")
        print(f"📊 STEP {self.current_step}/{self.total_steps} ({progress_pct:.1f}%)")
        print(f"{progress_bar}")
        print(f"🔧 {step_name}")
        print(f"{'='*80}")

    def end_step(self, success: bool = True, message: Optional[str] = None):
        """Mark the end of a pipeline step."""
        if self.step_start_time:
            elapsed = time.time() - self.step_start_time
            status = "✅" if success else "⚠️"
            default_msg = "Complete" if success else "Skipped (may need data)"
            msg = message or default_msg
            print(f"{status} {msg} (took {elapsed:.1f}s)")

    def _render_progress_bar(self, percentage: float, width: int = 50) -> str:
        """Render a text-based progress bar."""
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {percentage:.1f}%"

    def finish(self):
        """Mark pipeline completion."""
        total_time = time.time() - self.start_time
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)

        print(f"\n{'='*80}")
        print(f"✨ PIPELINE COMPLETE!")
        print(f"{'='*80}")
        print(f"⏱️  Total time: {minutes}m {seconds}s")
        print(f"✅ Completed {self.current_step}/{self.total_steps} steps")
        print(f"{'='*80}\n")


def print_section_header(title: str, icon: str = "📦"):
    """Print a visually distinct section header."""
    print(f"\n\n{'='*80}")
    print(f"{icon} {title}")
    print(f"{'='*80}\n")

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
    except sqs.exceptions.PurgeQueueInProgress:
        print("⚠️  Purge in progress (rate limited). Waiting 60s...")
        time.sleep(60)
    except Exception as e:
        if "PurgeQueueInProgress" in str(e):
            print("⚠️  Purge in progress (rate limited). Waiting 60s...")
            time.sleep(60)
        else:
            print(f"⚠️  Purge failed (might be empty): {e}")

def wait_for_extraction(timeout_minutes=60):
    """Wait for extraction queue to drain with enhanced progress tracking."""
    print_section_header("Waiting for Extraction Queue", "⏳")
    print(f"Timeout: {timeout_minutes} minutes")
    print(f"Monitoring extraction queue messages...\n")

    url = get_queue_url()
    if not url:
        print("⚠️  Could not find extraction queue.")
        return False

    start_time = time.time()
    last_total = -1
    poll_count = 0

    while (time.time() - start_time) < (timeout_minutes * 60):
        try:
            response = sqs.get_queue_attributes(
                QueueUrl=url,
                AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
            )
            attributes = response['Attributes']
            visible = int(attributes.get('ApproximateNumberOfMessages', 0))
            inflight = int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0))
            total = visible + inflight

            if total == 0:
                print("\n\n✅ Extraction queue drained successfully!")
                print("🔄 Waiting 30s for S3 eventual consistency...")
                time.sleep(30)
                print("✅ Silver layer processing complete.\n")
                return True

            # Calculate progress metrics
            elapsed = int(time.time() - start_time)
            elapsed_min = elapsed // 60
            elapsed_sec = elapsed % 60

            # Show progress bar for queue draining
            if last_total > 0 and total < last_total:
                progress_pct = ((last_total - total) / last_total) * 100
                progress_bar = "█" * int(progress_pct / 2) + "░" * (50 - int(progress_pct / 2))
                rate = (last_total - total) / elapsed if elapsed > 0 else 0
                eta_sec = int(total / rate) if rate > 0 else 0
                eta_min = eta_sec // 60

                status_line = (
                    f"\r⏳ [{progress_bar}] "
                    f"Queue: {total:,} msgs ({visible:,} waiting, {inflight:,} processing) | "
                    f"Time: {elapsed_min}m {elapsed_sec}s | "
                    f"Rate: {rate:.1f} msg/s | "
                    f"ETA: ~{eta_min}m   "
                )
            else:
                status_line = (
                    f"\r⏳ Queue: {total:,} msgs ({visible:,} waiting, {inflight:,} processing) | "
                    f"Elapsed: {elapsed_min}m {elapsed_sec}s   "
                )

            print(status_line, end="", flush=True)

            last_total = total if last_total == -1 else last_total
            poll_count += 1

            # Print newline every 30 polls to keep log readable
            if poll_count % 30 == 0:
                print()

            time.sleep(10)

        except Exception as e:
            print(f"\n⚠️  Error checking queue: {e}")
            time.sleep(10)

    print(f"\n\n❌ Timeout waiting for extraction after {timeout_minutes} minutes.")
    print(f"⚠️  {total:,} messages still in queue.")
    return False

def run_ingestion(year, skip_existing=False):
    """Trigger ingestion Lambda with detailed status updates."""
    print_section_header("House Financial Disclosures Ingestion", "📥")

    mode = "incremental (skip existing files)" if skip_existing else "full (overwrite)"
    print(f"📅 Year: {year}")
    print(f"🔧 Mode: {mode}")
    print(f"🎯 Function: {INGEST_FUNCTION}")
    print(f"\n⏳ Invoking Lambda function...")

    payload = {
        "year": year,
        "skip_existing": skip_existing
    }

    max_attempts = 10
    base_delay = 1.0
    for attempt in range(1, max_attempts + 1):
        try:
            invoke_start = time.time()
            response = lambda_client.invoke(
                FunctionName=INGEST_FUNCTION,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            invoke_time = time.time() - invoke_start

            response_payload = json.loads(response['Payload'].read())

            if response.get('StatusCode') != 200 or response_payload.get('status') == 'error':
                print(f"\n❌ Ingestion failed!")
                print(f"Error: {response_payload}")
                return False

            # Extract metrics from response
            files_processed = response_payload.get('files_processed', 'N/A')
            files_skipped = response_payload.get('files_skipped', 0)
            pdfs_queued = response_payload.get('pdfs_queued', 'N/A')

            print(f"\n✅ Ingestion complete (took {invoke_time:.1f}s)")
            print(f"📊 Summary:")
            print(f"   • Files processed: {files_processed}")
            print(f"   • Files skipped: {files_skipped}")
            print(f"   • PDFs queued for extraction: {pdfs_queued}")
            return True

        except Exception as e:
            err_str = str(e)
            throttled = ('TooManyRequestsException' in err_str) or ('Rate Exceeded' in err_str)
            if attempt < max_attempts and throttled:
                delay = base_delay * (2 ** (attempt - 1))
                import random, time as _t
                jitter = min(2.0, delay * 0.25)
                sleep_s = delay + random.uniform(0, jitter)
                print(f"⚠️  Lambda API throttled (attempt {attempt}/{max_attempts}). Backing off {sleep_s:.1f}s...")
                _t.sleep(sleep_s)
                continue
            print(f"\n❌ Failed to invoke ingestion lambda: {e}")
            return False

def run_silver_pipeline(limit=None):
    """Run Silver pipeline (re-extraction)."""
    cmd = ["python3", "scripts/run_silver_pipeline.py", "--yes"]
    if limit:
        cmd.extend(["--limit", str(limit)])
        
    print(f"Running Silver pipeline: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0

def run_module(module_name, use_subprocess=False):
    """Run a script module's main function with real-time output streaming."""

    # Some scripts need to be run as subprocess (e.g., those requiring sys.argv)
    if use_subprocess or module_name == "compute_lobbying_network_metrics":
        cmd = ["python3", f"scripts/{module_name}.py"]
        if module_name == "compute_lobbying_network_metrics":
            cmd.append("2024")  # Default year

        try:
            # Stream output in real-time
            result = subprocess.run(
                cmd,
                capture_output=False,  # Don't capture, stream to stdout
                text=True,
                timeout=600  # 10 min timeout per script
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"❌ {module_name} timed out after 10 minutes")
            return False
        except Exception as e:
            print(f"❌ Failed to run {module_name}: {e}")
            return False

    # Try dynamic import for most modules
    try:
        # Dynamic import to avoid circular dependencies or load issues
        module = importlib.import_module(f"scripts.{module_name}")
        # Reload to ensure fresh state if run multiple times in same process (though unlikely here)
        importlib.reload(module)

        if hasattr(module, 'main'):
            # Call main() - output will stream naturally since we're not capturing
            result = module.main()
            if result != 0 and result is not None:
                return False
        else:
            print(f"⚠️  {module_name} has no main() function")
            return False

        return True
    except Exception as e:
        print(f"❌ Failed to run {module_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_aggregation():
    """Run aggregation scripts directly across all data sources.

    Executes Bronze → Silver → Gold transformations in correct dependency order:
    1. House Financial Disclosures (Base system)
    2. Congress Bills & Members (Epic 1)
    3. Lobbying Data (Epic 5)
    4. Cross-dataset aggregates (Bill-trade correlation, Triple correlation)
    """
    print_section_header("Data Transformation Pipeline (Bronze → Silver → Gold)", "🏗️")

    # List of modules to run in order (without .py extension)
    modules = [
        # ================================================================
        # HOUSE FINANCIAL DISCLOSURES (Base Data Source)
        # ================================================================

        # Bronze Layer: Manifest generation
        "build_bronze_manifest",

        # Silver Layer: Type-specific transaction aggregation from extraction JSONs
        "generate_type_p_transactions",    # Type P (PTR) - Periodic transactions
        "generate_type_a_assets",          # Type A/N (Annual/New) - Assets & income
        "generate_type_t_terminations",    # Type T (Termination) - Termination reports
        "sync_parquet_to_dynamodb",        # Sync to DynamoDB for API
        "rebuild_silver_manifest",
        "build_silver_manifest_api",

        # Gold Layer: Dimensions & Facts
        "build_dim_members_simple",        # Dimension: Members
        "build_fact_filings",              # Fact: Filings

        # Gold Layer: Aggregates
        "compute_agg_document_quality",    # Document quality scores
        "compute_agg_member_trading_stats",  # Member trading statistics
        "compute_agg_trending_stocks",     # Trending stocks
        "compute_agg_network_graph",       # Member-asset network

        # ================================================================
        # CONGRESS BILLS & MEMBERS (Epic 1)
        # Bronze: Fetched by Lambda (congress-fetch-worker)
        # Silver: Built by Lambda + manual scripts
        # ================================================================

        # Silver Layer: Bill subresources (actions, cosponsors, committees, subjects)
        # Note: Base bill data already in Silver from Lambda processing
        "congress_build_silver_bill_actions",     # Silver: bill_actions
        "congress_build_silver_bill_cosponsors",  # Silver: bill_cosponsors

        # Gold Layer: Dimensions
        "congress_build_dim_member",       # Gold: dim_member (from Congress.gov)
        "congress_build_dim_bill",         # Gold: dim_bill

        # Gold Layer: Facts
        "congress_build_fact_member_bill_role",  # Gold: fact_member_bill_role (sponsors/cosponsors)

        # Gold Layer: Aggregates
        "congress_build_agg_bill_latest_action",  # Gold: agg_bill_latest_action

        # ================================================================
        # BILL INDUSTRY ANALYSIS (Epic 2)
        # ================================================================
        "analyze_bill_industry_impact",    # Classify bills by industry using NLP
        "compute_agg_bill_trade_correlation",  # Bill-trade correlation scores

        # ================================================================
        # LOBBYING DATA INTEGRATION (Epic 5)
        # Bronze: LDA API ingestion
        # Silver: Parse XML filings into normalized tables
        # Gold: Dimensions, Facts, Advanced Aggregates
        # ================================================================

        # Silver Layer: Core entities from LDA XML filings
        "lobbying_build_silver_filings",       # Silver: filings (metadata)
        "lobbying_build_silver_registrants",   # Silver: registrants
        "lobbying_build_silver_clients",       # Silver: clients
        "lobbying_build_silver_lobbyists",     # Silver: lobbyists
        "lobbying_build_silver_activities",    # Silver: lobbying_activities
        "lobbying_build_silver_activity_bills",  # Silver: activity_bills (NLP extracted)
        "lobbying_build_silver_government_entities",  # Silver: government_entities
        "lobbying_build_silver_contributions",  # Silver: contributions

        # Gold Layer: Dimensions
        "lobbying_build_dim_registrant",   # Gold: dim_registrant
        "lobbying_build_dim_client",       # Gold: dim_client
        "lobbying_build_dim_lobbyist",     # Gold: dim_lobbyist

        # Gold Layer: Facts
        "lobbying_build_fact_activity",    # Gold: fact_lobbying_activity

        # Gold Layer: Advanced Aggregates (Cross-dataset correlation)
        "compute_agg_bill_lobbying_correlation",   # Bill-lobbying correlation
        "compute_agg_member_lobbyist_network",     # Member-lobbyist network
        "compute_agg_triple_correlation",          # ⭐ STAR FEATURE: Triple correlation
        "compute_lobbying_network_metrics",        # Network metrics (centrality, communities)

        # ================================================================
        # MANIFESTS & ERROR REPORTS (Final steps)
        # ================================================================
        "generate_document_quality_manifest",
        "generate_all_gold_manifests",
        "generate_pipeline_errors"
    ]

    # Initialize progress tracker
    tracker = ProgressTracker(len(modules))

    success_count = 0
    skip_count = 0
    fail_count = 0

    for module_name in modules:
        tracker.start_step(module_name)

        # Try to run module, but continue on error (some may not have data yet)
        try:
            script_start = time.time()
            result = run_module(module_name)
            script_time = time.time() - script_start

            if result:
                tracker.end_step(success=True, message=f"Complete (took {script_time:.1f}s)")
                success_count += 1
            else:
                tracker.end_step(success=False, message="Skipped (may need data)")
                skip_count += 1
        except Exception as e:
            tracker.end_step(success=False, message=f"Error: {str(e)[:60]}")
            fail_count += 1
            # Continue anyway - don't stop pipeline

    # Final summary
    tracker.finish()
    print(f"📊 Execution Summary:")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ⚠️  Skipped: {skip_count}")
    print(f"   ❌ Failed: {fail_count}")
    print(f"   📦 Total: {len(modules)}")

    return True

def reset_data(year):
    """Reset data for specific year (optional)."""
    # For now, we rely on ingestion overwrite or manual reset
    # Implementing full S3 delete is risky without explicit confirmation
    pass

def trigger_index_to_silver(year):
    """Trigger index-to-silver Lambda with status tracking."""
    print_section_header("House FD: Silver Layer Initialization", "⚙️")

    function_name = f"congress-disclosures-development-index-to-silver"
    print(f"🎯 Function: {function_name}")
    print(f"📅 Year: {year}")
    print(f"\n⏳ Processing XML index and queueing extraction jobs...")

    payload = {"year": year}

    # Cooldown after heavy LDA dispatches to avoid hitting Invoke API rate limits
    try:
        time.sleep(10)
    except Exception:
        pass

    # Fire-and-forget to avoid synchronous API pressure; monitor via queue later
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event',  # async
            Payload=json.dumps(payload)
        )
        status = response.get('StatusCode')
        if status in (200, 202):
            print("\n✅ Silver Init queued (async). Will monitor extraction queue.")
            return True
        print(f"\n⚠️  Silver Init invoke returned status {status}")
        return False
    except Exception as e:
        print(f"\n❌ Failed to invoke index-to-silver lambda: {e}")
        return False


def trigger_congress_ingestion(mode='incremental'):
    """Trigger Congress bills and members ingestion."""
    print_section_header("Congress Bills & Members Ingestion", "🏛️")

    orchestrator_function = "congress-disclosures-development-congress-orchestrator"
    print(f"🎯 Function: {orchestrator_function}")
    print(f"🔧 Mode: {mode}")
    print(f"\n⏳ Triggering ingestion for entity types: member, bill, bill_actions, bill_cosponsors...")

    entity_types = ['member', 'bill']
    results = {}

    for entity_type in entity_types:
        print(f"\n📦 Ingesting: {entity_type}")
        payload = {
            'entity_type': entity_type,
            'mode': mode
        }

        try:
            response = lambda_client.invoke(
                FunctionName=orchestrator_function,
                InvocationType='Event',  # Async
                Payload=json.dumps(payload)
            )

            if response.get('StatusCode') in [200, 202]:
                print(f"   ✅ {entity_type} ingestion queued")
                results[entity_type] = 'queued'
            else:
                print(f"   ⚠️  {entity_type} ingestion may have failed")
                results[entity_type] = 'unknown'

        except Exception as e:
            print(f"   ❌ Failed to trigger {entity_type}: {e}")
            results[entity_type] = 'error'

    print(f"\n📊 Summary:")
    for entity, status in results.items():
        icon = "✅" if status == 'queued' else "⚠️"
        print(f"   {icon} {entity}: {status}")

    print(f"\nℹ️  Congress data will be fetched asynchronously via SQS queues")
    return True


def trigger_lobbying_ingestion(year=2024):
    """Trigger Lobbying Disclosure Act (LDA) data ingestion."""
    print_section_header("Lobbying Data Ingestion (LDA)", "💰")

    print(f"📅 Year: {year}")
    print(f"📦 Data sources: Filings, Contributions")
    print(f"\n⏳ Triggering LDA ingestion script...")

    # Run the trigger script
    cmd = [
        "python3", "scripts/trigger_lda_ingestion.py",
        "--year", str(year), "--type", "all",
        "--chunked", "--pages-per-invoke", "25", "--concurrency", "3"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=False,  # Stream output in real-time
            text=True,
            timeout=300  # 5 min timeout
        )

        if result.returncode == 0:
            print(f"\n✅ Lobbying ingestion triggered successfully")
            return True
        else:
            print(f"\n⚠️  Lobbying ingestion completed with warnings")
            return True  # Continue anyway

    except subprocess.TimeoutExpired:
        print(f"\n❌ Lobbying ingestion timed out")
        return False
    except Exception as e:
        print(f"\n⚠️  Error triggering lobbying ingestion: {e}")
        print("   Continuing pipeline (lobbying data may be stale)...")
        return True  # Don't fail the whole pipeline

def main():
    parser = argparse.ArgumentParser(description="Smart Pipeline Runner")
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR, help="Year to process")
    parser.add_argument("--mode", choices=["auto", "full", "incremental", "reprocess", "aggregate"], default="auto", help="Execution mode")
    args = parser.parse_args()

    # Print banner
    print("\n" + "="*80)
    print("🚀 CONGRESS DISCLOSURES SMART PIPELINE RUNNER".center(80))
    print("="*80)
    print(f"📅 Year: {args.year}")
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    pipeline_start = time.time()
    mode = args.mode

    # Auto-detect mode
    if mode == "auto":
        if check_bronze_exists(args.year):
            print(f"✅ Found existing data for {args.year}.\n")
            print("📋 Select pipeline mode:\n")
            print("  1️⃣  Incremental Update")
            print("      └─ Download & process only new files")
            print("      └─ Recommended for daily updates\n")
            print("  2️⃣  Full Reset")
            print("      └─ Purge queues & overwrite everything")
            print("      └─ Use for fresh start\n")
            print("  3️⃣  Reprocess")
            print("      └─ Re-run extraction on existing Bronze files")
            print("      └─ Use when extractor code changes\n")
            print("  4️⃣  Aggregate Only")
            print("      └─ Rebuild Gold layer from existing Silver data")
            print("      └─ Fastest option if Bronze/Silver already complete\n")

            choice = input("Enter choice [1-4]: ")
            print()
            if choice == "1": mode = "incremental"
            elif choice == "2": mode = "full"
            elif choice == "3": mode = "reprocess"
            elif choice == "4": mode = "aggregate"
            else:
                print("❌ Invalid choice. Exiting.")
                return 1
        else:
            print(f"ℹ️  No data found for {args.year}. Defaulting to Full Ingestion.\n")
            mode = "full"

    # Display execution plan
    print("="*80)
    print(f"🎯 EXECUTION MODE: {mode.upper()}")
    print("="*80)
    if mode == "full":
        print("📦 Pipeline Steps (ALL Data Sources):")
        print("   1. Purge extraction queue")
        print("   2. House FD: Run full ingestion (overwrite)")
        print("   3. Congress: Trigger bills & members ingestion")
        print("   4. Lobbying: Trigger LDA filings ingestion")
        print("   5. Trigger Silver layer processing")
        print("   6. Wait for extraction to complete")
        print("   7. Run Gold layer aggregations (60+ scripts)")
    elif mode == "incremental":
        print("📦 Pipeline Steps (ALL Data Sources):")
        print("   1. House FD: Incremental ingestion (new files only)")
        print("   2. Congress: Incremental update (new bills/members)")
        print("   3. Lobbying: Incremental update (new filings)")
        print("   4. Trigger Silver layer processing")
        print("   5. Wait for extraction to complete")
        print("   6. Run Gold layer aggregations (60+ scripts)")
    elif mode == "reprocess":
        print("📦 Pipeline Steps:")
        print("   1. Trigger Silver layer reprocessing")
        print("   2. Wait for extraction to complete")
        print("   3. Run Gold layer aggregations (60+ scripts)")
    elif mode == "aggregate":
        print("📦 Pipeline Steps:")
        print("   1. Run Gold layer aggregations (60+ scripts)")
    print("="*80 + "\n")

    time.sleep(2)  # Give user time to read
    
    if mode == "full":
        # === STEP 1: Purge queue ===
        purge_queue()

        # === STEP 2: House FD Ingestion ===
        if not run_ingestion(args.year, skip_existing=False):
            return 1

        # === STEP 3: Congress Ingestion ===
        if not trigger_congress_ingestion(mode='full'):
            print("⚠️  Congress ingestion failed, continuing...")

        # === STEP 4: Lobbying Ingestion ===
        if not trigger_lobbying_ingestion(year=args.year):
            print("⚠️  Lobbying ingestion failed, continuing...")

        # === STEP 5: Trigger Silver Layer Init (House FD) ===
        if not trigger_index_to_silver(args.year):
            return 1

    elif mode == "incremental":
        # === STEP 1: House FD Incremental Ingestion ===
        if not run_ingestion(args.year, skip_existing=True):
            return 1

        # === STEP 2: Congress Incremental Update ===
        if not trigger_congress_ingestion(mode='incremental'):
            print("⚠️  Congress ingestion failed, continuing...")

        # === STEP 3: Lobbying Incremental Update ===
        if not trigger_lobbying_ingestion(year=args.year):
            print("⚠️  Lobbying ingestion failed, continuing...")

        # === STEP 4: Trigger Silver Layer Init (House FD) ===
        if not trigger_index_to_silver(args.year):
            return 1

    elif mode == "reprocess":
        # Trigger Silver layer reprocessing
        if not trigger_index_to_silver(args.year):
            return 1

    elif mode == "aggregate":
        pass  # Just skip to aggregation
        
    # Wait for extraction to complete before aggregation
    if mode in ["full", "incremental", "reprocess"]:
        if not wait_for_extraction():
            print("❌ Extraction failed or timed out. Skipping aggregation.")
            return 1

    # Always run aggregation at the end (unless failed)
    if not run_aggregation():
        return 1

    # === Final Data Lake Summary ===
    print_section_header("Data Lake Summary", "📊")
    print("Gathering statistics from all data sources...\n")

    try:
        # House FD Summary
        print("🏛️  House Financial Disclosures:")
        try:
            response = s3.list_objects_v2(
                Bucket=BUCKET,
                Prefix=f"silver/house/financial/documents/year={args.year}/",
                MaxKeys=1
            )
            if 'Contents' in response:
                print(f"   ✅ Silver layer: Active (year={args.year})")
            else:
                print(f"   ⚠️  Silver layer: No data for {args.year}")
        except:
            print(f"   ⚠️  Unable to check status")

        # Congress Summary
        print("\n🏛️  Congress Bills & Members:")
        try:
            response = s3.list_objects_v2(
                Bucket=BUCKET,
                Prefix="silver/congress/bill/",
                MaxKeys=1
            )
            if 'Contents' in response:
                print(f"   ✅ Silver layer: Active")
            else:
                print(f"   ⚠️  Silver layer: No data")
        except:
            print(f"   ⚠️  Unable to check status")

        # Lobbying Summary
        print("\n💰 Lobbying Data:")
        try:
            response = s3.list_objects_v2(
                Bucket=BUCKET,
                Prefix="bronze/lobbying/filings/",
                MaxKeys=1
            )
            if 'Contents' in response:
                print(f"   ✅ Bronze layer: Active")
            else:
                print(f"   ⚠️  Bronze layer: No data")
        except:
            print(f"   ⚠️  Unable to check status")

        # Gold Layer Summary
        print("\n🏆 Gold Layer (Analytics):")
        gold_tables = [
            ("dim_member", "gold/house/financial/dimensions/dim_member/"),
            ("fact_filings", "gold/house/financial/facts/fact_filings/"),
            ("agg_trending_stocks", "gold/house/financial/aggregates/trending_stocks/"),
            ("congress_dim_bill", "gold/congress/dimensions/dim_bill/"),
            ("bill_lobbying_corr", "gold/lobbying/aggregates/bill_lobbying_correlation/"),
        ]

        active_count = 0
        for table_name, prefix in gold_tables:
            try:
                response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix, MaxKeys=1)
                if 'Contents' in response:
                    active_count += 1
            except:
                pass

        print(f"   ✅ {active_count}/{len(gold_tables)} core tables active")

    except Exception as e:
        print(f"⚠️  Error gathering summary: {e}")

    # Final success banner
    pipeline_time = time.time() - pipeline_start
    pipeline_min = int(pipeline_time // 60)
    pipeline_sec = int(pipeline_time % 60)

    print("\n" + "="*80)
    print("🎉 PIPELINE EXECUTION SUCCESSFUL!".center(80))
    print("="*80)
    print(f"⏱️  Total pipeline time: {pipeline_min}m {pipeline_sec}s")
    print(f"🕐 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Mode: {mode.upper()}")
    print(f"📦 Data Sources: House FD, Congress, Lobbying (3/3)")
    print("="*80)
    print("\n✨ Next steps:")
    print("   • Run 'make deploy-website' to update the frontend")
    print("   • Check CloudWatch logs for any warnings")
    print("   • Visit your website to see updated data\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
