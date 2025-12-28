# API Gateway routes for filing assets and positions

# GET /v1/filings/{doc_id}/assets
resource "aws_apigatewayv2_route" "get_filing_assets" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/filings/{doc_id}/assets"
  target    = "integrations/${aws_apigatewayv2_integration.get_filing_assets.id}"
}

resource "aws_apigatewayv2_integration" "get_filing_assets" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api["get_filing_assets"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/filings/{doc_id}/positions
resource "aws_apigatewayv2_route" "get_filing_positions" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/filings/{doc_id}/positions"
  target    = "integrations/${aws_apigatewayv2_integration.get_filing_positions.id}"
}

resource "aws_apigatewayv2_integration" "get_filing_positions" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api["get_filing_positions"].invoke_arn
  payload_format_version = "2.0"
}
