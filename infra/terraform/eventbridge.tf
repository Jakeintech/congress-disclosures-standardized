# EventBridge Rules for Pipeline Scheduling

# IAM Role for EventBridge to trigger Step Functions
resource "aws_iam_role" "eventbridge_step_functions_role" {
  name = "${var.project_name}-eventbridge-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# IAM Policy for EventBridge
resource "aws_iam_role_policy" "eventbridge_step_functions_policy" {
  name = "${var.project_name}-eventbridge-step-functions-policy"
  role = aws_iam_role.eventbridge_step_functions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = [
          aws_sfn_state_machine.house_fd_pipeline.arn,
          aws_sfn_state_machine.congress_pipeline.arn,
          aws_sfn_state_machine.lobbying_pipeline.arn
        ]
      }
    ]
  })
}

# House FD Pipeline - Daily Schedule (DISABLED until watermarking is complete)
# STORY-001: Changed from hourly to daily to prevent $4,000/month cost explosion
resource "aws_cloudwatch_event_rule" "house_fd_daily" {
  name                = "${var.project_name}-house-fd-daily"
  description         = "Trigger House FD pipeline daily at 4 AM EST"
  schedule_expression = "cron(0 9 * * ? *)" # 9 AM UTC = 4 AM EST
  state               = "DISABLED"          # Enable after watermarking is implemented (STORY-003)

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Pipeline    = "house-fd"
  }
}

resource "aws_cloudwatch_event_target" "trigger_house_fd" {
  rule     = aws_cloudwatch_event_rule.house_fd_daily.name
  arn      = aws_sfn_state_machine.house_fd_pipeline.arn
  role_arn = aws_iam_role.eventbridge_step_functions_role.arn

  input = jsonencode({
    execution_type = "scheduled"
    year           = tonumber(formatdate("YYYY", timestamp()))
    triggered_by   = "eventbridge"
  })
}

# Congress.gov Pipeline - Daily at 3 AM EST
resource "aws_cloudwatch_event_rule" "congress_daily" {
  name                = "${var.project_name}-congress-daily"
  description         = "Trigger Congress.gov pipeline daily at 3 AM EST"
  schedule_expression = "cron(0 8 * * ? *)" # 8 AM UTC = 3 AM EST

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Pipeline    = "congress"
  }
}

resource "aws_cloudwatch_event_target" "trigger_congress" {
  rule     = aws_cloudwatch_event_rule.congress_daily.name
  arn      = aws_sfn_state_machine.congress_pipeline.arn
  role_arn = aws_iam_role.eventbridge_step_functions_role.arn

  input = jsonencode({
    execution_type = "scheduled"
    year           = tonumber(formatdate("YYYY", timestamp()))
    triggered_by   = "eventbridge"
  })
}

# Lobbying Pipeline - Weekly on Monday at 6 AM EST
resource "aws_cloudwatch_event_rule" "lobbying_weekly" {
  name                = "${var.project_name}-lobbying-weekly"
  description         = "Trigger Lobbying pipeline weekly on Mondays at 6 AM EST"
  schedule_expression = "cron(0 11 ? * MON *)" # 11 AM UTC = 6 AM EST on Mondays

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Pipeline    = "lobbying"
  }
}

resource "aws_cloudwatch_event_target" "trigger_lobbying" {
  rule     = aws_cloudwatch_event_rule.lobbying_weekly.name
  arn      = aws_sfn_state_machine.lobbying_pipeline.arn
  role_arn = aws_iam_role.eventbridge_step_functions_role.arn

  input = jsonencode({
    execution_type = "scheduled"
    trigger_time   = "$${aws.events.event.time}"
  })
}

# Cross-Dataset Correlation Pipeline - Triggered by House FD completion
# (This is handled within the House FD state machine, no EventBridge rule needed)

# Optional: Manual trigger rule (disabled by default)
resource "aws_cloudwatch_event_rule" "manual_trigger" {
  name        = "${var.project_name}-manual-trigger"
  description = "Manual trigger for pipelines via AWS Console"
  event_pattern = jsonencode({
    source      = ["custom.pipeline"]
    detail-type = ["Pipeline Manual Trigger"]
  })
  state = "DISABLED"

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Outputs
output "house_fd_schedule_rule_arn" {
  description = "ARN of House FD daily schedule rule"
  value       = aws_cloudwatch_event_rule.house_fd_daily.arn
}

output "congress_schedule_rule_arn" {
  description = "ARN of Congress.gov daily schedule rule"
  value       = aws_cloudwatch_event_rule.congress_daily.arn
}

output "lobbying_schedule_rule_arn" {
  description = "ARN of Lobbying weekly schedule rule"
  value       = aws_cloudwatch_event_rule.lobbying_weekly.arn
}

output "eventbridge_role_arn" {
  description = "ARN of EventBridge execution role"
  value       = aws_iam_role.eventbridge_step_functions_role.arn
}
