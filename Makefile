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
PYTHON := python3.11
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

fresh-start: setup init deploy-auto ## Complete fresh start: Setup -> Init -> Deploy -> Ingest 2025
	@echo "🚀 Starting Fresh Installation..."
	@$(MAKE) ingest-year YEAR=2025
	@echo "✓ Fresh start complete! Data is ingesting."

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

package-all: package-ingest package-index package-extract package-extract-structured package-seed package-seed-members package-quality ## Package all Lambda functions

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
	@rm -rf $(LAMBDA_DIR)/house_fd_index_to_silver/dist $(LAMBDA_DIR)/house_fd_index_to_silver/function.zip
	@mkdir -p $(LAMBDA_DIR)/house_fd_index_to_silver/dist
	$(PIP) install -r $(LAMBDA_DIR)/house_fd_index_to_silver/requirements.txt -t $(LAMBDA_DIR)/house_fd_index_to_silver/dist
	@cp $(LAMBDA_DIR)/house_fd_index_to_silver/handler.py $(LAMBDA_DIR)/house_fd_index_to_silver/dist/
	@cp -r $(LAMBDA_DIR)/house_fd_index_to_silver/schemas $(LAMBDA_DIR)/house_fd_index_to_silver/dist/
	@cp -r ingestion/lib $(LAMBDA_DIR)/house_fd_index_to_silver/dist/lib
	@cd $(LAMBDA_DIR)/house_fd_index_to_silver/dist && zip -r ../function.zip . > /dev/null
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/house_fd_index_to_silver/function.zip"

package-extract: ## Package house_fd_extract_document Lambda
	@echo "Packaging house_fd_extract_document..."
	@rm -rf $(LAMBDA_DIR)/house_fd_extract_document/dist $(LAMBDA_DIR)/house_fd_extract_document/function.zip
	@mkdir -p $(LAMBDA_DIR)/house_fd_extract_document/dist/
	$(PIP) install --platform manylinux2014_x86_64 --implementation cp --python-version 3.11 --only-binary=:all: --upgrade -r $(LAMBDA_DIR)/house_fd_extract_document/requirements.txt -t $(LAMBDA_DIR)/house_fd_extract_document/dist
	@cp $(LAMBDA_DIR)/house_fd_extract_document/handler.py $(LAMBDA_DIR)/house_fd_extract_document/dist/
	# Copy entire shared schemas directory to ensure all files are included
	@cp -r ingestion/schemas $(LAMBDA_DIR)/house_fd_extract_document/dist/
	@cp -r ingestion/lib $(LAMBDA_DIR)/house_fd_extract_document/dist/lib
	@cd $(LAMBDA_DIR)/house_fd_extract_document/dist && zip -r ../function.zip . > /dev/null
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/house_fd_extract_document/function.zip"

package-extract-structured: ## Package house_fd_extract_structured_code Lambda with all new extractors
	@echo "Packaging house_fd_extract_structured_code..."
	@rm -rf $(LAMBDA_DIR)/house_fd_extract_structured_code/package $(LAMBDA_DIR)/house_fd_extract_structured_code/function.zip
	@mkdir -p $(LAMBDA_DIR)/house_fd_extract_structured_code/package
	$(PIP) install -r $(LAMBDA_DIR)/house_fd_extract_structured_code/requirements.txt -t $(LAMBDA_DIR)/house_fd_extract_structured_code/package
	@cp $(LAMBDA_DIR)/house_fd_extract_structured_code/handler.py $(LAMBDA_DIR)/house_fd_extract_structured_code/package/
	# Copy entire shared lib with all new extractors
	@cp -r ingestion/lib $(LAMBDA_DIR)/house_fd_extract_structured_code/package/lib
	@cd $(LAMBDA_DIR)/house_fd_extract_structured_code/package && zip -r ../function.zip . > /dev/null
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/house_fd_extract_structured_code/function.zip"
	@ls -lh $(LAMBDA_DIR)/house_fd_extract_structured_code/function.zip | awk '{print "  Package size:", $$5}'

package-seed: ## Package gold_seed Lambda
	@echo "Packaging gold_seed..."
	@rm -rf $(LAMBDA_DIR)/gold_seed/package
	@mkdir -p $(LAMBDA_DIR)/gold_seed/package
	# gold_seed relies on AWS SDK for pandas Lambda layer; no local deps required
	@cp $(LAMBDA_DIR)/gold_seed/handler.py $(LAMBDA_DIR)/gold_seed/package/
	@cd $(LAMBDA_DIR)/gold_seed/package && zip -r ../function.zip . > /dev/null
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/gold_seed/function.zip"

package-seed-members: ## Package gold_seed_members Lambda
	@echo "Packaging gold_seed_members..."
	@rm -rf $(LAMBDA_DIR)/gold_seed_members/package
	@mkdir -p $(LAMBDA_DIR)/gold_seed_members/package
	$(PIP) install -r $(LAMBDA_DIR)/gold_seed_members/requirements.txt -t $(LAMBDA_DIR)/gold_seed_members/package
	@cp $(LAMBDA_DIR)/gold_seed_members/handler.py $(LAMBDA_DIR)/gold_seed_members/package/
	@cd $(LAMBDA_DIR)/gold_seed_members/package && zip -r ../function.zip . > /dev/null
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/gold_seed_members/function.zip"

package-quality: ## Package data_quality_validator Lambda
	@echo "Packaging data_quality_validator..."
	@rm -rf $(LAMBDA_DIR)/data_quality_validator/package
	@mkdir -p $(LAMBDA_DIR)/data_quality_validator/package
	$(PIP) install -r $(LAMBDA_DIR)/data_quality_validator/requirements.txt -t $(LAMBDA_DIR)/data_quality_validator/package
	@cp $(LAMBDA_DIR)/data_quality_validator/handler.py $(LAMBDA_DIR)/data_quality_validator/package/
	@mkdir -p $(LAMBDA_DIR)/data_quality_validator/package/ingestion
	@cp -r ingestion/lib $(LAMBDA_DIR)/data_quality_validator/package/ingestion/lib
	@cp -r ingestion/schemas $(LAMBDA_DIR)/data_quality_validator/package/ingestion/schemas
	@cd $(LAMBDA_DIR)/data_quality_validator/package && zip -r ../function.zip . > /dev/null
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/data_quality_validator/function.zip"

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

##@ Deployment

deploy-extractors: package-extract-structured ## Package and deploy extraction Lambda with new extractors
	@echo "Uploading house_fd_extract_structured_code to S3..."
	@aws s3 cp $(LAMBDA_DIR)/house_fd_extract_structured_code/function.zip \
		s3://congress-disclosures-standardized/lambda-deployments/house_fd_extract_structured_code/function.zip
	@echo "✓ Uploaded to S3"
	@echo "Applying Terraform to update Lambda function..."
	cd $(TERRAFORM_DIR) && terraform apply -target=aws_lambda_function.extract_structured_code -auto-approve
	@echo "✓ Extraction Lambda deployed with new extractors"

deploy-website: ## Deploy website to S3
	@echo "Deploying website to S3..."
	@aws s3 sync website/ s3://congress-disclosures-standardized/website/ --exclude "*.DS_Store" --exclude "*.bak"
	@echo "✓ Website deployed to s3://congress-disclosures-standardized/website/"
	@echo "  URL: https://congress-disclosures-standardized.s3.amazonaws.com/website/index.html"

deploy-all-lambdas: package-all ## Package and deploy all Lambdas
	@echo "Deploying all Lambda functions..."
	cd $(TERRAFORM_DIR) && terraform apply -auto-approve
	@echo "✓ All Lambdas deployed"

quick-deploy-extract: ## Quick dev cycle: package + deploy extract Lambda
	@echo "Quick deploying extract Lambda..."
	@make package-extract
	@aws lambda update-function-code \
		--function-name congress-disclosures-development-extract-document \
		--zip-file fileb://$(LAMBDA_DIR)/house_fd_extract_document/function.zip \
		--query 'LastUpdateStatus' --output text
	@echo "Waiting for deployment..."
	@sleep 5
	@aws lambda get-function \
		--function-name congress-disclosures-development-extract-document \
		--query 'Configuration.LastUpdateStatus' --output text
	@echo "✓ Extract Lambda deployed"

##@ Data Operations

ingest-year: ## Ingest data for a specific year (usage: make ingest-year YEAR=2025)
	@if [ -z "$(YEAR)" ]; then \
		echo "Error: YEAR not specified. Usage: make ingest-year YEAR=2025"; \
		exit 1; \
	fi
	@echo "Triggering ingestion for year $(YEAR)..."
	aws lambda invoke \
		--function-name congress-disclosures-development-ingest-zip \
		--payload '{"year": $(YEAR)}' \
		--cli-binary-format raw-in-base64-out \
		response.json
	@cat response.json | $(PYTHON) -m json.tool
	@rm response.json
	@echo "✓ Ingestion triggered for year $(YEAR)"

ingest-current: ## Ingest current year
	$(MAKE) ingest-year YEAR=$(shell date +%Y)

run-silver-pipeline: ## Run Silver pipeline on all Bronze PDFs (re-extract with new extractors)
	@echo "Running Silver pipeline on all Bronze files..."
	@echo "This will trigger extraction for all PDFs in Bronze layer"
	@$(PYTHON) scripts/run_silver_pipeline.py --yes
	@echo "✓ Silver pipeline triggered"

run-silver-test: ## Run Silver pipeline on limited PDFs (for testing)
	@echo "Running Silver pipeline on 10 PDFs (test mode)..."
	@$(PYTHON) scripts/run_silver_pipeline.py --yes --limit 10

aggregate-data: ## Generate all aggregated data files (manifests, transactions)
aggregate-data: ## Aggregate all filing types into Gold layer
	@echo "Aggregating data into Gold layer..."
	@$(PYTHON) scripts/build_bronze_manifest.py
	@$(PYTHON) scripts/generate_type_p_transactions.py
	@$(PYTHON) scripts/generate_type_a_assets.py
	@$(PYTHON) scripts/generate_type_t_terminations.py
	@$(PYTHON) scripts/sync_parquet_to_dynamodb.py
	@echo "Rebuilding Silver manifest (v2)..."
	@$(PYTHON) scripts/rebuild_silver_manifest.py
	@echo "Generating Silver manifest API..."
	@$(PYTHON) scripts/build_silver_manifest_api.py
	@echo "Building Gold Layer (Facts)..."
	@$(PYTHON) scripts/build_fact_filings.py
	@echo "Computing Gold Layer Aggregates..."
	@$(PYTHON) scripts/compute_agg_document_quality.py
	@$(PYTHON) scripts/compute_agg_member_trading_stats.py
	@$(PYTHON) scripts/compute_agg_trending_stocks.py
	@$(PYTHON) scripts/compute_agg_network_graph.py
	@echo "Generating Gold Layer Manifests..."
	@$(PYTHON) scripts/generate_document_quality_manifest.py
	@$(PYTHON) scripts/generate_all_gold_manifests.py
	@echo "Generating Pipeline Error Report..."
	@$(PYTHON) scripts/generate_pipeline_errors.py
	@echo "✓ Data aggregation complete"

pipeline: ## Smart Pipeline: End-to-end execution with interactive mode (Full/Incremental/Reprocess)
	@$(PYTHON) scripts/run_smart_pipeline.py

run-pipeline: pipeline ## Alias for pipeline
	@echo "✓ Pipeline executed via smart runner"

check-extraction-queue: ## Check SQS extraction queue status
	@echo "Checking extraction queue status..."
	@aws sqs get-queue-attributes \
		--queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-extract-queue \
		--attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible ApproximateNumberOfMessagesDelayed \
		--query 'Attributes' --output table
	@echo "✓ Queue status retrieved"

purge-extraction-queue: ## Purge extraction queue (clear all messages)
	@echo "⚠️  WARNING: This will delete ALL messages in the extraction queue!"
	@read -p "Are you sure? [y/N]: " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "Purging extraction queue..."
	@aws sqs purge-queue --queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-extract-queue
	@echo "✓ Extraction queue purged"

reset-pipeline: ## Reset pipeline (clear S3 silver/gold and purge queues)
	@echo "Resetting pipeline..."
	@$(PYTHON) scripts/reset_pipeline.py

reset-and-run-all: ## Full System Reset & Run: Deploy Infra -> Reset Data -> Run Pipeline -> Deploy Website
	@echo "⚠️  WARNING: This will DEPLOY infrastructure, DELETE ALL DATA, and RE-RUN the pipeline!"
	@read -p "Are you sure? [y/N]: " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "1. Deploying Infrastructure (Terraform)..."
	@$(MAKE) deploy-all-lambdas
	@echo "2. Resetting Data (Clearing S3 & Queues)..."
	@$(PYTHON) scripts/reset_pipeline.py --force --include-bronze
	@echo "3. Running Pipeline (Full Reset Mode)..."
	@$(PYTHON) scripts/run_smart_pipeline.py --mode full --year 2025
	@echo "4. Validating Pipeline Integrity..."
	@$(MAKE) validate-pipeline
	@echo "5. Deploying Website..."
	@$(MAKE) deploy-website
	@echo "✓ Full system reset and execution complete!"

validate-pipeline: ## Validate pipeline integrity (S3 vs XML, Tags, DLQ, Silver Layer)
	@echo "Validating pipeline integrity..."
	@$(PYTHON) scripts/validate_pipeline_integrity.py

purge-dlq: ## Purge dead letter queue
	@echo "Purging dead letter queue..."
	@aws sqs purge-queue --queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-extract-dlq
	@echo "✓ DLQ purged"

check-dlq: ## Check dead letter queue status
	@echo "Checking DLQ status..."
	@aws sqs get-queue-attributes \
		--queue-url https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-extract-dlq \
		--attribute-names ApproximateNumberOfMessages \
		--query 'Attributes.ApproximateNumberOfMessages' --output text | \
		xargs -I {} echo "Messages in DLQ: {}"

test-extractions: ## Test and validate extraction results by filing type
	@echo "Testing extraction results..."
	@$(PYTHON) scripts/test_extraction_results.py

update-pipeline-status: ## Generate pipeline status JSON for UI dashboard
	@echo "Generating pipeline status..."
	@mkdir -p website/data
	@$(PYTHON) scripts/get_pipeline_status.py > website/data/pipeline_status.json 2>&1
	@echo "✓ Pipeline status updated: website/data/pipeline_status.json"

upload-pipeline-status: update-pipeline-status ## Upload pipeline status to S3
	@echo "Uploading pipeline status to website..."
	@aws s3 cp website/data/pipeline_status.json s3://congress-disclosures-standardized/website/data/pipeline_status.json \
		--content-type application/json \
		--cache-control "max-age=30"
	@echo "✓ Pipeline status uploaded to S3"

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
	aws logs tail /aws/lambda/congress-disclosures-development-ingest-zip --follow

logs-index: ## Tail logs for index Lambda
	aws logs tail /aws/lambda/congress-disclosures-development-index-to-silver --follow

logs-extract: ## Tail logs for extract Lambda
	aws logs tail /aws/lambda/congress-disclosures-development-extract-document --follow

logs-extract-recent: ## Show recent extract Lambda logs (last 2min, errors + successes)
	@aws logs tail /aws/lambda/congress-disclosures-development-extract-document --since 2m --format short | grep -E "(Processing doc_id|Starting text extraction|validation failed|ERROR)" | tail -30

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
