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
      requestId               = "$context.requestId"
      ip                      = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      httpMethod              = "$context.httpMethod"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      protocol                = "$context.protocol"
      responseLength          = "$context.responseLength"
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
