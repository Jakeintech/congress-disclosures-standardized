# GitHub Actions Setup Guide

This guide explains how to configure GitHub Actions to trigger AWS Step Functions for automated pipeline execution.

## Overview

The daily incremental workflow (`.github/workflows/daily_incremental.yml`) triggers AWS Step Functions instead of running Python scripts directly. This provides:

- **Modern orchestration**: Use AWS Step Functions for complex pipeline logic
- **Better monitoring**: CloudWatch logs and Step Functions execution history
- **Automatic retries**: Built-in error handling and retry logic
- **Parallel execution**: Step Functions can run multiple tasks in parallel

## Required GitHub Secrets

The following secrets must be configured in your GitHub repository settings.

### Navigation to Secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** for each secret below

### Required Secrets

#### 1. AWS_ROLE_ARN
**Description**: ARN of the IAM role that GitHub Actions will assume to interact with AWS.

**Format**: `arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME`

**How to get this value**:
```bash
# After deploying infrastructure with Terraform
cd infra/terraform
terraform output github_actions_role_arn
```

**Example**: `arn:aws:iam::123456789012:role/congress-disclosures-github-actions`

**Setup instructions**:
1. Create an IAM role for GitHub OIDC (see [AWS GitHub OIDC Guide](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services))
2. Attach policies:
   - `AWSStepFunctionsFullAccess` (or custom policy with `states:StartExecution`, `states:DescribeExecution`)
   - Trust policy allowing GitHub Actions OIDC provider

#### 2. HOUSE_FD_STATE_MACHINE_ARN
**Description**: ARN of the House Financial Disclosures Step Functions state machine.

**Format**: `arn:aws:states:REGION:ACCOUNT_ID:stateMachine:STATE_MACHINE_NAME`

**How to get this value**:
```bash
# After deploying infrastructure with Terraform
cd infra/terraform
terraform output house_fd_pipeline_arn
```

**Example**: `arn:aws:states:us-east-1:123456789012:stateMachine:congress-disclosures-development-house-fd-pipeline`

---

## Workflow Configuration

### Daily Scheduled Execution

The workflow runs automatically every day at **6:00 AM UTC** (per STORY-006 requirements).

```yaml
on:
  schedule:
    - cron: '0 6 * * *'  # 6:00 AM UTC daily
```

### Manual Trigger (workflow_dispatch)

You can manually trigger the workflow with custom parameters:

1. Go to **Actions** → **Daily Incremental Update** → **Run workflow**
2. Optionally specify:
   - **year**: Year to process (defaults to current year)
   - **mode**: `incremental` or `full_refresh`

### Workflow Steps

1. **Configure AWS Credentials**: Assumes the IAM role using OIDC
2. **Trigger Step Function**: Starts Step Functions execution
3. **Wait for Completion**: Polls execution status every 30 seconds until completion

---

## Workflow Behavior

### Success Case
- Step Functions execution completes with `SUCCEEDED` status
- Workflow prints execution output
- Workflow exits with code 0 ✅

### Failure Cases

| Status | Behavior | Exit Code |
|--------|----------|-----------|
| `FAILED` | Print error details and exit | 1 ❌ |
| `TIMED_OUT` | Print timeout message and exit | 1 ❌ |
| `ABORTED` | Print abort message and exit | 1 ❌ |
| Workflow timeout (2 hours) | Exit even if execution still running | 1 ❌ |

### Execution Timeout

- **Step Functions timeout**: 2 hours (7200 seconds) - configured in state machine
- **Workflow timeout**: 2 hours (matches Step Functions timeout)
- **Poll interval**: 30 seconds

---

## Monitoring

### View Workflow Runs

1. Go to **Actions** tab in GitHub repository
2. Select **Daily Incremental Update** workflow
3. Click on a specific run to see logs

### View Step Functions Execution

```bash
# Get execution ARN from GitHub Actions logs, then:
aws stepfunctions describe-execution \
  --execution-arn "arn:aws:states:us-east-1:123456789012:execution:..."

# View execution history
aws stepfunctions get-execution-history \
  --execution-arn "arn:aws:states:us-east-1:123456789012:execution:..." \
  --max-results 100
```

### CloudWatch Logs

Step Functions execution logs are stored in CloudWatch:

```bash
# View logs
aws logs tail /aws/vendedlogs/states/congress-disclosures-development-pipelines --follow
```

---

## Testing

### Test Workflow Locally (using act)

```bash
# Install act (https://github.com/nektos/act)
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash  # Linux

# Create .secrets file with:
# AWS_ROLE_ARN=arn:aws:iam::123456789012:role/...
# HOUSE_FD_STATE_MACHINE_ARN=arn:aws:states:us-east-1:123456789012:stateMachine:...

# Run workflow
act workflow_dispatch --secret-file .secrets
```

### Manual Test via AWS CLI

```bash
# Trigger state machine directly (bypasses GitHub Actions)
aws stepfunctions start-execution \
  --state-machine-arn $HOUSE_FD_STATE_MACHINE_ARN \
  --name "manual-test-$(date +%Y%m%d-%H%M%S)" \
  --input '{"execution_type":"manual","year":2025,"mode":"incremental"}'

# Check status
aws stepfunctions describe-execution \
  --execution-arn "arn:aws:states:..."
```

---

## Troubleshooting

### Error: "User is not authorized to perform: sts:AssumeRoleWithWebIdentity"

**Solution**: Check that the IAM role trust policy allows GitHub OIDC:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
        }
      }
    }
  ]
}
```

### Error: "State machine does not exist"

**Solution**: Verify the `HOUSE_FD_STATE_MACHINE_ARN` secret value:

```bash
# List all state machines
aws stepfunctions list-state-machines
```

### Workflow timeout before completion

**Solution**: If pipeline takes longer than 2 hours:
1. Check Step Functions execution in AWS Console
2. Increase workflow timeout in `.github/workflows/daily_incremental.yml`:
   ```yaml
   - name: Wait for Step Function Completion
     timeout-minutes: 240  # 4 hours
   ```

---

## Security Best Practices

1. **Use OIDC instead of long-lived credentials**: No need to store AWS access keys
2. **Principle of least privilege**: IAM role should only have permissions for Step Functions
3. **Environment-specific secrets**: Use different secrets for dev/staging/production
4. **Audit GitHub Actions logs**: Regularly review execution logs for anomalies
5. **Rotate IAM roles periodically**: Update trust policies and rotate credentials

---

## Next Steps

1. ✅ Configure required GitHub secrets
2. ✅ Deploy infrastructure with Terraform
3. ✅ Test manual workflow trigger
4. ✅ Verify scheduled execution
5. ✅ Set up CloudWatch alerts for failures

## Related Documentation

- [AWS Step Functions Documentation](../state_machines/README.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Terraform Outputs](../infra/terraform/outputs.tf)
- [State Machine Definitions](../state_machines/)

---

**Last Updated**: 2026-01-05  
**Story**: STORY-006  
**Maintainer**: DevOps Team
