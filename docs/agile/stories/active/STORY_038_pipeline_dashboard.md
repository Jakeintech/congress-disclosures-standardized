# STORY-038: Create CloudWatch Pipeline Dashboard

**Epic**: EPIC-001 | **Sprint**: Sprint 4 | **Points**: 5 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** platform operator
**I want** CloudWatch dashboard for pipeline metrics
**So that** I monitor execution health

## Acceptance Criteria
- **GIVEN** CloudWatch dashboard deployed
- **WHEN** I view it
- **THEN** Shows pipeline execution count, success rate, duration
- **AND** Shows Lambda error rates by function
- **AND** Shows SQS queue depth
- **AND** Auto-refreshes every 1 minute

## Technical Tasks
- [ ] Create dashboard via Terraform
- [ ] Add pipeline execution widgets
- [ ] Add Lambda metrics widgets
- [ ] Add SQS queue depth widget
- [ ] Add data freshness widget
- [ ] Configure auto-refresh

## Dashboard Widgets
1. Pipeline Executions (last 30 days)
2. Success Rate (%)
3. Execution Duration (by phase)
4. Lambda Errors (by function)
5. SQS Queue Depth
6. Data Freshness (hours since last update)

## Terraform
```hcl
resource "aws_cloudwatch_dashboard" "pipeline" {
  dashboard_name = "congress-data-platform-pipeline"
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [["AWS/States", "ExecutionsSucceeded"]]
          period = 300
          stat = "Sum"
          region = "us-east-1"
          title = "Pipeline Executions"
        }
      }
    ]
  })
}
```

## Estimated Effort: 5 hours
**Target**: Jan 6, 2026
