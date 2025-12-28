# Congress.gov API Ingestion SQS Queues

# =============================================================================
# Congress API Fetch Queue (for individual entity fetches from Congress.gov API)
# =============================================================================

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
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds # Should be > Lambda timeout
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

# =============================================================================
# Congress Bronze-to-Silver Transform Queue
# =============================================================================

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
# Outputs
# =============================================================================

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
