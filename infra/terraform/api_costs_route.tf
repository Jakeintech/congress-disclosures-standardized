# GET /v1/costs - AWS Costs
resource "aws_apigatewayv2_route" "get_aws_costs" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/costs"
  target    = "integrations/${aws_apigatewayv2_integration.get_aws_costs.id}"
}

resource "aws_apigatewayv2_integration" "get_aws_costs" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_aws_costs"].invoke_arn
  payload_format_version = "2.0"
}
