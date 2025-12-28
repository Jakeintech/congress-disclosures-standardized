# Code-Based Structured Extraction (NO Textract)
# This Lambda extracts structured data using CODE ONLY (regex, patterns)

# SQS Queue for code-based extraction jobs
resource "aws_sqs_queue" "code_extraction_queue" {
  name                       = "${local.name_prefix}-code-extraction-queue"
  visibility_timeout_seconds = 360 # 6 minutes (Lambda timeout * 2)
  message_retention_seconds  = 1209600 # 14 days
  receive_wait_time_seconds  = 20 # Long polling

  # DLQ for failed code extractions
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.code_extraction_dlq.arn
    maxReceiveCount     = 3 # Retry 3 times before DLQ
  })


  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-code-extraction-queue"
      Component = "sqs"
      Purpose   = "code-extraction"
    }
  )
}

# Dead Letter Queue for code extraction failures
resource "aws_sqs_queue" "code_extraction_dlq" {
  name                      = "${local.name_prefix}-code-extraction-dlq"
  message_retention_seconds = 1209600 # 14 days


  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-code-extraction-dlq"
      Component = "sqs"
      Purpose   = "code-extraction-dlq"
    }
  )
}

# Redrive allow policy (allows messages to be moved back from DLQ)
resource "aws_sqs_queue_redrive_allow_policy" "code_extraction_dlq_redrive" {
  queue_url = aws_sqs_queue.code_extraction_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.code_extraction_queue.arn]
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "extract_structured_code" {
  name              = "/aws/lambda/${local.name_prefix}-extract-structured-code"
  retention_in_days = var.cloudwatch_log_retention_days


  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-extract-structured-code-logs"
      Component = "cloudwatch"
    }
  )
}

# Lambda Function: house_fd_extract_structured_code
resource "aws_lambda_function" "extract_structured_code" {
  function_name = "${local.name_prefix}-extract-structured-code"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  # Deploy from S3
  s3_bucket        = aws_s3_bucket.data_lake.id
  s3_key           = "lambda-deployments/house_fd_extract_structured_code/function.zip"
  source_code_hash = fileexists("${path.module}/../../ingestion/lambdas/house_fd_extract_structured_code/function.zip") ? filebase64sha256("${path.module}/../../ingestion/lambdas/house_fd_extract_structured_code/function.zip") : null

  timeout     = 180 # 3 minutes (code-based extraction is fast)
  memory_size = 1024 # Needs more memory for OCR

  layers = [var.tesseract_layer_arn]

  environment {
    variables = {
      S3_BUCKET_NAME              = aws_s3_bucket.data_lake.id
      S3_SILVER_PREFIX            = "silver"
      LOG_LEVEL                   = "INFO"
      PYTHONUNBUFFERED            = "1"
      TZ                          = "UTC"
    }
  }

  # Reserved concurrent executions disabled for free tier compatibility
  # reserved_concurrent_executions = 5

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }


  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-extract-structured-code"
      Component = "lambda"
      Purpose   = "code-extraction"
    }
  )

  lifecycle {
    ignore_changes = [
      source_code_hash,
      filename
    ]
  }

  depends_on = [


    null_resource.package_lambdas,
    aws_cloudwatch_log_group.extract_structured_code,
    aws_iam_role_policy.lambda_logging
  ]
}

# Event Source Mapping: SQS → Lambda (ENABLED)
resource "aws_lambda_event_source_mapping" "code_extraction_trigger" {
  event_source_arn = aws_sqs_queue.code_extraction_queue.arn
  function_name    = aws_lambda_function.extract_structured_code.arn

  batch_size                         = 10 # Process 10 messages at a time
  maximum_batching_window_in_seconds = 5  # Wait up to 5s to collect batch

  # Partial batch response (don't fail entire batch if one message fails)
  function_response_types = ["ReportBatchItemFailures"]

  enabled = true # ENABLED from the start

  depends_on = [


    null_resource.package_lambdas,
    aws_iam_role_policy.lambda_sqs_access
  ]
}

# Lambda Permission for SQS to invoke
resource "aws_lambda_permission" "allow_sqs_invoke_code_extraction" {
  statement_id  = "AllowSQSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.extract_structured_code.function_name
  principal     = "sqs.amazonaws.com"
  source_arn    = aws_sqs_queue.code_extraction_queue.arn
}

# Outputs
output "code_extraction_queue_url" {
  description = "URL of code extraction queue"
  value       = aws_sqs_queue.code_extraction_queue.url
}

output "code_extraction_queue_arn" {
  description = "ARN of code extraction queue"
  value       = aws_sqs_queue.code_extraction_queue.arn
}

output "lambda_extract_structured_code_name" {
  description = "Name of code extraction Lambda"
  value       = aws_lambda_function.extract_structured_code.function_name
}

output "lambda_extract_structured_code_arn" {
  description = "ARN of code extraction Lambda"
  value       = aws_lambda_function.extract_structured_code.arn
}
