# API Gateway HTTP API for Congressional Trading Data API
# Provides public access to Gold layer data via Lambda integrations

# ============================================================================
# API Gateway HTTP API
# ============================================================================

resource "aws_apigatewayv2_api" "congress_api" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"
  description   = "Congressional Trading Data API - Public access to Gold layer analytics"

  cors_configuration {
    allow_origins = ["*", "http://congress-disclosures-standardized.s3-website-us-east-1.amazonaws.com", "https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"]
    max_age       = 300
  }

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-api"
      Component = "api-gateway"
    }
  )
}

# ============================================================================
# API Gateway Stage (Production)
# ============================================================================

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.congress_api.id
  name        = "$default"
  auto_deploy = true
  description = "Default production stage"

  # CloudWatch logging
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
    })
  }

  # Throttling (rate limiting)
  default_route_settings {
    throttling_burst_limit = 10   # Max concurrent requests
    throttling_rate_limit  = 1000 # Requests per hour (calculated as per-second × 3600)
  }

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-api-stage"
      Component = "api-gateway"
    }
  )
}

# ============================================================================
# CloudWatch Log Group for API Gateway
# ============================================================================

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${local.name_prefix}-api"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-api-logs"
      Component = "api-gateway"
    }
  )
}

# ============================================================================
# API Gateway Routes and Lambda Integrations
# ============================================================================

# Member Endpoints
# ----------------------------------------------------------------------------

# GET /v1/members - List members
resource "aws_apigatewayv2_route" "get_members" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/members"
  target    = "integrations/${aws_apigatewayv2_integration.get_members.id}"
}

resource "aws_apigatewayv2_integration" "get_members" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_members"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/members/{bioguide_id} - Member profile
resource "aws_apigatewayv2_route" "get_member" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/members/{bioguide_id}"
  target    = "integrations/${aws_apigatewayv2_integration.get_member.id}"
}

resource "aws_apigatewayv2_integration" "get_member" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_member"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/members/{bioguide_id}/trades - Member trades
resource "aws_apigatewayv2_route" "get_member_trades" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/members/{bioguide_id}/trades"
  target    = "integrations/${aws_apigatewayv2_integration.get_member_trades.id}"
}

resource "aws_apigatewayv2_integration" "get_member_trades" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_member_trades"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/members/{bioguide_id}/portfolio - Member portfolio
resource "aws_apigatewayv2_route" "get_member_portfolio" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/members/{bioguide_id}/portfolio"
  target    = "integrations/${aws_apigatewayv2_integration.get_member_portfolio.id}"
}

resource "aws_apigatewayv2_integration" "get_member_portfolio" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_member_portfolio"].invoke_arn
  payload_format_version = "2.0"
}

# Trading & Stock Endpoints
# ----------------------------------------------------------------------------

# GET /v1/trades - List trades
resource "aws_apigatewayv2_route" "get_trades" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/trades"
  target    = "integrations/${aws_apigatewayv2_integration.get_trades.id}"
}

resource "aws_apigatewayv2_integration" "get_trades" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_trades"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/stocks/{ticker} - Stock summary
resource "aws_apigatewayv2_route" "get_stock" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/stocks/{ticker}"
  target    = "integrations/${aws_apigatewayv2_integration.get_stock.id}"
}

resource "aws_apigatewayv2_integration" "get_stock" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_stock"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/stocks/{ticker}/activity - Stock trading activity
resource "aws_apigatewayv2_route" "get_stock_activity" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/stocks/{ticker}/activity"
  target    = "integrations/${aws_apigatewayv2_integration.get_stock_activity.id}"
}

resource "aws_apigatewayv2_integration" "get_stock_activity" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_stock_activity"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/stocks - List stocks
resource "aws_apigatewayv2_route" "get_stocks" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/stocks"
  target    = "integrations/${aws_apigatewayv2_integration.get_stocks.id}"
}

resource "aws_apigatewayv2_integration" "get_stocks" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_stocks"].invoke_arn
  payload_format_version = "2.0"
}

# Analytics Endpoints
# ----------------------------------------------------------------------------

# GET /v1/analytics/top-traders
resource "aws_apigatewayv2_route" "get_top_traders" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/top-traders"
  target    = "integrations/${aws_apigatewayv2_integration.get_top_traders.id}"
}

resource "aws_apigatewayv2_integration" "get_top_traders" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_top_traders"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/analytics/trending-stocks
resource "aws_apigatewayv2_route" "get_trending_stocks" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/trending-stocks"
  target    = "integrations/${aws_apigatewayv2_integration.get_trending_stocks.id}"
}

resource "aws_apigatewayv2_integration" "get_trending_stocks" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_trending_stocks"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/analytics/sector-activity
resource "aws_apigatewayv2_route" "get_sector_activity" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/sector-activity"
  target    = "integrations/${aws_apigatewayv2_integration.get_sector_activity.id}"
}

resource "aws_apigatewayv2_integration" "get_sector_activity" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_sector_activity"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/analytics/compliance
resource "aws_apigatewayv2_route" "get_compliance" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/compliance"
  target    = "integrations/${aws_apigatewayv2_integration.get_compliance.id}"
}

resource "aws_apigatewayv2_integration" "get_compliance" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_compliance"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/analytics/trading-timeline
resource "aws_apigatewayv2_route" "get_trading_timeline" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/trading-timeline"
  target    = "integrations/${aws_apigatewayv2_integration.get_trading_timeline.id}"
}

resource "aws_apigatewayv2_integration" "get_trading_timeline" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_trading_timeline"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/analytics/summary
resource "aws_apigatewayv2_route" "get_summary" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/summary"
  target    = "integrations/${aws_apigatewayv2_integration.get_summary.id}"
}

resource "aws_apigatewayv2_integration" "get_summary" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_summary"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/analytics/network-graph
resource "aws_apigatewayv2_route" "get_network_graph" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/network-graph"
  target    = "integrations/${aws_apigatewayv2_integration.get_network_graph.id}"
}

resource "aws_apigatewayv2_integration" "get_network_graph" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_network_graph"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/analytics/activity
resource "aws_apigatewayv2_route" "get_recent_activity" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/activity"
  target    = "integrations/${aws_apigatewayv2_integration.get_recent_activity.id}"
}

resource "aws_apigatewayv2_integration" "get_recent_activity" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_recent_activity"].invoke_arn
  payload_format_version = "2.0"
}

# Advanced Analytics (God Mode) Endpoints
# ----------------------------------------------------------------------------

# GET /v1/analytics/alpha
resource "aws_apigatewayv2_route" "get_congressional_alpha" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/alpha"
  target    = "integrations/${aws_apigatewayv2_integration.get_congressional_alpha.id}"
}

resource "aws_apigatewayv2_integration" "get_congressional_alpha" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_congressional_alpha"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/analytics/conflicts
resource "aws_apigatewayv2_route" "get_conflict_detection" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/conflicts"
  target    = "integrations/${aws_apigatewayv2_integration.get_conflict_detection.id}"
}

resource "aws_apigatewayv2_integration" "get_conflict_detection" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_conflict_detection"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/analytics/portfolio
resource "aws_apigatewayv2_route" "get_portfolio_recon" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/portfolio"
  target    = "integrations/${aws_apigatewayv2_integration.get_portfolio_recon.id}"
}

resource "aws_apigatewayv2_integration" "get_portfolio_recon" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_portfolio_recon"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/analytics/insights
resource "aws_apigatewayv2_route" "get_pattern_insights" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/insights"
  target    = "integrations/${aws_apigatewayv2_integration.get_pattern_insights.id}"
}

resource "aws_apigatewayv2_integration" "get_pattern_insights" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_pattern_insights"].invoke_arn
  payload_format_version = "2.0"
}

# Search & Filing Endpoints
# ----------------------------------------------------------------------------

# GET /v1/search
resource "aws_apigatewayv2_route" "search" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/search"
  target    = "integrations/${aws_apigatewayv2_integration.search.id}"
}

resource "aws_apigatewayv2_integration" "search" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["search"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/filings
resource "aws_apigatewayv2_route" "get_filings" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/filings"
  target    = "integrations/${aws_apigatewayv2_integration.get_filings.id}"
}

resource "aws_apigatewayv2_integration" "get_filings" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_filings"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/filings/{doc_id}
resource "aws_apigatewayv2_route" "get_filing" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/filings/{doc_id}"
  target    = "integrations/${aws_apigatewayv2_integration.get_filing.id}"
}

resource "aws_apigatewayv2_integration" "get_filing" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_filing"].invoke_arn
  payload_format_version = "2.0"
}

# ============================================================================
# Lambda Permissions for API Gateway
# ============================================================================

# Allow API Gateway to invoke all API Lambda functions
resource "aws_lambda_permission" "api_invoke" {
  for_each = aws_lambda_function.api

  statement_id  = "AllowAPIGatewayInvoke-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.function_name
  principal     = "apigateway.amazonaws.com"

  # Allow invocation from any route in this API
  source_arn = "${aws_apigatewayv2_api.congress_api.execution_arn}/*/*"
}

# ============================================================================
# Outputs
# ============================================================================

output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.congress_api.api_endpoint
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.congress_api.id
}

output "api_gateway_execution_arn" {
  description = "Execution ARN of the API Gateway"
  value       = aws_apigatewayv2_api.congress_api.execution_arn
}
