# Lambda Functions for Gold Transformations using DuckDB

# Upload DuckDB layer to S3 (required for layers > 70MB)
resource "aws_s3_object" "duckdb_layer" {
  bucket = var.s3_bucket_name
  key    = "lambda-layers/congress-duckdb.zip"
  source = "${path.module}/../../layers/duckdb/congress-duckdb.zip"
  etag   = fileexists("${path.module}/../../layers/duckdb/congress-duckdb.zip") ? filemd5("${path.module}/../../layers/duckdb/congress-duckdb.zip") : null

  lifecycle {
    ignore_changes = [etag]
  }

  tags = {
    Name        = "duckdb-lambda-layer"
    Project     = var.project_name
    Environment = var.environment
  }
}

# DuckDB Lambda Layer (uploaded via S3)
resource "aws_lambda_layer_version" "duckdb" {
  layer_name          = "${var.project_name}-duckdb"
  description         = "DuckDB 0.9.2 + PyArrow 14.0.1 for S3-native analytics"
  s3_bucket           = aws_s3_object.duckdb_layer.bucket
  s3_key              = aws_s3_object.duckdb_layer.key
  compatible_runtimes = ["python3.11"]
  compatible_architectures = ["x86_64"]

  depends_on = [aws_s3_object.duckdb_layer]
}

# Lambda Function: Build Fact Transactions
resource "aws_lambda_function" "build_fact_transactions_duckdb" {
  function_name = "${var.project_name}-build-fact-transactions-duckdb"
  description   = "Build fact_ptr_transactions incrementally using DuckDB"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "build_fact_transactions_duckdb.lambda_handler"
  runtime       = "python3.11"
  timeout       = 600  # 10 minutes
  memory_size   = 1024 # 1GB - DuckDB benefits from more memory

  filename         = "${path.module}/../../build/gold_transformations.zip"
  source_code_hash = fileexists("${path.module}/../../build/gold_transformations.zip") ? filebase64sha256("${path.module}/../../build/gold_transformations.zip") : null

  layers = [aws_lambda_layer_version.duckdb.arn]

  environment {
    variables = {
      S3_BUCKET_NAME  = var.s3_bucket_name
      WATERMARK_TABLE = aws_dynamodb_table.pipeline_watermarks.name
      LOG_LEVEL       = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = {
    Name        = "${var.project_name}-build-fact-transactions-duckdb"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-transformation"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

# Lambda Function: Build Dim Members (SCD Type 2)
resource "aws_lambda_function" "build_dim_members_duckdb" {
  function_name = "${var.project_name}-build-dim-members-duckdb"
  description   = "Build dim_member with SCD Type 2 using DuckDB"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "build_dim_members_duckdb.lambda_handler"
  runtime       = "python3.11"
  timeout       = 600
  memory_size   = 1024

  filename         = "${path.module}/../../build/gold_transformations.zip"
  source_code_hash = fileexists("${path.module}/../../build/gold_transformations.zip") ? filebase64sha256("${path.module}/../../build/gold_transformations.zip") : null

  layers = [aws_lambda_layer_version.duckdb.arn]

  environment {
    variables = {
      S3_BUCKET_NAME  = var.s3_bucket_name
      WATERMARK_TABLE = aws_dynamodb_table.pipeline_watermarks.name
      LOG_LEVEL       = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = {
    Name        = "${var.project_name}-build-dim-members-duckdb"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-transformation"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

# Lambda Function: Compute Trending Stocks
resource "aws_lambda_function" "compute_trending_stocks_duckdb" {
  function_name = "${var.project_name}-compute-trending-stocks-duckdb"
  description   = "Compute trending stocks aggregations using DuckDB"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "compute_trending_stocks_duckdb.lambda_handler"
  runtime       = "python3.11"
  timeout       = 600
  memory_size   = 1024

  filename         = "${path.module}/../../build/gold_transformations.zip"
  source_code_hash = fileexists("${path.module}/../../build/gold_transformations.zip") ? filebase64sha256("${path.module}/../../build/gold_transformations.zip") : null

  layers = [aws_lambda_layer_version.duckdb.arn]

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = {
    Name        = "${var.project_name}-compute-trending-stocks-duckdb"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-aggregation"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

# CloudWatch Log Groups for Gold Transformations
resource "aws_cloudwatch_log_group" "build_fact_transactions_logs" {
  name              = "/aws/lambda/${aws_lambda_function.build_fact_transactions_duckdb.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "build_dim_members_logs" {
  name              = "/aws/lambda/${aws_lambda_function.build_dim_members_duckdb.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "compute_trending_stocks_logs" {
  name              = "/aws/lambda/${aws_lambda_function.compute_trending_stocks_duckdb.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Outputs
output "duckdb_layer_arn" {
  description = "ARN of DuckDB Lambda layer"
  value       = aws_lambda_layer_version.duckdb.arn
}

output "build_fact_transactions_function_arn" {
  description = "ARN of build_fact_transactions Lambda function"
  value       = aws_lambda_function.build_fact_transactions_duckdb.arn
}

output "build_dim_members_function_arn" {
  description = "ARN of build_dim_members Lambda function"
  value       = aws_lambda_function.build_dim_members_duckdb.arn
}

output "compute_trending_stocks_function_arn" {
  description = "ARN of compute_trending_stocks Lambda function"
  value       = aws_lambda_function.compute_trending_stocks_duckdb.arn
}
