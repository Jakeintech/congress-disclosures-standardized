
# GET /v1/filings/{doc_id}/transactions
resource "aws_apigatewayv2_route" "get_filing_transactions" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/filings/{doc_id}/transactions"
  target    = "integrations/${aws_apigatewayv2_integration.get_filing_transactions.id}"
}

resource "aws_apigatewayv2_integration" "get_filing_transactions" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_filing_transactions"].invoke_arn
  payload_format_version = "2.0"
}
