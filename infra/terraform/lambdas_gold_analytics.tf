# Lambda Functions for Gold Layer Analytics & Quality
# These functions perform heavy compute/aggregation and data quality checks

# ============================================================================
# DATA QUALITY
# ============================================================================

# Lambda Function: Run Soda Checks
# Validates data quality using Soda Core
resource "aws_lambda_function" "run_soda_checks" {
  function_name = "${var.project_name}-run-soda-checks"
  description   = "Run Soda Core data quality checks"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/quality/run_soda_checks.zip"
  source_code_hash = fileexists("${path.module}/../../build/run_soda_checks.zip") ? filebase64sha256("${path.module}/../../build/run_soda_checks.zip") : null

  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:20"]

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
    }
  }

  tags = {
    Name        = "${var.project_name}-run-soda-checks"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "data-quality"
  }
}

resource "aws_cloudwatch_log_group" "run_soda_checks_logs" {
  name              = "/aws/lambda/${aws_lambda_function.run_soda_checks.function_name}"
  retention_in_days = 30
  tags              = local.standard_tags
}

# ============================================================================
# NETWORK & GRAPH ANALYTICS
# ============================================================================

# Lambda Function: Compute Network Graph
# Builds the trading network graph (Members -> Stocks)
resource "aws_lambda_function" "compute_network_graph" {
  function_name = "${var.project_name}-compute-network-graph"
  description   = "Compute member-stock trading network graph"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/gold-layer/compute_network_graph.zip"
  source_code_hash = fileexists("${path.module}/../../build/compute_network_graph.zip") ? filebase64sha256("${path.module}/../../build/compute_network_graph.zip") : null

  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:20"]

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
    }
  }

  tags = {
    Name        = "${var.project_name}-compute-network-graph"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "analytics"
  }
}

resource "aws_cloudwatch_log_group" "compute_network_graph_logs" {
  name              = "/aws/lambda/${aws_lambda_function.compute_network_graph.function_name}"
  retention_in_days = 30
  tags              = local.standard_tags
}

# Lambda Function: Compute Lobbying Aggregates
# Aggregates lobbying data by firm, client, and issue
resource "aws_lambda_function" "compute_lobbying_aggregates" {
  function_name = "${var.project_name}-compute-lobbying-aggregates"
  description   = "Compute lobbying aggregations"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/gold-layer/compute_lobbying_aggregates.zip"
  source_code_hash = fileexists("${path.module}/../../build/compute_lobbying_aggregates.zip") ? filebase64sha256("${path.module}/../../build/compute_lobbying_aggregates.zip") : null

  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:20"]

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
    }
  }

  tags = {
    Name        = "${var.project_name}-compute-lobbying-aggregates"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "analytics"
  }
}

resource "aws_cloudwatch_log_group" "compute_lobbying_aggregates_logs" {
  name              = "/aws/lambda/${aws_lambda_function.compute_lobbying_aggregates.function_name}"
  retention_in_days = 30
  tags              = local.standard_tags
}
