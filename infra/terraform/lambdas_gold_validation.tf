# Lambda Function for Gold Layer Dimension Validation

# Lambda Function: Validate Dimensions
resource "aws_lambda_function" "validate_dimensions" {
  function_name = "${var.project_name}-validate-dimensions"
  description   = "Validate Gold dimension tables before building facts"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 120
  memory_size   = 512

  s3_bucket = var.s3_bucket_name
  s3_key    = "lambda-deployments/validate_dimensions/function.zip"

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = var.log_level
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
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "validate_dimensions_logs" {
  name              = "/aws/lambda/${aws_lambda_function.validate_dimensions.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Name        = "${var.project_name}-validate-dimensions-logs"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Outputs
output "validate_dimensions_function_name" {
  description = "Name of Validate Dimensions Lambda function"
  value       = aws_lambda_function.validate_dimensions.function_name
}

output "validate_dimensions_function_arn" {
  description = "ARN of Validate Dimensions Lambda function"
  value       = aws_lambda_function.validate_dimensions.arn
}
