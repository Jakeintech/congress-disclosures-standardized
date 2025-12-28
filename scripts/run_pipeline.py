#!/usr/bin/env python3
"""
Unified Pipeline Runner for Congress Disclosures.

Run data pipeline stages with options for layer selection,
clean refresh, and audit logging.

Usage:
    python scripts/run_pipeline.py --all          # Run everything
    python scripts/run_pipeline.py --gold         # Just Gold layer
    python scripts/run_pipeline.py --silver --gold # Silver + Gold
    python scripts/run_pipeline.py --clean --all   # Full clean refresh
"""

import argparse
import subprocess
import sys
import os
import json
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
LOG_DIR = PROJECT_DIR / "logs"

# Pipeline scripts organized by layer
PIPELINE_SCRIPTS = {
    'bronze': [
        # Bronze layer ingestion (from Congress.gov API)
        # These are typically run via Lambda or manual trigger
    ],
    'silver': [
        'scripts/congress_transform_members.py',
        'scripts/congress_build_dim_bill.py',
    ],
    'gold': [
        'scripts/congress_build_dim_member.py',
        'scripts/congress_build_fact_member_bill_role.py',
        'scripts/congress_compute_agg_member_stats.py',
    ],
    'website': [
        'scripts/build_congress_network_data.py',
        'scripts/build_network_graph.py',
        'scripts/build_member_profiles.py',
    ],
}

# Full pipeline order
LAYER_ORDER = ['bronze', 'silver', 'gold', 'website']


class PipelineRunner:
    def __init__(self, dry_run=False, audit=True, clean=False):
        self.dry_run = dry_run
        self.audit = audit
        self.clean = clean
        self.results = {
            'start_time': datetime.utcnow().isoformat(),
            'layers': {},
            'errors': [],
            'dry_run': dry_run,
            'clean': clean,
        }
    
    def run_script(self, script_path: str) -> dict:
        """Execute a single script and return result."""
        full_path = PROJECT_DIR / script_path
        
        if not full_path.exists():
            logger.warning(f"Script not found: {script_path}")
            return {'script': script_path, 'status': 'skipped', 'reason': 'not_found'}
        
        logger.info(f"  Running: {script_path}")
        
        if self.dry_run:
            return {'script': script_path, 'status': 'dry_run'}
        
        start = datetime.utcnow()
        try:
            result = subprocess.run(
                ['python3', str(full_path)],
                cwd=str(PROJECT_DIR),
                capture_output=True,
                text=True,
                timeout=600  # 10 min timeout
            )
            duration = (datetime.utcnow() - start).total_seconds()
            
            if result.returncode == 0:
                logger.info(f"    ✓ Completed in {duration:.1f}s")
                return {
                    'script': script_path,
                    'status': 'success',
                    'duration': duration,
                    'stdout_lines': len(result.stdout.splitlines()),
                }
            else:
                logger.error(f"    ✗ Failed with exit code {result.returncode}")
                return {
                    'script': script_path,
                    'status': 'error',
                    'exit_code': result.returncode,
                    'stderr': result.stderr[:500] if result.stderr else None,
                    'duration': duration,
                }
        except subprocess.TimeoutExpired:
            logger.error(f"    ✗ Timeout after 600s")
            return {'script': script_path, 'status': 'timeout'}
        except Exception as e:
            logger.error(f"    ✗ Exception: {e}")
            return {'script': script_path, 'status': 'exception', 'error': str(e)}
    
    def run_layer(self, layer: str) -> bool:
        """Run all scripts for a layer. Returns True if successful."""
        scripts = PIPELINE_SCRIPTS.get(layer, [])
        
        if not scripts:
            logger.info(f"📦 {layer.upper()} layer: No scripts configured")
            return True
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📦 {layer.upper()} Layer ({len(scripts)} scripts)")
        logger.info('='*60)
        
        layer_results = []
        all_success = True
        
        for script in scripts:
            result = self.run_script(script)
            layer_results.append(result)
            if result.get('status') not in ('success', 'dry_run', 'skipped'):
                all_success = False
                self.results['errors'].append(result)
        
        self.results['layers'][layer] = {
            'scripts': layer_results,
            'success': all_success,
        }
        
        return all_success
    
    def run_clean(self):
        """Clean existing data (with confirmation)."""
        if not self.clean:
            return
        
        logger.warning("\n⚠️  CLEAN MODE: This will delete existing Gold layer data!")
        
        if self.dry_run:
            logger.info("   (dry-run: would delete gold/congress/* from S3)")
            return
        
        # Require explicit confirmation
        confirm = os.environ.get('PIPELINE_CONFIRM_CLEAN', '')
        if confirm != 'YES':
            logger.error("   Set PIPELINE_CONFIRM_CLEAN=YES to confirm deletion")
            sys.exit(1)
        
        logger.info("   Deleting gold/congress/* ...")
        subprocess.run([
            'aws', 's3', 'rm', 
            's3://congress-disclosures-standardized/gold/congress/',
            '--recursive'
        ], check=True)
        logger.info("   ✓ Gold layer cleared")
    
    def run(self, layers: list):
        """Run specified pipeline layers."""
        logger.info("\n" + "="*60)
        logger.info("🚀 CONGRESS PIPELINE RUNNER")
        logger.info("="*60)
        logger.info(f"   Layers: {', '.join(layers)}")
        logger.info(f"   Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        if self.clean:
            logger.info(f"   Clean: YES (will delete existing data)")
        logger.info("")
        
        # Handle clean mode
        if self.clean:
            self.run_clean()
        
        # Run each layer in order
        for layer in LAYER_ORDER:
            if layer in layers:
                success = self.run_layer(layer)
                if not success and layer != 'website':  # Continue even if website fails
                    logger.error(f"\n❌ Pipeline stopped at {layer} layer due to errors")
                    break
        
        # Finalize
        self.results['end_time'] = datetime.utcnow().isoformat()
        self.results['success'] = len(self.results['errors']) == 0
        
        # Write audit log
        if self.audit and not self.dry_run:
            self.write_audit_log()
        
        # Summary
        self.print_summary()
        
        return self.results['success']
    
    def write_audit_log(self):
        """Write audit log to file."""
        LOG_DIR.mkdir(exist_ok=True)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        log_file = LOG_DIR / f"pipeline_run_{timestamp}.json"
        
        with open(log_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"\n📋 Audit log: {log_file}")
    
    def print_summary(self):
        """Print execution summary."""
        logger.info("\n" + "="*60)
        logger.info("📊 PIPELINE SUMMARY")
        logger.info("="*60)
        
        for layer, data in self.results.get('layers', {}).items():
            scripts = data.get('scripts', [])
            success_count = sum(1 for s in scripts if s.get('status') == 'success')
            status = "✓" if data.get('success') else "✗"
            logger.info(f"   {status} {layer.upper()}: {success_count}/{len(scripts)} scripts succeeded")
        
        if self.results.get('errors'):
            logger.info(f"\n   ⚠️  {len(self.results['errors'])} errors occurred")
        else:
            logger.info(f"\n   ✅ All scripts completed successfully!")


def main():
    parser = argparse.ArgumentParser(
        description='Congress Disclosures Pipeline Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all              Run full pipeline
  %(prog)s --gold --website   Run Gold + Website layers
  %(prog)s --gold --dry-run   Show what Gold layer would run
  %(prog)s --clean --all      Full refresh (requires PIPELINE_CONFIRM_CLEAN=YES)
        """
    )
    
    # Layer selection
    parser.add_argument('--bronze', action='store_true', help='Run Bronze layer ingestion')
    parser.add_argument('--silver', action='store_true', help='Run Silver layer transformation')
    parser.add_argument('--gold', action='store_true', help='Run Gold layer aggregation')
    parser.add_argument('--website', action='store_true', help='Run Website ISR regeneration')
    parser.add_argument('--all', action='store_true', help='Run all layers')
    
    # Options
    parser.add_argument('--clean', action='store_true', help='Delete existing data before running')
    parser.add_argument('--no-audit', action='store_true', help='Disable audit logging')
    parser.add_argument('--dry-run', action='store_true', help='Show what would run without executing')
    
    args = parser.parse_args()
    
    # Determine which layers to run
    layers = []
    if args.all:
        layers = LAYER_ORDER.copy()
    else:
        if args.bronze:
            layers.append('bronze')
        if args.silver:
            layers.append('silver')
        if args.gold:
            layers.append('gold')
        if args.website:
            layers.append('website')
    
    if not layers:
        # Default to gold + website if no layer specified
        logger.info("No layer specified, defaulting to --gold --website")
        layers = ['gold', 'website']
    
    # Run pipeline
    runner = PipelineRunner(
        dry_run=args.dry_run,
        audit=not args.no_audit,
        clean=args.clean
    )
    
    success = runner.run(layers)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
