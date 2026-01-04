# Lambda Functions for Gold Layer Validation

# Validate Dimensions Lambda
resource "aws_lambda_function" "validate_dimensions" {
  function_name = "${var.project_name}-validate-dimensions"
  description   = "Validate that all Gold dimension tables exist and are valid before building facts"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 120
  memory_size   = 512

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/gold-layer/validate_dimensions.zip"
  source_code_hash = fileexists("${path.module}/../../build/validate_dimensions.zip") ? filebase64sha256("${path.module}/../../build/validate_dimensions.zip") : null

  layers = [aws_lambda_layer_version.duckdb.arn]

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
      ENVIRONMENT    = var.environment
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = {
    Name        = "${var.project_name}-validate-dimensions"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-validation"
    Sprint      = "sprint-3"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "validate_dimensions_logs" {
  name              = "/aws/lambda/${aws_lambda_function.validate_dimensions.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Output
output "validate_dimensions_function_name" {
  description = "Name of Validate Dimensions Lambda"
  value       = aws_lambda_function.validate_dimensions.function_name
}

output "validate_dimensions_function_arn" {
  description = "ARN of Validate Dimensions Lambda"
  value       = aws_lambda_function.validate_dimensions.arn
}
