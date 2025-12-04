# Congress.gov Pipeline CloudWatch Alarms and Monitoring

# =============================================================================
# Congress Fetch DLQ Alarm
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "congress_fetch_dlq_messages" {
  count = var.enable_congress_pipeline && var.enable_cost_alerts ? 1 : 0

  alarm_name          = "${local.name_prefix}-congress-fetch-dlq"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 5   # Alert when more than 5 messages in DLQ
  alarm_description   = "Alert when Congress API fetch messages appear in DLQ (indicates API fetch failures)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.congress_fetch_dlq[0].name
  }

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  tags = merge(
    local.congress_tags,
    {
      Name      = "${local.name_prefix}-congress-fetch-dlq-alarm"
      Component = "monitoring"
      Pipeline  = "congress-fetch"
    }
  )
}

# =============================================================================
# Congress Silver DLQ Alarm
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "congress_silver_dlq_messages" {
  count = var.enable_congress_pipeline && var.enable_cost_alerts ? 1 : 0

  alarm_name          = "${local.name_prefix}-congress-silver-dlq"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 5   # Alert when more than 5 messages in DLQ
  alarm_description   = "Alert when Congress Bronze-to-Silver messages appear in DLQ (indicates transform failures)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.congress_silver_dlq[0].name
  }

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  tags = merge(
    local.congress_tags,
    {
      Name      = "${local.name_prefix}-congress-silver-dlq-alarm"
      Component = "monitoring"
      Pipeline  = "congress-silver"
    }
  )
}

# =============================================================================
# Congress Fetch Queue Age Alarm (Optional - detect stuck processing)
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "congress_fetch_queue_age" {
  count = var.enable_congress_pipeline && var.enable_cost_alerts ? 1 : 0

  alarm_name          = "${local.name_prefix}-congress-fetch-queue-age"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = 300 # 5 minutes
  statistic           = "Maximum"
  threshold           = 3600 # 1 hour (messages older than 1 hour indicate stuck processing)
  alarm_description   = "Alert when Congress fetch queue messages are stuck (oldest message > 1 hour old)"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.congress_fetch_queue[0].name
  }

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  tags = merge(
    local.congress_tags,
    {
      Name      = "${local.name_prefix}-congress-fetch-age-alarm"
      Component = "monitoring"
      Pipeline  = "congress-fetch"
    }
  )
}

# =============================================================================
# Congress Fetch Lambda Error Rate Alarm (Optional)
# =============================================================================

# Note: This alarm will be created once the Lambda function exists (in STORY 1.3)
# Placeholder for future implementation:
#
# resource "aws_cloudwatch_metric_alarm" "congress_fetch_lambda_errors" {
#   alarm_name          = "${local.name_prefix}-congress-fetch-lambda-errors"
#   comparison_operator = "GreaterThanThreshold"
#   evaluation_periods  = 1
#   metric_name         = "Errors"
#   namespace           = "AWS/Lambda"
#   period              = 300 # 5 minutes
#   statistic           = "Sum"
#   threshold           = 10  # Alert when more than 10 errors in 5 minutes
#   alarm_description   = "Alert on Congress API fetch Lambda errors"
#   treat_missing_data  = "notBreaching"
#
#   dimensions = {
#     FunctionName = aws_lambda_function.congress_fetch_entity[0].function_name
#   }
#
#   alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []
# }

# =============================================================================
# CloudWatch Log Groups (for Lambda functions)
# =============================================================================

# Congress Fetch Lambda Logs
resource "aws_cloudwatch_log_group" "congress_fetch_lambda" {
  count = var.enable_congress_pipeline ? 1 : 0

  name              = "/aws/lambda/${local.congress_fetch_lambda_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.congress_tags,
    {
      Name      = "${local.congress_fetch_lambda_name}-logs"
      Component = "logging"
      Pipeline  = "congress-fetch"
    }
  )
}

# Congress Orchestrator Lambda Logs
resource "aws_cloudwatch_log_group" "congress_orchestrator_lambda" {
  count = var.enable_congress_pipeline ? 1 : 0

  name              = "/aws/lambda/${local.congress_orchestrator_lambda_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.congress_tags,
    {
      Name      = "${local.congress_orchestrator_lambda_name}-logs"
      Component = "logging"
      Pipeline  = "congress-orchestration"
    }
  )
}

# Congress Bronze-to-Silver Lambda Logs
resource "aws_cloudwatch_log_group" "congress_silver_lambda" {
  count = var.enable_congress_pipeline ? 1 : 0

  name              = "/aws/lambda/${local.congress_silver_lambda_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.congress_tags,
    {
      Name      = "${local.congress_silver_lambda_name}-logs"
      Component = "logging"
      Pipeline  = "congress-silver"
    }
  )
}

# =============================================================================
# Outputs
# =============================================================================

output "congress_fetch_dlq_alarm_name" {
  description = "Name of Congress fetch DLQ CloudWatch alarm"
  value       = var.enable_congress_pipeline && var.enable_cost_alerts ? aws_cloudwatch_metric_alarm.congress_fetch_dlq_messages[0].alarm_name : ""
}

output "congress_silver_dlq_alarm_name" {
  description = "Name of Congress Silver DLQ CloudWatch alarm"
  value       = var.enable_congress_pipeline && var.enable_cost_alerts ? aws_cloudwatch_metric_alarm.congress_silver_dlq_messages[0].alarm_name : ""
}

output "congress_fetch_log_group_name" {
  description = "Name of Congress fetch Lambda CloudWatch log group"
  value       = var.enable_congress_pipeline ? aws_cloudwatch_log_group.congress_fetch_lambda[0].name : ""
}

output "congress_orchestrator_log_group_name" {
  description = "Name of Congress orchestrator Lambda CloudWatch log group"
  value       = var.enable_congress_pipeline ? aws_cloudwatch_log_group.congress_orchestrator_lambda[0].name : ""
}

output "congress_silver_log_group_name" {
  description = "Name of Congress Silver Lambda CloudWatch log group"
  value       = var.enable_congress_pipeline ? aws_cloudwatch_log_group.congress_silver_lambda[0].name : ""
}
