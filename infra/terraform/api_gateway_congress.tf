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

# GET /v1/congress/bills/{bill_id}/actions (Epic 3 - Bill Actions Timeline)
resource "aws_apigatewayv2_route" "get_bill_actions" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{bill_id}/actions"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_actions.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_actions" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_actions"].invoke_arn
}

# GET /v1/congress/bills/{bill_id}/text
resource "aws_apigatewayv2_route" "get_bill_text" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{bill_id}/text"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_text.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_text" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_text"].invoke_arn
}

# GET /v1/congress/bills/{bill_id}/committees
resource "aws_apigatewayv2_route" "get_bill_committees" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{bill_id}/committees"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_committees.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_committees" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_committees"].invoke_arn
}

# GET /v1/congress/bills/{bill_id}/cosponsors
resource "aws_apigatewayv2_route" "get_bill_cosponsors" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{bill_id}/cosponsors"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_cosponsors.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_cosponsors" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_cosponsors"].invoke_arn
}

# GET /v1/congress/bills/{bill_id}/subjects
resource "aws_apigatewayv2_route" "get_bill_subjects" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{bill_id}/subjects"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_subjects.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_subjects" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_subjects"].invoke_arn
}

# GET /v1/congress/bills/{bill_id}/summaries
resource "aws_apigatewayv2_route" "get_bill_summaries" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{bill_id}/summaries"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_summaries.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_summaries" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_summaries"].invoke_arn
}

# GET /v1/congress/bills/{bill_id}/titles
resource "aws_apigatewayv2_route" "get_bill_titles" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{bill_id}/titles"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_titles.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_titles" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_titles"].invoke_arn
}

# GET /v1/congress/bills/{bill_id}/amendments
resource "aws_apigatewayv2_route" "get_bill_amendments" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{bill_id}/amendments"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_amendments.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_amendments" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_amendments"].invoke_arn
}

# GET /v1/congress/bills/{bill_id}/related
resource "aws_apigatewayv2_route" "get_bill_related" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{bill_id}/related"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_related.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_related" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_related"].invoke_arn
}
