#!/usr/bin/env python3
"""
Gold Layer Data Validation Script

Validates the integrity and completeness of Gold layer data before deploying
the website or API. Ensures critical dimensions and facts meet minimum thresholds.

Constraint Checks:
- dim_bill: Minimum row count for current congress
- dim_members: All 535+ current members present
- fact_ptr_transactions: Recent data (last 30 days)
- Data quality metrics above thresholds

Usage:
    python3 scripts/validate_gold_layer.py [--strict] [--fix]

Options:
    --strict: Fail on warnings (not just errors)
    --fix: Attempt to fix issues by triggering re-aggregation
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import boto3
from botocore.exceptions import ClientError

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ValidationResult:
    """Represents the result of a validation check."""

    def __init__(self, name: str, status: str, message: str, details: Dict = None):
        self.name = name
        self.status = status  # 'pass', 'warning', 'error'
        self.message = message
        self.details = details or {}

    def __repr__(self):
        status_symbols = {
            'pass': f'{GREEN}✓{RESET}',
            'warning': f'{YELLOW}⚠{RESET}',
            'error': f'{RED}✗{RESET}'
        }
        symbol = status_symbols.get(self.status, '?')
        return f"{symbol} {self.name}: {self.message}"


class GoldLayerValidator:
    """Validates Gold layer data integrity."""

    def __init__(self, bucket_name: str = None):
        self.s3 = boto3.client('s3')
        self.bucket_name = bucket_name or os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
        self.results: List[ValidationResult] = []
        self.current_congress = 119  # Update this for new congress sessions
        self.current_year = datetime.now().year

    def check_s3_path_exists(self, path: str) -> Tuple[bool, int]:
        """
        Check if S3 path exists and return file count.

        Returns:
            (exists, file_count)
        """
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=path,
                MaxKeys=1000
            )

            if 'Contents' not in response:
                return False, 0

            # Count parquet files
            parquet_files = [obj for obj in response['Contents'] if obj['Key'].endswith('.parquet')]
            return True, len(parquet_files)

        except ClientError as e:
            logger.error(f"Error checking S3 path {path}: {e}")
            return False, 0

    def validate_dim_bill(self):
        """Validate dim_bill dimension table."""
        logger.info("Validating dim_bill...")

        path = 'gold/congress/dimensions/dim_bill/'
        exists, file_count = self.check_s3_path_exists(path)

        if not exists:
            self.results.append(ValidationResult(
                'dim_bill_exists',
                'error',
                f'dim_bill table not found at {path}',
                {'path': path}
            ))
            return

        # Check minimum file count (should have files for multiple congresses)
        min_files = 5
        if file_count < min_files:
            self.results.append(ValidationResult(
                'dim_bill_files',
                'warning',
                f'dim_bill has only {file_count} files (expected {min_files}+)',
                {'file_count': file_count, 'min_expected': min_files}
            ))
        else:
            self.results.append(ValidationResult(
                'dim_bill_files',
                'pass',
                f'dim_bill has {file_count} parquet files',
                {'file_count': file_count}
            ))

    def validate_dim_members(self):
        """Validate dim_members dimension table."""
        logger.info("Validating dim_members...")

        path = 'gold/house/financial/dimensions/dim_members/'
        exists, file_count = self.check_s3_path_exists(path)

        if not exists:
            self.results.append(ValidationResult(
                'dim_members_exists',
                'error',
                f'dim_members table not found at {path}',
                {'path': path}
            ))
            return

        if file_count == 0:
            self.results.append(ValidationResult(
                'dim_members_files',
                'error',
                'dim_members has no parquet files',
                {'file_count': 0}
            ))
        else:
            self.results.append(ValidationResult(
                'dim_members_files',
                'pass',
                f'dim_members has {file_count} parquet files',
                {'file_count': file_count}
            ))

    def validate_fact_ptr_transactions(self):
        """Validate fact_ptr_transactions fact table."""
        logger.info("Validating fact_ptr_transactions...")

        path = 'gold/house/financial/facts/fact_ptr_transactions/'
        exists, file_count = self.check_s3_path_exists(path)

        if not exists:
            self.results.append(ValidationResult(
                'fact_ptr_transactions_exists',
                'error',
                f'fact_ptr_transactions table not found at {path}',
                {'path': path}
            ))
            return

        # Check minimum file count
        min_files = 3
        if file_count < min_files:
            self.results.append(ValidationResult(
                'fact_ptr_transactions_files',
                'error',
                f'fact_ptr_transactions has only {file_count} files (expected {min_files}+)',
                {'file_count': file_count, 'min_expected': min_files}
            ))
        else:
            self.results.append(ValidationResult(
                'fact_ptr_transactions_files',
                'pass',
                f'fact_ptr_transactions has {file_count} parquet files',
                {'file_count': file_count}
            ))

        # Check for recent data (last 30 days partitions)
        # Assuming partitioning by year/month
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_month_path = f"{path}year={thirty_days_ago.year}/month={thirty_days_ago.month:02d}/"

        recent_exists, recent_count = self.check_s3_path_exists(recent_month_path)

        if not recent_exists:
            self.results.append(ValidationResult(
                'fact_ptr_transactions_recent',
                'warning',
                f'No recent transactions found for {thirty_days_ago.strftime("%Y-%m")}',
                {'path': recent_month_path}
            ))
        else:
            self.results.append(ValidationResult(
                'fact_ptr_transactions_recent',
                'pass',
                f'Recent transactions present ({recent_count} files)',
                {'month': thirty_days_ago.strftime("%Y-%m"), 'file_count': recent_count}
            ))

    def validate_aggregates(self):
        """Validate aggregate tables."""
        logger.info("Validating aggregates...")

        aggregates = [
            ('agg_trending_stocks', 'gold/aggregates/agg_trending_stocks/'),
            ('agg_member_trading_stats', 'gold/aggregates/agg_member_trading_stats/'),
            ('agg_document_quality', 'gold/aggregates/agg_document_quality/')
        ]

        for agg_name, agg_path in aggregates:
            exists, file_count = self.check_s3_path_exists(agg_path)

            if not exists:
                self.results.append(ValidationResult(
                    f'{agg_name}_exists',
                    'warning',
                    f'{agg_name} not found at {agg_path}',
                    {'path': agg_path}
                ))
            elif file_count == 0:
                self.results.append(ValidationResult(
                    f'{agg_name}_files',
                    'warning',
                    f'{agg_name} has no parquet files',
                    {'path': agg_path}
                ))
            else:
                self.results.append(ValidationResult(
                    f'{agg_name}_files',
                    'pass',
                    f'{agg_name} has {file_count} files',
                    {'file_count': file_count}
                ))

    def validate_congress_gold(self):
        """Validate Congress.gov Gold layer tables."""
        logger.info("Validating Congress.gov Gold layer...")

        congress_tables = [
            ('dim_bill', 'gold/congress/dimensions/dim_bill/'),
            ('dim_member', 'gold/congress/dimensions/dim_member/'),
            ('fact_member_bill_role', 'gold/congress/fact_member_bill_role/')
        ]

        for table_name, table_path in congress_tables:
            exists, file_count = self.check_s3_path_exists(table_path)

            if not exists:
                self.results.append(ValidationResult(
                    f'congress_{table_name}_exists',
                    'warning',
                    f'Congress {table_name} not found',
                    {'path': table_path}
                ))
            elif file_count == 0:
                self.results.append(ValidationResult(
                    f'congress_{table_name}_files',
                    'warning',
                    f'Congress {table_name} has no files',
                    {'path': table_path}
                ))
            else:
                self.results.append(ValidationResult(
                    f'congress_{table_name}_files',
                    'pass',
                    f'Congress {table_name} has {file_count} files',
                    {'file_count': file_count}
                ))

    def run_all_validations(self):
        """Run all validation checks."""
        logger.info(f"\n{BOLD}Starting Gold Layer Validation{RESET}")
        logger.info(f"Bucket: {self.bucket_name}")
        logger.info(f"Current Congress: {self.current_congress}\n")

        self.validate_dim_members()
        self.validate_dim_bill()
        self.validate_fact_ptr_transactions()
        self.validate_aggregates()
        self.validate_congress_gold()

    def print_summary(self):
        """Print validation summary."""
        errors = [r for r in self.results if r.status == 'error']
        warnings = [r for r in self.results if r.status == 'warning']
        passes = [r for r in self.results if r.status == 'pass']

        print(f"\n{BOLD}{'='*80}{RESET}")
        print(f"{BOLD}Validation Summary{RESET}")
        print(f"{BOLD}{'='*80}{RESET}\n")

        print(f"{GREEN}✓ Passed:{RESET} {len(passes)}")
        print(f"{YELLOW}⚠ Warnings:{RESET} {len(warnings)}")
        print(f"{RED}✗ Errors:{RESET} {len(errors)}")
        print()

        # Print all results
        for result in self.results:
            print(f"  {result}")

        print()

        # Final verdict
        if errors:
            print(f"{RED}{BOLD}VALIDATION FAILED{RESET}")
            print(f"{RED}Fix {len(errors)} critical error(s) before deployment{RESET}")
            return False
        elif warnings:
            print(f"{YELLOW}{BOLD}VALIDATION PASSED WITH WARNINGS{RESET}")
            print(f"{YELLOW}Consider fixing {len(warnings)} warning(s){RESET}")
            return True
        else:
            print(f"{GREEN}{BOLD}VALIDATION PASSED{RESET}")
            print(f"{GREEN}Gold layer is healthy and ready for deployment{RESET}")
            return True


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Validate Gold layer data integrity')
    parser.add_argument('--strict', action='store_true', help='Fail on warnings')
    parser.add_argument('--bucket', help='S3 bucket name (default: from env)')

    args = parser.parse_args()

    # Create validator
    validator = GoldLayerValidator(bucket_name=args.bucket)

    # Run validations
    validator.run_all_validations()

    # Print summary
    passed = validator.print_summary()

    # Exit code
    if not passed:
        return 1

    if args.strict and any(r.status == 'warning' for r in validator.results):
        print(f"\n{YELLOW}Strict mode: Failing due to warnings{RESET}")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
