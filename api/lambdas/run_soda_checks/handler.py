"""
Lambda function to run Soda Core data quality checks.

This function executes data quality checks defined in YAML files
and fails the pipeline if any checks fail.
"""

import json
import logging
import os
from typing import Dict, Any

import duckdb
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
SNS_TOPIC_ARN = os.environ.get('DATA_QUALITY_ALERTS_TOPIC_ARN')

# Global connection (reused across warm invocations)
_conn = None

def get_duckdb_connection():
    """Get or create DuckDB connection with S3 support."""
    global _conn
    if _conn is None:
        logger.info("Creating new DuckDB connection")
        _conn = duckdb.connect(':memory:')
        _conn.execute("INSTALL httpfs; LOAD httpfs;")
        _conn.execute("SET enable_http_metadata_cache=true;")
        _conn.execute("SET s3_region='us-east-1';")
    return _conn


def run_soda_checks(checks_config: Dict[str, Any], conn: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    """
    Run data quality checks using DuckDB SQL.

    This is a simplified version that runs basic SQL checks.
    For full Soda Core functionality, use the soda-core library.
    """
    results = {
        'total_checks': 0,
        'passed': 0,
        'failed': 0,
        'warnings': 0,
        'failures': []
    }

    table_name = checks_config.get('table')
    s3_path = checks_config.get('s3_path')
    checks = checks_config.get('checks', [])

    logger.info(f"Running {len(checks)} checks on table: {table_name}")

    # Create view for the table
    conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{s3_path}')")

    for check in checks:
        results['total_checks'] += 1
        check_name = check.get('name', f'Check #{results["total_checks"]}')
        check_sql = check.get('sql')
        check_type = check.get('type', 'boolean')

        try:
            result = conn.execute(check_sql).fetchone()[0]

            if check_type == 'boolean':
                # Boolean checks must return True
                if result:
                    results['passed'] += 1
                    logger.info(f"✓ PASSED: {check_name}")
                else:
                    results['failed'] += 1
                    results['failures'].append({
                        'check': check_name,
                        'sql': check_sql,
                        'result': result
                    })
                    logger.error(f"✗ FAILED: {check_name}")

            elif check_type == 'count':
                # Count checks must return 0
                if result == 0:
                    results['passed'] += 1
                    logger.info(f"✓ PASSED: {check_name}")
                else:
                    results['failed'] += 1
                    results['failures'].append({
                        'check': check_name,
                        'sql': check_sql,
                        'count': result
                    })
                    logger.error(f"✗ FAILED: {check_name} - Found {result} violations")

        except Exception as e:
            results['failed'] += 1
            results['failures'].append({
                'check': check_name,
                'error': str(e)
            })
            logger.error(f"✗ ERROR: {check_name} - {str(e)}")

    return results


def send_sns_alert(results: Dict[str, Any], context: Any):
    """Send SNS alert if checks failed."""
    if not SNS_TOPIC_ARN:
        logger.warning("No SNS topic configured, skipping alert")
        return

    sns = boto3.client('sns')

    message = f"""
Data Quality Checks Failed

Function: {context.function_name}
Request ID: {context.request_id}

Results:
- Total Checks: {results['total_checks']}
- Passed: {results['passed']}
- Failed: {results['failed']}
- Warnings: {results['warnings']}

Failures:
{json.dumps(results['failures'], indent=2)}

Please investigate and fix data quality issues.
"""

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject='Data Quality Checks Failed',
        Message=message
    )
    logger.info(f"Sent SNS alert to {SNS_TOPIC_ARN}")


def lambda_handler(event, context):
    """
    Lambda handler for running data quality checks.

    Expected event format:
    {
        "checks": [
            {
                "table": "silver_transactions",
                "s3_path": "s3://bucket/path/*.parquet",
                "checks": [
                    {
                        "name": "No duplicate doc_ids",
                        "type": "count",
                        "sql": "SELECT COUNT(*) - COUNT(DISTINCT doc_id) FROM silver_transactions"
                    }
                ]
            }
        ]
    }
    """
    logger.info(f"Running data quality checks: {json.dumps(event)}")

    try:
        conn = get_duckdb_connection()

        all_results = {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'check_sets': []
        }

        for check_config in event.get('checks', []):
            results = run_soda_checks(check_config, conn)

            all_results['total_checks'] += results['total_checks']
            all_results['passed'] += results['passed']
            all_results['failed'] += results['failed']
            all_results['warnings'] += results['warnings']
            all_results['check_sets'].append({
                'table': check_config.get('table'),
                'results': results
            })

        # Send alert if checks failed
        if all_results['failed'] > 0:
            send_sns_alert(all_results, context)

            # Fail the Lambda to trigger Step Functions Catch
            raise Exception(
                f"Data quality checks failed: {all_results['failed']} failures out of {all_results['total_checks']} checks"
            )

        logger.info(f"All checks passed! {all_results['passed']}/{all_results['total_checks']}")

        return {
            'statusCode': 200,
            'body': json.dumps(all_results)
        }

    except Exception as e:
        logger.error(f"Error running data quality checks: {str(e)}")
        raise
