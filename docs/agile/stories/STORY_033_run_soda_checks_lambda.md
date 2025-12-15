# STORY-033: Create run_soda_checks Lambda

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 5 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** data quality engineer
**I want** Soda quality checks Lambda
**So that** we validate Gold layer data quality

## Acceptance Criteria
- **GIVEN** Soda YAML checks in `/soda/checks/`
- **WHEN** Lambda executes
- **THEN** Runs all quality checks against Parquet files
- **AND** Returns pass/fail/warn status
- **AND** Logs detailed results
- **AND** Raises error on critical failures

## Technical Tasks
- [ ] Create Lambda directory: `ingestion/lambdas/run_soda_checks/`
- [ ] Load Soda YAML checks from S3 or package
- [ ] Execute checks against S3 Parquet files
- [ ] Parse results (pass/fail/warn)
- [ ] Return structured response
- [ ] Package with soda-core layer

## Implementation
```python
from soda.scan import Scan

def lambda_handler(event, context):
    scan = Scan()
    scan.set_data_source_name("s3")

    # Add checks
    for check_file in ['silver_filings.yml', 'gold_transactions.yml']:
        scan.add_sodacl_yaml_file(f'/opt/soda/checks/{check_file}')

    # Execute
    scan.execute()

    # Parse results
    results = {
        'checks_run': scan.get_checks_count(),
        'checks_passed': scan.get_checks_passed_count(),
        'checks_failed': scan.get_checks_failed_count(),
        'status': 'passed' if scan.get_checks_failed_count() == 0 else 'failed'
    }

    if results['status'] == 'failed':
        raise Exception('Quality checks failed')

    return results
```

## Estimated Effort: 5 hours
**Target**: Jan 2, 2026
