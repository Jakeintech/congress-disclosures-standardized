# CloudWatch Log Groups for Lambda functions & Pipelines
# Consolidated from cloudwatch.tf and cloudwatch_congress.tf

# -----------------------------------------------------------
# From cloudwatch.tf
# -----------------------------------------------------------
resource "aws_cloudwatch_log_group" "ingest_zip" {
  name              = "/aws/lambda/${local.name_prefix}-ingest-zip"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-ingest-zip-logs"
      Component = "logging"
      Lambda    = "ingest-zip"
    }
  )
}

resource "aws_cloudwatch_log_group" "index_to_silver" {
  name              = "/aws/lambda/${local.name_prefix}-index-to-silver"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-index-to-silver-logs"
      Component = "logging"
      Lambda    = "index-to-silver"
    }
  )
}

resource "aws_cloudwatch_log_group" "extract_document" {
  name              = "/aws/lambda/${local.name_prefix}-extract-document"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-extract-document-logs"
      Component = "logging"
      Lambda    = "extract-document"
    }
  )
}

resource "aws_cloudwatch_log_group" "gold_seed" {
  name              = "/aws/lambda/${local.name_prefix}-gold-seed"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-gold-seed-logs"
      Component = "logging"
      Lambda    = "gold-seed"
    }
  )
}

resource "aws_cloudwatch_log_group" "gold_seed_members" {
  name              = "/aws/lambda/${local.name_prefix}-gold-seed-members"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-gold-seed-members-logs"
      Component = "logging"
      Lambda    = "gold-seed-members"
    }
  )
}

resource "aws_cloudwatch_log_group" "data_quality_validator" {
  name              = "/aws/lambda/${local.name_prefix}-data-quality-validator"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-data-quality-validator-logs"
      Component = "logging"
      Lambda    = "data-quality-validator"
    }
  )
}

# -----------------------------------------------------------
# From cloudwatch_congress.tf
# -----------------------------------------------------------
# Congress Fetch Lambda Logs
resource "aws_cloudwatch_log_group" "congress_fetch_lambda" {
  count = var.enable_congress_pipeline ? 1 : 0

  name              = "/aws/lambda/${local.congress_fetch_lambda_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.congress_tags,
    {
      Name      = "${local.congress_fetch_lambda_name}-logs"
      Component = "logging"
      Pipeline  = "congress-fetch"
    }
  )
}

# Congress Orchestrator Lambda Logs
resource "aws_cloudwatch_log_group" "congress_orchestrator_lambda" {
  count = var.enable_congress_pipeline ? 1 : 0

  name              = "/aws/lambda/${local.congress_orchestrator_lambda_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.congress_tags,
    {
      Name      = "${local.congress_orchestrator_lambda_name}-logs"
      Component = "logging"
      Pipeline  = "congress-orchestration"
    }
  )
}

# Congress Bronze-to-Silver Lambda Logs
resource "aws_cloudwatch_log_group" "congress_silver_lambda" {
  count = var.enable_congress_pipeline ? 1 : 0

  name              = "/aws/lambda/${local.congress_silver_lambda_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.congress_tags,
    {
      Name      = "${local.congress_silver_lambda_name}-logs"
      Component = "logging"
      Pipeline  = "congress-silver"
    }
  )
}

# -----------------------------------------------------------
# Outputs
# -----------------------------------------------------------
output "cloudwatch_log_group_ingest" {
  description = "CloudWatch log group for ingest Lambda"
  value       = aws_cloudwatch_log_group.ingest_zip.name
}

output "cloudwatch_log_group_extract" {
  description = "CloudWatch log group for extract Lambda"
  value       = aws_cloudwatch_log_group.extract_document.name
}

output "congress_fetch_log_group_name" {
  description = "Name of Congress fetch Lambda CloudWatch log group"
  value       = var.enable_congress_pipeline ? aws_cloudwatch_log_group.congress_fetch_lambda[0].name : ""
}

output "congress_orchestrator_log_group_name" {
  description = "Name of Congress orchestrator Lambda CloudWatch log group"
  value       = var.enable_congress_pipeline ? aws_cloudwatch_log_group.congress_orchestrator_lambda[0].name : ""
}

output "congress_silver_log_group_name" {
  description = "Name of Congress Silver Lambda CloudWatch log group"
  value       = var.enable_congress_pipeline ? aws_cloudwatch_log_group.congress_silver_lambda[0].name : ""
}

# -----------------------------------------------------------
# From step_functions.tf (Orchestration Log Groups)
# -----------------------------------------------------------
# CloudWatch Log Group for Pipeline Metrics Lambda
resource "aws_cloudwatch_log_group" "publish_pipeline_metrics" {
  name              = "/aws/lambda/${var.project_name}-publish-pipeline-metrics"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# CloudWatch Log Groups for check lambdas
resource "aws_cloudwatch_log_group" "check_house_fd_updates_logs" {
  name              = "/aws/lambda/${local.name_prefix}-check-house-fd-updates"
  retention_in_days = var.cloudwatch_log_retention_days
  tags              = local.standard_tags
}

resource "aws_cloudwatch_log_group" "check_lobbying_updates_logs" {
  name              = "/aws/lambda/${local.name_prefix}-check-lobbying-updates"
  retention_in_days = var.cloudwatch_log_retention_days
  tags              = local.standard_tags
}

resource "aws_cloudwatch_log_group" "check_congress_updates_logs" {
  name              = "/aws/lambda/${local.name_prefix}-check-congress-updates"
  retention_in_days = var.cloudwatch_log_retention_days
  tags              = local.standard_tags
}
