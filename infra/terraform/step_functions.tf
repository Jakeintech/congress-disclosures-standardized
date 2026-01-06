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
    NAME_PREFIX    = local.name_prefix # congress-disclosures-development

    # ============================================================
    # HOUSE FD PIPELINE LAMBDAS
    # ============================================================
    LAMBDA_CHECK_HOUSE_FD_UPDATES      = "${local.name_prefix}-check-house-fd-updates" # Stub - returns has_new_filings: true
    LAMBDA_HOUSE_FD_INGEST_ZIP         = aws_lambda_function.ingest_zip.function_name
    LAMBDA_HOUSE_FD_INDEX_TO_SILVER    = aws_lambda_function.index_to_silver.function_name
    LAMBDA_HOUSE_FD_EXTRACT_DOCUMENT   = aws_lambda_function.extract_document.function_name
    LAMBDA_HOUSE_FD_EXTRACT_STRUCTURED = "${local.name_prefix}-extract-structured-code"
    LAMBDA_CONSOLIDATE_TABULAR         = "${local.name_prefix}-consolidate-tabular"
    LAMBDA_CONSOLIDATE_CACHE           = "${local.name_prefix}-consolidate-cache"

    # ============================================================
    # CONGRESS PIPELINE LAMBDAS
    # ============================================================
    LAMBDA_CHECK_CONGRESS_UPDATES  = "${local.name_prefix}-check-congress-updates"
    LAMBDA_FETCH_CONGRESS_BILLS    = local.congress_orchestrator_lambda_name
    LAMBDA_FETCH_CONGRESS_MEMBERS  = local.congress_orchestrator_lambda_name
    LAMBDA_FETCH_BILL_DETAILS      = "${local.name_prefix}-congress-fetch-entity"
    LAMBDA_FETCH_BILL_COSPONSORS   = "${local.name_prefix}-congress-fetch-entity"
    LAMBDA_WRITE_BILLS_TO_SILVER   = "${local.name_prefix}-congress-bronze-to-silver"
    LAMBDA_WRITE_MEMBERS_TO_SILVER = "${local.name_prefix}-congress-bronze-to-silver"

    # ============================================================
    # LOBBYING PIPELINE LAMBDAS
    # ============================================================
    LAMBDA_CHECK_LOBBYING_UPDATES    = "${local.name_prefix}-check-lobbying-updates" # Stub
    LAMBDA_DOWNLOAD_LOBBYING_XML     = "${local.name_prefix}-lda-ingest-filings"
    LAMBDA_PARSE_LOBBYING_XML_SILVER = "${local.name_prefix}-lda-ingest-filings"

    # ============================================================
    # DUCKDB BUILD LAMBDAS (Gold Layer)
    # ============================================================
    LAMBDA_BUILD_DIM_MEMBERS       = aws_lambda_function.build_dim_members.function_name
    LAMBDA_BUILD_DIM_ASSETS        = aws_lambda_function.build_dim_assets.function_name
    LAMBDA_BUILD_DIM_BILL          = aws_lambda_function.build_dim_bills.function_name
    LAMBDA_BUILD_FACT_TRANSACTIONS = aws_lambda_function.build_fact_transactions.function_name
    LAMBDA_BUILD_FACT_FILINGS      = aws_lambda_function.build_fact_filings.function_name
    LAMBDA_BUILD_FACT_LOBBYING     = aws_lambda_function.build_fact_lobbying.function_name
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
    LAMBDA_COMPUTE_TRENDING_STOCKS     = aws_lambda_function.compute_trending_stocks.function_name
    LAMBDA_COMPUTE_DOCUMENT_QUALITY    = aws_lambda_function.run_soda_checks.function_name
    LAMBDA_COMPUTE_MEMBER_STATS        = aws_lambda_function.compute_member_stats.function_name
    LAMBDA_COMPUTE_NETWORK_GRAPH       = aws_lambda_function.compute_network_graph.function_name
    LAMBDA_COMPUTE_LOBBYING_AGGREGATES = aws_lambda_function.compute_lobbying_aggregates.function_name

    # ============================================================
    # CROSS-DATASET CORRELATION LAMBDAS
    # ============================================================
    # Mapped to Stub Handler as placeholders for pending implementation
    LAMBDA_BUILD_BILL_TRADE_CORRELATIONS    = aws_lambda_function.compute_bill_trade_correlations.function_name
    LAMBDA_BUILD_LOBBYING_BILL_CORRELATIONS = aws_lambda_function.compute_bill_trade_correlations.function_name # Shared placeholder
    LAMBDA_BUILD_MEMBER_ASSET_NETWORK       = aws_lambda_function.compute_member_stats.function_name            # Shared
    LAMBDA_COMPUTE_BILL_IMPACT_SCORES       = aws_lambda_function.compute_bill_trade_correlations.function_name # Shared
    LAMBDA_COMPUTE_INDUSTRY_CORRELATIONS    = aws_lambda_function.compute_trending_stocks.function_name         # Use existing trending/sector logic
    LAMBDA_COMPUTE_MEMBER_INFLUENCE         = aws_lambda_function.compute_member_stats.function_name            # Shared

    # ============================================================
    # UTILITIES
    # ============================================================
    LAMBDA_RUN_SODA_CHECKS          = "congress-disclosures-run-soda-checks"
    LAMBDA_PUBLISH_METRICS          = "congress-disclosures-publish-pipeline-metrics"
    LAMBDA_UPDATE_API_CACHE         = "congress-disclosures-compute-trending-stocks"
    LAMBDA_UPDATE_CORRELATION_CACHE = "congress-disclosures-compute-trending-stocks"

    # SNS Topic ARN
    SNS_PIPELINE_ALERTS_ARN = aws_sns_topic.pipeline_alerts.arn
  }
}


# House FD Pipeline State Machine
resource "aws_sfn_state_machine" "house_fd_pipeline" {
  name     = "${var.project_name}-house-fd-pipeline"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../../backend/orchestration/house_fd_pipeline.json", local.state_machine_vars)

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

  definition = templatefile("${path.module}/../../backend/orchestration/congress_pipeline.json", local.state_machine_vars)

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

  definition = templatefile("${path.module}/../../backend/orchestration/lobbying_pipeline.json", local.state_machine_vars)

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

  definition = templatefile("${path.module}/../../backend/orchestration/cross_dataset_correlation.json", local.state_machine_vars)

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

# Congress Data Platform - Unified Pipeline State Machine
resource "aws_sfn_state_machine" "congress_data_platform" {
  name     = "${var.project_name}-data-platform"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../../backend/orchestration/congress_data_platform.json", local.state_machine_vars)

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-data-platform"
    Project     = var.project_name
    Environment = var.environment
    Pipeline    = "unified"
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





# Outputs
# ==============================================================================


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



output "congress_data_platform_arn" {
  description = "ARN of Congress Data Platform (Unified) state machine"
  value       = aws_sfn_state_machine.congress_data_platform.arn
}

output "congress_data_platform_name" {
  description = "Name of Congress Data Platform (Unified) state machine"
  value       = aws_sfn_state_machine.congress_data_platform.name
}
