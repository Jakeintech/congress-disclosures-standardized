# CloudWatch Dashboards, Alarms, and Monitoring Resources
# Consolidated from cloudwatch.tf and cloudwatch_congress.tf

# -----------------------------------------------------------
# From cloudwatch.tf (Alarms & Dashboards & SNS)
# -----------------------------------------------------------
# SNS Topic for alerts (optional)
resource "aws_sns_topic" "alerts" {
  count = var.enable_cost_alerts && var.alert_email != "" ? 1 : 0

  name = "${local.name_prefix}-alerts"

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-alerts"
      Component = "monitoring"
    }
  )
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count = var.enable_cost_alerts && var.alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Lambda error rate alarms
resource "aws_cloudwatch_metric_alarm" "ingest_errors" {
  count = var.enable_cost_alerts ? 1 : 0

  alarm_name          = "${local.name_prefix}-ingest-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert when ingest Lambda has >5 errors in 5 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.ingest_zip.function_name
  }

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-ingest-errors-alarm"
      Component = "monitoring"
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "extract_errors" {
  count = var.enable_cost_alerts ? 1 : 0

  alarm_name          = "${local.name_prefix}-extract-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2 # 2 consecutive periods
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 10 # Higher threshold since this runs more frequently
  alarm_description   = "Alert when extract Lambda has >10 errors in 10 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.extract_document.function_name
  }

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-extract-errors-alarm"
      Component = "monitoring"
    }
  )
}

# Lambda throttling alarm (indicates concurrency limit reached)
resource "aws_cloudwatch_metric_alarm" "extract_throttles" {
  count = var.enable_cost_alerts ? 1 : 0

  alarm_name          = "${local.name_prefix}-extract-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 60 # 1 minute
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert when extract Lambda is throttled"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.extract_document.function_name
  }

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-extract-throttles-alarm"
      Component = "monitoring"
    }
  )
}

# Lambda duration alarm (for cost monitoring)
resource "aws_cloudwatch_metric_alarm" "extract_duration" {
  count = var.enable_cost_alerts ? 1 : 0

  alarm_name          = "${local.name_prefix}-extract-long-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3 # 3 consecutive periods
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 120000 # 2 minutes average (in milliseconds)
  alarm_description   = "Alert when extract Lambda average duration >2 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.extract_document.function_name
  }

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-extract-duration-alarm"
      Component = "monitoring"
    }
  )
}

# Custom metric for extraction success/failure tracking
resource "aws_cloudwatch_log_metric_filter" "extraction_success" {
  name           = "${local.name_prefix}-extraction-success"
  log_group_name = aws_cloudwatch_log_group.extract_document.name
  pattern        = "?INFO ?extraction ?successful"

  metric_transformation {
    name      = "ExtractionSuccess"
    namespace = "CongressDisclosures"
    value     = "1"
    unit      = "Count"
  }
}

resource "aws_cloudwatch_log_metric_filter" "extraction_failure" {
  name           = "${local.name_prefix}-extraction-failure"
  log_group_name = aws_cloudwatch_log_group.extract_document.name
  pattern        = "?ERROR ?extraction ?failed"

  metric_transformation {
    name      = "ExtractionFailure"
    namespace = "CongressDisclosures"
    value     = "1"
    unit      = "Count"
  }
}

# Dashboard for monitoring (optional, for visualization)
resource "aws_cloudwatch_dashboard" "main" {
  count = var.enable_cost_alerts ? 1 : 0

  dashboard_name = "${local.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", { stat = "Sum", label = "Ingest Invocations" }],
            [".", "Errors", { stat = "Sum", label = "Ingest Errors" }],
            [".", "Duration", { stat = "Average", label = "Ingest Duration (avg)" }]
          ]
          period = 300
          stat   = "Sum"
          region = local.region
          title  = "Ingest Lambda Metrics"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", { stat = "Sum", label = "Extract Invocations" }],
            [".", "Errors", { stat = "Sum", label = "Extract Errors" }],
            [".", "Duration", { stat = "Average", label = "Extract Duration (avg)" }],
            [".", "Throttles", { stat = "Sum", label = "Extract Throttles" }]
          ]
          period = 300
          stat   = "Sum"
          region = local.region
          title  = "Extract Lambda Metrics"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/SQS", "NumberOfMessagesSent", { stat = "Sum" }],
            [".", "NumberOfMessagesReceived", { stat = "Sum" }],
            [".", "ApproximateNumberOfMessagesVisible", { stat = "Average" }]
          ]
          period = 300
          stat   = "Sum"
          region = local.region
          title  = "SQS Queue Metrics"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["CongressDisclosures", "ExtractionSuccess", { stat = "Sum" }],
            [".", "ExtractionFailure", { stat = "Sum" }]
          ]
          period = 300
          stat   = "Sum"
          region = local.region
          title  = "Extraction Success/Failure"
        }
      }
    ]
  })
}

# -----------------------------------------------------------
# From cloudwatch_congress.tf (Alarms)
# -----------------------------------------------------------

# Congress Fetch DLQ Alarm
resource "aws_cloudwatch_metric_alarm" "congress_fetch_dlq_messages" {
  count = var.enable_congress_pipeline && var.enable_cost_alerts ? 1 : 0

  alarm_name          = "${local.name_prefix}-congress-fetch-dlq"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 5 # Alert when more than 5 messages in DLQ
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

# Congress Silver DLQ Alarm
resource "aws_cloudwatch_metric_alarm" "congress_silver_dlq_messages" {
  count = var.enable_congress_pipeline && var.enable_cost_alerts ? 1 : 0

  alarm_name          = "${local.name_prefix}-congress-silver-dlq"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 5 # Alert when more than 5 messages in DLQ
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

# Congress Fetch Queue Age Alarm (Optional - detect stuck processing)
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

# -----------------------------------------------------------
# Outputs
# -----------------------------------------------------------
output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = var.enable_cost_alerts && var.alert_email != "" ? aws_sns_topic.alerts[0].arn : null
}

output "cloudwatch_dashboard_url" {
  description = "URL to CloudWatch dashboard"
  value       = var.enable_cost_alerts ? "https://console.aws.amazon.com/cloudwatch/home?region=${local.region}#dashboards:name=${local.name_prefix}-dashboard" : null
}

output "congress_fetch_dlq_alarm_name" {
  description = "Name of Congress fetch DLQ CloudWatch alarm"
  value       = var.enable_congress_pipeline && var.enable_cost_alerts ? aws_cloudwatch_metric_alarm.congress_fetch_dlq_messages[0].alarm_name : ""
}

output "congress_silver_dlq_alarm_name" {
  description = "Name of Congress Silver DLQ CloudWatch alarm"
  value       = var.enable_congress_pipeline && var.enable_cost_alerts ? aws_cloudwatch_metric_alarm.congress_silver_dlq_messages[0].alarm_name : ""
}
