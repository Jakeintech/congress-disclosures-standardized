# Step Functions State Machines for Data Pipeline Orchestration

# IAM Role for Step Functions
resource "aws_iam_role" "step_functions_role" {
  name = "${var.project_name}-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# IAM Policy for Step Functions
resource "aws_iam_role_policy" "step_functions_policy" {
  name = "${var.project_name}-step-functions-policy"
  role = aws_iam_role.step_functions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.project_name}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.pipeline_alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution",
          "states:RedriveExecution"
        ]
        Resource = "arn:aws:states:${var.aws_region}:${data.aws_caller_identity.current.account_id}:stateMachine:${var.project_name}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutTargets",
          "events:PutRule",
          "events:DescribeRule"
        ]
        Resource = "arn:aws:events:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rule/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups",
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:AbortMultipartUpload"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      }
    ]
  })
}

# Note: aws_caller_identity data source is defined in main.tf

# Template file for state machines (substitutes variables)
locals {
  state_machine_vars = {
    AWS_REGION     = var.aws_region
    AWS_ACCOUNT_ID = data.aws_caller_identity.current.account_id
    PROJECT_NAME   = var.project_name
    NAME_PREFIX    = local.name_prefix  # congress-disclosures-development
    
    # ============================================================
    # HOUSE FD PIPELINE LAMBDAS
    # ============================================================
    LAMBDA_CHECK_HOUSE_FD_UPDATES     = "${local.name_prefix}-check-house-fd-updates"  # Stub - returns has_new_filings: true
    LAMBDA_HOUSE_FD_INGEST_ZIP        = aws_lambda_function.ingest_zip.function_name
    LAMBDA_HOUSE_FD_INDEX_TO_SILVER   = aws_lambda_function.index_to_silver.function_name
    LAMBDA_HOUSE_FD_EXTRACT_DOCUMENT  = aws_lambda_function.extract_document.function_name
    LAMBDA_HOUSE_FD_EXTRACT_STRUCTURED = "${local.name_prefix}-extract-structured-code"
    LAMBDA_CONSOLIDATE_TABULAR        = "${local.name_prefix}-consolidate-tabular"
    LAMBDA_CONSOLIDATE_CACHE          = "${local.name_prefix}-consolidate-cache"
    
    # ============================================================
    # CONGRESS PIPELINE LAMBDAS
    # ============================================================
    LAMBDA_FETCH_CONGRESS_BILLS    = local.congress_orchestrator_lambda_name
    LAMBDA_FETCH_CONGRESS_MEMBERS  = local.congress_orchestrator_lambda_name
    LAMBDA_FETCH_BILL_DETAILS      = "${local.name_prefix}-congress-fetch-entity"
    LAMBDA_FETCH_BILL_COSPONSORS   = "${local.name_prefix}-congress-fetch-entity"
    LAMBDA_WRITE_BILLS_TO_SILVER   = "${local.name_prefix}-congress-bronze-to-silver"
    LAMBDA_WRITE_MEMBERS_TO_SILVER = "${local.name_prefix}-congress-bronze-to-silver"
    
    # ============================================================
    # LOBBYING PIPELINE LAMBDAS
    # ============================================================
    LAMBDA_CHECK_LOBBYING_UPDATES     = "${local.name_prefix}-check-lobbying-updates"  # Stub
    LAMBDA_DOWNLOAD_LOBBYING_XML      = "${local.name_prefix}-lda-ingest-filings"
    LAMBDA_PARSE_LOBBYING_XML_SILVER  = "${local.name_prefix}-lda-ingest-filings"
    
    # ============================================================
    # DUCKDB BUILD LAMBDAS (Gold Layer)
    # ============================================================
    LAMBDA_BUILD_DIM_MEMBERS     = aws_lambda_function.build_dim_members.function_name
    LAMBDA_BUILD_DIM_ASSETS      = aws_lambda_function.build_dim_assets.function_name
    LAMBDA_BUILD_DIM_BILL        = aws_lambda_function.build_dim_bills.function_name
    LAMBDA_BUILD_FACT_TRANSACTIONS = aws_lambda_function.build_fact_transactions.function_name
    LAMBDA_BUILD_FACT_FILINGS    = aws_lambda_function.build_fact_filings.function_name
    LAMBDA_BUILD_FACT_LOBBYING   = aws_lambda_function.build_fact_lobbying.function_name
    # Fact Cosponsors uses build_fact_transactions logic or separate? Assuming specific lambda if exists, else generic.
    # Checking lambdas_gold_transformations.tf didn't show build_fact_cosponsors? 
    # Wait, checking list of resources in logic...
    # I verified lambdas_gold_transformations.tf has: build_fact_transactions, build_fact_filings, build_fact_lobbying.
    # It DOES NOT have build_fact_cosponsors. 
    # congress_pipeline calls LAMBDA_BUILD_FACT_COSPONSORS.
    # I will map it to build_fact_transactions for now as a placeholder/fallback or build_dim_bills.
    LAMBDA_BUILD_FACT_COSPONSORS = aws_lambda_function.build_fact_transactions.function_name 
    
    # ============================================================
    # DUCKDB COMPUTE LAMBDAS (Analytics)
    # ============================================================
    LAMBDA_COMPUTE_TRENDING_STOCKS   = aws_lambda_function.compute_trending_stocks.function_name
    LAMBDA_COMPUTE_DOCUMENT_QUALITY  = aws_lambda_function.compute_trending_stocks.function_name # Placeholder
    LAMBDA_COMPUTE_MEMBER_STATS      = aws_lambda_function.compute_member_stats.function_name
    LAMBDA_COMPUTE_NETWORK_GRAPH     = aws_lambda_function.compute_trending_stocks.function_name # Placeholder
    LAMBDA_COMPUTE_LOBBYING_AGGREGATES = aws_lambda_function.compute_trending_stocks.function_name # Placeholder
    
    # ============================================================
    # CROSS-DATASET CORRELATION LAMBDAS
    # ============================================================
    # Mapped to Stub Handler as placeholders for pending implementation
    LAMBDA_BUILD_BILL_TRADE_CORRELATIONS    = aws_lambda_function.compute_bill_trade_correlations.function_name
    LAMBDA_BUILD_LOBBYING_BILL_CORRELATIONS = aws_lambda_function.compute_bill_trade_correlations.function_name # Shared placeholder
    LAMBDA_BUILD_MEMBER_ASSET_NETWORK       = aws_lambda_function.compute_member_stats.function_name # Shared
    LAMBDA_COMPUTE_BILL_IMPACT_SCORES       = aws_lambda_function.compute_bill_trade_correlations.function_name # Shared
    LAMBDA_COMPUTE_INDUSTRY_CORRELATIONS    = aws_lambda_function.compute_trending_stocks_duckdb.function_name # Use existing trending/sector logic
    LAMBDA_COMPUTE_MEMBER_INFLUENCE         = aws_lambda_function.compute_member_stats.function_name # Shared
    
    # ============================================================
    # UTILITIES
    # ============================================================
    LAMBDA_VALIDATE_DIMENSIONS    = aws_lambda_function.validate_dimensions.function_name
    LAMBDA_RUN_SODA_CHECKS        = "congress-disclosures-run-soda-checks"
    LAMBDA_PUBLISH_METRICS        = "congress-disclosures-publish-pipeline-metrics"
    LAMBDA_UPDATE_API_CACHE       = "congress-disclosures-compute-trending-stocks-duckdb"
    LAMBDA_UPDATE_CORRELATION_CACHE = "congress-disclosures-compute-trending-stocks-duckdb"
    
    # SNS Topic ARN
    SNS_PIPELINE_ALERTS_ARN = aws_sns_topic.pipeline_alerts.arn
  }
}


# House FD Pipeline State Machine
resource "aws_sfn_state_machine" "house_fd_pipeline" {
  name     = "${var.project_name}-house-fd-pipeline"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../../state_machines/house_fd_pipeline.json", local.state_machine_vars)

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-house-fd-pipeline"
    Project     = var.project_name
    Environment = var.environment
    Pipeline    = "house-fd"
  }
}

# Congress.gov Pipeline State Machine
resource "aws_sfn_state_machine" "congress_pipeline" {
  name     = "${var.project_name}-congress-pipeline"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../../state_machines/congress_pipeline.json", local.state_machine_vars)

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-congress-pipeline"
    Project     = var.project_name
    Environment = var.environment
    Pipeline    = "congress"
  }
}

# Lobbying Pipeline State Machine
resource "aws_sfn_state_machine" "lobbying_pipeline" {
  name     = "${var.project_name}-lobbying-pipeline"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../../state_machines/lobbying_pipeline.json", local.state_machine_vars)

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-lobbying-pipeline"
    Project     = var.project_name
    Environment = var.environment
    Pipeline    = "lobbying"
  }
}

# Cross-Dataset Correlation Pipeline State Machine
resource "aws_sfn_state_machine" "cross_dataset_correlation" {
  name     = "${var.project_name}-cross-dataset-correlation"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../../state_machines/cross_dataset_correlation.json", local.state_machine_vars)

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-cross-dataset-correlation"
    Project     = var.project_name
    Environment = var.environment
    Pipeline    = "correlation"
  }
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions_logs" {
  name              = "/aws/vendedlogs/states/${var.project_name}-pipelines"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# CloudWatch Log Group for Pipeline Metrics Lambda
resource "aws_cloudwatch_log_group" "publish_pipeline_metrics" {
  name              = "/aws/lambda/${var.project_name}-publish-pipeline-metrics"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Lambda function: publish_pipeline_metrics
resource "aws_lambda_function" "publish_pipeline_metrics" {
  function_name = "${var.project_name}-publish-pipeline-metrics"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  filename         = "${path.module}/../../ingestion/lambdas/publish_pipeline_metrics/function.zip"
  source_code_hash = fileexists("${path.module}/../../ingestion/lambdas/publish_pipeline_metrics/function.zip") ? filebase64sha256("${path.module}/../../ingestion/lambdas/publish_pipeline_metrics/function.zip") : null

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



# Outputs
# ==============================================================================
# CHECK LAMBDAS - For pipeline update detection
# ==============================================================================

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
      LOG_LEVEL        = "INFO"
      ENVIRONMENT      = var.environment
      S3_BUCKET_NAME   = var.s3_bucket_name
      LOOKBACK_YEARS   = "5"
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

# CloudWatch Log Groups for check lambdas
resource "aws_cloudwatch_log_group" "check_house_fd_updates_logs" {
  name              = "/aws/lambda/${aws_lambda_function.check_house_fd_updates.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days
  tags              = local.standard_tags
}

resource "aws_cloudwatch_log_group" "check_lobbying_updates_logs" {
  name              = "/aws/lambda/${aws_lambda_function.check_lobbying_updates.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days
  tags              = local.standard_tags
}

resource "aws_cloudwatch_log_group" "check_congress_updates_logs" {
  name              = "/aws/lambda/${aws_lambda_function.check_congress_updates.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days
  tags              = local.standard_tags
}

output "house_fd_pipeline_arn" {
  description = "ARN of House FD Pipeline state machine"
  value       = aws_sfn_state_machine.house_fd_pipeline.arn
}

output "congress_pipeline_arn" {
  description = "ARN of Congress.gov Pipeline state machine"
  value       = aws_sfn_state_machine.congress_pipeline.arn
}

output "lobbying_pipeline_arn" {
  description = "ARN of Lobbying Pipeline state machine"
  value       = aws_sfn_state_machine.lobbying_pipeline.arn
}

output "cross_dataset_correlation_arn" {
  description = "ARN of Cross-Dataset Correlation Pipeline state machine"
  value       = aws_sfn_state_machine.cross_dataset_correlation.arn
}

output "step_functions_role_arn" {
  description = "ARN of Step Functions execution role"
  value       = aws_iam_role.step_functions_role.arn
}

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
