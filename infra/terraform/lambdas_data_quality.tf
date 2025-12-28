# Lambda Layer and Function for Data Quality Checks using Soda Core

# Upload Soda Core layer to S3 (required for layers > 70MB)
resource "aws_s3_object" "soda_core_layer" {
  bucket = var.s3_bucket_name
  key    = "lambda-layers/congress-soda-core.zip"
  source = "${path.module}/../../layers/soda_core/congress-soda-core.zip"
  etag   = fileexists("${path.module}/../../layers/soda_core/congress-soda-core.zip") ? filemd5("${path.module}/../../layers/soda_core/congress-soda-core.zip") : null

  lifecycle {
    ignore_changes = [etag]
  }

  tags = {
    Name        = "soda-core-lambda-layer"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Soda Core Lambda Layer (uploaded via S3)
resource "aws_lambda_layer_version" "soda_core" {
  layer_name          = "${var.project_name}-soda-core"
  description         = "Soda Core 3.3.2 + DuckDB for data quality checks"
  s3_bucket           = aws_s3_object.soda_core_layer.bucket
  s3_key              = aws_s3_object.soda_core_layer.key
  compatible_runtimes = ["python3.11"]
  compatible_architectures = ["x86_64"]

  depends_on = [aws_s3_object.soda_core_layer]
}

# Upload Soda checks to S3
resource "aws_s3_object" "soda_checks" {
  for_each = fileset("${path.module}/../../soda/checks", "*.yml")

  bucket = var.s3_bucket_name
  key    = "soda/checks/${each.value}"
  source = "${path.module}/../../soda/checks/${each.value}"
  etag   = filemd5("${path.module}/../../soda/checks/${each.value}")

  tags = {
    Name        = "soda-check-${each.value}"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Upload Soda configuration to S3
resource "aws_s3_object" "soda_configuration" {
  bucket = var.s3_bucket_name
  key    = "soda/configuration.yml"
  source = "${path.module}/../../soda/configuration.yml"
  etag   = filemd5("${path.module}/../../soda/configuration.yml")

  tags = {
    Name        = "soda-configuration"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Lambda Function: Run Soda Checks
resource "aws_lambda_function" "run_soda_checks" {
  function_name = "${var.project_name}-run-soda-checks"
  description   = "Run data quality checks using Soda Core + DuckDB"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  s3_bucket = aws_s3_bucket.data_lake.id
  s3_key    = "lambda-deployments/run_soda_checks/function.zip"

  timeout     = 300
  memory_size = 1024

  layers = [aws_lambda_layer_version.soda_core.arn]

  environment {
    variables = {
      DATA_QUALITY_ALERTS_TOPIC_ARN = aws_sns_topic.data_quality_alerts.arn
      LOG_LEVEL                     = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = {
    Name        = "${var.project_name}-run-soda-checks"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "data-quality"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "run_soda_checks_logs" {
  name              = "/aws/lambda/${aws_lambda_function.run_soda_checks.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Outputs
output "soda_core_layer_arn" {
  description = "ARN of Soda Core Lambda layer"
  value       = aws_lambda_layer_version.soda_core.arn
}

output "run_soda_checks_function_arn" {
  description = "ARN of run_soda_checks Lambda function"
  value       = aws_lambda_function.run_soda_checks.arn
}
