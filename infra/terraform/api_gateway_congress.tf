# ============================================================================
# Congress API Gateway Routes
# ============================================================================
# Routes for Congress.gov legislative data endpoints

# GET /v1/congress/bills
resource "aws_apigatewayv2_route" "get_congress_bills" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills"
  target    = "integrations/${aws_apigatewayv2_integration.get_congress_bills.id}"
}

resource "aws_apigatewayv2_integration" "get_congress_bills" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_congress_bills"].invoke_arn
}

# GET /v1/congress/bills/{bill_id}
resource "aws_apigatewayv2_route" "get_congress_bill" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{bill_id}"
  target    = "integrations/${aws_apigatewayv2_integration.get_congress_bill.id}"
}

resource "aws_apigatewayv2_integration" "get_congress_bill" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_congress_bill"].invoke_arn
}

# GET /v1/congress/members
resource "aws_apigatewayv2_route" "get_congress_members" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/members"
  target    = "integrations/${aws_apigatewayv2_integration.get_congress_members.id}"
}

resource "aws_apigatewayv2_integration" "get_congress_members" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_congress_members"].invoke_arn
}

# GET /v1/congress/members/{bioguide_id}
resource "aws_apigatewayv2_route" "get_congress_member" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/members/{bioguide_id}"
  target    = "integrations/${aws_apigatewayv2_integration.get_congress_member.id}"
}

resource "aws_apigatewayv2_integration" "get_congress_member" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_congress_member"].invoke_arn
}

# GET /v1/analytics/members/{bioguide_id}/legislation-trades
resource "aws_apigatewayv2_route" "get_member_leg_trades" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/members/{bioguide_id}/legislation-trades"
  target    = "integrations/${aws_apigatewayv2_integration.get_member_leg_trades.id}"
}

resource "aws_apigatewayv2_integration" "get_member_leg_trades" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_member_leg_trades"].invoke_arn
}

# GET /v1/analytics/stocks/{ticker}/legislative-exposure
resource "aws_apigatewayv2_route" "get_stock_leg_exposure" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/analytics/stocks/{ticker}/legislative-exposure"
  target    = "integrations/${aws_apigatewayv2_integration.get_stock_leg_exposure.id}"
}

resource "aws_apigatewayv2_integration" "get_stock_leg_exposure" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_stock_leg_exposure"].invoke_arn
}
