# DynamoDB table for Terraform state locking
# This must exist BEFORE the backend configuration is used
# Bootstrap by commenting out backend.tf, running terraform apply, then uncommenting backend.tf

resource "aws_dynamodb_table" "terraform_locks" {
  name         = "congress-disclosures-terraform-locks"
  billing_mode = "PAY_PER_REQUEST" # Free tier: 25 RCU/WCU included
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = merge(var.common_tags, {
    Name        = "Terraform State Lock Table"
    Description = "DynamoDB table for managing Terraform state locks"
  })
}

# Output the table name for reference
output "terraform_lock_table" {
  value       = aws_dynamodb_table.terraform_locks.name
  description = "DynamoDB table used for Terraform state locking"
}
