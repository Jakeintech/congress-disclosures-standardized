# STORY-008: Fix Terraform Variable Duplication

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 2 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** DevOps engineer
**I want** unique Lambda function names (not duplicated)
**So that** state machine references correct functions

## Acceptance Criteria

### Scenario 1: Each Lambda has unique name
- **GIVEN** Terraform `step_functions.tf` lines 131-164
- **WHEN** I review Lambda function name variables
- **THEN** Each variable has unique value
- **AND** No copy-paste duplicates

## Technical Tasks
- [ ] Review `step_functions.tf` lines 131-164
- [ ] Identify duplicated function names
- [ ] Create unique names for each function
- [ ] Update state machine template substitution
- [ ] Run `terraform plan` to verify changes

## Current Issue
```hcl
# WRONG - All point to same function
LAMBDA_COMPUTE_TRENDING_STOCKS   = "congress-disclosures-compute-trending-stocks-duckdb"
LAMBDA_COMPUTE_DOCUMENT_QUALITY  = "congress-disclosures-compute-trending-stocks-duckdb"  # DUPLICATE!
LAMBDA_COMPUTE_MEMBER_STATS      = "congress-disclosures-compute-trending-stocks-duckdb"  # DUPLICATE!
```

## Fix
```hcl
# CORRECT - Unique names
LAMBDA_COMPUTE_TRENDING_STOCKS   = "congress-disclosures-compute-trending-stocks-duckdb"
LAMBDA_COMPUTE_DOCUMENT_QUALITY  = "congress-disclosures-compute-document-quality-duckdb"
LAMBDA_COMPUTE_MEMBER_STATS      = "congress-disclosures-compute-member-stats-duckdb"
```

## Estimated Effort: 2 hours

**Target**: Dec 18, 2025
