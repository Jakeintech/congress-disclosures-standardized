# SNS Alert Testing Guide

This guide covers how to test and verify SNS email subscriptions for pipeline alerts.

## Overview

The system has two SNS topics for different types of alerts:

1. **`pipeline_alerts`** - Critical pipeline execution failures and errors
2. **`data_quality_alerts`** - Data quality check warnings and failures

## Configuration

### 1. Set Alert Email in Terraform Variables

Edit your `terraform.tfvars` file (or set environment variables):

```hcl
# For email alerts
alert_email = "your-email@example.com"

# Optional: For SMS alerts  
alert_phone_number = "+1234567890"  # E.164 format
```

Or via environment variables in `.env`:

```bash
TF_VAR_alert_email=your-email@example.com
TF_VAR_alert_phone_number=+1234567890
```

### 2. Deploy Infrastructure

```bash
cd infra/terraform
terraform init
terraform apply
```

### 3. Confirm Email Subscription

After deployment:

1. Check your email inbox for "AWS Notification - Subscription Confirmation"
2. Click the "Confirm subscription" link in the email
3. You'll see a confirmation page from AWS

**Important**: You must confirm the subscription before you'll receive alerts!

## Verifying Subscription Status

### Check via AWS CLI

```bash
# List all subscriptions for pipeline_alerts topic
aws sns list-subscriptions-by-topic \
  --topic-arn $(terraform output -raw pipeline_alerts_topic_arn)

# Check subscription status
aws sns get-subscription-attributes \
  --subscription-arn <subscription-arn-from-above>
```

### Check via AWS Console

1. Go to [SNS Console](https://console.aws.amazon.com/sns/)
2. Navigate to "Subscriptions"
3. Look for subscriptions with:
   - Topic: `congress-disclosures-pipeline-alerts`
   - Status: "Confirmed" (not "PendingConfirmation")

## Testing Alert Delivery

### Method 1: Send Test Message via AWS CLI

```bash
# Test pipeline alerts topic
aws sns publish \
  --topic-arn $(cd infra/terraform && terraform output -raw pipeline_alerts_topic_arn) \
  --subject "Test Alert - Pipeline Monitoring" \
  --message "This is a test alert. If you receive this, SNS email delivery is working correctly."

# Test data quality alerts topic  
aws sns publish \
  --topic-arn $(cd infra/terraform && terraform output -raw data_quality_alerts_topic_arn) \
  --subject "Test Alert - Data Quality Monitoring" \
  --message "This is a test data quality alert."
```

**Expected Result**: You should receive an email within 1 minute with the test message.

### Method 2: Trigger a Real Pipeline Failure

**Option A: Invalid Lambda Input**

Start a state machine execution with invalid input to trigger an error:

```bash
# Get state machine ARN
STATE_MACHINE_ARN=$(cd infra/terraform && terraform output -json | jq -r '.state_machines.value.house_fd_pipeline')

# Start execution with invalid input
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --name "test-failure-$(date +%Y%m%d-%H%M%S)" \
  --input '{"year": "invalid"}'
```

**Option B: Force Lambda Timeout**

Temporarily reduce Lambda timeout to force a failure:

```bash
# Reduce timeout to 3 seconds (will fail on large operations)
aws lambda update-function-configuration \
  --function-name congress-disclosures-ingest-zip \
  --timeout 3

# Trigger ingestion (will timeout)
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --name "test-timeout-$(date +%Y%m%d-%H%M%S)" \
  --input '{"year": 2025}'

# Restore original timeout after test
aws lambda update-function-configuration \
  --function-name congress-disclosures-ingest-zip \
  --timeout 600
```

### Method 3: Test via Step Functions Console

1. Go to [Step Functions Console](https://console.aws.amazon.com/states/)
2. Select state machine: `congress-disclosures-house-fd-pipeline`
3. Click "Start execution"
4. Enter invalid JSON input:
   ```json
   {
     "year": null,
     "invalid_field": true
   }
   ```
5. Monitor execution - it should fail and trigger SNS alert

## Alert Message Formats

### Pipeline Failure Alert

```
Subject: Pipeline Failure - House FD Pipeline

Message:
Pipeline failed.

Error: {"errorType": "Lambda.ServiceException", "Cause": "..."}

Execution ID: arn:aws:states:us-east-1:123456789012:execution:congress-disclosures-house-fd-pipeline:abc123
```

### Data Quality Failure Alert

```
Subject: Data Quality Check Failed - House FD Pipeline

Message:
Data quality check failed at ValidateSilverQuality.

Error: {"errorType": "DataQualityFailure", "Cause": "..."}

Execution ID: arn:aws:states:us-east-1:123456789012:execution:congress-disclosures-house-fd-pipeline:abc123
```

### Pipeline Warning Alert

```
Subject: Pipeline Warning - House FD Pipeline

Message:
Pipeline completed with warnings.

Warning: Quality checks passed with warnings

Execution ID: arn:aws:states:us-east-1:123456789012:execution:congress-disclosures-house-fd-pipeline:abc123
```

## Acceptance Criteria Verification

As per **STORY-007** acceptance criteria:

### ✅ Scenario 1: Pipeline failure sends alert

- [x] **GIVEN** State machine execution fails
- [x] **WHEN** Error state publishes to SNS
- [x] **THEN** Email received within 1 minute
- [x] **AND** Email contains execution ARN
- [x] **AND** Email contains error message

**Verification Steps**:

1. Trigger a test failure using Method 2 above
2. Wait up to 1 minute
3. Check email inbox
4. Verify email contains:
   - Subject line with pipeline name
   - Execution ARN (format: `arn:aws:states:...`)
   - Error details from `$.error.Cause`

### ✅ Scenario 2: Quality check failure sends warning

- [x] **GIVEN** Soda checks have warnings (not failures)
- [x] **WHEN** Warning published to SNS
- [x] **THEN** Email received with warning details

**Verification Steps**:

1. Run pipeline with data that triggers Soda warnings
2. Check for email with subject "Pipeline Warning" or "Data Quality Check Failed"
3. Verify warning details are included

## Troubleshooting

### Email Not Received

**Check subscription confirmation**:
```bash
aws sns get-subscription-attributes \
  --subscription-arn <your-subscription-arn>
```

If status is `PendingConfirmation`, check spam folder for confirmation email.

**Verify SNS permissions**:
```bash
# Check Step Functions role has SNS publish permissions
aws iam get-role-policy \
  --role-name congress-disclosures-step-functions-role \
  --policy-name congress-disclosures-step-functions-policy
```

Should include:
```json
{
  "Effect": "Allow",
  "Action": ["sns:Publish"],
  "Resource": "arn:aws:sns:*:*:congress-disclosures-pipeline-alerts"
}
```

### Subscription Keeps Getting Deleted

If `count = 0` in Terraform (because `alert_email = ""`), the subscription will be destroyed.

**Fix**: Ensure environment variable is set:
```bash
export TF_VAR_alert_email="your-email@example.com"
terraform apply
```

### Wrong Email Format

SNS requires valid email addresses. Common issues:

- ❌ `user` (missing domain)
- ❌ `user@localhost` (invalid domain)
- ✅ `user@example.com` (valid)

### Delayed Email Delivery

SNS typically delivers within seconds, but can take up to 5 minutes in rare cases.

**Check SNS publish logs**:
```bash
aws cloudwatch logs filter-log-events \
  --log-group-name /aws/states/congress-disclosures-house-fd-pipeline \
  --filter-pattern "sns:publish"
```

## Cost Implications

- **SNS Email**: Free for first 1,000 email deliveries/month
- **SNS SMS**: $0.00645 per SMS (paid, not in free tier)

Typical usage: ~5-10 alerts/month → **$0.00/month** (well within free tier)

## Security Considerations

- Email addresses are stored in Terraform state (encrypted if using S3 backend with encryption)
- Consider using a team distribution list instead of personal emails
- Phone numbers (SMS) are stored in plaintext in Terraform state - use cautiously

## Next Steps

After verification:

1. ✅ Confirm email subscription
2. ✅ Test alert delivery
3. ✅ Document alert response procedures for your team
4. Consider setting up:
   - Slack/PagerDuty integration (via Lambda subscriber)
   - CloudWatch alarms for repeated failures
   - Automated remediation workflows

## Related Documentation

- [Step Functions Error Handling](STATE_MACHINE_FLOW.md)
- [CloudWatch Alarms](ARCHITECTURE.md#monitoring)
- [STORY-007: SNS Email Subscriptions](agile/stories/active/STORY_007_sns_email_subscriptions.md)
