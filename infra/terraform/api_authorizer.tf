# ============================================================================
# API Gateway Lambda Authorizer
# ============================================================================
# Secures the API using a Lambda function that validates API keys or tokens.

# ----------------------------------------------------------------------------
# Authorizer Lambda Function
# ----------------------------------------------------------------------------
resource "aws_lambda_function" "api_authorizer" {
  function_name = "${local.name_prefix}-api-authorizer"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 5
  memory_size   = 128

  # Using a placeholder script if the actual authorizer code doesn't exist yet
  # In a real scenario, this would point to the built artifact
  filename = "${path.module}/../../backend/functions/auth/authorizer/function.zip"

  # If the file doesn't exist, we'll need to ensure it's created or use a dummy
  # for the initial plan to succeed.
  source_code_hash = fileexists("${path.module}/../../backend/functions/auth/authorizer/function.zip") ? filebase64sha256("${path.module}/../../backend/functions/auth/authorizer/function.zip") : null

  environment {
    variables = {
      LOG_LEVEL         = "INFO"
      API_KEYS_SSM_PATH = "/${var.project_name}/${var.environment}/api-keys"
    }
  }

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-api-authorizer"
      Component = "security"
      Purpose   = "auth"
    }
  )
}

# ----------------------------------------------------------------------------
# CloudWatch Log Group for Authorizer
# ----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "api_authorizer" {
  name              = "/aws/lambda/${aws_lambda_function.api_authorizer.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = local.standard_tags
}

# ----------------------------------------------------------------------------
# API Gateway Authorizer Definition
# ----------------------------------------------------------------------------
resource "aws_apigatewayv2_authorizer" "main" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  authorizer_type  = "REQUEST"
  authorizer_uri   = aws_lambda_function.api_authorizer.invoke_arn
  identity_sources = ["$request.header.X-Api-Key"]
  name             = "${local.name_prefix}-authorizer"

  # Caching results for 5 minutes (300 seconds) to reduce Lambda invocations
  authorizer_payload_format_version = "2.0"
  enable_simple_responses           = true
  authorizer_result_ttl_in_seconds  = 300
}

# ----------------------------------------------------------------------------
# Permission for API Gateway to Invoke Authorizer
# ----------------------------------------------------------------------------
resource "aws_lambda_permission" "api_gateway_authorizer" {
  statement_id  = "AllowAPIGatewayInvokeAuthorizer"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_authorizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.congress_api.execution_arn}/authorizers/${aws_apigatewayv2_authorizer.main.id}"
}

# ----------------------------------------------------------------------------
# Outputs
# ----------------------------------------------------------------------------
output "authorizer_id" {
  description = "ID of the API Gateway Authorizer"
  value       = aws_apigatewayv2_authorizer.main.id
}
