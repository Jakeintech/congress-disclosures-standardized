# Alert Types and Notification Catalog

This document catalogs all alert types configured in the pipeline, their triggers, and notification destinations.

## SNS Topics

### 1. Pipeline Alerts (`congress-disclosures-pipeline-alerts`)

**Purpose**: Critical pipeline execution failures and errors that require immediate attention

**Subscribers**:
- Email (conditional - if `alert_email` variable is set)
- SMS (conditional - if `alert_phone_number` variable is set)

**ARN**: Available via Terraform output:
```bash
terraform output pipeline_alerts_topic_arn
```

### 2. Data Quality Alerts (`congress-disclosures-data-quality-alerts`)

**Purpose**: Data quality check warnings and failures from Soda validations

**Subscribers**:
- Email (conditional - if `alert_email` variable is set)

**ARN**: Available via Terraform output:
```bash
terraform output data_quality_alerts_topic_arn
```

## Alert Types

### Pipeline Execution Alerts

#### 1. Pipeline Failure - House FD Pipeline

**Trigger**: Any uncaught exception in House Financial Disclosures pipeline

**Source State Machines**: `house_fd_pipeline.json`

**Notification States**:
- `NotifyPipelineFailure`

**Subject**: `Pipeline Failure - House FD Pipeline`

**Message Format**:
```
Pipeline failed.

Error: {error details from $.error.Cause}

Execution ID: {execution ARN}
```

**Example**:
```
Pipeline failed.

Error: Lambda.ServiceException: Function timed out after 300 seconds

Execution ID: arn:aws:states:us-east-1:464813693153:execution:congress-disclosures-house-fd-pipeline:manual-20260104
```

**Possible Causes**:
- Lambda timeout
- S3 access denied
- Invalid input parameters
- Network connectivity issues
- Dependency failures (SQS, DynamoDB)

**Response Actions**:
1. Check CloudWatch Logs for the specific Lambda function
2. Review Step Functions execution history in AWS Console
3. Verify AWS service health dashboard
4. Check if issue is transient (retry) or persistent (requires fix)

---

#### 2. Pipeline Failure - Congress.gov Pipeline

**Trigger**: Any uncaught exception in Congress.gov data sync pipeline

**Source State Machines**: `congress_pipeline.json`

**Notification States**:
- `NotifyPipelineFailure`

**Subject**: `Pipeline Failure - Congress.gov Pipeline`

**Message Format**:
```
Pipeline failed.

Error: {error details}

Execution ID: {execution ARN}
```

**Possible Causes**:
- Congress.gov API rate limiting
- API key expired or invalid
- Network connectivity issues
- Data parsing errors

**Response Actions**:
1. Check Congress.gov API status
2. Verify API key in SSM Parameter Store
3. Review rate limit headers in CloudWatch Logs
4. Consider implementing exponential backoff

---

#### 3. Pipeline Failure - Lobbying Pipeline

**Trigger**: Any uncaught exception in Senate LDA lobbying disclosures pipeline

**Source State Machines**: `lobbying_pipeline.json`

**Notification States**:
- `NotifyPipelineFailure`

**Subject**: `Pipeline Failure - Lobbying Pipeline`

**Message Format**:
```
Pipeline failed.

Error: {error details}

Execution ID: {execution ARN}
```

**Possible Causes**:
- Senate.gov website changes
- ZIP file format changes
- XML parsing errors
- S3 storage issues

---

#### 4. Pipeline Failure - Cross-Dataset Correlation

**Trigger**: Any uncaught exception in cross-dataset analytics pipeline

**Source State Machines**: `cross_dataset_correlation.json`

**Notification States**:
- `NotifyPipelineFailure`

**Subject**: `Pipeline Failure - Correlation Pipeline`

**Message Format**:
```
Pipeline failed.

Error: {error details}

Execution ID: {execution ARN}
```

**Possible Causes**:
- Missing dimension data (members, bills, disclosures)
- DuckDB query failures
- Memory exhaustion
- Incomplete upstream data

---

### Data Quality Alerts

#### 5. Data Quality Check Failed - Silver Layer

**Trigger**: Soda checks fail on Silver layer data after extraction

**Source State Machines**: `house_fd_pipeline.json`

**Notification States**:
- `NotifyQualityFailure` (after `ValidateSilverQuality` state)

**Subject**: `Data Quality Check Failed - House FD Pipeline`

**Message Format**:
```
Data quality check failed at {step name}.

Error: {error details}

Execution ID: {execution ARN}
```

**Example Soda Check Failures**:
- Missing required columns
- NULL values in non-nullable fields
- Invalid data types
- Row count thresholds not met
- Freshness checks failed

**Response Actions**:
1. Review Soda check results in Lambda logs
2. Investigate Silver layer data in S3
3. Check if source data (Bronze) is corrupted
4. Verify extraction logic hasn't introduced errors

---

#### 6. Data Quality Check Failed - Gold Layer

**Trigger**: Soda checks fail on Gold layer data after transformation

**Source State Machines**: `house_fd_pipeline.json`

**Notification States**:
- `NotifyQualityFailure` (after `ValidateGoldQuality` state)

**Subject**: `Data Quality Check Failed - House FD Pipeline`

**Message Format**:
```
Data quality check failed at {step name}.

Error: {error details}

Execution ID: {execution ARN}
```

**Example Soda Check Failures**:
- Fact table referential integrity violations
- Dimension table duplicate keys
- Metric calculation errors
- Aggregation threshold violations

**Response Actions**:
1. Review Gold transformation scripts
2. Check dimension tables for missing keys
3. Validate business logic in transformations
4. Consider rolling back to previous version

---

### Warning Alerts

#### 7. Pipeline Warning

**Trigger**: Non-critical issues that don't stop pipeline execution

**Source State Machines**: `house_fd_pipeline.json`

**Notification States**:
- `NotifyPipelineWarning`

**Subject**: `Pipeline Warning - House FD Pipeline`

**Message Format**:
```
Pipeline completed with warnings.

Warning: {warning details}

Execution ID: {execution ARN}
```

**Example Warnings**:
- Quality checks passed with warnings (not failures)
- Some documents failed extraction but pipeline continued
- API rate limit approaching (but not exceeded)
- Cache update failed but data layer succeeded

**Response Actions**:
1. Review warnings - may not require immediate action
2. Monitor for trends (increasing warnings over time)
3. Schedule investigation during next maintenance window

---

## Alert Flow Diagram

```
State Machine Error
    │
    ├─► Critical Error? ─Yes─► NotifyPipelineFailure ─► SNS: pipeline_alerts ─► Email/SMS
    │                                                                          └► PagerDuty (future)
    │
    ├─► Quality Check Failed? ─Yes─► NotifyQualityFailure ─► SNS: pipeline_alerts ─► Email
    │                                                          OR data_quality_alerts
    │
    └─► Non-Critical Warning? ─Yes─► NotifyPipelineWarning ─► SNS: pipeline_alerts ─► Email
```

## Alert Severity Levels

| Level    | Alert Type                  | Requires Action | Max Response Time | Notification Method |
|----------|-----------------------------|-----------------|-------------------|---------------------|
| CRITICAL | Pipeline Failure            | Yes             | 1 hour            | Email + SMS         |
| HIGH     | Data Quality Check Failed   | Yes             | 4 hours           | Email               |
| MEDIUM   | Pipeline Warning            | Review          | 24 hours          | Email               |
| LOW      | Informational               | No              | N/A               | Logs only           |

## Muting/Filtering Alerts

### Temporarily Disable Email Alerts

```bash
# Remove email from Terraform config
cd infra/terraform
terraform apply -var="alert_email="
```

### Filter by Subject in Email Client

Create email filters for:
- `Pipeline Failure` → High priority inbox
- `Data Quality Check Failed` → Medium priority
- `Pipeline Warning` → Low priority or archive

### SNS Message Filtering (Advanced)

Add filter policies to SNS subscriptions:

```hcl
resource "aws_sns_topic_subscription" "pipeline_alerts_email" {
  topic_arn = aws_sns_topic.pipeline_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
  
  filter_policy = jsonencode({
    severity = ["CRITICAL", "HIGH"]  # Only critical and high severity
  })
}
```

Note: Requires updating state machines to include severity in message attributes.

## Alert History and Auditing

### View Recent Alerts

```bash
# Query SNS publish logs
aws cloudwatch logs insights query \
  --log-group-name /aws/states/congress-disclosures-house-fd-pipeline \
  --start-time $(date -u -d '7 days ago' +%s) \
  --end-time $(date +%s) \
  --query-string '
    fields @timestamp, @message
    | filter @message like /sns:publish/
    | sort @timestamp desc
  '
```

### Alert Frequency Metrics

```bash
# Count alerts by type in last 30 days
aws cloudwatch get-metric-statistics \
  --namespace AWS/SNS \
  --metric-name NumberOfMessagesPublished \
  --dimensions Name=TopicName,Value=congress-disclosures-pipeline-alerts \
  --start-time $(date -u -d '30 days ago' --iso-8601) \
  --end-time $(date -u --iso-8601) \
  --period 86400 \
  --statistics Sum
```

## Future Enhancements

Planned improvements for alert system (see Epic-001):

1. **PagerDuty Integration** (STORY-TBD)
   - Critical alerts trigger PagerDuty incident
   - On-call rotation support

2. **Slack Integration** (STORY-TBD)
   - Real-time alerts to Slack channel
   - Interactive remediation buttons

3. **Alert Aggregation** (STORY-TBD)
   - Batch similar alerts (e.g., multiple extraction failures)
   - Reduce alert fatigue

4. **Auto-Remediation** (STORY-TBD)
   - Automatic retry for transient failures
   - Self-healing infrastructure

5. **Alert Analytics Dashboard** (STORY-TBD)
   - Grafana/CloudWatch dashboard
   - Alert trends and MTTR metrics

## Related Documentation

- [SNS Alert Testing Guide](SNS_ALERT_TESTING.md)
- [Step Functions Error Handling](STATE_MACHINE_FLOW.md)
- [Monitoring and Observability](ARCHITECTURE.md#monitoring)
- [Incident Response Procedures](INCIDENT_RESPONSE.md) (TBD)

## Maintenance

This document should be updated when:
- New state machines are added
- Alert message formats change
- New SNS topics are created
- Severity levels are redefined
- Integration with new notification systems (PagerDuty, Slack, etc.)

**Last Updated**: January 4, 2026
**Document Owner**: Platform Engineering Team
