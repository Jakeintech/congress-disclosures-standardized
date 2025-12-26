# STORY-040: Configure CloudWatch Alarms

**Epic**: EPIC-001 | **Sprint**: Sprint 4 | **Points**: 3 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** platform operator
**I want** CloudWatch alarms for critical failures
**So that** I'm alerted immediately

## Acceptance Criteria
- **GIVEN** CloudWatch alarms configured
- **WHEN** Pipeline fails
- **THEN** SNS alert sent within 1 minute
- **AND** Alarm triggers for: pipeline failure, cost threshold, Lambda timeout, queue backed up

## Technical Tasks
- [ ] Create alarm for pipeline failure
- [ ] Create alarm for cost > $15
- [ ] Create alarm for Lambda timeout (>80% limit)
- [ ] Create alarm for queue depth > 1000
- [ ] Test alarm delivery

## Terraform
```hcl
resource "aws_cloudwatch_metric_alarm" "pipeline_failure" {
  alarm_name          = "pipeline-execution-failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_actions       = [aws_sns_topic.pipeline_alerts.arn]
}
```

## Estimated Effort: 3 hours
**Target**: Jan 7, 2026
