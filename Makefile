.PHONY: help init plan deploy destroy test lint format clean package docs

# Default target
.DEFAULT_GOAL := help

# Load environment variables from .env if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Variables
TERRAFORM_DIR := infra/terraform
LAMBDA_DIR := ingestion/lambdas
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
FLAKE8 := $(PYTHON) -m flake8
MYPY := $(PYTHON) -m mypy

##@ General

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup & Installation

install: ## Install Python dependencies
	$(PIP) install -r ingestion/requirements.txt
	$(PIP) install -r requirements-dev.txt
	@echo "✓ Python dependencies installed"

install-dev: install ## Install dev dependencies including formatters and linters
	$(PIP) install black flake8 pylint mypy pytest pytest-cov
	@echo "✓ Development tools installed"

setup: install ## Initial setup: create .env, install deps
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env from .env.example - please configure it"; \
	fi
	@echo "✓ Setup complete. Next steps:"
	@echo "  1. Edit .env with your AWS configuration"
	@echo "  2. Run 'make init' to initialize Terraform"
	@echo "  3. Run 'make plan' to see infrastructure changes"

##@ Terraform

init: ## Initialize Terraform
	cd $(TERRAFORM_DIR) && terraform init
	@echo "✓ Terraform initialized"

validate: ## Validate Terraform configuration
	cd $(TERRAFORM_DIR) && terraform validate
	@echo "✓ Terraform configuration valid"

plan: validate ## Show Terraform plan
	cd $(TERRAFORM_DIR) && terraform plan

deploy: ## Deploy infrastructure with Terraform
	cd $(TERRAFORM_DIR) && terraform apply
	@echo "✓ Infrastructure deployed"

deploy-auto: ## Deploy infrastructure without confirmation (use in CI)
	cd $(TERRAFORM_DIR) && terraform apply -auto-approve

destroy: ## Destroy infrastructure (WARNING: irreversible)
	@echo "WARNING: This will destroy all infrastructure including S3 data!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	cd $(TERRAFORM_DIR) && terraform destroy

refresh: ## Refresh Terraform state
	cd $(TERRAFORM_DIR) && terraform refresh

output: ## Show Terraform outputs
	cd $(TERRAFORM_DIR) && terraform output

##@ Lambda Packaging

package-all: package-ingest package-index package-extract ## Package all Lambda functions

package-ingest: ## Package house_fd_ingest_zip Lambda
	@echo "Packaging house_fd_ingest_zip..."
	@rm -rf $(LAMBDA_DIR)/house_fd_ingest_zip/package
	@mkdir -p $(LAMBDA_DIR)/house_fd_ingest_zip/package
	$(PIP) install -r $(LAMBDA_DIR)/house_fd_ingest_zip/requirements.txt -t $(LAMBDA_DIR)/house_fd_ingest_zip/package
	@cp $(LAMBDA_DIR)/house_fd_ingest_zip/handler.py $(LAMBDA_DIR)/house_fd_ingest_zip/package/
	@cp -r ingestion/lib $(LAMBDA_DIR)/house_fd_ingest_zip/package/
	@cd $(LAMBDA_DIR)/house_fd_ingest_zip/package && zip -r ../function.zip . > /dev/null
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/house_fd_ingest_zip/function.zip"

package-index: ## Package house_fd_index_to_silver Lambda
	@echo "Packaging house_fd_index_to_silver..."
	@rm -rf $(LAMBDA_DIR)/house_fd_index_to_silver/package
	@mkdir -p $(LAMBDA_DIR)/house_fd_index_to_silver/package
	$(PIP) install -r $(LAMBDA_DIR)/house_fd_index_to_silver/requirements.txt -t $(LAMBDA_DIR)/house_fd_index_to_silver/package
	@cp $(LAMBDA_DIR)/house_fd_index_to_silver/handler.py $(LAMBDA_DIR)/house_fd_index_to_silver/package/
	@cp -r ingestion/lib $(LAMBDA_DIR)/house_fd_index_to_silver/package/
	@cd $(LAMBDA_DIR)/house_fd_index_to_silver/package && zip -r ../function.zip . > /dev/null
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/house_fd_index_to_silver/function.zip"

package-extract: ## Package house_fd_extract_document Lambda
	@echo "Packaging house_fd_extract_document..."
	@rm -rf $(LAMBDA_DIR)/house_fd_extract_document/package
	@mkdir -p $(LAMBDA_DIR)/house_fd_extract_document/package
	$(PIP) install -r $(LAMBDA_DIR)/house_fd_extract_document/requirements.txt -t $(LAMBDA_DIR)/house_fd_extract_document/package
	@cp $(LAMBDA_DIR)/house_fd_extract_document/handler.py $(LAMBDA_DIR)/house_fd_extract_document/package/
	@cp -r ingestion/lib $(LAMBDA_DIR)/house_fd_extract_document/package/
	@cd $(LAMBDA_DIR)/house_fd_extract_document/package && zip -r ../function.zip . > /dev/null
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/house_fd_extract_document/function.zip"

##@ Testing

test: ## Run all tests
	$(PYTEST) tests/ -v

test-unit: ## Run unit tests only
	$(PYTEST) tests/unit/ -v

test-integration: ## Run integration tests (requires AWS)
	$(PYTEST) tests/integration/ -v

test-cov: ## Run tests with coverage report
	$(PYTEST) tests/ --cov=ingestion --cov-report=html --cov-report=term
	@echo "✓ Coverage report generated in htmlcov/index.html"

##@ Code Quality

lint: ## Run linting (flake8, pylint)
	$(FLAKE8) ingestion/
	@echo "✓ Linting passed"

type-check: ## Run type checking (mypy)
	$(MYPY) ingestion/
	@echo "✓ Type checking passed"

format: ## Format code with black
	$(BLACK) ingestion/ tests/
	@echo "✓ Code formatted"

format-check: ## Check code formatting without modifying
	$(BLACK) --check ingestion/ tests/

check-all: format-check lint type-check test-unit ## Run all checks (format, lint, type, test)
	@echo "✓ All checks passed!"

##@ Data Operations

ingest-year: ## Ingest data for a specific year (usage: make ingest-year YEAR=2025)
	@if [ -z "$(YEAR)" ]; then \
		echo "Error: YEAR not specified. Usage: make ingest-year YEAR=2025"; \
		exit 1; \
	fi
	@echo "Triggering ingestion for year $(YEAR)..."
	aws lambda invoke \
		--function-name house-fd-ingest-zip \
		--payload '{"year": $(YEAR)}' \
		--cli-binary-format raw-in-base64-out \
		response.json
	@cat response.json | $(PYTHON) -m json.tool
	@rm response.json
	@echo "✓ Ingestion triggered for year $(YEAR)"

ingest-current: ## Ingest current year
	$(MAKE) ingest-year YEAR=$(shell date +%Y)

check-extraction-queue: ## Check SQS extraction queue status
	@echo "Checking extraction queue status..."
	aws sqs get-queue-attributes \
		--queue-url $$(aws sqs get-queue-url --queue-name house-fd-extract-queue --query 'QueueUrl' --output text) \
		--attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible
	@echo "✓ Queue status retrieved"

##@ Documentation

docs: ## Build documentation (if using Sphinx or similar)
	@echo "Building documentation..."
	@echo "✓ Documentation built (placeholder - add doc generation here)"

serve-docs: ## Serve documentation locally
	@echo "Serving documentation at http://localhost:8000"
	@cd docs && $(PYTHON) -m http.server 8000

##@ Cleanup

clean: ## Clean temporary files and caches
	@echo "Cleaning temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@rm -rf htmlcov/ .coverage coverage.xml
	@echo "✓ Cleaned temporary files"

clean-packages: ## Clean Lambda package directories
	@echo "Cleaning Lambda packages..."
	@find $(LAMBDA_DIR) -type d -name "package" -exec rm -rf {} + 2>/dev/null || true
	@find $(LAMBDA_DIR) -type f -name "function.zip" -delete 2>/dev/null || true
	@echo "✓ Cleaned Lambda packages"

clean-all: clean clean-packages ## Clean everything including build artifacts

##@ Monitoring

logs-ingest: ## Tail logs for ingest Lambda
	aws logs tail /aws/lambda/house-fd-ingest-zip --follow

logs-index: ## Tail logs for index Lambda
	aws logs tail /aws/lambda/house-fd-index-to-silver --follow

logs-extract: ## Tail logs for extract Lambda
	aws logs tail /aws/lambda/house-fd-extract-document --follow

##@ Utilities

verify-aws: ## Verify AWS credentials are configured
	@aws sts get-caller-identity > /dev/null && echo "✓ AWS credentials valid" || echo "✗ AWS credentials invalid"

cost-estimate: ## Estimate monthly AWS costs (requires configured infrastructure)
	@echo "Estimating AWS costs..."
	@echo "S3 Storage: Use AWS Cost Explorer or 'aws ce get-cost-and-usage'"
	@echo "Lambda: Check CloudWatch metrics for invocation count"
	@echo "See docs/ARCHITECTURE.md for cost estimation details"

security-scan: ## Run basic security scan on code
	@echo "Running security scan..."
	@$(PYTHON) -m pip install bandit > /dev/null 2>&1 || true
	@$(PYTHON) -m bandit -r ingestion/ -ll || echo "Install bandit for security scanning: pip install bandit"

##@ Community & Contribution

contributors: ## Show top contributors
	@echo "Top contributors to this project:"
	@git shortlog -sn --all --no-merges | head -20

check-contrib: format-check lint test-unit ## Quick check before submitting PR
	@echo "✓ Pre-contribution checks passed!"
	@echo "Ready to commit. Don't forget to:"
	@echo "  1. Write clear commit messages"
	@echo "  2. Update documentation if needed"
	@echo "  3. Add tests for new features"

##@ Self-Hosting

self-host-setup: setup init ## Complete setup for self-hosting
	@echo ""
	@echo "==================================================================="
	@echo "Self-hosting setup complete! Next steps:"
	@echo "==================================================================="
	@echo "1. Edit .env and infra/terraform/terraform.tfvars with your config"
	@echo "2. Run 'make plan' to review infrastructure changes"
	@echo "3. Run 'make deploy' to create AWS resources"
	@echo "4. Run 'make ingest-year YEAR=2025' to start ingestion"
	@echo ""
	@echo "For detailed instructions, see docs/DEPLOYMENT.md"
	@echo "==================================================================="
