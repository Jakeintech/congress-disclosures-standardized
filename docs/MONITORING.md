# Congress Disclosures Pipeline Monitoring Guide

This guide covers monitoring, alerting, and troubleshooting for both the Financial Disclosures (FD) and Congress.gov pipelines.

---

## Overview

The pipeline uses CloudWatch for:
- **Logs**: Lambda function execution logs (30-day retention)
- **Metrics**: SQS queue depth, Lambda errors, DLQ messages
- **Alarms**: Automated alerts for DLQ messages, stuck queues, Lambda errors

---

## Quick Commands

### Check Queue Status

**Financial Disclosures Extraction Queue**:
```bash
make check-extraction-queue
```
Or manually:
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-extract-queue \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible
```

**Congress Fetch Queue**:
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-congress-fetch-queue \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible ApproximateAgeOfOldestMessage
```

**Congress Silver Queue**:
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-congress-silver-queue \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible
```

### Check Dead Letter Queues (DLQ)

**Financial Disclosures DLQ**:
```bash
make check-dlq
```

**Congress Fetch DLQ**:
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-congress-fetch-dlq \
  --attribute-names ApproximateNumberOfMessages --query 'Attributes.ApproximateNumberOfMessages' --output text
```

**Congress Silver DLQ**:
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-congress-silver-dlq \
  --attribute-names ApproximateNumberOfMessages --query 'Attributes.ApproximateNumberOfMessages' --output text
```

### Tail Lambda Logs

**Financial Disclosures Lambdas**:
```bash
# Ingest Lambda
make logs-ingest

# Extract Lambda
make logs-extract

# Recent extract logs (errors + successes)
make logs-extract-recent
```

**Congress.gov Lambdas**:
```bash
# Fetch entity Lambda
aws logs tail /aws/lambda/congress-disclosures-development-congress-fetch-entity --follow

# Orchestrator Lambda
aws logs tail /aws/lambda/congress-disclosures-development-congress-orchestrator --follow

# Bronze-to-Silver Lambda
aws logs tail /aws/lambda/congress-disclosures-development-congress-bronze-to-silver --follow
```

### Purge Queues (Caution!)

**Financial Disclosures**:
```bash
make purge-extraction-queue  # Interactive confirmation
```

**Congress Fetch Queue**:
```bash
aws sqs purge-queue --queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-congress-fetch-queue
```

**Congress Silver Queue**:
```bash
aws sqs purge-queue --queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-congress-silver-queue
```

---

## CloudWatch Alarms

### Financial Disclosures Pipeline

| Alarm Name                                           | Metric                           | Threshold | Description                                      |
|------------------------------------------------------|----------------------------------|-----------|--------------------------------------------------|
| `congress-disclosures-development-dlq-messages`      | ApproximateNumberOfMessagesVisible | > 0       | Alerts when any message appears in FD DLQ        |

### Congress.gov Pipeline

| Alarm Name                                                | Metric                           | Threshold | Description                                          |
|-----------------------------------------------------------|----------------------------------|-----------|------------------------------------------------------|
| `congress-disclosures-development-congress-fetch-dlq`     | ApproximateNumberOfMessagesVisible | > 5       | Alerts when Congress fetch failures appear in DLQ    |
| `congress-disclosures-development-congress-silver-dlq`    | ApproximateNumberOfMessagesVisible | > 5       | Alerts when Bronze-to-Silver failures appear in DLQ  |
| `congress-disclosures-development-congress-fetch-queue-age` | ApproximateAgeOfOldestMessage    | > 3600s   | Alerts when fetch queue messages are stuck (>1 hour) |

**Alarm Actions**:
- If `alert_email` is configured in Terraform variables, alarms publish to SNS topic
- SNS topic: `arn:aws:sns:us-east-1:464813693153:congress-disclosures-development-alerts`

### Viewing Alarms

**AWS Console**:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#alarmsV2:
```

**CLI**:
```bash
aws cloudwatch describe-alarms --alarm-name-prefix congress-disclosures-development
```

---

## Troubleshooting Common Issues

### 1. Messages in DLQ

**Symptom**: CloudWatch alarm triggered for DLQ messages.

**Cause**: Lambda failed to process message after 3 retries (default `maxReceiveCount`).

**Investigation**:
```bash
# Receive message from DLQ to inspect it
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-congress-fetch-dlq \
  --max-number-of-messages 1 \
  --message-attribute-names All

# Check Lambda logs for errors (replace timestamp with your DLQ message timestamp)
aws logs filter-log-events \
  --log-group-name /aws/lambda/congress-disclosures-development-congress-fetch-entity \
  --start-time 1701648000000 \
  --filter-pattern "ERROR"
```

**Resolution**:
1. Fix root cause (e.g., API rate limiting, invalid JSON, Lambda timeout)
2. Re-queue DLQ message to main queue after fix:
   ```bash
   # Get message from DLQ
   MESSAGE=$(aws sqs receive-message --queue-url <DLQ-URL> --max-number-of-messages 1)

   # Send to main queue
   BODY=$(echo $MESSAGE | jq -r '.Messages[0].Body')
   aws sqs send-message --queue-url <MAIN-QUEUE-URL> --message-body "$BODY"

   # Delete from DLQ
   RECEIPT=$(echo $MESSAGE | jq -r '.Messages[0].ReceiptHandle')
   aws sqs delete-message --queue-url <DLQ-URL> --receipt-handle "$RECEIPT"
   ```

---

### 2. Queue Stuck (Old Messages)

**Symptom**: `congress-fetch-queue-age` alarm triggered (oldest message > 1 hour).

**Cause**: Lambda not processing messages fast enough, or Lambda concurrency limit reached.

**Investigation**:
```bash
# Check queue attributes
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-congress-fetch-queue \
  --attribute-names All | jq '.Attributes'

# Check Lambda concurrency
aws lambda get-function-concurrency \
  --function-name congress-disclosures-development-congress-fetch-entity
```

**Resolution**:
1. Increase Lambda concurrency (Terraform variable `lambda_congress_fetch_max_concurrency`)
2. Check for Lambda errors in CloudWatch Logs
3. Verify Lambda is not throttled:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Throttles \
     --dimensions Name=FunctionName,Value=congress-disclosures-development-congress-fetch-entity \
     --start-time 2025-12-04T00:00:00Z \
     --end-time 2025-12-04T23:59:59Z \
     --period 300 \
     --statistics Sum
   ```

---

### 3. Lambda Errors

**Symptom**: Lambda invocations failing (visible in CloudWatch Logs).

**Investigation**:
```bash
# View recent errors (last 5 minutes)
aws logs tail /aws/lambda/congress-disclosures-development-congress-fetch-entity \
  --since 5m --filter-pattern "ERROR"

# Get error count for specific time window
aws logs filter-log-events \
  --log-group-name /aws/lambda/congress-disclosures-development-congress-fetch-entity \
  --start-time 1701648000000 \
  --end-time 1701651600000 \
  --filter-pattern "ERROR" \
  --query 'events[*].message' --output text
```

**Common Errors**:

| Error Message                                      | Cause                                  | Solution                                                |
|----------------------------------------------------|----------------------------------------|---------------------------------------------------------|
| `Task timed out after 300.00 seconds`              | Lambda timeout (default 5 min)         | Increase `lambda_congress_timeout_seconds` in Terraform |
| `Rate exceeded: 429 Too Many Requests`             | Congress.gov API rate limit (5000/hr)  | Reduce Lambda concurrency or add backoff logic          |
| `Unable to import module 'handler'`                | Missing dependencies in Lambda package | Re-package and deploy Lambda (`make package-congress-fetch`) |
| `S3 bucket does not exist: congress-disclosures-*` | S3 bucket misconfigured                | Check `S3_BUCKET_NAME` environment variable             |
| `SSM parameter not found: /congress-disclosures/...` | Congress API key not in SSM            | Add API key to SSM Parameter Store (see below)          |

---

### 4. Congress API Rate Limiting

**Symptom**: Lambda logs show `429 Too Many Requests` errors.

**Cause**: Exceeding Congress.gov API rate limit (5000 requests/hour with API key).

**Investigation**:
```bash
# Count recent Lambda invocations (proxy for API requests)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=congress-disclosures-development-congress-fetch-entity \
  --start-time 2025-12-04T10:00:00Z \
  --end-time 2025-12-04T11:00:00Z \
  --period 3600 \
  --statistics Sum
```

**Resolution**:
1. Reduce Lambda concurrency: Update Terraform variable `lambda_congress_fetch_max_concurrency` (default: 5)
2. Add exponential backoff: Implemented in `congress_api_client.py` using `tenacity` library
3. Verify API key is valid:
   ```bash
   aws ssm get-parameter --name /congress-disclosures/development/congress-api-key --with-decryption
   ```

---

## SSM Parameter Store Configuration

### Add Congress.gov API Key

**Required for Congress.gov pipeline** (get API key from https://api.congress.gov/sign-up/):
```bash
aws ssm put-parameter \
  --name /congress-disclosures/development/congress-api-key \
  --value "YOUR_API_KEY_HERE" \
  --type SecureString \
  --description "Congress.gov API key for development environment"
```

**Verify**:
```bash
aws ssm get-parameter --name /congress-disclosures/development/congress-api-key --with-decryption
```

**Update** (if key changes):
```bash
aws ssm put-parameter \
  --name /congress-disclosures/development/congress-api-key \
  --value "NEW_API_KEY_HERE" \
  --type SecureString \
  --overwrite
```

---

## CloudWatch Dashboards (Future)

*Placeholder for custom CloudWatch dashboard showing:*
- SQS queue depth over time
- Lambda invocation/error rates
- Bronze/Silver/Gold data volume metrics
- Cost metrics (S3 storage, Lambda invocations)

**Create Dashboard** (manual step, not in Terraform yet):
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:
```

---

## Log Insights Queries

### Find Failed API Requests
```
fields @timestamp, @message
| filter @message like /ERROR/
| filter @message like /Congress API/
| sort @timestamp desc
| limit 20
```

### Count Lambda Invocations by Status
```
fields @timestamp, status
| stats count() by status
| sort status
```

### Average Lambda Duration
```
fields @duration
| stats avg(@duration), max(@duration), min(@duration)
```

---

## Maintenance Tasks

### Daily
- Check DLQ message counts (should be 0)
- Review recent Lambda errors (if any)

### Weekly
- Review SQS queue age metrics (detect stuck processing)
- Audit CloudWatch log retention settings (cost optimization)

### Monthly
- Review API usage vs rate limits (Congress.gov: 5000/hr)
- Check S3 storage costs (optimize lifecycle policies if needed)

---

## Support Contacts

**Congress.gov API Support**:
- Email: api@loc.gov
- Documentation: https://api.congress.gov/
- Status Page: https://status.congress.gov/

**AWS Support**:
- CloudWatch: https://console.aws.amazon.com/support/home
- SQS: https://docs.aws.amazon.com/sqs/
- Lambda: https://docs.aws.amazon.com/lambda/

---

**Last Updated**: 2025-12-04
