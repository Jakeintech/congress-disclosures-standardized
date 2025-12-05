# Lobbying Disclosure Act (LDA) Data Pipeline Lambda Functions

# =============================================================================
# Lambda Function: lda_ingest_filings
# =============================================================================

resource "aws_cloudwatch_log_group" "lda_ingest_filings" {
  name              = "/aws/lambda/${local.name_prefix}-lda-ingest-filings"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-lda-ingest-filings-logs"
      Component = "cloudwatch"
    }
  )
}

resource "aws_lambda_function" "lda_ingest_filings" {
  function_name = "${local.name_prefix}-lda-ingest-filings"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  # Deploy from S3
  s3_bucket        = aws_s3_bucket.data_lake.id
  s3_key           = "lambda-deployments/lda_ingest_filings/function.zip"
  source_code_hash = fileexists("${path.module}/../../ingestion/lambdas/lda_ingest_filings/function.zip") ? filebase64sha256("${path.module}/../../ingestion/lambdas/lda_ingest_filings/function.zip") : null

  timeout     = var.lambda_timeout_seconds
  memory_size = var.lambda_ingest_memory_mb

  environment {
    variables = {
      S3_BUCKET_NAME     = aws_s3_bucket.data_lake.id
      S3_BRONZE_PREFIX   = "bronze"
      EXTRACTION_VERSION = var.extraction_version
      LOG_LEVEL          = "INFO"
      PYTHONUNBUFFERED   = "1"
      TZ                 = "UTC"
    }
  }

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  layers = var.lambda_layer_arns

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-lda-ingest-filings"
      Component = "lambda"
      Purpose   = "lobbying-ingestion"
    }
  )

  lifecycle {
    ignore_changes = [
      source_code_hash,
      filename
    ]
  }

  depends_on = [
    aws_cloudwatch_log_group.lda_ingest_filings,
    aws_iam_role_policy.lambda_logging,
    aws_iam_role_policy.lambda_s3_access
  ]
}

# Lambda permission for manual invocation
resource "aws_lambda_permission" "allow_manual_invoke_lda_ingest" {
  statement_id  = "AllowManualInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lda_ingest_filings.function_name
  principal     = local.account_id
}

# =============================================================================
# Outputs
# =============================================================================

output "lda_ingest_lambda_arn" {
  description = "ARN of LDA ingest Lambda function"
  value       = aws_lambda_function.lda_ingest_filings.arn
}

output "lda_ingest_lambda_name" {
  description = "Name of LDA ingest Lambda function"
  value       = aws_lambda_function.lda_ingest_filings.function_name
}
