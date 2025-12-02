# Main infrastructure outputs
# These values can be used by other tools or for manual reference

output "account_id" {
  description = "AWS Account ID"
  value       = local.account_id
}

output "region" {
  description = "AWS Region"
  value       = local.region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# S3 outputs (from s3.tf)
# Already defined in s3.tf, but we can aggregate here if needed

# Lambda outputs (from lambda.tf)
# Already defined in lambda.tf

# SQS outputs (from sqs.tf)
# Already defined in sqs.tf

# CloudWatch outputs (from cloudwatch.tf)
# Already defined in cloudwatch.tf

# Aggregate quick reference output
output "quick_reference" {
  description = "Quick reference guide for common operations"
  value = {
    ingest_command = "aws lambda invoke --function-name ${aws_lambda_function.ingest_zip.function_name} --payload '{\"year\": 2025}' response.json"
    s3_bucket      = aws_s3_bucket.data_lake.id
    sqs_queue_url  = aws_sqs_queue.extraction_queue.url
    logs_ingest    = "aws logs tail ${aws_cloudwatch_log_group.ingest_zip.name} --follow"
    logs_extract   = "aws logs tail ${aws_cloudwatch_log_group.extract_document.name} --follow"
  }
}

# Cost estimation helper
output "monthly_cost_estimate" {
  description = "Estimated monthly cost breakdown (USD) based on typical usage"
  value = {
    s3_storage_20gb = "$0.46"
    lambda_compute  = "$0.08 - $2.00 (depends on invocations)"
    sqs             = "$0.00 (within free tier)"
    cloudwatch_logs = "$0.50"
    total_estimate  = "$0.96 - $2.96 per month"
    note            = "Textract dependency removed; costs are storage + Lambda only."
  }
}

# Deployment instructions
output "next_steps" {
  description = "Next steps after Terraform deployment"
  value       = <<-EOT
  Terraform deployment complete! Next steps:

  1. Trigger initial ingestion:
     aws lambda invoke --function-name ${aws_lambda_function.ingest_zip.function_name} \
       --payload '{"year": 2025}' response.json

  2. Monitor ingestion progress:
     aws logs tail ${aws_cloudwatch_log_group.ingest_zip.name} --follow

  3. Check extraction queue:
     aws sqs get-queue-attributes \
       --queue-url ${aws_sqs_queue.extraction_queue.url} \
       --attribute-names ApproximateNumberOfMessages

  4. Monitor extraction:
     aws logs tail ${aws_cloudwatch_log_group.extract_document.name} --follow

  5. View dashboard (if alerts enabled):
     ${var.enable_cost_alerts ? "https://console.aws.amazon.com/cloudwatch/home?region=${local.region}#dashboards:name=${local.name_prefix}-dashboard" : "Dashboard not enabled"}

  For more details, see docs/DEPLOYMENT.md
  EOT
}

# Data Lake Layer URLs
output "s3_bronze_layer_url" {
  description = "S3 console URL for bronze layer (raw data)"
  value       = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.data_lake.id}?prefix=bronze/&region=${local.region}"
}

output "s3_silver_layer_url" {
  description = "S3 console URL for silver layer (normalized data)"
  value       = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.data_lake.id}?prefix=silver/&region=${local.region}"
}

output "s3_gold_layer_url" {
  description = "S3 console URL for gold layer (query-facing data)"
  value       = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.data_lake.id}?prefix=gold/&region=${local.region}"
}

# CLI commands for accessing data
output "data_access_commands" {
  description = "AWS CLI commands for accessing data layers"
  value = {
    list_bronze = "aws s3 ls s3://${aws_s3_bucket.data_lake.id}/bronze/ --recursive --human-readable"
    list_silver = "aws s3 ls s3://${aws_s3_bucket.data_lake.id}/silver/ --recursive --human-readable"
    list_gold   = "aws s3 ls s3://${aws_s3_bucket.data_lake.id}/gold/ --recursive --human-readable"
  }
}
