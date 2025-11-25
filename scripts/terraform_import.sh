#!/usr/bin/env bash
set -e

# Change to Terraform directory
cd "$(dirname "$0")/../infra/terraform"

# Determine environment (production or development) based on branch name if needed
# For simplicity, default to development; CI can set ENV variable before calling this script
ENVIRONMENT=${ENVIRONMENT:-development}

# List of resources to import (resource_type resource_name terraform_id)
resources=(
  "aws_s3_bucket data_lake congress-disclosures-${ENVIRONMENT}-data-lake"
  "aws_dynamodb_table terraform_locks congress-disclosures-terraform-locks"
  "aws_budgets_budget monthly_free_tier congress-disclosures-${ENVIRONMENT}-monthly-free-tier"
  "aws_budgets_budget daily_limit congress-disclosures-${ENVIRONMENT}-daily-limit"
  "aws_budgets_budget lambda_budget congress-disclosures-${ENVIRONMENT}-lambda-budget"
  "aws_budgets_budget s3_budget congress-disclosures-${ENVIRONMENT}-s3-budget"
  "aws_iam_role shutdown_lambda congress-disclosures-${ENVIRONMENT}-shutdown-lambda-role"
  "aws_cloudwatch_log_group ingest_zip /aws/lambda/congress-disclosures-${ENVIRONMENT}-ingest-zip"
  # Add other resources as needed
)

for entry in "${resources[@]}"; do
  IFS=' ' read -r type name id <<< "$entry"
  if ! terraform state list | grep -q "^${type}\.${name}$"; then
    echo "Importing ${type}.${name}..."
    terraform import "${type}.${name}" "${id}"
  else
    echo "${type}.${name} already in state"
  fi
done
