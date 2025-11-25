############################################
# Seed automation: invoke gold_seed Lambda #
############################################

resource "null_resource" "run_gold_seed" {
  # Re-run when bucket or seed version changes
  triggers = {
    bucket       = aws_s3_bucket.data_lake.id
    seed_version = var.seed_data_version
  }

  # Invoke the seed lambda once post-apply (idempotent in code)
  provisioner "local-exec" {
    command = <<EOT
aws lambda invoke \
  --function-name ${aws_lambda_function.gold_seed.function_name} \
  --payload '{"command":"seed"}' \
  seed_output.json >/dev/null 2>&1 || true
if [ -f seed_output.json ]; then cat seed_output.json; rm seed_output.json; fi
EOT
  }

  depends_on = [
    aws_lambda_function.gold_seed,
    aws_s3_bucket.data_lake
  ]
}

resource "null_resource" "run_gold_seed_members" {
  triggers = {
    bucket       = aws_s3_bucket.data_lake.id
    seed_version = var.seed_data_version
    ssm_param    = local.ssm_congress_api_key_param
  }

  provisioner "local-exec" {
    # Allow failure without breaking terraform apply; logs response if present
    command = <<EOT
aws lambda invoke \
  --function-name ${aws_lambda_function.gold_seed_members.function_name} \
  --payload '{"command":"seed"}' \
  seed_members_output.json >/dev/null 2>&1 || true
if [ -f seed_members_output.json ]; then cat seed_members_output.json; rm seed_members_output.json; fi
EOT
  }

  depends_on = [
    aws_lambda_function.gold_seed_members,
    aws_iam_role_policy.lambda_ssm_congress_api,
    aws_s3_bucket.data_lake
  ]
}
