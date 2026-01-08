# Terraform Refactor Quick Reference

## One-Page Summary

### FILES TO DELETE (8 files)
```
api_gateway_assets.tf
api_gateway_members.tf
api_gateway_transactions.tf
api_costs_route.tf
api_storage_route.tf
lambda_stub.tf
lambdas_analytics.tf
lambdas_data_quality.tf
```

### FILES TO MERGE INTO api_lambdas.tf (2 files → delete)
```
api_gateway_congress.tf      → Add routes to local.api_lambdas map
api_gateway_lobbying.tf      → Add routes to local.api_lambdas map
```

### FILES TO CONSOLIDATE (7 merges)
```
lambda.tf + lambda_congress.tf + lambda_lobbying.tf 
  → Create: lambda_bronze_layer.tf

structured_extraction.tf + structured_code_extraction.tf 
  → Create: lambda_silver_layer.tf

sqs.tf + sqs_congress.tf + sqs_lobbying.tf + (structured_extraction.tf sqs part)
  → Create: sqs_queues.tf

step_functions.tf (extract 4 lambdas & 3 log groups)
  → Create: lambda_orchestration.tf

cloudwatch.tf + cloudwatch_congress.tf (all log groups)
  → Create: cloudwatch_logs.tf

variables.tf + variables_congress.tf
  → Merge into single variables.tf
```

### FILES TO CREATE (3 new)
```
api_authorizer.tf              (Lambda authorizer for API auth)
cloudwatch_dashboards.tf       (Operational dashboards)
lambda_orchestration.tf        (Step Functions check/publish lambdas)
```

### REMOVE FROM EXISTING FILES
```
dynamodb.tf
  - Remove: aws_dynamodb_table.house_fd_documents (legacy)

lambda_congress.tf
  - Remove: aws_lambda_layer_version.congress_pandas_layer (duplicate)
```

---

## What to Do FIRST

1. **Read the full reports**:
   - `docs/TERRAFORM_AUDIT.md` - Comprehensive audit
   - `docs/TERRAFORM_RESOURCE_MAPPING.md` - Detailed resource inventory

2. **Create feature branch**:
   ```bash
   git checkout -b terraform/modernization
   ```

3. **Backup current state**:
   ```bash
   mkdir -p infra/terraform/.backup
   cp infra/terraform/*.tf infra/terraform/.backup/
   terraform -chdir=infra/terraform state pull > infra/terraform/.backup/terraform.tfstate.backup
   ```

4. **Phase 1: DELETE (low risk - no resource changes)**
   - Delete: api_gateway_assets.tf, api_gateway_members.tf, api_gateway_transactions.tf, api_costs_route.tf, api_storage_route.tf
   - Delete: lambda_stub.tf, lambdas_analytics.tf, lambdas_data_quality.tf
   - Test: `terraform plan` should show 0 changes
   - Commit: "refactor: delete duplicate/stub Terraform files"

5. **Phase 2: REMOVE (low risk - deletes unused resources)**
   - Remove `aws_dynamodb_table.house_fd_documents` from dynamodb.tf
   - Remove `aws_lambda_layer_version.congress_pandas_layer` from lambda_congress.tf
   - Test: `terraform plan` should show 2 resource deletions
   - Verify no apps depend on these resources first!
   - Commit: "refactor: remove legacy/unused Terraform resources"

6. **Phase 3: CONSOLIDATE (medium risk - reorganization)**
   - Move log groups to new cloudwatch_logs.tf
   - Move SQS queues to new sqs_queues.tf
   - Move orchestration lambdas to new lambda_orchestration.tf
   - Each commit after testing
   - Test: `terraform plan` should show 0 changes

7. **Phase 4: MERGE API ROUTES (medium risk)**
   - Add Congress/Lobbying routes to api_lambdas.tf local.api_lambdas map
   - Test: `terraform plan` should show no changes to API endpoints
   - Delete old files
   - Commit: "refactor: consolidate API Gateway routes into api_lambdas.tf"

8. **Phase 5: CREATE MISSING RESOURCES (medium risk)**
   - Create api_authorizer.tf with Lambda authorizer
   - Create cloudwatch_dashboards.tf with dashboards
   - Test: `terraform plan` should show new resources
   - Commit: "feat: add Lambda authorizer and CloudWatch dashboards"

---

## Key Points

### Why Consolidate?
- **Maintenance**: Single source of truth for each component
- **Discoverability**: All Lambdas by layer in one place
- **Consistency**: Standard naming, similar structures

### What Won't Change?
- No actual AWS infrastructure changes (except Phase 2 deletions)
- All routes/endpoints remain functional
- All Lambda functions work identically

### What Will Change?
- File organization
- Terraform source layout (not infrastructure)
- Easier to navigate and maintain

### Testing Strategy
```bash
# After each phase
terraform plan -out=tfplan
  # Should show: either "0 changes" or only expected changes
terraform apply tfplan
  # Apply the changes
```

### Rollback Plan
If issues arise:
```bash
git reset --hard HEAD~1
terraform -chdir=infra/terraform state pull > current.tfstate
cp .backup/terraform.tfstate.backup terraform.tfstate
terraform refresh
```

---

## Files to Keep As-Is

```
✓ api_gateway.tf              (HTTP API, stage, logging)
✓ api_lambdas.tf             (Will consolidate Congress/Lobbying routes into locals)
✓ bucket_policy.tf
✓ budgets.tf
✓ dynamodb_api.tf            (API layer tables)
✓ eventbridge.tf             (Scheduled rules - keep)
✓ github_oidc.tf
✓ glue_catalog.tf
✓ iam.tf                     (Will add api_authorizer role to api_authorizer.tf)
✓ lambdas_gold_transformations.tf  (Rename to lambdas_gold_layer.tf for consistency)
✓ lambda_packaging.tf
✓ main.tf
✓ outputs.tf                 (May need updates for consolidated outputs)
✓ s3.tf
✓ seeds.tf
✓ sns.tf                     (Add cross-dataset-correlation topic)
✓ state_backend.tf
✓ backend.tf
✓ step_functions.tf          (Will remove 4 lambdas that move to lambda_orchestration.tf)
✓ terraform.tfvars
✓ terraform.tfvars.example
✓ variables.tf               (Merge with variables_congress.tf)
```

---

## Final File Structure Goal

```
infra/terraform/
├── core/
│   ├── main.tf
│   ├── variables.tf                    # merged from variables_congress.tf
│   ├── outputs.tf
│   ├── backend.tf
│   └── state_backend.tf
├── storage/
│   ├── s3.tf
│   └── glue_catalog.tf
├── database/
│   ├── dynamodb.tf                     # removed house_fd_documents
│   └── dynamodb_api.tf
├── queues/
│   └── sqs_queues.tf                   # NEW - consolidated
├── security/
│   ├── iam.tf
│   └── api_authorizer.tf               # NEW
├── lambdas/
│   ├── lambda_bronze_layer.tf          # NEW - consolidated
│   ├── lambda_silver_layer.tf          # NEW - consolidated
│   ├── lambdas_gold_layer.tf           # RENAMED (was lambdas_gold_transformations.tf)
│   ├── lambda_orchestration.tf         # NEW - from step_functions.tf
│   ├── api_lambdas.tf                  # merged Congress/Lobbying routes
│   └── lambda_packaging.tf
├── api/
│   └── api_gateway.tf
├── orchestration/
│   ├── step_functions.tf               # removed 4 lambdas
│   ├── eventbridge.tf
│   └── sns.tf
├── monitoring/
│   ├── cloudwatch_logs.tf              # NEW - consolidated
│   └── cloudwatch_dashboards.tf        # NEW
├── config/
│   ├── terraform.tfvars
│   ├── terraform.tfvars.example
│   ├── budgets.tf
│   ├── bucket_policy.tf
│   ├── github_oidc.tf
│   └── seeds.tf
└── .backup/                            # local backup (git-ignored)
```

Files deleted from terraform directory:
- api_gateway_assets.tf
- api_gateway_members.tf
- api_gateway_transactions.tf
- api_costs_route.tf
- api_storage_route.tf
- api_gateway_congress.tf (merged into api_lambdas.tf)
- api_gateway_lobbying.tf (merged into api_lambdas.tf)
- lambda_stub.tf
- lambdas_analytics.tf
- lambdas_data_quality.tf
- lambda.tf (merged into lambda_bronze_layer.tf)
- lambda_congress.tf (merged into lambda_bronze_layer.tf)
- lambda_lobbying.tf (merged into lambda_bronze_layer.tf)
- structured_extraction.tf (merged into lambda_silver_layer.tf)
- structured_code_extraction.tf (merged into lambda_silver_layer.tf)
- sqs.tf (merged into sqs_queues.tf)
- sqs_congress.tf (merged into sqs_queues.tf)
- sqs_lobbying.tf (merged into sqs_queues.tf)
- cloudwatch.tf (merged into cloudwatch_logs.tf)
- cloudwatch_congress.tf (merged into cloudwatch_logs.tf)
- variables_congress.tf (merged into variables.tf)
- lambdas_gold_transformations.tf (renamed to lambdas_gold_layer.tf)

Total: 43 files → 25 files
