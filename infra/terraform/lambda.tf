# Data source for Lambda deployment packages (will be created later)
# For now, we'll use placeholder zips - actual code will be packaged by CI/CD

# Lambda function: house_fd_ingest_zip
resource "aws_lambda_function" "ingest_zip" {
  function_name = "${local.name_prefix}-ingest-zip"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  # Placeholder - actual deployment will be done via CI/CD or manual packaging
  filename         = "${path.module}/../../ingestion/lambdas/house_fd_ingest_zip/function.zip"
  source_code_hash = fileexists("${path.module}/../../ingestion/lambdas/house_fd_ingest_zip/function.zip") ? filebase64sha256("${path.module}/../../ingestion/lambdas/house_fd_ingest_zip/function.zip") : null

  timeout     = var.lambda_timeout_seconds
  memory_size = var.lambda_ingest_memory_mb

  # Environment variables
  environment {
    variables = {
      S3_BUCKET_NAME      = aws_s3_bucket.data_lake.id
      S3_BRONZE_PREFIX    = "bronze"
      SQS_QUEUE_URL       = aws_sqs_queue.extraction_queue.url
      EXTRACTION_VERSION  = var.extraction_version
      LOG_LEVEL           = "INFO"
      PYTHONUNBUFFERED    = "1"
      TZ                  = "UTC"
    }
  }

  # Reserved concurrent executions (1 for ingestion to avoid duplicate processing)
  reserved_concurrent_executions = 1

  # Enable X-Ray tracing (optional)
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  # Lambda layers (if any)
  layers = var.lambda_layer_arns

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-ingest-zip"
      Component = "lambda"
      Purpose   = "ingestion"
    }
  )

  # Ignore changes to source code hash (managed by CI/CD)
  lifecycle {
    ignore_changes = [
      source_code_hash,
      filename
    ]
  }

  # Depends on log group being created first
  depends_on = [
    aws_cloudwatch_log_group.ingest_zip,
    aws_iam_role_policy.lambda_logging
  ]
}

# Lambda function: house_fd_index_to_silver
resource "aws_lambda_function" "index_to_silver" {
  function_name = "${local.name_prefix}-index-to-silver"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  filename         = "${path.module}/../../ingestion/lambdas/house_fd_index_to_silver/function.zip"
  source_code_hash = fileexists("${path.module}/../../ingestion/lambdas/house_fd_index_to_silver/function.zip") ? filebase64sha256("${path.module}/../../ingestion/lambdas/house_fd_index_to_silver/function.zip") : null

  timeout     = 120 # 2 minutes (lighter processing)
  memory_size = var.lambda_index_memory_mb

  environment {
    variables = {
      S3_BUCKET_NAME     = aws_s3_bucket.data_lake.id
      S3_BRONZE_PREFIX   = "bronze"
      S3_SILVER_PREFIX   = "silver"
      EXTRACTION_VERSION = var.extraction_version
      LOG_LEVEL          = "INFO"
      PYTHONUNBUFFERED   = "1"
      TZ                 = "UTC"
    }
  }

  reserved_concurrent_executions = 2

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  layers = var.lambda_layer_arns

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-index-to-silver"
      Component = "lambda"
      Purpose   = "normalization"
    }
  )

  lifecycle {
    ignore_changes = [
      source_code_hash,
      filename
    ]
  }

  depends_on = [
    aws_cloudwatch_log_group.index_to_silver,
    aws_iam_role_policy.lambda_logging
  ]
}

# Lambda function: house_fd_extract_document
resource "aws_lambda_function" "extract_document" {
  function_name = "${local.name_prefix}-extract-document"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  filename         = "${path.module}/../../ingestion/lambdas/house_fd_extract_document/function.zip"
  source_code_hash = fileexists("${path.module}/../../ingestion/lambdas/house_fd_extract_document/function.zip") ? filebase64sha256("${path.module}/../../ingestion/lambdas/house_fd_extract_document/function.zip") : null

  timeout     = var.lambda_timeout_seconds
  memory_size = var.lambda_extract_memory_mb

  # Ephemeral storage for large PDFs (default 512 MB, max 10240 MB)
  ephemeral_storage {
    size = 1024 # 1 GB (within free tier)
  }

  environment {
    variables = {
      S3_BUCKET_NAME           = aws_s3_bucket.data_lake.id
      S3_BRONZE_PREFIX         = "bronze"
      S3_SILVER_PREFIX         = "silver"
      EXTRACTION_VERSION       = var.extraction_version
      TEXTRACT_MAX_PAGES_SYNC  = var.textract_max_pages_sync
      LOG_LEVEL                = "INFO"
      PYTHONUNBUFFERED         = "1"
      TZ                       = "UTC"
    }
  }

  # Higher concurrency for extraction (but capped for cost control)
  reserved_concurrent_executions = var.lambda_max_concurrent_executions

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  layers = var.lambda_layer_arns

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-extract-document"
      Component = "lambda"
      Purpose   = "extraction"
    }
  )

  lifecycle {
    ignore_changes = [
      source_code_hash,
      filename
    ]
  }

  depends_on = [
    aws_cloudwatch_log_group.extract_document,
    aws_iam_role_policy.lambda_logging
  ]
}

# Lambda permission for manual invocation (for ingest Lambda)
resource "aws_lambda_permission" "allow_manual_invoke_ingest" {
  statement_id  = "AllowManualInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest_zip.function_name
  principal     = local.account_id
}

# Lambda permission for SQS to invoke extract Lambda
resource "aws_lambda_permission" "allow_sqs_invoke_extract" {
  statement_id  = "AllowSQSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.extract_document.function_name
  principal     = "sqs.amazonaws.com"
  source_arn    = aws_sqs_queue.extraction_queue.arn
}

# Outputs
output "lambda_ingest_zip_arn" {
  description = "ARN of ingest Lambda function"
  value       = aws_lambda_function.ingest_zip.arn
}

output "lambda_ingest_zip_name" {
  description = "Name of ingest Lambda function"
  value       = aws_lambda_function.ingest_zip.function_name
}

output "lambda_index_to_silver_arn" {
  description = "ARN of index-to-silver Lambda function"
  value       = aws_lambda_function.index_to_silver.arn
}

output "lambda_index_to_silver_name" {
  description = "Name of index-to-silver Lambda function"
  value       = aws_lambda_function.index_to_silver.function_name
}

output "lambda_extract_document_arn" {
  description = "ARN of extract document Lambda function"
  value       = aws_lambda_function.extract_document.arn
}

output "lambda_extract_document_name" {
  description = "Name of extract document Lambda function"
  value       = aws_lambda_function.extract_document.function_name
}
