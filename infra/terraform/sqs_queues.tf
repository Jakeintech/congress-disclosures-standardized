# SQS Queues for all pipelines
# Consolidated from sqs.tf, sqs_congress.tf, sqs_lobbying.tf

# =============================================================================
# Extraction Queues (from sqs.tf)
# =============================================================================

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
# Extraction Queue (for PDF processing)
resource "aws_sqs_queue" "extraction_queue" {
  name                       = "${var.project_name}-${var.environment}-extract-queue"
  visibility_timeout_seconds = 300    # 5 minutes for Lambda processing
  message_retention_seconds  = 345600 # 4 days
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.extraction_dlq.arn
    maxReceiveCount     = 3
  })

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
# NOTE: Function definition is in lambda_silver_layer.tf (formerly structured_extraction.tf)
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

# CloudWatch alarm for DLQ messages (Specific to extraction DLQ)
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

# =============================================================================
# Congress.gov API Ingestion SQS Queues (from sqs_congress.tf)
# =============================================================================

# Congress API Fetch Queue (for individual entity fetches from Congress.gov API)

# Dead Letter Queue for API fetch failures
resource "aws_sqs_queue" "congress_fetch_dlq" {
  count = var.enable_congress_pipeline ? 1 : 0

  name = local.congress_fetch_dlq_name

  # Longer retention for troubleshooting failed API requests
  message_retention_seconds = 1209600 # 14 days (maximum)

  tags = merge(
    local.congress_tags,
    {
      Name      = local.congress_fetch_dlq_name
      Component = "queue"
      Purpose   = "dead-letter-queue"
      Pipeline  = "congress-fetch"
    }
  )
}

# Main Congress API fetch queue
resource "aws_sqs_queue" "congress_fetch_queue" {
  count = var.enable_congress_pipeline ? 1 : 0

  name                       = local.congress_fetch_queue_name
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds     # Should be > Lambda timeout
  message_retention_seconds  = var.sqs_message_retention_days * 86400 # Convert days to seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.congress_fetch_dlq[0].arn
    maxReceiveCount     = var.sqs_max_receive_count
  })

  tags = merge(
    local.congress_tags,
    {
      Name      = local.congress_fetch_queue_name
      Component = "queue"
      Purpose   = "api-fetch"
      Pipeline  = "congress-fetch"
    }
  )
}

# Congress Bronze-to-Silver Transform Queue

# Dead Letter Queue for Bronze-to-Silver transform failures
resource "aws_sqs_queue" "congress_silver_dlq" {
  count = var.enable_congress_pipeline ? 1 : 0

  name = local.congress_silver_dlq_name

  message_retention_seconds = 1209600 # 14 days (maximum)

  tags = merge(
    local.congress_tags,
    {
      Name      = local.congress_silver_dlq_name
      Component = "queue"
      Purpose   = "dead-letter-queue"
      Pipeline  = "congress-silver"
    }
  )
}

# Main Bronze-to-Silver transform queue
resource "aws_sqs_queue" "congress_silver_queue" {
  count = var.enable_congress_pipeline ? 1 : 0

  name                       = local.congress_silver_queue_name
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds # Should be > Lambda timeout
  message_retention_seconds  = var.sqs_message_retention_days * 86400

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.congress_silver_dlq[0].arn
    maxReceiveCount     = var.sqs_max_receive_count
  })

  tags = merge(
    local.congress_tags,
    {
      Name      = local.congress_silver_queue_name
      Component = "queue"
      Purpose   = "bronze-to-silver"
      Pipeline  = "congress-silver"
    }
  )
}

# =============================================================================
# Lobbying Extraction Queues (from sqs_lobbying.tf)
# =============================================================================

resource "aws_sqs_queue" "lda_bill_extraction_queue" {
  name                       = "${local.name_prefix}-lda-bill-extraction-queue"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 1209600 # 14 days
  receive_wait_time_seconds  = 20

  # Optional DLQ for failed LDA bill extraction messages
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.lda_bill_extraction_dlq.arn
    maxReceiveCount     = 3
  })

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-lda-bill-extraction-queue"
      Component = "sqs"
      Purpose   = "lda-bill-extraction"
    }
  )
}

resource "aws_sqs_queue" "lda_bill_extraction_dlq" {
  name                      = "${local.name_prefix}-lda-bill-extraction-dlq"
  message_retention_seconds = 1209600

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-lda-bill-extraction-dlq"
      Component = "sqs"
      Purpose   = "lda-bill-extraction-dlq"
    }
  )
}

# =============================================================================
# Outputs
# =============================================================================

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

output "sqs_congress_fetch_queue_url" {
  description = "URL of Congress API fetch SQS queue"
  value       = var.enable_congress_pipeline ? aws_sqs_queue.congress_fetch_queue[0].url : ""
}

output "sqs_congress_fetch_queue_arn" {
  description = "ARN of Congress API fetch SQS queue"
  value       = var.enable_congress_pipeline ? aws_sqs_queue.congress_fetch_queue[0].arn : ""
}

output "sqs_congress_fetch_dlq_url" {
  description = "URL of Congress fetch dead letter queue"
  value       = var.enable_congress_pipeline ? aws_sqs_queue.congress_fetch_dlq[0].url : ""
}

output "sqs_congress_fetch_dlq_arn" {
  description = "ARN of Congress fetch dead letter queue"
  value       = var.enable_congress_pipeline ? aws_sqs_queue.congress_fetch_dlq[0].arn : ""
}

output "sqs_congress_silver_queue_url" {
  description = "URL of Congress Bronze-to-Silver SQS queue"
  value       = var.enable_congress_pipeline ? aws_sqs_queue.congress_silver_queue[0].url : ""
}

output "sqs_congress_silver_queue_arn" {
  description = "ARN of Congress Bronze-to-Silver SQS queue"
  value       = var.enable_congress_pipeline ? aws_sqs_queue.congress_silver_queue[0].arn : ""
}

output "sqs_congress_silver_dlq_url" {
  description = "URL of Congress Silver dead letter queue"
  value       = var.enable_congress_pipeline ? aws_sqs_queue.congress_silver_dlq[0].url : ""
}

output "sqs_congress_silver_dlq_arn" {
  description = "ARN of Congress Silver dead letter queue"
  value       = var.enable_congress_pipeline ? aws_sqs_queue.congress_silver_dlq[0].arn : ""
}

output "lda_bill_extraction_queue_url" {
  description = "URL of LDA bill extraction queue"
  value       = aws_sqs_queue.lda_bill_extraction_queue.url
}

output "lda_bill_extraction_queue_arn" {
  description = "ARN of LDA bill extraction queue"
  value       = aws_sqs_queue.lda_bill_extraction_queue.arn
}
