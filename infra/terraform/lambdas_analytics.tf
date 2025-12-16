# =============================================================================
# Lambda Function: compute_member_stats
# =============================================================================
# Already defined in lambdas_gold_transformations.tf


# =============================================================================
# Lambda Function: compute_bill_trade_correlations (Shared for Correlations)
# =============================================================================
# This function will handle bill-trade correlations and impact scores for now.
resource "aws_lambda_function" "compute_bill_trade_correlations" {
  function_name = "${var.project_name}-compute-bill-trade-correlations"
  description   = "Compute correlations between bills and trades"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512

  # Use same zip for now as a base, or unique one if we create it
  # We will use 'compute_member_stats' zip as a placeholder if code missing, 
  # or better, point to a new directory we are about to create.
  s3_bucket = var.s3_bucket_name
  s3_key    = "lambda-deployments/compute_bill_trade_correlations/function.zip"
  
  layers = [
    aws_lambda_layer_version.congress_pandas_layer.arn
  ]

  environment {
     variables = {
      S3_BUCKET_NAME = var.s3_bucket_name
      LOG_LEVEL      = "INFO"
     }
  }

  tags = merge(
     local.standard_tags,
     {
       Component = "analytics"
       Purpose   = "correlations"
     }
  )

  lifecycle {
     ignore_changes = [source_code_hash, filename]
  }

  depends_on = [
    aws_lambda_layer_version.congress_pandas_layer,
    null_resource.package_lambdas
  ]
}

output "compute_bill_trade_correlations_function_name" {
  value = aws_lambda_function.compute_bill_trade_correlations.function_name
}
