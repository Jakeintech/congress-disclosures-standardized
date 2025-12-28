# Sprint 2: Gold Layer Lambda Functions

**Sprint Goal**: Create all Gold layer Lambda function wrappers for dimensions, facts, and aggregates

**Duration**: Week 2 (Dec 23-27, 2025)
**Story Points**: 48
**Status**: ✅ Complete (10/10 stories, 48/48 points)

---

## Sprint Objectives

### Primary Goal 🎯
Wrap all existing Python scripts as Lambda functions to enable Step Functions orchestration of the Gold layer.

### Key Results
1. ✅ 3 dimension builder Lambdas created (dim_members, dim_assets, dim_bills)
2. ✅ 3 fact builder Lambdas created (fact_transactions, fact_filings, fact_lobbying)
3. ✅ 2 aggregate builder Lambdas created (trending_stocks, member_stats)
4. ✅ Extraction versioning infrastructure deployed (enables iterative quality improvements)
5. ✅ 20 unit tests passing (80%+ coverage for Gold wrappers)
6. ✅ All Lambdas tested individually
7. ✅ Terraform deployed successfully

**Deferred to Sprint 3**:
- dim_lobbyists, dim_dates (dimensions)
- fact_cosponsors, fact_amendments (facts)
- All other aggregates deferred to Sprint 3/4

---

## Sprint Backlog

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| STORY-016 | Create build_dim_members Lambda wrapper | 5 | P0 |
| STORY-017 | Create build_dim_assets Lambda wrapper | 5 | P1 |
| STORY-018 | Create build_dim_bills Lambda wrapper | 5 | P1 |
| STORY-021 | Create build_fact_transactions Lambda wrapper | 8 | P0 |
| STORY-022 | Create build_fact_filings Lambda wrapper | 5 | P0 |
| STORY-023 | Create build_fact_lobbying Lambda wrapper | 5 | P1 |
| STORY-026 | Create compute_trending_stocks Lambda wrapper | 3 | P1 |
| STORY-027 | Create compute_member_stats Lambda wrapper | 3 | P1 |
| STORY-052 | Write unit tests - Sprint 2 Gold layer wrappers | 4 | P0 |
| STORY-054 | Extraction versioning infrastructure | 5 | P0 |
| **Total** | **10 stories** | **48** | |

**Changes from Original Plan**:
- ❌ Deferred STORY-019: dim_lobbyists (3 points) → Sprint 3
- ❌ Deferred STORY-020: dim_dates (3 points) → Sprint 3
- ❌ Deferred STORY-024: fact_cosponsors (3 points) → Sprint 3
- ❌ Deferred STORY-025: fact_amendments (3 points) → Sprint 3
- ✅ Added STORY-052: Unit tests for Gold wrappers (4 points)
- ✅ Added STORY-054: Extraction versioning infrastructure (5 points)

---

## Day-by-Day Plan

### Day 1-2 (Mon-Tue, Dec 23-24): Dimension Builders (15 points)
- STORY-016: dim_members (P0) - 5 hours
- STORY-017: dim_assets (P1) - 5 hours
- STORY-018: dim_bills (P1) - 5 hours

**Goal**: 3 dimension Lambdas deployed and tested

---

### Day 3 (Wed, Dec 25): Fact Builders + Extraction Versioning (18 points)
- STORY-021: fact_transactions (P0) - 8 hours
- STORY-022: fact_filings (P0) - 5 hours
- **STORY-054: Extraction versioning infrastructure (P0) - 5 hours** ⭐ **CRITICAL FOR DATA QUALITY**
  - Add `__version__` to all 6 extractors (type_p, type_a, type_t, type_x, type_d, type_w)
  - Update extraction metadata to include version fields (`extractor_version`, `extractor_class`, `baseline_version`)
  - Create DynamoDB `extraction_versions` table (tracks quality metrics per version)
  - Implement multi-version Silver storage (`silver/objects/filing_type=type_p/extractor_version=1.0.0/`)
  - Add S3 lifecycle policy (expire old versions after 90 days)
  - Update Gold layer scripts to be version-aware (read from specific extractor versions)

**Goal**: Core fact tables operational + extraction versioning foundation established

**Why This Matters**: Enables iterative extraction quality improvements without massive reprocessing. When we improve Type P extraction from 87% → 94% accuracy, we can reprocess just 2024-2025 (1,200 PDFs) instead of ALL years (50,000 PDFs). See `docs/agile/DATA_QUALITY_AND_VERSIONING_STRATEGY.md` for full strategy.

---

### Day 4 (Thu, Dec 26): Fact Builders + Aggregates (11 points)
- STORY-023: fact_lobbying (P1) - 5 hours
- STORY-026: trending_stocks (P1) - 3 hours
- STORY-027: member_stats (P1) - 3 hours

**Goal**: Lobbying facts + key aggregates complete

---

### Day 5 (Fri, Dec 27): Testing + Review (4 points)
- STORY-052: Write unit tests for Gold wrappers (4 hours)
  - 20 tests across 8 Lambda functions
  - Coverage target: 80%
  - pytest + moto for AWS mocking
- Sprint Review (1 hour) - Demo all 8 Lambdas
- Sprint Retrospective (1 hour)

**Goal**: 20 unit tests passing, all Lambdas production-ready

---

## Lambda Wrapper Pattern

**All Gold Lambdas follow this pattern**:

```python
# ingestion/lambdas/build_dim_members/handler.py
import sys
import os

# Add scripts directory to path
sys.path.insert(0, '/opt/python/scripts')

def lambda_handler(event, context):
    """Lambda wrapper for build_dim_members script."""
    from build_dim_members_simple import main

    # Extract parameters from event
    rebuild = event.get('rebuild', False)
    incremental_date = event.get('incremental_date')

    # Run the script
    result = main(
        rebuild=rebuild,
        incremental_date=incremental_date
    )

    return {
        'statusCode': 200,
        'body': result
    }
```

**Terraform Pattern**:
```hcl
resource "aws_lambda_function" "build_dim_members" {
  function_name = "${local.name_prefix}-build-dim-members"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  role          = aws_iam_role.gold_lambda_role.arn
  timeout       = 600
  memory_size   = 2048

  filename         = "${path.module}/../../lambda_packages/build_dim_members.zip"
  source_code_hash = filebase64sha256("${path.module}/../../lambda_packages/build_dim_members.zip")

  layers = [
    aws_lambda_layer_version.data_processing.arn
  ]

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      AWS_REGION     = var.aws_region
    }
  }
}
```

---

## Definition of Done (Sprint Level)

- [ ] All 8 Lambda functions created (3 dim + 3 fact + 2 agg)
- [ ] All functions packaged and deployed via Terraform
- [ ] Each function tested individually (invoke with sample data)
- [ ] 20 unit tests added (≥80% coverage)
- [ ] Documentation updated (Lambda requirements spec)
- [ ] Sprint review completed
- [ ] No critical bugs

### Deferred Stories (Sprint 3)
- [ ] STORY-019: dim_lobbyists (3 points)
- [ ] STORY-020: dim_dates (3 points)
- [ ] STORY-024: fact_cosponsors (3 points)
- [ ] STORY-025: fact_amendments (3 points)

---

## Success Metrics

- [ ] 8 Lambda functions deployed (3 dim + 3 fact + 2 agg)
- [ ] All functions tested successfully with sample data
- [ ] Terraform apply successful
- [ ] 20 unit tests passing (STORY-052)
- [ ] Test coverage ≥ 80% for Gold layer wrappers
- [ ] 4 lower-priority Lambdas deferred to Sprint 3 (capacity management)

### Capacity Planning
- **Planned Points**: 43
- **Team Velocity**: 40-45 points/week (AI-assisted development)
- **Buffer**: Included in realistic estimates
- **Deferred**: 12 points moved to Sprint 3 for sustainable pace

---

**Sprint Owner**: Engineering Team Lead
**Last Updated**: 2025-12-14
