resource "aws_dynamodb_table" "house_fd_documents" {
  name           = "house_fd_documents"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "doc_id"
  range_key      = "year"

  attribute {
    name = "doc_id"
    type = "S"
  }

  attribute {
    name = "year"
    type = "N"
  }

  tags = {
    Name        = "house_fd_documents"
    Environment = var.environment
    Project     = "congress-disclosures"
  }
}
