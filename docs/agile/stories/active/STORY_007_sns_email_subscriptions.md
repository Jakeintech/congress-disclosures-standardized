# STORY-007: Add SNS Email Subscriptions for Alerts

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 2 | **Priority**: P1 | **Status**: Done

## User Story
**As a** platform operator
**I want** SNS alerts delivered to email
**So that** I'm notified of pipeline failures

## Acceptance Criteria

### Scenario 1: Pipeline failure sends alert ✅
- **GIVEN** State machine execution fails
- **WHEN** Error state publishes to SNS
- **THEN** Email received within 1 minute
- **AND** Email contains execution ARN, error message

### Scenario 2: Quality check failure sends warning ✅
- **GIVEN** Soda checks have warnings (not failures)
- **WHEN** Warning published to SNS
- **THEN** Email received with warning details

## Technical Tasks
- [x] Add email subscription to Terraform
- [x] Configure SNS topic subscription
- [x] Update state machines with execution ARN in alerts
- [x] Document alert delivery testing procedures
- [x] Document all alert types and formats
- [x] Add configuration examples to .env.example
- [x] Create comprehensive testing guide

## Implementation Summary

### SNS Topics Created
1. **`pipeline_alerts`** - Critical pipeline failures and errors
2. **`data_quality_alerts`** - Data quality check warnings/failures

### Email Subscriptions Configured
```hcl
# infra/terraform/sns.tf
resource "aws_sns_topic_subscription" "pipeline_alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.pipeline_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_sns_topic_subscription" "data_quality_alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.data_quality_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
```

### State Machine Integration
All state machines now include `NotifyPipelineFailure` states with:
- Execution ARN in message
- Detailed error information
- Descriptive subject lines
- Retry logic for SNS publish failures

**Files Updated**:
- `state_machines/house_fd_pipeline.json` - Enhanced error message format
- `state_machines/congress_pipeline.json` - Already compliant
- `state_machines/lobbying_pipeline.json` - Already compliant
- `state_machines/cross_dataset_correlation.json` - Already compliant

### Configuration
Variables in `infra/terraform/variables.tf`:
- `alert_email` - Email address for alerts (default: "")
- `alert_phone_number` - Optional SMS alerts (default: "")

### Documentation Created
1. **`docs/SNS_ALERT_TESTING.md`** - Complete testing guide including:
   - Subscription confirmation steps
   - Multiple testing methods (CLI, Console, real failures)
   - Troubleshooting common issues
   - Acceptance criteria verification checklist

2. **`docs/ALERT_TYPES.md`** - Alert catalog including:
   - All alert types with message formats
   - Alert severity levels
   - Response procedures
   - Alert flow diagrams
   - Future enhancement roadmap

3. **`.env.example`** - Updated with alert configuration examples

## Testing Instructions

See **`docs/SNS_ALERT_TESTING.md`** for detailed testing procedures.

Quick test:
```bash
# 1. Set alert email
export TF_VAR_alert_email="your-email@example.com"

# 2. Deploy
cd infra/terraform && terraform apply

# 3. Confirm email subscription (check inbox)

# 4. Send test alert
aws sns publish \
  --topic-arn $(terraform output -raw pipeline_alerts_topic_arn) \
  --subject "Test Alert" \
  --message "Testing SNS email delivery"
```

## Verification Checklist
- [x] Email subscription created conditionally (if alert_email set)
- [x] SNS publish permissions granted to Step Functions role
- [x] All state machines include execution ARN in error messages
- [x] Alert message format matches acceptance criteria
- [x] Testing guide documents subscription confirmation
- [x] Alert types catalog created
- [x] Configuration examples provided

## Related Stories
- STORY-040: CloudWatch Alarms (uses same SNS topics)
- STORY-056: Extraction Quality Dashboard (monitoring integration)
- STORY-050: State Machine Rollback (error handling)

## Notes
- Email subscriptions require manual confirmation (AWS requirement)
- SMS is optional and incurs costs ($0.00645/SMS)
- Subscriptions are destroyed if `alert_email = ""` (by design)
- Free tier covers 1,000 email deliveries/month

**Completed**: January 4, 2026
