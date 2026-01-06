# Lambda Functions for Gold Layer Transformations (Sprint 2)
#
# This file defines Lambda wrappers for dimension builders, fact builders,
# and aggregate computations. These Lambdas are orchestrated by Step Functions.

# ============================================================================
# DIMENSION BUILDERS
# ============================================================================

# Lambda Function: Build dim_members
resource "aws_lambda_function" "build_dim_members" {
  function_name = "${var.project_name}-build-dim-members"
  description   = "Build dim_members dimension table (SCD Type 2)"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300 # 5 minutes
  memory_size   = 512

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/gold-layer/build_dim_members.zip"
  source_code_hash = fileexists("${path.module}/../../build/build_dim_members.zip") ? filebase64sha256("${path.module}/../../build/build_dim_members.zip") : null

  # Use AWS SDK for pandas layer (includes pandas, numpy, pyarrow)
  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:20"]

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
    Name        = "${var.project_name}-build-dim-members"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-dimension"
    Sprint      = "sprint-2"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "build_dim_members_v2_logs" {
  name              = "/aws/lambda/${aws_lambda_function.build_dim_members.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Lambda Function: Build dim_assets
resource "aws_lambda_function" "build_dim_assets" {
  function_name = "${var.project_name}-build-dim-assets"
  description   = "Build dim_assets dimension table"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/gold-layer/build_dim_assets.zip"
  source_code_hash = fileexists("${path.module}/../../build/build_dim_assets.zip") ? filebase64sha256("${path.module}/../../build/build_dim_assets.zip") : null

  # Use AWS SDK for pandas layer (includes pandas, numpy, pyarrow)
  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:20"]

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
    Name        = "${var.project_name}-build-dim-assets"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-dimension"
    Sprint      = "sprint-2"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "build_dim_assets_logs" {
  name              = "/aws/lambda/${aws_lambda_function.build_dim_assets.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Lambda Function: Build dim_bills
resource "aws_lambda_function" "build_dim_bills" {
  function_name = "${var.project_name}-build-dim-bills"
  description   = "Build dim_bills dimension table from Congress.gov data"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/gold-layer/build_dim_bills.zip"
  source_code_hash = fileexists("${path.module}/../../build/build_dim_bills.zip") ? filebase64sha256("${path.module}/../../build/build_dim_bills.zip") : null

  # Use AWS SDK for pandas layer (includes pandas, numpy, pyarrow)
  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:20"]

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
    Name        = "${var.project_name}-build-dim-bills"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-dimension"
    Sprint      = "sprint-2"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "build_dim_bills_logs" {
  name              = "/aws/lambda/${aws_lambda_function.build_dim_bills.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# ============================================================================
# FACT BUILDERS
# ============================================================================

# Lambda Function: Build fact_transactions
resource "aws_lambda_function" "build_fact_transactions" {
  function_name = "${var.project_name}-build-fact-transactions"
  description   = "Build fact_ptr_transactions from Type P extractions"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 600 # 10 minutes - transactions are large
  memory_size   = 1024

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/gold-layer/build_fact_transactions.zip"
  source_code_hash = fileexists("${path.module}/../../build/build_fact_transactions.zip") ? filebase64sha256("${path.module}/../../build/build_fact_transactions.zip") : null

  # Use AWS SDK for pandas layer (includes pandas, numpy, pyarrow)
  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:20"]

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
    Name        = "${var.project_name}-build-fact-transactions"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-fact"
    Sprint      = "sprint-2"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "build_fact_transactions_v2_logs" {
  name              = "/aws/lambda/${aws_lambda_function.build_fact_transactions.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Lambda Function: Build fact_filings
resource "aws_lambda_function" "build_fact_filings" {
  function_name = "${var.project_name}-build-fact-filings"
  description   = "Build fact_filings from Silver layer filings metadata"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/gold-layer/build_fact_filings.zip"
  source_code_hash = fileexists("${path.module}/../../build/build_fact_filings.zip") ? filebase64sha256("${path.module}/../../build/build_fact_filings.zip") : null

  # Use AWS SDK for pandas layer (includes pandas, numpy, pyarrow)
  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:20"]

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
    Name        = "${var.project_name}-build-fact-filings"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-fact"
    Sprint      = "sprint-2"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "build_fact_filings_logs" {
  name              = "/aws/lambda/${aws_lambda_function.build_fact_filings.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Lambda Function: Build fact_lobbying
resource "aws_lambda_function" "build_fact_lobbying" {
  function_name = "${var.project_name}-build-fact-lobbying"
  description   = "Build fact_lobbying from LDA disclosure data"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 600
  memory_size   = 1024

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/gold-layer/build_fact_lobbying.zip"
  source_code_hash = fileexists("${path.module}/../../build/build_fact_lobbying.zip") ? filebase64sha256("${path.module}/../../build/build_fact_lobbying.zip") : null

  # Use AWS SDK for pandas layer (includes pandas, numpy, pyarrow)
  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:20"]

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
    Name        = "${var.project_name}-build-fact-lobbying"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-fact"
    Sprint      = "sprint-2"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "build_fact_lobbying_logs" {
  name              = "/aws/lambda/${aws_lambda_function.build_fact_lobbying.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# ============================================================================
# AGGREGATION COMPUTATIONS
# ============================================================================

# Lambda Function: Compute trending_stocks
resource "aws_lambda_function" "compute_trending_stocks" {
  function_name = "${var.project_name}-compute-trending-stocks"
  description   = "Compute trending stocks aggregations (7d, 30d, 90d windows)"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/gold-layer/compute_trending_stocks.zip"
  source_code_hash = fileexists("${path.module}/../../build/compute_trending_stocks.zip") ? filebase64sha256("${path.module}/../../build/compute_trending_stocks.zip") : null

  # Use AWS SDK for pandas layer (includes pandas, numpy, pyarrow)
  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:20"]

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
    Name        = "${var.project_name}-compute-trending-stocks"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-aggregation"
    Sprint      = "sprint-2"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "compute_trending_stocks_v2_logs" {
  name              = "/aws/lambda/${aws_lambda_function.compute_trending_stocks.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Lambda Function: Compute member_stats
resource "aws_lambda_function" "compute_member_stats" {
  function_name = "${var.project_name}-compute-member-stats"
  description   = "Compute member trading statistics and compliance metrics"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/gold-layer/compute_member_stats.zip"
  source_code_hash = fileexists("${path.module}/../../build/compute_member_stats.zip") ? filebase64sha256("${path.module}/../../build/compute_member_stats.zip") : null

  # Use AWS SDK for pandas layer (includes pandas, numpy, pyarrow)
  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:20"]

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
    Name        = "${var.project_name}-compute-member-stats"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-aggregation"
    Sprint      = "sprint-2"
  }

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

resource "aws_cloudwatch_log_group" "compute_member_stats_logs" {
  name              = "/aws/lambda/${aws_lambda_function.compute_member_stats.function_name}"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "lambda_build_dim_members_arn" {
  description = "ARN of build_dim_members Lambda function"
  value       = aws_lambda_function.build_dim_members.arn
}

output "lambda_build_dim_assets_arn" {
  description = "ARN of build_dim_assets Lambda function"
  value       = aws_lambda_function.build_dim_assets.arn
}

output "lambda_build_dim_bills_arn" {
  description = "ARN of build_dim_bills Lambda function"
  value       = aws_lambda_function.build_dim_bills.arn
}

output "lambda_build_fact_transactions_arn" {
  description = "ARN of build_fact_transactions Lambda function"
  value       = aws_lambda_function.build_fact_transactions.arn
}

output "lambda_build_fact_filings_arn" {
  description = "ARN of build_fact_filings Lambda function"
  value       = aws_lambda_function.build_fact_filings.arn
}

output "lambda_build_fact_lobbying_arn" {
  description = "ARN of build_fact_lobbying Lambda function"
  value       = aws_lambda_function.build_fact_lobbying.arn
}

output "lambda_compute_trending_stocks_arn" {
  description = "ARN of compute_trending_stocks Lambda function"
  value       = aws_lambda_function.compute_trending_stocks.arn
}

output "lambda_compute_member_stats_arn" {
  description = "ARN of compute_member_stats Lambda function"
  value       = aws_lambda_function.compute_member_stats.arn
}

# Lambda Function: Compute Bill-Trade Correlations
# Added to fix missing reference in step_functions.tf
resource "aws_lambda_function" "compute_bill_trade_correlations" {
  function_name = "${var.project_name}-compute-bill-trade-correlations"
  description   = "Compute correlations between legislative activity and trading behavior"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 1024

  s3_bucket        = var.s3_bucket_name
  s3_key           = "lambda-deployments/gold-layer/compute_bill_trade_correlations.zip"
  # Use a dummy hash if the file doesn't exist yet to allow terraform plan
  source_code_hash = fileexists("${path.module}/../../build/compute_bill_trade_correlations.zip") ? filebase64sha256("${path.module}/../../build/compute_bill_trade_correlations.zip") : null

  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:20"]

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
    }
  }

  tags = {
    Name        = "${var.project_name}-compute-bill-trade-correlations"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "gold-analytics"
  }
}

resource "aws_cloudwatch_log_group" "compute_bill_trade_correlations_logs" {
  name              = "/aws/lambda/${aws_lambda_function.compute_bill_trade_correlations.function_name}"
  retention_in_days = 30
  tags              = local.standard_tags
}
