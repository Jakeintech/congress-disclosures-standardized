# STORY-007: Add SNS Email Subscriptions for Alerts

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 2 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** platform operator
**I want** SNS alerts delivered to email
**So that** I'm notified of pipeline failures

## Acceptance Criteria

### Scenario 1: Pipeline failure sends alert
- **GIVEN** State machine execution fails
- **WHEN** Error state publishes to SNS
- **THEN** Email received within 1 minute
- **AND** Email contains execution ARN, error message

### Scenario 2: Quality check failure sends warning
- **GIVEN** Soda checks have warnings (not failures)
- **WHEN** Warning published to SNS
- **THEN** Email received with warning details

## Technical Tasks
- [ ] Add email subscription to Terraform
- [ ] Configure SNS topic subscription
- [ ] Confirm subscription via email
- [ ] Test alert delivery
- [ ] Document alert types

## Implementation
```hcl
# sns.tf
resource "aws_sns_topic_subscription" "pipeline_alerts_email" {
  topic_arn = aws_sns_topic.pipeline_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

variable "alert_email" {
  type        = string
  description = "Email address for pipeline alerts"
  default     = "team@example.com"
}
```

## Test Requirements
```bash
# Send test alert
aws sns publish \
  --topic-arn arn:aws:sns:... \
  --subject "Test Alert" \
  --message "Test message"
```

## Estimated Effort: 2 hours

**Target**: Dec 18, 2025
