# GitHub Actions with Step Functions Integration

This document explains how GitHub Actions workflows trigger AWS Step Functions for pipeline orchestration.

## Overview

As of STORY-006, all GitHub Actions workflows now trigger AWS Step Functions state machines instead of running Python scripts directly. This provides:

- ✅ Modern orchestration with AWS Step Functions
- ✅ Better error handling and retry logic
- ✅ Visual workflow monitoring in AWS Console
- ✅ Automatic wait loops until completion
- ✅ Comprehensive execution logging

## Workflows

### 1. Daily Incremental Update (`daily_incremental.yml`)

**Purpose**: Automatically ingests new House financial disclosure filings daily.

**Schedule**: Every day at 6:00 AM UTC

**Triggers**:
- Cron: `0 6 * * *` (6:00 AM UTC daily)
- Manual: `workflow_dispatch` (for testing)

**Step Functions**: `house_fd_pipeline`

**Execution Flow**:
1. Configures AWS credentials via OIDC
2. Starts Step Functions execution
3. Waits for completion (max 2 hours)
4. Logs execution status and output
5. Fails if pipeline fails

**Required Secrets**:
- `AWS_ROLE_ARN`: IAM role for GitHub Actions OIDC
- `HOUSE_FD_STATE_MACHINE_ARN`: ARN of House FD pipeline state machine

**Example Manual Trigger**:
```bash
# Via GitHub UI: Actions → Daily Incremental Update → Run workflow

# Via GitHub CLI:
gh workflow run daily_incremental.yml
```

### 2. Initial Load (`initial_load.yml`)

**Purpose**: Full reset and initial data load for a specific year.

**Schedule**: Manual only (requires confirmation)

**Triggers**:
- Manual: `workflow_dispatch` with parameters

**Parameters**:
- `year`: Year to process (required, default: 2025)
- `confirm_reset`: Type "RESET" to confirm (safety check)

**Step Functions**: `house_fd_pipeline`

**Execution Flow**:
1. Validates confirmation input
2. Configures AWS credentials
3. Starts Step Functions with `execution_type: manual`
4. Waits for completion
5. Reports results

**Required Secrets**:
- `AWS_ROLE_ARN`: IAM role for GitHub Actions OIDC
- `HOUSE_FD_STATE_MACHINE_ARN`: ARN of House FD pipeline state machine

**Example Manual Trigger**:
```bash
# Via GitHub UI:
# 1. Go to Actions → Initial Load (Full Reset)
# 2. Click "Run workflow"
# 3. Enter year: 2024
# 4. Enter confirm_reset: RESET

# Via GitHub CLI:
gh workflow run initial_load.yml \
  -f year=2024 \
  -f confirm_reset=RESET
```

### 3. Congress Daily Sync (`congress_daily_sync.yml`)

**Purpose**: Synchronizes bills and member data from Congress.gov API.

**Schedule**: Every day at 3:00 AM UTC

**Triggers**:
- Cron: `0 3 * * *` (3:00 AM UTC daily)
- Manual: `workflow_dispatch`

**Step Functions**: `congress_pipeline`

**Execution Flow**:
1. Configures AWS credentials
2. Starts Congress.gov pipeline
3. Waits for completion
4. Logs results to S3

**Required Secrets**:
- `AWS_ROLE_ARN`: IAM role for GitHub Actions OIDC
- `CONGRESS_STATE_MACHINE_ARN`: ARN of Congress pipeline state machine

## How Wait Loops Work

All workflows implement a wait loop pattern:

```bash
# Start execution and capture ARN
EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --name "execution-name" \
  --input '{"key":"value"}' \
  --query 'executionArn' \
  --output text)

# Poll status every 30 seconds (max 2 hours)
while [ $SECONDS -lt $TIMEOUT ]; do
  STATUS=$(aws stepfunctions describe-execution \
    --execution-arn "$EXECUTION_ARN" \
    --query 'status' \
    --output text)
  
  if [ "$STATUS" = "SUCCEEDED" ]; then
    echo "✅ Success"
    exit 0
  elif [ "$STATUS" = "FAILED" ]; then
    echo "❌ Failed"
    exit 1
  fi
  
  sleep 30
done
```

**Timeout**: 2 hours (7200 seconds)

**Polling Interval**: 30 seconds

**Status Checks**:
- `SUCCEEDED` → Exit 0 (success)
- `FAILED`, `TIMED_OUT`, `ABORTED` → Exit 1 (failure)
- `RUNNING` → Continue waiting

## Required GitHub Secrets

Configure these secrets in GitHub repository settings:

### AWS Authentication
```
AWS_ROLE_ARN
  Example: arn:aws:iam::464813693153:role/github-actions-role
  Purpose: OIDC role for GitHub Actions to assume
```

### State Machine ARNs
```
HOUSE_FD_STATE_MACHINE_ARN
  Example: arn:aws:states:us-east-1:464813693153:stateMachine:congress-disclosures-house-fd-pipeline
  Purpose: House Financial Disclosures pipeline
  
CONGRESS_STATE_MACHINE_ARN
  Example: arn:aws:states:us-east-1:464813693153:stateMachine:congress-disclosures-congress-pipeline
  Purpose: Congress.gov bills and members pipeline
```

## Getting State Machine ARNs from Terraform

After deploying infrastructure with Terraform:

```bash
# Get all state machine ARNs
terraform output house_fd_pipeline_arn
terraform output congress_pipeline_arn
terraform output lobbying_pipeline_arn

# Or get all outputs
terraform output
```

**Example Output**:
```
house_fd_pipeline_arn = "arn:aws:states:us-east-1:464813693153:stateMachine:congress-disclosures-house-fd-pipeline"
congress_pipeline_arn = "arn:aws:states:us-east-1:464813693153:stateMachine:congress-disclosures-congress-pipeline"
```

## Monitoring Executions

### GitHub Actions Logs
View logs in GitHub:
- Go to **Actions** tab
- Click on workflow run
- Expand step logs to see execution ARN and status updates

### AWS Step Functions Console
View detailed execution:
1. Go to [AWS Step Functions Console](https://console.aws.amazon.com/states/home)
2. Click on state machine name
3. Select execution by name (e.g., `daily-incremental-20260104-123456`)
4. View visual workflow, inputs, outputs, errors

### CloudWatch Logs
```bash
# Step Functions logs
aws logs tail /aws/vendedlogs/states/congress-disclosures-pipelines --follow

# Lambda logs (individual steps)
aws logs tail /aws/lambda/congress-disclosures-ingest-zip --follow
```

## Troubleshooting

### Error: "Execution ARN not captured"
**Cause**: AWS CLI might not be installed or configured

**Solution**: Verify AWS credentials step runs successfully

### Error: "Pipeline timed out after 2 hours"
**Cause**: State machine execution exceeded timeout

**Solutions**:
1. Check CloudWatch logs for stuck Lambda
2. Check SQS queue depth
3. Increase Lambda concurrency
4. Investigate failed steps in Step Functions console

### Error: "State machine not found"
**Cause**: Secret `STATE_MACHINE_ARN` not configured or incorrect

**Solutions**:
1. Run `terraform output` to get ARN
2. Add secret to GitHub repository settings
3. Verify ARN format is correct

### Execution Fails with "AccessDeniedException"
**Cause**: IAM role doesn't have permission to start execution

**Solution**: Verify `github_oidc.tf` grants `states:StartExecution` permission

### Manual Trigger Not Working
**Cause**: `workflow_dispatch` permissions or branch mismatch

**Solutions**:
1. Ensure you're on the correct branch (usually `main`)
2. Verify workflow file is in `.github/workflows/`
3. Check workflow syntax is valid YAML

## Testing

### Test Wait Loop Locally (Bash)
```bash
export STATE_MACHINE_ARN="arn:aws:states:..."

EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn "$STATE_MACHINE_ARN" \
  --name "test-$(date +%s)" \
  --input '{"execution_type":"manual","year":2025}' \
  --query 'executionArn' \
  --output text)

echo "Started: $EXECUTION_ARN"

# Check status
aws stepfunctions describe-execution \
  --execution-arn "$EXECUTION_ARN" \
  --query 'status'
```

### Test Manual Trigger (GitHub CLI)
```bash
# Install GitHub CLI
brew install gh  # macOS
# or: sudo apt install gh  # Ubuntu

# Authenticate
gh auth login

# Trigger workflow
gh workflow run daily_incremental.yml

# View run
gh run list --workflow=daily_incremental.yml
gh run view <run_id> --log
```

## Migration from Python Scripts (STORY-006)

**Before (Python Scripts)**:
```yaml
- name: Run Pipeline
  run: |
    python scripts/run_smart_pipeline.py --mode incremental
```

**After (Step Functions)**:
```yaml
- name: Trigger Pipeline (Step Functions)
  run: |
    EXECUTION_ARN=$(aws stepfunctions start-execution \
      --state-machine-arn ${{ secrets.HOUSE_FD_STATE_MACHINE_ARN }} \
      --input '{"execution_type":"scheduled"}' \
      --query 'executionArn' \
      --output text)
    
    # Wait loop...
```

**Benefits**:
- No Python dependencies needed in GitHub Actions
- Better error handling and retries via Step Functions
- Visual workflow monitoring
- Automatic CloudWatch logging
- Separation of concerns (orchestration vs. execution)

## Related Documentation

- [State Machine Flow](STATE_MACHINE_FLOW.md) - Detailed pipeline architecture (if available)
- [Deployment Guide](DEPLOYMENT.md) - Infrastructure setup (if available)
- [CLAUDE.md](../CLAUDE.md) - AI agent development context and repository architecture
- [Architecture Documentation](ARCHITECTURE.md) - Overall system design (if available)

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review AWS Step Functions execution in console
3. Check CloudWatch logs for detailed errors
4. Create issue with execution ARN and error details
