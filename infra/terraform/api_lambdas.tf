# ============================================================================
# API Lambda Layer (Shared Libraries)
# ============================================================================

# NOTE: Using AWS-provided AWSSDKPandas layer instead of custom layer
# to avoid 250MB unzipped size limit. The AWS layer includes:
# - pandas, numpy, pyarrow, duckdb, and other data processing libraries
# See: https://aws-sdk-pandas.readthedocs.io/en/stable/layers.html

# Custom DuckDB Lambda Layer
# AWS SDK Pandas layer does NOT include duckdb, so we need a custom layer
resource "aws_lambda_layer_version" "api_duckdb_layer" {
  layer_name          = "${local.name_prefix}-api-duckdb"
  description         = "DuckDB for API Lambdas"
  s3_bucket           = aws_s3_bucket.data_lake.id
  s3_key              = "lambda-deployments/layers/api_duckdb_layer.zip"
  compatible_runtimes = ["python3.11"]

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
      aws_lambda_layer_version.api_duckdb_layer.arn # Custom DuckDB layer
    ]
    environment_variables = {
      S3_BUCKET_NAME        = aws_s3_bucket.data_lake.id
      LOG_LEVEL             = "INFO"
      CONGRESS_GOV_API_KEY  = data.aws_ssm_parameter.congress_api_key.value
    }
  }

  # List of API Lambda functions to create
  api_lambdas = {
    # Member endpoints
    "get_members"                 = { route = "GET /v1/members" }
    "get_member"                  = { route = "GET /v1/members/{bioguide_id}" }
    "get_member_trades"           = { route = "GET /v1/members/{bioguide_id}/trades" }
    "get_member_portfolio"        = { route = "GET /v1/members/{bioguide_id}/portfolio" }
    "get_member_filings"          = { route = "GET /v1/members/{name}/filings" }
    "get_member_transactions"     = { route = "GET /v1/members/{name}/transactions" }
    "get_member_assets"           = { route = "GET /v1/members/{name}/assets" }

    # Trading & Stock endpoints
    "get_trades"         = { route = "GET /v1/trades" }
    "get_stock"          = { route = "GET /v1/stocks/{ticker}" }
    "get_stock_activity" = { route = "GET /v1/stocks/{ticker}/activity" }
    "get_stocks"         = { route = "GET /v1/stocks" }

    # Analytics endpoints
    "get_top_traders"       = { route = "GET /v1/analytics/top-traders" }
    "get_trending_stocks"   = { route = "GET /v1/analytics/trending-stocks" }
    "get_sector_activity"   = { route = "GET /v1/analytics/sector-activity" }
    "get_compliance"        = { route = "GET /v1/analytics/compliance" }
    "get_trading_timeline"  = { route = "GET /v1/analytics/trading-timeline" }
    "get_summary"           = { route = "GET /v1/analytics/summary" }
    "get_network_graph"     = { route = "GET /v1/analytics/network-graph" }
    "get_recent_activity"   = { route = "GET /v1/analytics/activity" }

    # Advanced Analytics (God Mode) endpoints
    "get_congressional_alpha"      = { route = "GET /v1/analytics/alpha" }
    "get_conflict_detection"       = { route = "GET /v1/analytics/conflicts" }
    "get_portfolio_recon"          = { route = "GET /v1/analytics/portfolio" }  # Shortened: 58 chars
    "get_pattern_insights"         = { route = "GET /v1/analytics/insights" }

    # Search & Filing endpoints
    "search"      = { route = "GET /v1/search" }
    "get_filings" = { route = "GET /v1/filings" }
    "get_filing"  = { route = "GET /v1/filings/{doc_id}" }
    "get_filing_transactions" = { route = "GET /v1/filings/{doc_id}/transactions" }
    "get_filing_assets"       = { route = "GET /v1/filings/{doc_id}/assets" }
    "get_filing_positions"    = { route = "GET /v1/filings/{doc_id}/positions" }

    # Congress.gov API endpoints
    "get_congress_bills"    = { route = "GET /v1/congress/bills" }
    "get_congress_bill"     = { route = "GET /v1/congress/bills/{bill_id}" }
    "get_bill_actions"      = { route = "GET /v1/congress/bills/{bill_id}/actions" }
    "get_bill_text"         = { route = "GET /v1/congress/bills/{bill_id}/text" }
    "get_bill_committees"   = { route = "GET /v1/congress/bills/{bill_id}/committees" }
    "get_bill_cosponsors"   = { route = "GET /v1/congress/bills/{bill_id}/cosponsors" }
    "get_bill_subjects"     = { route = "GET /v1/congress/bills/{bill_id}/subjects" }
    "get_bill_summaries"    = { route = "GET /v1/congress/bills/{bill_id}/summaries" }
    "get_bill_titles"       = { route = "GET /v1/congress/bills/{bill_id}/titles" }
    "get_bill_amendments"   = { route = "GET /v1/congress/bills/{bill_id}/amendments" }
    "get_bill_related"      = { route = "GET /v1/congress/bills/{bill_id}/related" }
    "get_congress_members"  = { route = "GET /v1/congress/members" }
    "get_congress_member"   = { route = "GET /v1/congress/members/{bioguide_id}" }

    # Committee endpoints
    "get_congress_committees" = { route = "GET /v1/congress/committees" }
    "get_congress_committee"  = { route = "GET /v1/congress/committees/{chamber}/{code}" }
    "get_committee_bills"     = { route = "GET /v1/congress/committees/{chamber}/{code}/bills" }
    "get_committee_members"   = { route = "GET /v1/congress/committees/{chamber}/{code}/members" }
    "get_committee_reports"   = { route = "GET /v1/congress/committees/{chamber}/{code}/reports" }

    # Cross-domain Analytics endpoints (shortened names for 64 char limit)
    "get_member_leg_trades"   = { route = "GET /v1/analytics/members/{bioguide_id}/legislation-trades" }
    "get_stock_leg_exposure"  = { route = "GET /v1/analytics/stocks/{ticker}/legislative-exposure" }

    # Lobbying Data endpoints (shortened names for 64 char limit)
    "get_lobbying_filings"       = { route = "GET /v1/lobbying/filings" }
    "get_lobbying_client"        = { route = "GET /v1/lobbying/clients/{client_id}" }
    "get_lobbying_network"       = { route = "GET /v1/lobbying/network" }
    "get_bill_lob_activity"      = { route = "GET /v1/congress/bills/{bill_id}/lobbying" }
    "get_member_lob_connects"    = { route = "GET /v1/members/{bioguide_id}/lobbying" }
    "get_triple_correlations"    = { route = "GET /v1/correlations/triple" }

    # System endpoints
    "get_aws_costs"    = { route = "GET /v1/costs" }
    "list_s3_objects"  = { route = "GET /v1/storage/{layer}" }
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

  lifecycle {
    ignore_changes = [source_code_hash]
  }

  depends_on = [


    null_resource.package_lambdas,
    aws_iam_role_policy.lambda_logging
  ]
}

# Lambda permissions for API Gateway to invoke API functions
resource "aws_lambda_permission" "api_gateway" {
  for_each = local.api_lambdas

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.congress_api.execution_arn}/*/*"
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
