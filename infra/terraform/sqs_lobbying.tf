# LDA Bill Extraction Queue (for post-ingest processing of LDA filings)

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

output "lda_bill_extraction_queue_url" {
  description = "URL of LDA bill extraction queue"
  value       = aws_sqs_queue.lda_bill_extraction_queue.url
}

output "lda_bill_extraction_queue_arn" {
  description = "ARN of LDA bill extraction queue"
  value       = aws_sqs_queue.lda_bill_extraction_queue.arn
}

