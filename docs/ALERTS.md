# Congress Disclosures Pipeline Alert System

This document describes the SNS-based alert system for the Congress Disclosures pipeline, including setup, alert types, and troubleshooting.

---

## Overview

The pipeline uses **Amazon SNS (Simple Notification Service)** to deliver real-time alerts for:
- Pipeline execution failures
- Data quality check warnings and failures
- Dead Letter Queue (DLQ) message arrivals
- CloudWatch alarm triggers

**Alert Delivery**: Email (primary), SMS (optional)

---

## Quick Setup

### 1. Configure Email Address

Edit your `infra/terraform/terraform.tfvars`:

```hcl
# RECOMMENDED: Receive pipeline & quality alerts via SNS
alert_email = "your-email@example.com"
```

### 2. Deploy Infrastructure

```bash
cd infra/terraform
terraform apply
```

### 3. Confirm Email Subscription

**Within 5 minutes**, you will receive an email from AWS Notifications:

**Subject**: `AWS Notification - Subscription Confirmation`

**Click the "Confirm subscription" link** in the email.

> ⚠️ **Important**: Alerts will NOT be delivered until you confirm the subscription.

### 4. Verify Subscription

```bash
# List all subscriptions for pipeline alerts topic
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:$(aws sts get-caller-identity --query Account --output text):congress-disclosures-pipeline-alerts

# Look for your email with SubscriptionArn (not "PendingConfirmation")
```

**Expected output** (after confirmation):
```json
{
  "Subscriptions": [
    {
      "SubscriptionArn": "arn:aws:sns:us-east-1:123456789012:congress-disclosures-pipeline-alerts:abc123...",
      "Owner": "123456789012",
      "Protocol": "email",
      "Endpoint": "your-email@example.com",
      "TopicArn": "arn:aws:sns:us-east-1:123456789012:congress-disclosures-pipeline-alerts"
    }
  ]
}
```

---

## SNS Topics

The pipeline uses **two SNS topics** for different alert categories:

### 1. Pipeline Alerts Topic

**Topic Name**: `congress-disclosures-pipeline-alerts`

**Purpose**: Critical pipeline execution failures

**Alert Types**:
- State Machine execution failures
- Lambda function errors (Step Functions context)
- SQS Dead Letter Queue (DLQ) messages
- CloudWatch alarms for stuck queues

**Configured Subscriptions**:
- **Email**: Controlled by `alert_email` variable
- **SMS** (optional): Controlled by `alert_phone_number` variable

**ARN**: `arn:aws:sns:us-east-1:${account_id}:congress-disclosures-pipeline-alerts`

### 2. Data Quality Alerts Topic

**Topic Name**: `congress-disclosures-data-quality-alerts`

**Purpose**: Data quality check warnings and failures

**Alert Types**:
- Soda data quality check failures
- Schema validation errors
- Missing required fields
- Data freshness warnings

**Configured Subscriptions**:
- **Email**: Controlled by `alert_email` variable

**ARN**: `arn:aws:sns:us-east-1:${account_id}:congress-disclosures-data-quality-alerts`

---

## Alert Types & Examples

### 1. State Machine Execution Failure

**Trigger**: Step Functions state machine enters `Fail` state

**Email Subject**: `Pipeline Execution Failed: house_fd_pipeline`

**Email Body Example**:
```
Execution ARN: arn:aws:states:us-east-1:123456789012:execution:house_fd_pipeline:abc123
Error: States.TaskFailed
Cause: Lambda function congress-disclosures-development-extract failed with error: Task timed out after 900.00 seconds
Timestamp: 2025-12-29T10:30:45Z

Check CloudWatch Logs for details:
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Flambda$252Fcongress-disclosures-development-extract
```

**Response Time**: Within 1 minute of failure

**Action Required**:
1. Check execution details in Step Functions console
2. Review Lambda logs for root cause
3. Fix issue and re-run pipeline

---

### 2. Dead Letter Queue (DLQ) Messages

**Trigger**: Message sent to DLQ after max retries (default: 5 attempts)

**Email Subject**: `ALARM: "congress-disclosures-development-dlq-messages" in US East (N. Virginia)`

**Email Body Example**:
```
You are receiving this email because your Amazon CloudWatch Alarm "congress-disclosures-development-dlq-messages" in the US East (N. Virginia) region has entered the ALARM state.

Reason for State Change:
Threshold Crossed: 1 out of the last 1 datapoints [5.0 (29/12/25 10:35:00)] was greater than the threshold (0.0) (minimum 1 datapoint for OK -> ALARM transition).

Alarm Description:
Alerts when messages appear in financial disclosures DLQ

View this alarm in the AWS Management Console:
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#alarmsV2:alarm/congress-disclosures-development-dlq-messages
```

**Response Time**: Within 5 minutes of message entering DLQ

**Action Required**:
1. Inspect DLQ message to identify failed payload
2. Check Lambda error logs
3. Fix root cause
4. Re-queue message or re-process manually

**How to Inspect DLQ**:
```bash
# View messages in DLQ (doesn't delete them)
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/congress-disclosures-development-extract-dlq \
  --max-number-of-messages 10 \
  --message-attribute-names All

# Check DLQ message count
make check-dlq
```

---

### 3. Data Quality Check Failures

**Trigger**: Soda checks detect data quality issues

**Email Subject**: `Data Quality Alert: Bronze Layer Validation Failed`

**Email Body Example**:
```
Data Quality Check Failed

Layer: bronze/house/financial/2025/
Check: missing_required_fields
Severity: ERROR
Failed Rows: 42 out of 1,250

Details:
- DocId field missing in 42 filings
- Last check passed: 2025-12-28T18:00:00Z

Run ID: soda-check-20251229-103045

View full report:
s3://congress-disclosures-standardized/quality-reports/soda/bronze/2025-12-29/report.html
```

**Response Time**: Within 5 minutes of check completion

**Action Required**:
1. Review Soda check report in S3
2. Identify data source issue
3. Fix upstream pipeline or data source
4. Re-run affected pipeline stage

---

### 4. Stuck Queue (Age Alarm)

**Trigger**: Oldest message in queue exceeds 1 hour

**Email Subject**: `ALARM: "congress-fetch-queue-age" in US East (N. Virginia)`

**Email Body Example**:
```
Threshold Crossed: 1 out of the last 1 datapoints [3900.0 (29/12/25 10:40:00)] was greater than the threshold (3600.0).

Alarm Description:
Alerts when fetch queue messages are stuck (>1 hour)
```

**Response Time**: Within 5 minutes of threshold breach

**Action Required**:
1. Check Lambda concurrency limits
2. Verify Lambda is processing messages
3. Check for Lambda errors or throttling
4. Increase concurrency if needed

**Investigation Commands**:
```bash
# Check queue age and depth
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/congress-disclosures-development-congress-fetch-queue \
  --attribute-names ApproximateNumberOfMessages ApproximateAgeOfOldestMessage

# Check Lambda concurrency
aws lambda get-function-concurrency \
  --function-name congress-disclosures-development-congress-fetch-entity
```

---

## Testing Alert Delivery

### Quick Test Using Make (Recommended)

```bash
# Check subscription status
make check-sns-subscriptions

# Test pipeline alerts
make test-pipeline-alert

# Test data quality alerts
make test-quality-alert

# Run all tests (check subscriptions + test both topics)
make test-all-alerts
```

**Expected**: Email(s) received within 1 minute

### Manual Test: Pipeline Alerts Topic

```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Send test alert to pipeline alerts topic
aws sns publish \
  --topic-arn "arn:aws:sns:us-east-1:${ACCOUNT_ID}:congress-disclosures-pipeline-alerts" \
  --subject "Test Alert: Pipeline Monitoring" \
  --message "This is a test alert from the Congress Disclosures pipeline. If you received this, your SNS email subscription is working correctly."
```

**Expected**: Email received within 1 minute

### Manual Test: Data Quality Alerts Topic

```bash
# Send test alert to data quality topic
aws sns publish \
  --topic-arn "arn:aws:sns:us-east-1:${ACCOUNT_ID}:congress-disclosures-data-quality-alerts" \
  --subject "Test Alert: Data Quality Monitoring" \
  --message "This is a test alert for data quality checks. If you received this, your SNS email subscription is working correctly."
```

**Expected**: Email received within 1 minute

### Verify Subscription Status

```bash
# Using Make
make check-sns-subscriptions

# Or manually
# Check pipeline alerts subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn "arn:aws:sns:us-east-1:${ACCOUNT_ID}:congress-disclosures-pipeline-alerts" \
  --query 'Subscriptions[*].[Protocol,Endpoint,SubscriptionArn]' \
  --output table

# Check data quality alerts subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn "arn:aws:sns:us-east-1:${ACCOUNT_ID}:congress-disclosures-data-quality-alerts" \
  --query 'Subscriptions[*].[Protocol,Endpoint,SubscriptionArn]' \
  --output table
```

**Expected**: Your email listed with a full SubscriptionArn (not "PendingConfirmation")

---

## CloudWatch Alarms Connected to SNS

The following CloudWatch alarms publish to SNS topics when triggered:

| Alarm Name                                           | Metric                            | Threshold | SNS Topic              |
|------------------------------------------------------|-----------------------------------|-----------|------------------------|
| `congress-disclosures-development-dlq-messages`      | SQS ApproximateNumberOfMessages   | > 0       | pipeline-alerts        |
| `congress-fetch-dlq`                                 | SQS ApproximateNumberOfMessages   | > 5       | alerts (general)       |
| `congress-silver-dlq`                                | SQS ApproximateNumberOfMessages   | > 5       | alerts (general)       |
| `congress-fetch-queue-age`                           | SQS ApproximateAgeOfOldestMessage | > 3600s   | alerts (general)       |

**Note**: The `alerts` topic is a separate, general-purpose SNS topic for CloudWatch alarms. It is conditionally created based on the `alert_email` variable.

---

## Optional: SMS Alerts

For critical alerts, you can add SMS notifications:

### 1. Configure Phone Number

Edit `infra/terraform/terraform.tfvars`:

```hcl
alert_phone_number = "+1234567890"  # E.164 format (include country code)
```

### 2. Deploy

```bash
cd infra/terraform
terraform apply
```

### 3. Opt-In to SMS

AWS will send an SMS to confirm. **Reply "YES"** to activate.

**Cost**: $0.00645 per SMS in the US (see AWS SNS pricing)

---

## Troubleshooting

### Email Not Received After Terraform Apply

**Symptom**: No confirmation email received within 5 minutes

**Causes**:
1. Email in spam folder (check junk/spam)
2. Typo in `alert_email` variable
3. Corporate email filter blocking AWS emails

**Solutions**:
```bash
# Verify subscription is pending
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:${ACCOUNT_ID}:congress-disclosures-pipeline-alerts \
  --query 'Subscriptions[?SubscriptionArn==`PendingConfirmation`]'

# Resend confirmation email (delete and recreate subscription)
cd infra/terraform
terraform taint aws_sns_topic_subscription.pipeline_alerts_email[0]
terraform apply
```

---

### Alerts Not Delivered After Confirmation

**Symptom**: Subscription confirmed but no alerts received

**Causes**:
1. Subscription not actually confirmed (SubscriptionArn is "PendingConfirmation")
2. SNS topic permissions issue
3. Email delivery delays

**Solutions**:
```bash
# Verify subscription status
aws sns get-subscription-attributes \
  --subscription-arn <your-subscription-arn>

# Send test message
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:${ACCOUNT_ID}:congress-disclosures-pipeline-alerts \
  --subject "Test" \
  --message "Test message"
```

---

### Multiple Duplicate Alerts

**Symptom**: Receiving duplicate alerts for same event

**Cause**: Multiple email subscriptions exist (e.g., manual subscription + Terraform-managed)

**Solution**:
```bash
# List all subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:${ACCOUNT_ID}:congress-disclosures-pipeline-alerts

# Delete duplicate subscriptions (keep only Terraform-managed one)
aws sns unsubscribe --subscription-arn <duplicate-subscription-arn>
```

---

## Unsubscribing

### Temporary: Stop Receiving Alerts

Click "Unsubscribe" link at bottom of any SNS alert email.

> ⚠️ **Warning**: This will stop ALL alerts from that topic, including critical pipeline failures.

### Permanent: Remove Subscription via Terraform

Edit `infra/terraform/terraform.tfvars`:

```hcl
alert_email = ""  # Empty string disables subscription
```

Then apply:

```bash
cd infra/terraform
terraform apply
```

---

## Alert Response Playbook

### Priority 1: Pipeline Execution Failure
1. **Acknowledge**: Note the execution ARN from email
2. **Investigate**: Check Step Functions console and Lambda logs
3. **Diagnose**: Identify root cause (timeout, API error, S3 permission, etc.)
4. **Fix**: Deploy code fix or adjust configuration
5. **Re-run**: Trigger pipeline with same input
6. **Verify**: Monitor execution to completion

**SLA**: Respond within 1 hour, resolve within 4 hours

---

### Priority 2: DLQ Messages
1. **Inspect**: Retrieve message from DLQ
2. **Log Review**: Check Lambda error logs for failure reason
3. **Fix**: Correct code or data issue
4. **Re-queue**: Send message back to main queue after fix
5. **Monitor**: Ensure successful processing

**SLA**: Respond within 2 hours, resolve within 8 hours

---

### Priority 3: Data Quality Failures
1. **Review Report**: Download Soda check report from S3
2. **Assess Impact**: Determine if blocking issue or warning
3. **Trace Source**: Identify which upstream source caused issue
4. **Fix**: Correct data source or transformation logic
5. **Re-run**: Re-process affected data
6. **Validate**: Verify data quality checks pass

**SLA**: Respond within 4 hours, resolve within 1 business day

---

## Related Documentation

- **Monitoring Guide**: `docs/MONITORING.md` - CloudWatch logs, metrics, and dashboards
- **Deployment Guide**: `docs/DEPLOYMENT.md` - Infrastructure setup and configuration
- **Error Handling**: `docs/ERROR_HANDLING.md` - Pipeline error handling architecture
- **State Machine Flow**: `docs/STATE_MACHINE_FLOW.md` - Pipeline orchestration details

---

**Last Updated**: 2025-12-29  
**Version**: 1.0.0
