# ============================================================================
# Dynamic API Gateway Routes & Integrations
# ============================================================================
# This file dynamically generates all API Gateway integrations and routes
# based on the local.api_lambdas configuration in api_lambdas.tf.
# This replaces the legacy repetitive resource definitions.

locals {
  # Flatten the map of functions-to-routes into a list of route objects
  # structure: [ { key = "get_members", route = "GET /v1/members" }, ... ]
  api_routes_flat = flatten([
    for func_key, config in local.api_lambdas : [
      for route_str in config.routes : {
        function_key = func_key
        route_key    = route_str
        # Create a deterministic unique ID for the terraform resource key
        tf_id = "${func_key}-${substr(md5(route_str), 0, 8)}"
      }
    ]
  ])
}

# ============================================================================
# Integrations (1 per Lambda Function)
# ============================================================================
resource "aws_apigatewayv2_integration" "api" {
  for_each = local.api_lambdas

  api_id                 = aws_apigatewayv2_api.congress_api.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.api[each.key].invoke_arn
  payload_format_version = "2.0"
}

# ============================================================================
# Routes (Multiple per Lambda Function)
# ============================================================================
resource "aws_apigatewayv2_route" "api" {
  # Iterate over flattened routes to create unique resources
  for_each = {
    for r in local.api_routes_flat : r.tf_id => r
  }

  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = each.value.route_key
  target    = "integrations/${aws_apigatewayv2_integration.api[each.value.function_key].id}"
}

# ============================================================================
# Lambda Permissions (1 per Lambda Function)
# ============================================================================
# Allow API Gateway to invoke the Lambda functions.
# We grant permission for the entire API (*/*) to simplify alias management.
resource "aws_lambda_permission" "api_gateway_invoke" {
  for_each = local.api_lambdas

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.congress_api.execution_arn}/*/*"
}
