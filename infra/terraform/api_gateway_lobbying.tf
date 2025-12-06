# ============================================================================
# Lobbying Data API Routes
# ============================================================================
# These routes expose lobbying disclosure data from the LDA pipeline

# GET /v1/lobbying/filings - List lobbying filings
resource "aws_apigatewayv2_route" "get_lobbying_filings" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/lobbying/filings"
  target    = "integrations/${aws_apigatewayv2_integration.get_lobbying_filings.id}"
}

resource "aws_apigatewayv2_integration" "get_lobbying_filings" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_lobbying_filings"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/lobbying/clients/{client_id} - Get client details
resource "aws_apigatewayv2_route" "get_lobbying_client" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/lobbying/clients/{client_id}"
  target    = "integrations/${aws_apigatewayv2_integration.get_lobbying_client.id}"
}

resource "aws_apigatewayv2_integration" "get_lobbying_client" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_lobbying_client"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/lobbying/network - Get lobbying network graph
resource "aws_apigatewayv2_route" "get_lobbying_network" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/lobbying/network"
  target    = "integrations/${aws_apigatewayv2_integration.get_lobbying_network.id}"
}

resource "aws_apigatewayv2_integration" "get_lobbying_network" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_lobbying_network"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/lobbying/network-graph - Alias for network visualization
resource "aws_apigatewayv2_route" "get_lobbying_network_graph" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/lobbying/network-graph"
  target    = "integrations/${aws_apigatewayv2_integration.get_lobbying_network.id}"
}

# GET /v1/congress/bills/{bill_id}/lobbying - Get lobbying activity for a bill
resource "aws_apigatewayv2_route" "get_bill_lob_activity" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/congress/bills/{bill_id}/lobbying"
  target    = "integrations/${aws_apigatewayv2_integration.get_bill_lob_activity.id}"
}

resource "aws_apigatewayv2_integration" "get_bill_lob_activity" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_bill_lob_activity"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/members/{bioguide_id}/lobbying - Get lobbying connections for a member
resource "aws_apigatewayv2_route" "get_member_lob_connects" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/members/{bioguide_id}/lobbying"
  target    = "integrations/${aws_apigatewayv2_integration.get_member_lob_connects.id}"
}

resource "aws_apigatewayv2_integration" "get_member_lob_connects" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_member_lob_connects"].invoke_arn
  payload_format_version = "2.0"
}

# GET /v1/correlations/triple - Triple correlation analysis (STAR API)
resource "aws_apigatewayv2_route" "get_triple_correlations" {
  api_id    = aws_apigatewayv2_api.congress_api.id
  route_key = "GET /v1/correlations/triple"
  target    = "integrations/${aws_apigatewayv2_integration.get_triple_correlations.id}"
}

resource "aws_apigatewayv2_integration" "get_triple_correlations" {
  api_id           = aws_apigatewayv2_api.congress_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api["get_triple_correlations"].invoke_arn
  payload_format_version = "2.0"
}
