# Orchestration Lambda Functions
# Extracted from step_functions.tf

# Lambda function: publish_pipeline_metrics
resource "aws_lambda_function" "publish_pipeline_metrics" {
  function_name = "${var.project_name}-publish-pipeline-metrics"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  filename         = "${path.module}/../../backend/functions/ingestion/publish_pipeline_metrics/function.zip"
  source_code_hash = fileexists("${path.module}/../../backend/functions/ingestion/publish_pipeline_metrics/function.zip") ? filebase64sha256("${path.module}/../../backend/functions/ingestion/publish_pipeline_metrics/function.zip") : null

  timeout     = 30
  memory_size = 128

  environment {
    variables = {
      CLOUDWATCH_NAMESPACE = "CongressDisclosures/Pipeline"
      ENVIRONMENT          = var.environment
      LOG_LEVEL            = "INFO"
    }
  }

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  tags = merge(
    local.standard_tags,
    {
      Name      = "${var.project_name}-publish-pipeline-metrics"
      Component = "lambda"
      Purpose   = "metrics"
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
    aws_cloudwatch_log_group.publish_pipeline_metrics,
    aws_iam_role_policy.lambda_logging
  ]
}

# Check House FD Updates Lambda
resource "aws_lambda_function" "check_house_fd_updates" {
  function_name = "${local.name_prefix}-check-house-fd-updates"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 128

  s3_bucket = var.s3_bucket_name
  s3_key    = "lambda-deployments/check_house_fd_updates/function.zip"

  environment {
    variables = {
      LOG_LEVEL            = "INFO"
      ENVIRONMENT          = var.environment
      WATERMARK_TABLE_NAME = aws_dynamodb_table.pipeline_watermarks.name
      LOOKBACK_YEARS       = "5"
    }
  }

  tags = local.standard_tags
}

# Check Lobbying Updates Lambda
resource "aws_lambda_function" "check_lobbying_updates" {
  function_name = "${local.name_prefix}-check-lobbying-updates"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 128

  s3_bucket = var.s3_bucket_name
  s3_key    = "lambda-deployments/check_lobbying_updates/function.zip"

  environment {
    variables = {
      LOG_LEVEL      = "INFO"
      ENVIRONMENT    = var.environment
      S3_BUCKET_NAME = var.s3_bucket_name
      LOOKBACK_YEARS = "5"
    }
  }

  tags = local.standard_tags
}

# Check Congress Updates Lambda (STORY-047)
resource "aws_lambda_function" "check_congress_updates" {
  function_name = "${local.name_prefix}-check-congress-updates"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 128

  s3_bucket = var.s3_bucket_name
  s3_key    = "lambda-deployments/check_congress_updates/function.zip"

  environment {
    variables = {
      LOG_LEVEL            = "INFO"
      ENVIRONMENT          = var.environment
      WATERMARK_TABLE_NAME = aws_dynamodb_table.pipeline_watermarks.name
      LOOKBACK_YEARS       = "5"
      CONGRESS_API_KEY     = var.congress_gov_api_key
    }
  }

  tags = local.standard_tags
}

# Outputs

output "check_house_fd_updates_function_name" {
  description = "Name of Check House FD Updates Lambda"
  value       = aws_lambda_function.check_house_fd_updates.function_name
}

output "check_lobbying_updates_function_name" {
  description = "Name of Check Lobbying Updates Lambda"
  value       = aws_lambda_function.check_lobbying_updates.function_name
}

output "check_congress_updates_function_name" {
  description = "Name of Check Congress Updates Lambda"
  value       = aws_lambda_function.check_congress_updates.function_name
}
