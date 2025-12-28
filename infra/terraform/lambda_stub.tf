# Stub Lambda for placeholders
resource "aws_lambda_function" "stub_handler" {
  function_name = "${local.name_prefix}-stub-handler"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  # Use zip from S3 or local - reusing a simple zip or creating one
  # Since we just created the file, we can rely on facility to zip it, but 
  # for simplicity in this "Fix all" context, I will use a local file source or similar if possible.
  # However, consistent with other lambdas, I'll assume packaging.
  # For now, I'll point to the same zip path pattern.
  
  s3_bucket        = aws_s3_bucket.data_lake.id
  s3_key           = "lambda-deployments/stub_handler/function.zip"
  source_code_hash = fileexists("${path.module}/../../ingestion/lambdas/stub_handler/function.zip") ? filebase64sha256("${path.module}/../../ingestion/lambdas/stub_handler/function.zip") : null

  timeout     = 30
  memory_size = 128

  environment {
    variables = {
      LOG_LEVEL = "INFO"
    }
  }

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-stub-handler"
      Component = "lambda"
      Purpose   = "placeholder"
    }
  )

  lifecycle {
    ignore_changes = [
      source_code_hash,
      filename
    ]
  }
}

output "lambda_stub_handler_name" {
  value = aws_lambda_function.stub_handler.function_name
}
