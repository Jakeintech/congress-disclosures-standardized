# STORY-034: Write 70+ Unit Tests

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 8 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** QA engineer
**I want** comprehensive unit test coverage
**So that** we achieve 80%+ code coverage

## Acceptance Criteria
- **GIVEN** All Lambda functions
- **WHEN** I run `pytest tests/unit/`
- **THEN** 70+ tests execute
- **AND** Coverage ≥ 80%
- **AND** All tests passing

## Technical Tasks
- [ ] Create test files for all Lambdas
- [ ] Write tests for update detection (9 tests)
- [ ] Write tests for Bronze ingestion (9 tests)
- [ ] Write tests for Silver transformation (12 tests)
- [ ] Write tests for Gold builders (25 tests)
- [ ] Write tests for utilities (15 tests)
- [ ] Configure pytest-cov
- [ ] Add coverage reporting

## Test Structure
```
tests/unit/
├── lambdas/
│   ├── test_check_house_fd_updates.py (6 tests)
│   ├── test_house_fd_ingest_zip.py (6 tests)
│   ├── test_extract_document.py (8 tests)
│   ├── test_build_fact_transactions.py (10 tests)
│   └── ... (30 more test files)
├── lib/
│   ├── test_s3_utils.py (5 tests)
│   ├── test_parquet_writer.py (5 tests)
│   └── test_extraction_pipeline.py (5 tests)
```

## Coverage Target
- Lambda functions: 80%+
- Utilities: 85%+
- Extractors: 80%+
- Overall: 80%+

## Estimated Effort: 8 hours (spread over 2 days)
**Target**: Jan 2-3, 2026
