#!/usr/bin/env python3
"""
Master Orchestration Script: Rebuild Gold Layer
Runs all fact and aggregate table builders with data quality checks and S3 sync.
"""

import os
import sys
import logging
import subprocess
import time
from pathlib import Path
import pandas as pd
import boto3
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
DATA_DIR = BASE_DIR / "data"
GOLD_DIR = DATA_DIR / "gold"

def run_script(script_name, description, args=None):
    """Run a python script and check for errors."""
    logger.info(f"STARTING: {description} ({script_name})...")
    start_time = time.time()
    
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return False
    
    # Build command with optional args
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
        
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        duration = time.time() - start_time
        logger.info(f"COMPLETED: {description} in {duration:.2f}s")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FAILED: {description}")
        logger.error(f"Error Output:\n{e.stderr}")
        return False

def check_data_quality():
    """Run data quality checks on Gold layer outputs."""
    logger.info("="*80)
    logger.info("RUNNING DATA QUALITY CHECKS")
    logger.info("="*80)
    
    issues = []
    
    # Check fact tables
    fact_tables = [
        "fact_ptr_transactions",
        "fact_asset_holdings",
        "fact_liabilities",
        "fact_positions",
        "fact_gifts_travel",
        "fact_filings"
    ]
    
    for table in fact_tables:
        table_path = GOLD_DIR / "house" / "financial" / "facts" / table
        if not table_path.exists():
            issues.append(f"❌ {table}: Directory does not exist")
            continue
            
        parquet_files = list(table_path.glob("**/*.parquet"))
        if not parquet_files:
            issues.append(f"⚠️  {table}: No parquet files found")
            continue
            
        try:
            df = pd.concat([pd.read_parquet(f) for f in parquet_files])
            row_count = len(df)
            null_counts = df.isnull().sum()
            critical_nulls = null_counts[null_counts > 0]
            
            logger.info(f"✓ {table}: {row_count:,} rows")
            
            if row_count == 0:
                issues.append(f"⚠️  {table}: Empty table (0 rows)")
            
            if len(critical_nulls) > 0:
                for col, null_count in critical_nulls.items():
                    pct = (null_count / row_count) * 100
                    if pct > 50:
                        issues.append(f"⚠️  {table}.{col}: {pct:.1f}% null values")
                        
        except Exception as e:
            issues.append(f"❌ {table}: Error reading data - {e}")
    
    # Check aggregate tables
    agg_tables = [
        "agg_member_trading_stats",
        "agg_stock_activity",
        "agg_sector_activity",
        "agg_compliance_metrics",
        "agg_portfolio_snapshots",
        "agg_trading_timeline_daily"
    ]
    
    for table in agg_tables:
        table_path = GOLD_DIR / "aggregates" / table
        if not table_path.exists():
            issues.append(f"⚠️  {table}: Directory does not exist")
            continue
            
        parquet_files = list(table_path.glob("**/*.parquet"))
        if not parquet_files:
            issues.append(f"⚠️  {table}: No parquet files found")
            continue
            
        try:
            df = pd.concat([pd.read_parquet(f) for f in parquet_files])
            logger.info(f"✓ {table}: {len(df):,} rows")
        except Exception as e:
            issues.append(f"❌ {table}: Error reading data - {e}")
    
    logger.info("="*80)
    if issues:
        logger.warning(f"QUALITY CHECK COMPLETED WITH {len(issues)} ISSUES:")
        for issue in issues:
            logger.warning(f"  {issue}")
    else:
        logger.info("✅ ALL QUALITY CHECKS PASSED")
    logger.info("="*80)
    
    return len(issues) == 0

def sync_to_s3():
    """Sync Gold layer to S3."""
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
    logger.info("="*80)
    logger.info(f"SYNCING TO S3: s3://{bucket_name}/gold/")
    logger.info("="*80)
    
    try:
        result = subprocess.run(
            [
                'aws', 's3', 'sync',
                str(GOLD_DIR),
                f's3://{bucket_name}/gold/',
                '--delete'
            ],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("✅ S3 SYNC COMPLETED")
        logger.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("❌ S3 SYNC FAILED")
        logger.error(e.stderr)
        return False

def main():
    logger.info("="*80)
    logger.info("GOLD LAYER REBUILD STARTED")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("="*80)
    
    success = True
    
    # 1. Fact Tables (Independent of each other)
    # Most fact tables now auto-detect year or don't require it
    facts = [
        ("build_fact_ptr_transactions.py", "Fact PTR Transactions", None),
        ("build_fact_asset_holdings.py", "Fact Asset Holdings", ["--year", "2025"]),
        ("build_fact_liabilities.py", "Fact Liabilities", ["--year", "2025"]),
        ("build_fact_positions.py", "Fact Positions", ["--year", "2025"]),
        ("build_fact_gifts_travel.py", "Fact Gifts & Travel", ["--year", "2025"]),
        ("build_fact_filings.py", "Fact Filings", None),
    ]
    
    for script, desc, args in facts:
        if not run_script(script, desc, args):
            success = False
            logger.warning(f"Fact {desc} failed, continuing...")
            
    # 2. Aggregate Tables (Depend on Facts)
    # Tier 1: Core Analytics (no dependencies on other aggregates)
    core_aggregates = [
        ("compute_agg_member_trading_stats.py", "Member Trading Stats"),
        ("compute_agg_stock_activity.py", "Stock Activity"),
        ("compute_agg_sector_activity.py", "Sector Activity"),
        ("compute_agg_trending_stocks.py", "Trending Stocks"),
        ("compute_agg_trading_timeline_daily.py", "Trading Timeline Daily"),
        ("compute_agg_compliance_metrics.py", "Compliance Metrics"),
        ("compute_agg_document_quality.py", "Document Quality"),
    ]
    
    # Tier 2: Advanced Analytics ("God Mode")
    advanced_aggregates = [
        ("compute_agg_congressional_alpha.py", "Congressional Alpha"),
        ("compute_agg_conflict_detection.py", "Conflict Detection"),
        ("compute_agg_portfolio_reconstruction.py", "Portfolio Reconstruction"),
        ("compute_agg_timing_heatmap.py", "Timing Heatmap"),
        ("compute_agg_sector_analysis.py", "Sector Analysis"),
        ("compute_agg_trading_volume_timeseries.py", "Volume Timeseries"),
        ("compute_agg_portfolio_snapshots.py", "Portfolio Snapshots"),
    ]
    
    # Tier 3: Correlation Analytics (depend on bills + trades)
    correlation_aggregates = [
        ("compute_agg_bill_trade_correlation.py", "Bill-Trade Correlation"),
        ("compute_agg_bill_lobbying_correlation.py", "Bill-Lobbying Correlation"),
        ("compute_agg_triple_correlation.py", "Triple Correlation"),
    ]
    
    # Tier 4: Network Analytics
    network_aggregates = [
        ("compute_agg_network_graph.py", "Network Graph"),
        ("compute_agg_member_lobbyist_network.py", "Member-Lobbyist Network"),
    ]
    
    # Run all tiers
    all_aggregates = core_aggregates + advanced_aggregates + correlation_aggregates + network_aggregates
    
    for script, desc in all_aggregates:
        if not run_script(script, desc):
            success = False
            logger.warning(f"Aggregate {desc} failed, continuing...")
    
    # 3. Data Quality Checks
    quality_passed = check_data_quality()
    
    # 4. S3 Sync
    if success and quality_passed:
        sync_success = sync_to_s3()
        success = success and sync_success
    
    logger.info("="*80)
    if success:
        logger.info("✅ GOLD LAYER REBUILD SUCCESSFUL")
    else:
        logger.error("❌ GOLD LAYER REBUILD COMPLETED WITH ERRORS")
    logger.info("="*80)

if __name__ == "__main__":
    main()
