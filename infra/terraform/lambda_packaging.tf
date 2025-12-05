# Lambda Package Builder
# Automatically builds Lambda packages before Terraform deployment

resource "null_resource" "package_lambdas" {
  # Trigger on any code change by checking timestamps
  triggers = {
    # Force rebuild on every apply to ensure latest code
    always_run = timestamp()

    # Also trigger if Makefile changes
    makefile_hash = filemd5("${path.module}/../../Makefile")
  }

  provisioner "local-exec" {
    command     = "make package-all"
    working_dir = "${path.module}/../.."

    environment = {
      PYTHON = "python3"
    }
  }

  # Run before Lambda deployments
  lifecycle {
    create_before_destroy = true
  }
}

# Output to confirm packaging was run
output "lambda_packages_built" {
  value       = "Lambda packages built at ${null_resource.package_lambdas.id}"
  description = "Timestamp when Lambda packages were last built"
}
