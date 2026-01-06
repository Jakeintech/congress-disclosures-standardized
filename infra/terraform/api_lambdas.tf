# ============================================================================
# API Lambda Layer (Shared Libraries)
# ============================================================================

# NOTE: Using AWS-provided AWSSDKPandas layer instead of custom layer
# to avoid 250MB unzipped size limit. The AWS layer includes:
# - pandas, numpy, pyarrow, duckdb, and other data processing libraries
# See: https://aws-sdk-pandas.readthedocs.io/en/stable/layers.html

# Custom DuckDB Lambda Layer
# AWS SDK Pandas layer does NOT include duckdb, so we need a custom layer
# Using the latest DuckDB 1.1.3 layer built on 2025-12-25
resource "aws_lambda_layer_version" "api_duckdb_layer" {
  layer_name               = "${local.name_prefix}-api-duckdb"
  description              = "DuckDB 1.1.3 + PyArrow 18.1.0 for S3-native analytics (2025-12-25)"
  s3_bucket                = aws_s3_bucket.data_lake.id
  s3_key                   = "lambda-backend/layers/congress-duckdb-1.1.3.zip"
  compatible_runtimes      = ["python3.11"]
  compatible_architectures = ["x86_64"]

  lifecycle {
    ignore_changes = [source_code_hash]
  }
}

# ============================================================================
# API Lambda Functions
# ============================================================================

# Data source for Congress API key
data "aws_ssm_parameter" "congress_api_key" {
  name            = local.ssm_congress_api_key_param
  with_decryption = true
}

# Common Lambda configuration for API handlers
locals {
  api_lambda_config = {
    runtime     = "python3.11"
    timeout     = 29 # API Gateway max for synchronous invocation
    memory_size = 512
    layers = [
      "arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:24", # AWS Data Wrangler (pandas, numpy, pyarrow)
      "arn:aws:lambda:us-east-1:464813693153:layer:pydantic-2-10-4:1",         # Pydantic v2.10.4
      aws_lambda_layer_version.api_duckdb_layer.arn                            # Custom DuckDB layer
    ]
    environment_variables = {
      S3_BUCKET_NAME       = aws_s3_bucket.data_lake.id
      LOG_LEVEL            = "INFO"
      CONGRESS_GOV_API_KEY = data.aws_ssm_parameter.congress_api_key.value
    }
  }

  # List of API Lambda functions to create
  api_lambdas = {
    # Member endpoints
    "get_members"             = { routes = ["GET /v1/members"] }
    "get_member"              = { routes = ["GET /v1/members/{bioguide_id}"] }
    "get_member_trades"       = { routes = ["GET /v1/members/{bioguide_id}/trades"] }
    "get_member_portfolio"    = { routes = ["GET /v1/members/{bioguide_id}/portfolio"] }
    "get_member_filings"      = { routes = ["GET /v1/members/{name}/filings"] }
    "get_member_transactions" = { routes = ["GET /v1/members/{name}/transactions"] }
    "get_member_assets"       = { routes = ["GET /v1/members/{name}/assets"] }

    # Trading & Stock endpoints
    "get_trades"         = { routes = ["GET /v1/trades"] }
    "get_stock"          = { routes = ["GET /v1/stocks/{ticker}"] }
    "get_stock_activity" = { routes = ["GET /v1/stocks/{ticker}/activity"] }
    "get_stocks"         = { routes = ["GET /v1/stocks"] }

    # Analytics endpoints
    "get_top_traders"      = { routes = ["GET /v1/analytics/top-traders"] }
    "get_trending_stocks"  = { routes = ["GET /v1/analytics/trending-stocks"] }
    "get_sector_activity"  = { routes = ["GET /v1/analytics/sector-activity"] }
    "get_compliance"       = { routes = ["GET /v1/analytics/compliance"] }
    "get_trading_timeline" = { routes = ["GET /v1/analytics/trading-timeline"] }
    "get_summary"          = { routes = ["GET /v1/analytics/summary"] }
    "get_network_graph"    = { routes = ["GET /v1/analytics/network-graph"] }
    "get_recent_activity"  = { routes = ["GET /v1/analytics/activity"] }

    # Advanced Analytics (God Mode) endpoints
    "get_congressional_alpha" = { routes = ["GET /v1/analytics/alpha"] }
    "get_conflict_detection"  = { routes = ["GET /v1/analytics/conflicts"] }
    "get_portfolio_recon"     = { routes = ["GET /v1/analytics/portfolio"] }
    "get_pattern_insights"    = { routes = ["GET /v1/analytics/insights"] }

    # Search & Filing endpoints
    "search"                  = { routes = ["GET /v1/search"] }
    "get_filings"             = { routes = ["GET /v1/filings"] }
    "get_filing"              = { routes = ["GET /v1/filings/{doc_id}"] }
    "get_filing_transactions" = { routes = ["GET /v1/filings/{doc_id}/transactions"] }
    "get_filing_assets"       = { routes = ["GET /v1/filings/{doc_id}/assets"] }
    "get_filing_positions"    = { routes = ["GET /v1/filings/{doc_id}/positions"] }

    # Congress.gov API endpoints (with aliases)
    "get_congress_bills" = { routes = ["GET /v1/congress/bills"] }
    "get_congress_bill" = { routes = [
      "GET /v1/congress/bills/{bill_id}",
      "GET /v1/congress/bills/{congress}/{type}/{number}"
    ] }
    "get_bill_actions" = { routes = [
      "GET /v1/congress/bills/{bill_id}/actions",
      "GET /v1/congress/bills/{congress}/{type}/{number}/actions"
    ] }
    "get_bill_text" = { routes = [
      "GET /v1/congress/bills/{bill_id}/text",
      "GET /v1/congress/bills/{congress}/{type}/{number}/text"
    ] }
    "get_bill_committees" = { routes = [
      "GET /v1/congress/bills/{bill_id}/committees",
      "GET /v1/congress/bills/{congress}/{type}/{number}/committees"
    ] }
    "get_bill_cosponsors" = { routes = [
      "GET /v1/congress/bills/{bill_id}/cosponsors",
      "GET /v1/congress/bills/{congress}/{type}/{number}/cosponsors"
    ] }
    "get_bill_subjects" = { routes = [
      "GET /v1/congress/bills/{bill_id}/subjects",
      "GET /v1/congress/bills/{congress}/{type}/{number}/subjects"
    ] }
    "get_bill_summaries" = { routes = [
      "GET /v1/congress/bills/{bill_id}/summaries",
      "GET /v1/congress/bills/{congress}/{type}/{number}/summaries"
    ] }
    "get_bill_titles" = { routes = [
      "GET /v1/congress/bills/{bill_id}/titles",
      "GET /v1/congress/bills/{congress}/{type}/{number}/titles"
    ] }
    "get_bill_amendments" = { routes = [
      "GET /v1/congress/bills/{bill_id}/amendments",
      "GET /v1/congress/bills/{congress}/{type}/{number}/amendments"
    ] }
    "get_bill_related" = { routes = [
      "GET /v1/congress/bills/{bill_id}/related",
      "GET /v1/congress/bills/{congress}/{type}/{number}/related"
    ] }
    "get_congress_members" = { routes = ["GET /v1/congress/members"] }
    "get_congress_member"  = { routes = ["GET /v1/congress/members/{bioguide_id}"] }

    # Committee endpoints
    "get_congress_committees" = { routes = ["GET /v1/congress/committees"] }
    "get_congress_committee"  = { routes = ["GET /v1/congress/committees/{chamber}/{code}"] }
    "get_committee_bills"     = { routes = ["GET /v1/congress/committees/{chamber}/{code}/bills"] }
    "get_committee_members"   = { routes = ["GET /v1/congress/committees/{chamber}/{code}/members"] }
    "get_committee_reports"   = { routes = ["GET /v1/congress/committees/{chamber}/{code}/reports"] }

    # Cross-domain Analytics endpoints
    "get_member_leg_trades"  = { routes = ["GET /v1/analytics/members/{bioguide_id}/legislation-trades"] }
    "get_stock_leg_exposure" = { routes = ["GET /v1/analytics/stocks/{ticker}/legislative-exposure"] }

    # Lobbying Data endpoints (with aliases)
    "get_lobbying_filings" = { routes = ["GET /v1/lobbying/filings"] }
    "get_lobbying_client"  = { routes = ["GET /v1/lobbying/clients/{client_id}"] }
    "get_lobbying_network" = { routes = [
      "GET /v1/lobbying/network",
      "GET /v1/lobbying/network-graph"
    ] }
    "get_bill_lob_activity" = { routes = [
      "GET /v1/congress/bills/{bill_id}/lobbying",
      "GET /v1/congress/bills/{congress}/{type}/{number}/lobbying"
    ] }
    "get_member_lob_connects" = { routes = ["GET /v1/members/{bioguide_id}/lobbying"] }
    "get_triple_correlations" = { routes = ["GET /v1/correlations/triple"] }

    # System endpoints
    "get_aws_costs"   = { routes = ["GET /v1/costs"] }
    "list_s3_objects" = { routes = ["GET /v1/storage/{layer}"] }
    "get_version"     = { routes = ["GET /v1/version"] }
    "get_health"      = { routes = ["GET /v1/health"] }
  }
}

# Create all API Lambda functions
resource "aws_lambda_function" "api" {
  for_each = local.api_lambdas

  function_name = "${local.name_prefix}-api-${each.key}"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.handler"
  runtime       = local.api_lambda_config.runtime

  s3_bucket = aws_s3_bucket.data_lake.id
  s3_key    = "lambda-deployments/api/${each.key}.zip"

  # Ensure Lambda is updated when the local zip file changes
  source_code_hash = filebase64sha256("${path.module}/../../build/api/${each.key}.zip")

  timeout     = local.api_lambda_config.timeout
  memory_size = local.api_lambda_config.memory_size

  environment {
    variables = local.api_lambda_config.environment_variables
  }

  layers = local.api_lambda_config.layers

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }


  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-api-${each.key}"
      Component = "lambda"
      Purpose   = "api"
    }
  )

  depends_on = [


    null_resource.package_lambdas,
    aws_iam_role_policy.lambda_logging
  ]
}



# Outputs
output "api_lambda_functions" {
  description = "Map of API Lambda function names"
  value = {
    for k, v in aws_lambda_function.api : k => v.function_name
  }
}

output "api_lambda_arns" {
  description = "Map of API Lambda function ARNs"
  value = {
    for k, v in aws_lambda_function.api : k => v.arn
  }
}

# output "api_lambda_layer_arn" {
#   description = "ARN of API shared libraries layer"
#   value       = aws_lambda_layer_version.api_shared_libs.arn
# }
