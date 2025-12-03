# API Gateway routes for member analytics

# GET /v1/members/{name}/filings
resource "aws_apigatewayv2_route" "get_member_filings" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/members/{name}/filings"
  target    = "integrations/${aws_apigatewayv2_integration.get_member_filings.id}"
}

resource "aws_apigatewayv2_integration" "get_member_filings" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.api["get_member_filings"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/members/{name}/transactions  
resource "aws_apigatewayv2_route" "get_member_transactions" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/members/{name}/transactions"
  target    = "integrations/${aws_apigatewayv2_integration.get_member_transactions.id}"
}

resource "aws_apigatewayv2_integration" "get_member_transactions" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.api["get_member_transactions"].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_member_assets" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/members/{name}/assets"
  target    = "integrations/${aws_apigatewayv2_integration.get_member_assets.id}"
}

resource "aws_apigatewayv2_integration" "get_member_assets" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.api["get_member_assets"].invoke_arn
  payload_format_version = "2.0"
}
