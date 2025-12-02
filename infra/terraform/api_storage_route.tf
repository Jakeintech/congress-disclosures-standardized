# GET /v1/storage/{layer} - List S3 objects
resource "aws_apigatewayv2_route" "list_s3_objects" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/storage/{layer}"
  target    = "integrations/${aws_apigatewayv2_integration.list_s3_objects.id}"
}

resource "aws_apigatewayv2_integration" "list_s3_objects" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["list_s3_objects"].invoke_arn
  payload_format_version = "2.0"
}
