# Terraform Infrastructure Modernization Guide

## Overview

This modernization effort reorganizes the Terraform infrastructure from 43 scattered files into a logical, maintainable 25-file structure aligned with the lakehouse architecture (Bronze → Silver → Gold).

**Status**: Planning Phase  
**Scope**: File organization only (no AWS resource changes except 2 deletions)  
**Effort**: 5-8 sprints of implementation  
**Risk Level**: Low-to-Medium  

---

## Quick Links

1. **[TERRAFORM_AUDIT.md](./TERRAFORM_AUDIT.md)** - Full 330-line audit report
   - Identifies redundancies, deprecated patterns, missing resources
   - Detailed analysis of 200+ AWS resources
   - Architecture recommendations

2. **[TERRAFORM_RESOURCE_MAPPING.md](./TERRAFORM_RESOURCE_MAPPING.md)** - 486-line resource inventory
   - Exact resource names and file locations
   - What to delete, consolidate, and create
   - Per-file action items

3. **[TERRAFORM_REFACTOR_QUICK_REFERENCE.md](./TERRAFORM_REFACTOR_QUICK_REFERENCE.md)** - 1-page cheat sheet
   - File deletion list
   - 5-phase implementation plan
   - Rollback procedures

---

## At a Glance

### Files to Delete (8)
```
api_gateway_assets.tf          (4 duplicate routes)
api_gateway_members.tf         (3 duplicate routes)
api_gateway_transactions.tf    (1 duplicate route)
api_costs_route.tf             (1 duplicate route)
api_storage_route.tf           (1 duplicate route)
lambda_stub.tf                 (placeholder)
lambdas_analytics.tf           (unfinished, not in plan)
lambdas_data_quality.tf        (Soda framework not needed)
```

### Files to Consolidate (11)
```
lambda.tf + lambda_congress.tf + lambda_lobbying.tf
  → lambda_bronze_layer.tf (ingestion layer)

structured_extraction.tf + structured_code_extraction.tf
  → lambda_silver_layer.tf (extraction layer)

sqs.tf + sqs_congress.tf + sqs_lobbying.tf
  → sqs_queues.tf (all queues)

step_functions.tf (extract 4 lambdas)
  → lambda_orchestration.tf (orchestration)

cloudwatch.tf + cloudwatch_congress.tf
  → cloudwatch_logs.tf (all log groups)

api_gateway_congress.tf + api_gateway_lobbying.tf
  → merge into api_lambdas.tf (unified routes)

variables.tf + variables_congress.tf
  → single variables.tf
```

### Files to Create (3)
```
api_authorizer.tf              (Lambda authorizer for API authentication)
cloudwatch_dashboards.tf       (Operational dashboards)
lambda_orchestration.tf        (Step Functions orchestration lambdas)
```

### Resources to Remove (2)
```
dynamodb.tf: aws_dynamodb_table.house_fd_documents (legacy)
lambda_congress.tf: aws_lambda_layer_version.congress_pandas_layer (duplicate)
```

---

## Why This Reorganization?

### Current Pain Points (43 files)
- API Gateway routes defined in 8 different files → maintenance nightmare
- Lambda functions scattered across 7 files → hard to find related code
- SQS queues spread across 4 files → unclear which queues exist
- Log groups defined inline in Lambda files → difficult to manage retention
- Duplicate routes and resources → terraform plans show spurious changes

### After Reorganization (25 files)
- Single source of truth for each component
- Logical grouping by layer (Bronze/Silver/Gold) and function (API, orchestration)
- Easy to find related resources
- Consistent naming and structure
- 44% fewer files to maintain

---

## Implementation Phases

### Phase 1: Delete (Low Risk)
Delete 8 files with no resource changes. Test `terraform plan` shows 0 changes.

### Phase 2: Remove (Low Risk)
Remove 2 unused resources from existing files. Verify no production code depends on them.

### Phase 3: Consolidate (Medium Risk)
Move log groups, queues, and orchestration lambdas to new files. Each consolidation = 0 changes in `terraform plan`.

### Phase 4: Merge API Routes (Medium Risk)
Add Congress and Lobbying endpoints to api_lambdas.tf locals. Delete old files. No API changes.

### Phase 5: Create Missing Resources (Medium Risk)
Add Lambda authorizer and CloudWatch dashboards. New resources = infrastructure enhancement.

See [TERRAFORM_REFACTOR_QUICK_REFERENCE.md](./TERRAFORM_REFACTOR_QUICK_REFERENCE.md) for detailed phase breakdown.

---

## Target Architecture

```
infra/terraform/
├── core/
│   ├── main.tf                           # Locals, provider, data sources
│   ├── variables.tf                      # All variables (merged from variables_congress.tf)
│   ├── outputs.tf                        # All outputs
│   ├── backend.tf                        # Backend configuration
│   └── state_backend.tf                  # State locking table
│
├── storage/
│   ├── s3.tf                             # Data lake bucket
│   └── glue_catalog.tf                   # Glue Data Catalog
│
├── database/
│   ├── dynamodb.tf                       # Pipeline state tables (removed legacy table)
│   └── dynamodb_api.tf                   # API layer tables
│
├── queues/                               # ← NEW DIRECTORY
│   └── sqs_queues.tf                     # All SQS queues + DLQs + event mappings
│
├── security/
│   ├── iam.tf                            # Lambda execution roles
│   └── api_authorizer.tf                 # API authorizer role + lambda
│
├── lambdas/
│   ├── lambda_bronze_layer.tf            # Ingestion: ingest, index_to_silver, extract, congress, lobbying
│   ├── lambda_silver_layer.tf            # Extraction: code-based extraction
│   ├── lambdas_gold_layer.tf             # Transformations: dimension/fact builders
│   ├── api_lambdas.tf                    # API: 40+ endpoint handlers
│   ├── lambda_orchestration.tf           # Orchestration: Step Functions check/publish lambdas
│   └── lambda_packaging.tf               # Lambda packaging
│
├── api/
│   └── api_gateway.tf                    # HTTP API + stage + logging
│
├── orchestration/
│   ├── step_functions.tf                 # State machines (no lambdas)
│   ├── eventbridge.tf                    # Scheduled rules
│   └── sns.tf                            # Alert topics
│
├── monitoring/
│   ├── cloudwatch_logs.tf                # All log groups
│   └── cloudwatch_dashboards.tf          # Operational dashboards
│
└── config/
    ├── terraform.tfvars                  # Environment config
    ├── terraform.tfvars.example          # Template
    ├── budgets.tf                        # Cost alerts
    ├── bucket_policy.tf                  # S3 bucket policy
    ├── github_oidc.tf                    # GitHub Actions OIDC
    └── seeds.tf                          # Seed data
```

---

## Key Statistics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Files | 43 | 25 | -18 (42% reduction) |
| API Files | 11 | 2 | -9 (82% reduction) |
| Lambda Files | 7 | 5 | -2 (28% reduction) |
| Queue Files | 4 | 1 | -3 (75% reduction) |
| Log Group Locations | 8 | 1 | -7 (87% reduction) |
| Duplicate Routes | 16 | 0 | Eliminated |
| Duplicate Resources | 3+ | 0 | Eliminated |

---

## Success Criteria

### Phase Completion Checklist
- [ ] All files properly committed to git
- [ ] `terraform plan` shows expected changes only
- [ ] `terraform apply` succeeds without errors
- [ ] No drift detected in AWS resources
- [ ] All Lambda functions deployed correctly
- [ ] API endpoints respond normally
- [ ] No breaking changes to infrastructure

### Code Quality
- [ ] Consistent variable naming across files
- [ ] All outputs properly documented
- [ ] No unused variables or outputs
- [ ] Comments explain non-obvious logic
- [ ] Resource names follow pattern: `${local.name_prefix}-component-name`

### Documentation
- [ ] README updated with new file structure
- [ ] Contributing guide updated
- [ ] Output mapping documented
- [ ] Variable interdependencies noted

---

## Rollback Strategy

If issues arise at any phase:

1. **Immediate**: `git reset --hard <good-commit>`
2. **Terraform**: `terraform refresh` to sync with real state
3. **Restore**: Terraform state auto-recovery from locking table

See [TERRAFORM_REFACTOR_QUICK_REFERENCE.md](./TERRAFORM_REFACTOR_QUICK_REFERENCE.md#rollback-plan) for detailed rollback commands.

---

## Next Steps

1. **Read the full audit** ([TERRAFORM_AUDIT.md](./TERRAFORM_AUDIT.md))
2. **Review resource mapping** ([TERRAFORM_RESOURCE_MAPPING.md](./TERRAFORM_RESOURCE_MAPPING.md))
3. **Create feature branch**: `git checkout -b terraform/modernization`
4. **Follow Phase 1-5 plan** in [TERRAFORM_REFACTOR_QUICK_REFERENCE.md](./TERRAFORM_REFACTOR_QUICK_REFERENCE.md)
5. **Create PRs for review** (one per phase)
6. **Test thoroughly** before merging each phase
7. **Update docs** as you complete refactoring

---

## Contact & Questions

Refer to:
- CLAUDE.md - Project architecture overview
- docs/ARCHITECTURE.md - Detailed system design
- docs/DEPLOYMENT.md - Infrastructure deployment guide

For issues or questions about this modernization, see CONTRIBUTING.md.

---

## Appendix: Resource Tally

### Resources Being Deleted
- 2 DynamoDB tables (house_fd_documents)
- 1 Lambda layer (congress_pandas_layer)
- 16 API Gateway routes/integrations
- 1 stub Lambda function
- 6 Soda quality framework resources

Total: 26 resources removed

### Resources Being Created
- 1 Lambda authorizer
- 1 authorizer IAM role
- 2 CloudWatch dashboards
- 1 SNS topic (cross-dataset-correlation)
- 1+ IAM roles for new components

Total: ~5 resources created

**Net impact**: -21 resources (cleanup), +5 resources (new features) = -16 resources overall

This is intentional - we're reducing technical debt while adding critical features (API authentication, monitoring).

---

**Last Updated**: 2026-01-06  
**Status**: Ready for Phase 1 implementation  
**Maintainer**: See docs/CONTRIBUTING.md
