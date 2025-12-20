# GET /v1/congress/bills/{congress}/{type}/{number}
resource "aws_apigatewayv2_route" "get_congress_bill" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{congress}/{type}/{number}"
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

# GET /v1/congress/bills/{congress}/{type}/{number}/actions
resource "aws_apigatewayv2_route" "get_bill_actions" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{congress}/{type}/{number}/actions"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_actions.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_actions" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_actions"].invoke_arn
}

# GET /v1/congress/bills/{congress}/{type}/{number}/text
resource "aws_apigatewayv2_route" "get_bill_text" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{congress}/{type}/{number}/text"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_text.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_text" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_text"].invoke_arn
}

# GET /v1/congress/bills/{congress}/{type}/{number}/committees
resource "aws_apigatewayv2_route" "get_bill_committees" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{congress}/{type}/{number}/committees"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_committees.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_committees" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_committees"].invoke_arn
}

# GET /v1/congress/bills/{congress}/{type}/{number}/cosponsors
resource "aws_apigatewayv2_route" "get_bill_cosponsors" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{congress}/{type}/{number}/cosponsors"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_cosponsors.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_cosponsors" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_cosponsors"].invoke_arn
}

# GET /v1/congress/bills/{congress}/{type}/{number}/subjects
resource "aws_apigatewayv2_route" "get_bill_subjects" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{congress}/{type}/{number}/subjects"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_subjects.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_subjects" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_subjects"].invoke_arn
}

# GET /v1/congress/bills/{congress}/{type}/{number}/summaries
resource "aws_apigatewayv2_route" "get_bill_summaries" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{congress}/{type}/{number}/summaries"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_summaries.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_summaries" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_summaries"].invoke_arn
}

# GET /v1/congress/bills/{congress}/{type}/{number}/titles
resource "aws_apigatewayv2_route" "get_bill_titles" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{congress}/{type}/{number}/titles"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_titles.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_titles" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_titles"].invoke_arn
}

# GET /v1/congress/bills/{congress}/{type}/{number}/amendments
resource "aws_apigatewayv2_route" "get_bill_amendments" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{congress}/{type}/{number}/amendments"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_amendments.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_amendments" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_amendments"].invoke_arn
}

# GET /v1/congress/bills/{congress}/{type}/{number}/related
resource "aws_apigatewayv2_route" "get_bill_related" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{congress}/{type}/{number}/related"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_related.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_related" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_bill_related"].invoke_arn
}

# GET /v1/congress/committees
resource "aws_apigatewayv2_route" "get_congress_committees" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/committees"
  target    = "integrations/${aws_apigatewayv2_integration.get_congress_committees.id}"
}

resource "aws_apigatewayv2_integration" "get_congress_committees" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_congress_committees"].invoke_arn
}

# GET /v1/congress/committees/{chamber}/{code}
resource "aws_apigatewayv2_route" "get_congress_committee" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/committees/{chamber}/{code}"
  target    = "integrations/${aws_apigatewayv2_integration.get_congress_committee.id}"
}

resource "aws_apigatewayv2_integration" "get_congress_committee" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_congress_committee"].invoke_arn
}

# GET /v1/congress/committees/{chamber}/{code}/bills
resource "aws_apigatewayv2_route" "get_committee_bills" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/committees/{chamber}/{code}/bills"
  target    = "integrations/${aws_apigatewayv2_integration.get_committee_bills.id}"
}

resource "aws_apigatewayv2_integration" "get_committee_bills" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_committee_bills"].invoke_arn
}

# GET /v1/congress/committees/{chamber}/{code}/members
resource "aws_apigatewayv2_route" "get_committee_members" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/committees/{chamber}/{code}/members"
  target    = "integrations/${aws_apigatewayv2_integration.get_committee_members.id}"
}

resource "aws_apigatewayv2_integration" "get_committee_members" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_committee_members"].invoke_arn
}
# GET /v1/congress/committees/{chamber}/{code}/reports
resource "aws_apigatewayv2_route" "get_committee_reports" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/committees/{chamber}/{code}/reports"
  target    = "integrations/${aws_apigatewayv2_integration.get_committee_reports.id}"
}

resource "aws_apigatewayv2_integration" "get_committee_reports" {
  api_id             = aws_apigatewayv2_api.congress_api.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = aws_lambda_function.api["get_committee_reports"].invoke_arn
}
# GET /v1/congress/bills (plural list)
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
