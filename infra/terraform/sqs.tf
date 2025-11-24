# Dead Letter Queue (DLQ) for failed extraction jobs
resource "aws_sqs_queue" "extraction_dlq" {
  name = "${local.name_prefix}-extract-dlq"

  # Longer retention for troubleshooting failed messages
  message_retention_seconds = 1209600 # 14 days (maximum)

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-extract-dlq"
      Component = "queue"
      Purpose   = "dead-letter-queue"
    }
  )
}

# Main extraction queue
resource "aws_sqs_queue" "extraction_queue" {
  name = "${local.name_prefix}-extract-queue"

  # Visibility timeout must be longer than Lambda timeout
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds

  # Message retention
  message_retention_seconds = var.sqs_message_retention_days * 86400

  # Receive wait time (long polling reduces costs)
  receive_wait_time_seconds = 20 # Enable long polling

  # Dead letter queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.extraction_dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })

  # Enable SQS server-side encryption (free with SQS-managed keys)
  sqs_managed_sse_enabled = true

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-extract-queue"
      Component = "queue"
      Purpose   = "pdf-extraction"
    }
  )
}

# Lambda event source mapping for extraction queue
resource "aws_lambda_event_source_mapping" "extraction_queue" {
  event_source_arn = aws_sqs_queue.extraction_queue.arn
  function_name    = aws_lambda_function.extract_document.arn

  # Batch processing configuration
  batch_size                         = 10 # Process up to 10 messages per invocation
  maximum_batching_window_in_seconds = 5  # Wait up to 5 seconds to collect batch

  # Error handling
  function_response_types = ["ReportBatchItemFailures"] # Partial batch failures

  # Scaling configuration (free tier friendly)
  scaling_config {
    maximum_concurrency = var.lambda_max_concurrent_executions
  }
}

# CloudWatch alarm for DLQ messages
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  count = var.enable_cost_alerts ? 1 : 0

  alarm_name          = "${local.name_prefix}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alert when messages appear in DLQ"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.extraction_dlq.name
  }

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-dlq-alarm"
      Component = "monitoring"
    }
  )
}

# Outputs
output "sqs_extraction_queue_url" {
  description = "URL of extraction SQS queue"
  value       = aws_sqs_queue.extraction_queue.url
}

output "sqs_extraction_queue_arn" {
  description = "ARN of extraction SQS queue"
  value       = aws_sqs_queue.extraction_queue.arn
}

output "sqs_dlq_url" {
  description = "URL of dead letter queue"
  value       = aws_sqs_queue.extraction_dlq.url
}

output "sqs_dlq_arn" {
  description = "ARN of dead letter queue"
  value       = aws_sqs_queue.extraction_dlq.arn
}
