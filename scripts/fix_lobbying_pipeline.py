#!/usr/bin/env python3
"""
Fix Lobbying Pipeline

Runs all Silver and Gold layer scripts for lobbying data to populate
the database and enable the website lobbying explorer.

Usage:
    python3 scripts/fix_lobbying_pipeline.py
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

def run_script(script_name: str, year: int = 2025) -> bool:
    """Run a script and return success status."""
    script_path = Path(__file__).parent / f"{script_name}.py"

    if not script_path.exists():
        print(f"⚠️  Script not found: {script_name}")
        return False

    print(f"\n{'='*80}")
    print(f"🔧 Running: {script_name} --year {year}")
    print(f"{'='*80}")

    start = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--year", str(year)],
            capture_output=False,
            text=True,
            timeout=600  # 10 minute timeout
        )

        elapsed = time.time() - start

        if result.returncode == 0:
            print(f"✅ {script_name} completed successfully ({elapsed:.1f}s)")
            return True
        else:
            print(f"❌ {script_name} failed with code {result.returncode} ({elapsed:.1f}s)")
            return False

    except subprocess.TimeoutExpired:
        print(f"❌ {script_name} timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"❌ {script_name} failed: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix lobbying pipeline")
    parser.add_argument("--year", type=int, default=2025, help="Year to process (default: 2025)")
    args = parser.parse_args()

    year = args.year

    print("\n" + "=" * 80)
    print("💰 LOBBYING PIPELINE FIX".center(80))
    print("=" * 80)
    print(f"📅 Year: {year}")
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Check Bronze data
    print("\n📦 Checking Bronze layer lobbying data...")
    result = subprocess.run(
        ["aws", "s3", "ls", "s3://congress-disclosures-standardized/bronze/lobbying/", "--recursive"],
        capture_output=True,
        text=True
    )
    bronze_count = len(result.stdout.strip().split('\n')) if result.stdout else 0
    print(f"   Found {bronze_count} files in Bronze layer")

    if bronze_count == 0:
        print("\n⚠️  No Bronze lobbying data found!")
        print("   Run lobbying ingestion first:")
        print(f"   python3 scripts/trigger_lda_ingestion.py --year {year} --type all")
        return 1

    # Silver Layer Scripts
    print("\n" + "=" * 80)
    print("📊 SILVER LAYER (Normalized Tables)".center(80))
    print("=" * 80)

    silver_scripts = [
        "lobbying_build_silver_filings",
        "lobbying_build_silver_registrants",
        "lobbying_build_silver_clients",
        "lobbying_build_silver_lobbyists",
        "lobbying_build_silver_activities",
        "lobbying_build_silver_activity_bills",
        "lobbying_build_silver_government_entities",
        "lobbying_build_silver_contributions",
    ]

    silver_success = 0
    silver_failed = 0

    for script in silver_scripts:
        if run_script(script, year=year):
            silver_success += 1
        else:
            silver_failed += 1

    # Gold Layer Scripts
    print("\n" + "=" * 80)
    print("🏆 GOLD LAYER (Analytics & Dimensions)".center(80))
    print("=" * 80)

    gold_scripts = [
        "lobbying_build_dim_registrant",
        "lobbying_build_dim_client",
        "lobbying_build_dim_lobbyist",
        "lobbying_build_fact_activity",
    ]

    gold_success = 0
    gold_failed = 0

    for script in gold_scripts:
        if run_script(script, year=year):
            gold_success += 1
        else:
            gold_failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("📊 EXECUTION SUMMARY".center(80))
    print("=" * 80)
    print(f"\nSilver Layer:")
    print(f"   ✅ Successful: {silver_success}/{len(silver_scripts)}")
    print(f"   ❌ Failed: {silver_failed}/{len(silver_scripts)}")

    print(f"\nGold Layer:")
    print(f"   ✅ Successful: {gold_success}/{len(gold_scripts)}")
    print(f"   ❌ Failed: {gold_failed}/{len(gold_scripts)}")

    total_success = silver_success + gold_success
    total_scripts = len(silver_scripts) + len(gold_scripts)

    print(f"\nTotal:")
    print(f"   ✅ {total_success}/{total_scripts} scripts completed successfully")

    # Next steps
    print("\n" + "=" * 80)
    print("📋 NEXT STEPS".center(80))
    print("=" * 80)

    if silver_failed > 0 or gold_failed > 0:
        print("\n⚠️  Some scripts failed. Check errors above.")
        print("   You may need to:")
        print("   1. Ensure Bronze data exists (run ingestion)")
        print("   2. Check CloudWatch logs for errors")
        print("   3. Re-run individual scripts to debug")
        return 1

    print("\n✅ All scripts completed successfully!")
    print("\n📦 Now deploy the API Gateway routes:")
    print("   cd infra/terraform")
    print("   terraform plan")
    print("   terraform apply")

    print("\n🌐 Then test the lobbying API:")
    print("   curl 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com/v1/lobbying/filings?filing_year=2025&limit=10'")

    print("\n🎨 Finally, deploy the website:")
    print("   make deploy-website")

    print("\n🔍 Verify lobbying explorer works:")
    print("   https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/lobbying-explorer.html")

    print("\n" + "=" * 80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
