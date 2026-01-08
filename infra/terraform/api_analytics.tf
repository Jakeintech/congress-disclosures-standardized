# ========================================
# Analytics API Endpoints
# ========================================
# Lambda functions and API Gateway integrations
# for transaction analytics endpoints

# Lambda: GET /v1/analytics/filtered-transactions
resource "aws_lambda_function" "get_filtered_transactions" {
  filename      = "${path.module}/../../backend/functions/api/get_filtered_transactions/function.zip"
  function_name = "${var.project_name}-get-filtered-transactions"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
    }
  }

  tags = {
    Name        = "${var.project_name}-get-filtered-transactions"
    Environment = var.environment
    Purpose     = "Return filtered transactions by amount/criteria"
  }
}

# Lambda: GET /v1/analytics/crypto-transactions
resource "aws_lambda_function" "get_crypto_transactions" {
  filename      = "${path.module}/../../backend/functions/api/get_crypto_transactions/function.zip"
  function_name = "${var.project_name}-get-crypto-transactions"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
    }
  }

  tags = {
    Name        = "${var.project_name}-get-crypto-transactions"
    Environment = var.environment
    Purpose     = "Return crypto transaction activity and aggregates"
  }
}

# API Gateway Integration: Filtered Transactions
resource "aws_apigatewayv2_integration" "filtered_transactions" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.get_filtered_transactions.invoke_arn
}

resource "aws_apigatewayv2_route" "filtered_transactions" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/filtered-transactions"
  target    = "integrations/${aws_apigatewayv2_integration.filtered_transactions.id}"
}

resource "aws_lambda_permission" "filtered_transactions_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_filtered_transactions.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.congress_api.execution_arn}/*/*"
}

# API Gateway Integration: Crypto Transactions
resource "aws_apigatewayv2_integration" "crypto_transactions" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.get_crypto_transactions.invoke_arn
}

resource "aws_apigatewayv2_route" "crypto_transactions" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/crypto-transactions"
  target    = "integrations/${aws_apigatewayv2_integration.crypto_transactions.id}"
}

resource "aws_lambda_permission" "crypto_transactions_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_crypto_transactions.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.congress_api.execution_arn}/*/*"
}

# ========================================
# Outputs
# ========================================

output "api_endpoint_filtered_transactions" {
  value       = "${aws_apigatewayv2_api.congress_api.api_endpoint}/v1/analytics/filtered-transactions"
  description = "URL for filtered transactions endpoint"
}

output "api_endpoint_crypto_transactions" {
  value       = "${aws_apigatewayv2_api.congress_api.api_endpoint}/v1/analytics/crypto-transactions"
  description = "URL for crypto transactions endpoint"
}
