terraform {
  backend "s3" {
    bucket         = "congress-disclosures-standardized"
    key            = "terraform/development/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "congress-disclosures-terraform-locks"
  }
}
