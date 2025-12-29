.PHONY: help init plan deploy destroy test lint format clean package docs

# Default target
.DEFAULT_GOAL := help

# Load environment variables from .env if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Variables
# Version: 20251219175505
TERRAFORM_DIR := infra/terraform
LAMBDA_DIR := ingestion/lambdas
S3_BUCKET ?= congress-disclosures-standardized
PYTHON := python3.11
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
FLAKE8 := $(PYTHON) -m flake8
MYPY := $(PYTHON) -m mypy

# Ensure Terraform receives the Congress.gov API key from .env
# Terraform reads variables from TF_VAR_* env vars.
export TF_VAR_congress_gov_api_key := $(CONGRESS_GOV_API_KEY)

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

##@ Pipeline Execution

run-pipeline: ## Run full pipeline (silver → gold → website)
	@echo "🚀 Running full pipeline..."
	$(PYTHON) scripts/run_pipeline.py --all
	@echo "✓ Pipeline complete"

run-pipeline-silver: ## Run Silver layer transformation only
	$(PYTHON) scripts/run_pipeline.py --silver

run-pipeline-gold: ## Run Gold layer aggregation only
	$(PYTHON) scripts/run_pipeline.py --gold

run-pipeline-website: ## Regenerate website static data (ISR)
	$(PYTHON) scripts/run_pipeline.py --website

run-pipeline-full: ## Full clean refresh (requires PIPELINE_CONFIRM_CLEAN=YES)
	$(PYTHON) scripts/run_pipeline.py --all --clean --audit

run-pipeline-dry: ## Show what pipeline would run
	$(PYTHON) scripts/run_pipeline.py --all --dry-run

##@ Local Emulator (Development)

local-ingest: ## Download data locally (no AWS)
	@echo "🏠 Downloading data locally..."
	$(PYTHON) scripts/local_ingestion.py --year 2025 --limit-pdfs 50

local-ingest-full: ## Download ALL data locally (large download!)
	@echo "🏠 Downloading ALL data locally (this may take a while)..."
	$(PYTHON) scripts/local_ingestion.py --year 2025 --limit-pdfs 0

local-ingest-sample: ## Download small sample (10 PDFs)
	@echo "🏠 Downloading sample data..."
	$(PYTHON) scripts/local_ingestion.py --year 2025 --limit-pdfs 10 --limit-bills 5 --limit-lobbying 5

local-sync: ## Sync ALL S3 data to local_data/ (mirrors your S3 bucket)
	@echo "📦 Syncing S3 data to local_data/..."
	$(PYTHON) scripts/sync_s3_to_local.py --layer all --source all

local-sync-bronze: ## Sync only Bronze layer from S3
	@echo "📦 Syncing Bronze layer..."
	$(PYTHON) scripts/sync_s3_to_local.py --layer bronze

local-sync-sample: ## Sync small sample from S3 (100 files)
	@echo "📦 Syncing sample data..."
	$(PYTHON) scripts/sync_s3_to_local.py --max-files 100

local-sync-year: ## Sync specific year from S3 (usage: make local-sync-year YEAR=2025)
	@echo "📦 Syncing year $(YEAR)..."
	$(PYTHON) scripts/sync_s3_to_local.py --year $(YEAR)

local-sync-dry-run: ## Show what would be synced (no download)
	@echo "🔍 Dry run - showing what would be synced..."
	$(PYTHON) scripts/sync_s3_to_local.py --dry-run

local-view: ## View local data structure
	@echo "📊 Local data structure:"
	@if command -v tree > /dev/null; then \
		tree -L 3 local_data; \
	else \
		find local_data -maxdepth 3 -type d; \
	fi

local-serve: ## Start HTTP server to browse local data
	@echo "📡 Starting local data viewer at http://localhost:8000"
	@echo "   Press Ctrl+C to stop"
	@cd local_data && $(PYTHON) -m http.server 8000

local-clean: ## Clean local data directory
	@echo "🧹 Cleaning local data..."
	@rm -rf local_data
	@mkdir -p local_data
	@echo "✓ Local data cleaned"

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
	@bash scripts/sync_terraform_outputs.sh
	@echo "✓ Infrastructure deployed and .env synced"

deploy-auto: ## Deploy infrastructure without confirmation (use in CI)
	cd $(TERRAFORM_DIR) && terraform apply -auto-approve
	@bash scripts/sync_terraform_outputs.sh
	@echo "✓ Infrastructure deployed and .env synced"

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

package-all: package-ingest package-index package-extract package-extract-structured package-seed package-seed-members package-quality package-lda-ingest package-api package-pipeline-metrics package-check-house-fd package-check-congress package-check-lobbying package-compute-member-stats package-compute-bill-trade-correlations ## Package all Lambda functions


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
	@cp $(LAMBDA_DIR)/house_fd_extract_document/package/handler.py $(LAMBDA_DIR)/house_fd_extract_document/dist/
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

package-lda-ingest: ## Package lda_ingest_filings Lambda
	@echo "Packaging lda_ingest_filings..."
	@rm -rf $(LAMBDA_DIR)/lda_ingest_filings/package
	@mkdir -p $(LAMBDA_DIR)/lda_ingest_filings/package
	$(PIP) install -r $(LAMBDA_DIR)/lda_ingest_filings/requirements.txt -t $(LAMBDA_DIR)/lda_ingest_filings/package
	@cp $(LAMBDA_DIR)/lda_ingest_filings/handler.py $(LAMBDA_DIR)/lda_ingest_filings/package/
	@mkdir -p $(LAMBDA_DIR)/lda_ingest_filings/package/ingestion
	@cp -r ingestion/lib $(LAMBDA_DIR)/lda_ingest_filings/package/ingestion/lib
	@cd $(LAMBDA_DIR)/lda_ingest_filings/package && zip -r ../function.zip . > /dev/null
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/lda_ingest_filings/function.zip"

package-api: ## Package all API Lambda functions
	@echo "Packaging all API Lambdas..."
	@bash scripts/package_api_lambdas.sh

package-congress-fetch: ## Package congress_api_fetch_entity Lambda
	@echo "Packaging congress_api_fetch_entity..."
	@rm -rf $(LAMBDA_DIR)/congress_api_fetch_entity/package $(LAMBDA_DIR)/congress_api_fetch_entity/function.zip
	@mkdir -p $(LAMBDA_DIR)/congress_api_fetch_entity/package
	$(PIP) install -r $(LAMBDA_DIR)/congress_api_fetch_entity/requirements.txt -t $(LAMBDA_DIR)/congress_api_fetch_entity/package
	@cp $(LAMBDA_DIR)/congress_api_fetch_entity/handler.py $(LAMBDA_DIR)/congress_api_fetch_entity/package/
	@cp -r ingestion/lib $(LAMBDA_DIR)/congress_api_fetch_entity/package/lib
	@cd $(LAMBDA_DIR)/congress_api_fetch_entity/package && zip -r ../function.zip . > /dev/null
	@rm -rf $(LAMBDA_DIR)/congress_api_fetch_entity/package
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/congress_api_fetch_entity/function.zip"
	@ls -lh $(LAMBDA_DIR)/congress_api_fetch_entity/function.zip | awk '{print "  Package size:", $$5}'

package-congress-silver: ## Package congress_bronze_to_silver Lambda
	@echo "Packaging congress_bronze_to_silver..."
	@rm -rf $(LAMBDA_DIR)/congress_bronze_to_silver/package $(LAMBDA_DIR)/congress_bronze_to_silver/function.zip
	@mkdir -p $(LAMBDA_DIR)/congress_bronze_to_silver/package
	@# Install Linux-compatible binaries for deps (jsonschema/rpds-py)
	$(PIP) install \
		--platform manylinux2014_x86_64 \
		--target $(LAMBDA_DIR)/congress_bronze_to_silver/package \
		--implementation cp \
		--python-version 3.11 \
		--only-binary=:all: --upgrade \
		-r $(LAMBDA_DIR)/congress_bronze_to_silver/requirements.txt
	@cp $(LAMBDA_DIR)/congress_bronze_to_silver/handler.py $(LAMBDA_DIR)/congress_bronze_to_silver/package/
	@cp -r ingestion/lib $(LAMBDA_DIR)/congress_bronze_to_silver/package/lib
	@cd $(LAMBDA_DIR)/congress_bronze_to_silver/package && zip -r ../function.zip . > /dev/null
	@rm -rf $(LAMBDA_DIR)/congress_bronze_to_silver/package
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/congress_bronze_to_silver/function.zip"
	@ls -lh $(LAMBDA_DIR)/congress_bronze_to_silver/function.zip | awk '{print "  Package size:", $$5}'

package-pipeline-metrics: ## Package publish_pipeline_metrics Lambda
	@echo "Packaging publish_pipeline_metrics..."
	@rm -rf $(LAMBDA_DIR)/publish_pipeline_metrics/package $(LAMBDA_DIR)/publish_pipeline_metrics/function.zip
	@mkdir -p $(LAMBDA_DIR)/publish_pipeline_metrics/package
	@cp $(LAMBDA_DIR)/publish_pipeline_metrics/handler.py $(LAMBDA_DIR)/publish_pipeline_metrics/package/
	@cd $(LAMBDA_DIR)/publish_pipeline_metrics/package && $(PYTHON) ../../../../scripts/deterministic_zip.py . ../function.zip > /dev/null
	@rm -rf $(LAMBDA_DIR)/publish_pipeline_metrics/package
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/publish_pipeline_metrics/function.zip"

package-check-house-fd: ## Package check_house_fd_updates Lambda
	@echo "Packaging check_house_fd_updates..."
	@rm -rf $(LAMBDA_DIR)/check_house_fd_updates/package $(LAMBDA_DIR)/check_house_fd_updates/function.zip
	@mkdir -p $(LAMBDA_DIR)/check_house_fd_updates/package
	@cp $(LAMBDA_DIR)/check_house_fd_updates/handler.py $(LAMBDA_DIR)/check_house_fd_updates/package/
	@cd $(LAMBDA_DIR)/check_house_fd_updates/package && zip -r ../function.zip . > /dev/null
	@rm -rf $(LAMBDA_DIR)/check_house_fd_updates/package
	@aws s3 cp $(LAMBDA_DIR)/check_house_fd_updates/function.zip s3://$(S3_BUCKET)/lambda-deployments/check_house_fd_updates/function.zip
	@echo "✓ Lambda package created and uploaded"

package-check-congress: ## Package check_congress_updates Lambda
	@echo "Packaging check_congress_updates..."
	@rm -rf $(LAMBDA_DIR)/check_congress_updates/package $(LAMBDA_DIR)/check_congress_updates/function.zip
	@mkdir -p $(LAMBDA_DIR)/check_congress_updates/package
	@cp $(LAMBDA_DIR)/check_congress_updates/handler.py $(LAMBDA_DIR)/check_congress_updates/package/
	@cd $(LAMBDA_DIR)/check_congress_updates/package && zip -r ../function.zip . > /dev/null
	@rm -rf $(LAMBDA_DIR)/check_congress_updates/package
	@aws s3 cp $(LAMBDA_DIR)/check_congress_updates/function.zip s3://$(S3_BUCKET)/lambda-deployments/check_congress_updates/function.zip
	@echo "✓ Lambda package created and uploaded"

package-check-lobbying: ## Package check_lobbying_updates Lambda
	@echo "Packaging check_lobbying_updates..."
	@rm -rf $(LAMBDA_DIR)/check_lobbying_updates/package $(LAMBDA_DIR)/check_lobbying_updates/function.zip
	@mkdir -p $(LAMBDA_DIR)/check_lobbying_updates/package
	@cp $(LAMBDA_DIR)/check_lobbying_updates/handler.py $(LAMBDA_DIR)/check_lobbying_updates/package/
	@cd $(LAMBDA_DIR)/check_lobbying_updates/package && zip -r ../function.zip . > /dev/null
	@rm -rf $(LAMBDA_DIR)/check_lobbying_updates/package
	@aws s3 cp $(LAMBDA_DIR)/check_lobbying_updates/function.zip s3://$(S3_BUCKET)/lambda-deployments/check_lobbying_updates/function.zip
	@echo "✓ Lambda package created and uploaded"

package-compute-member-stats: ## Package compute_member_stats Lambda
	@echo "Packaging compute_member_stats..."
	@rm -rf $(LAMBDA_DIR)/compute_member_stats/package $(LAMBDA_DIR)/compute_member_stats/function.zip
	@mkdir -p $(LAMBDA_DIR)/compute_member_stats/package
	@cp $(LAMBDA_DIR)/compute_member_stats/handler.py $(LAMBDA_DIR)/compute_member_stats/package/
	@cd $(LAMBDA_DIR)/compute_member_stats/package && zip -r ../function.zip . > /dev/null
	@rm -rf $(LAMBDA_DIR)/compute_member_stats/package
	@aws s3 cp $(LAMBDA_DIR)/compute_member_stats/function.zip s3://$(S3_BUCKET)/lambda-deployments/compute_member_stats/function.zip
	@echo "✓ Lambda package created and uploaded"

package-compute-bill-trade-correlations: ## Package compute_bill_trade_correlations Lambda
	@echo "Packaging compute_bill_trade_correlations..."
	@rm -rf $(LAMBDA_DIR)/compute_bill_trade_correlations/package $(LAMBDA_DIR)/compute_bill_trade_correlations/function.zip
	@mkdir -p $(LAMBDA_DIR)/compute_bill_trade_correlations/package
	@cp $(LAMBDA_DIR)/compute_bill_trade_correlations/handler.py $(LAMBDA_DIR)/compute_bill_trade_correlations/package/
	@cd $(LAMBDA_DIR)/compute_bill_trade_correlations/package && zip -r ../function.zip . > /dev/null
	@rm -rf $(LAMBDA_DIR)/compute_bill_trade_correlations/package
	@aws s3 cp $(LAMBDA_DIR)/compute_bill_trade_correlations/function.zip s3://$(S3_BUCKET)/lambda-deployments/compute_bill_trade_correlations/function.zip
	@echo "✓ Lambda package created and uploaded"

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

fix-lobbying: ## Fix lobbying pipeline (run all Silver + Gold scripts, usage: make fix-lobbying YEAR=2025)
	@echo "🔧 Fixing lobbying pipeline..."
	$(PYTHON) scripts/fix_lobbying_pipeline.py --year $(or $(YEAR),2025)

deploy-extractors: package-extract-structured ## Package and deploy extraction Lambda with new extractors
	@echo "Uploading house_fd_extract_structured_code to S3..."
	@aws s3 cp $(LAMBDA_DIR)/house_fd_extract_structured_code/function.zip \
		s3://congress-disclosures-standardized/lambda-deployments/house_fd_extract_structured_code/function.zip
	@echo "✓ Uploaded to S3"
	@echo "Applying Terraform to update Lambda function..."
	cd $(TERRAFORM_DIR) && terraform apply -target=aws_lambda_function.extract_structured_code -auto-approve
	@echo "✓ Extraction Lambda deployed with new extractors"

deploy-website: ## Deploy website to S3 (regenerates all analytics data first)
	@echo "🔄 Syncing API Gateway URL from Terraform..."
	@./scripts/sync-api-url.sh
	@echo ""
	@echo "📊 Regenerating analytics data..."
	@echo "  → Document quality..."
	@$(PYTHON) scripts/compute_agg_document_quality.py
	@echo "  → Member trading stats..."
	@$(PYTHON) scripts/compute_agg_member_trading_stats.py
	@echo "  → Trending stocks..."
	@$(PYTHON) scripts/compute_agg_trending_stocks.py
	@echo "  → Network graph..."
	@$(PYTHON) scripts/compute_agg_network_graph.py
	@echo "  → Generating manifests..."
	@$(PYTHON) scripts/generate_document_quality_manifest.py
	@$(PYTHON) scripts/generate_all_gold_manifests.py
	@echo "✅ Analytics data regenerated"
	@echo ""
	@echo "🚀 Deploying website to S3..."
	@aws s3 sync website/ s3://congress-disclosures-standardized/website/ --exclude "*.DS_Store" --exclude "*.bak"
	@aws s3 cp docs/openapi.yaml s3://congress-disclosures-standardized/docs/openapi.yaml --content-type "application/x-yaml"
	@echo "✓ Website deployed to s3://congress-disclosures-standardized/website/"
	@echo "  URL: https://congress-disclosures-standardized.s3.amazonaws.com/website/index.html"
	@echo "✓ API Docs deployed to s3://congress-disclosures-standardized/website/api-docs/"
	@echo "  URL: https://congress-disclosures-standardized.s3.amazonaws.com/website/api-docs/index.html"

##@ Next.js Website (New Frontend)

build-nextjs: ## Build Next.js static export
	@echo "📦 Building Next.js static export..."
	@cd website && npm run build
	@echo "✓ Next.js build complete in website/out/"

build-bill-isr: ## Pre-generate ISR JSON files for archived congresses (115-118)
	@echo "🔄 Pre-generating bill detail ISR files..."
	@$(PYTHON) scripts/build_bill_detail_pages.py --congress 115 116 117 118 --output-dir website/out/data/bill_details
	@echo "✓ ISR files generated"

build-bill-isr-test: ## Test ISR generation (10 bills from Congress 118 only)
	@echo "🧪 Testing ISR generation..."
	@$(PYTHON) scripts/build_bill_detail_pages.py --congress 118 --limit 10 --output-dir website/out/data/bill_details
	@echo "✓ Test ISR files generated"

deploy-website: build-nextjs build-bill-isr ## Build and deploy Next.js website to S3
	@echo "🚀 Deploying Next.js website to S3..."
	@aws s3 sync website/out/ s3://congress-disclosures-standardized/website/ --exclude "*.DS_Store" --delete
	@echo "✓ Next.js website deployed to s3://congress-disclosures-standardized/website/"


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

quick-deploy-ingest: ## Quick dev cycle: package + deploy ingest Lambda
	@echo "Quick deploying ingest Lambda..."
	@make package-ingest
	@aws lambda update-function-code \
		--function-name congress-disclosures-development-ingest-zip \
		--zip-file fileb://$(LAMBDA_DIR)/house_fd_ingest_zip/function.zip \
		--query 'LastUpdateStatus' --output text
	@echo "Waiting for deployment..."
	@sleep 5
	@aws lambda get-function \
		--function-name congress-disclosures-development-ingest-zip \
		--query 'Configuration.LastUpdateStatus' --output text
	@echo "✓ Ingest Lambda deployed"

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
	@$(PYTHON) scripts/generate_type_t_terminations.py
	@$(PYTHON) scripts/sync_parquet_to_dynamodb.py
	@echo "Building Dimensions..."
	@$(PYTHON) scripts/build_dim_members_simple.py
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
	@echo "Computing Bills & Congress Analytics..."
	@$(PYTHON) scripts/analyze_bill_industry_impact.py || echo "  ⚠️  Bill industry analysis skipped (may need data)"
	@$(PYTHON) scripts/compute_agg_bill_trade_correlation.py || echo "  ⚠️  Bill-trade correlation skipped (may need data)"
	@$(PYTHON) scripts/congress_build_agg_bill_latest_action.py || echo "  ⚠️  Bill latest action skipped (may need data)"
	@echo "Computing Lobbying Analytics..."
	@$(PYTHON) scripts/compute_agg_bill_lobbying_correlation.py || echo "  ⚠️  Bill-lobbying correlation skipped (may need data)"
	@$(PYTHON) scripts/compute_agg_member_lobbyist_network.py || echo "  ⚠️  Member-lobbyist network skipped (may need data)"
	@$(PYTHON) scripts/compute_agg_triple_correlation.py || echo "  ⚠️  Triple correlation skipped (may need data)"
	@$(PYTHON) scripts/compute_lobbying_network_metrics.py 2024 || echo "  ⚠️  Network metrics skipped (may need data)"
	@echo "Generating Gold Layer Manifests..."
	@$(PYTHON) scripts/generate_document_quality_manifest.py
	@$(PYTHON) scripts/generate_all_gold_manifests.py
	@echo "Generating Pipeline Error Report..."
	@$(PYTHON) scripts/generate_pipeline_errors.py
	@echo "✓ Data aggregation complete"

##@ Congress Ingestion

ingest-congress-bill-subresources: ## Trigger ingestion of bill subresources (cosponsors, actions, committees, subjects)
	@echo "Triggering bill subresource ingestion..."
	@if [ -z "$(CONGRESS)" ]; then \
		echo "Error: CONGRESS variable required. Usage: make ingest-congress-bill-subresources CONGRESS=118"; \
		exit 1; \
	fi
	@$(PYTHON) scripts/trigger_bill_subresource_ingestion.py --congress $(CONGRESS)

ingest-congress-bill-subresources-test: ## Test bill subresource ingestion (10 bills only)
	@echo "Testing bill subresource ingestion (10 bills)..."
	@if [ -z "$(CONGRESS)" ]; then \
		echo "Error: CONGRESS variable required. Usage: make ingest-congress-bill-subresources-test CONGRESS=118"; \
		exit 1; \
	fi
	@$(PYTHON) scripts/trigger_bill_subresource_ingestion.py --congress $(CONGRESS) --limit 10

##@ Congress Silver Layer

build-congress-silver-cosponsors: ## Build Congress Silver bill_cosponsors from Bronze
	@echo "Building Congress Silver bill_cosponsors..."
	@$(PYTHON) scripts/congress_build_silver_bill_cosponsors.py

build-congress-silver-actions: ## Build Congress Silver bill_actions from Bronze
	@echo "Building Congress Silver bill_actions..."
	@$(PYTHON) scripts/congress_build_silver_bill_actions.py

build-congress-silver-bills: build-congress-silver-cosponsors build-congress-silver-actions ## Build all Congress bill Silver tables
	@echo "✓ Congress bill Silver layer build complete"

##@ Congress Gold Layer

build-congress-gold-member: ## Build Congress Gold dim_member from Silver
	@echo "Building Congress Gold dim_member..."
	@$(PYTHON) scripts/congress_build_dim_member.py

build-congress-gold-bill: ## Build Congress Gold dim_bill from Silver
	@echo "Building Congress Gold dim_bill..."
	@$(PYTHON) scripts/congress_build_dim_bill.py

build-congress-gold-fact: ## Build Congress Gold fact_member_bill_role from Silver
	@echo "Building Congress Gold fact_member_bill_role..."
	@$(PYTHON) scripts/congress_build_fact_member_bill_role.py

build-congress-gold-agg-latest-action: ## Build Congress Gold agg_bill_latest_action from Silver
	@echo "Building Congress Gold agg_bill_latest_action..."
	@$(PYTHON) scripts/congress_build_agg_bill_latest_action.py

build-congress-gold: build-congress-gold-member build-congress-gold-bill build-congress-gold-fact build-congress-gold-agg-latest-action ## Build all Congress Gold tables
	@echo "✓ Congress Gold layer build complete"

##@ Congress Analytics (FD-Congress Correlation)

build-congress-analytics-trade-windows: ## Analyze member trades around bill actions
	@echo "Building trade window analysis..."
	@$(PYTHON) scripts/congress_build_analytics_trade_windows.py

build-congress-analytics-stock-activity: ## Build stock-level congress activity
	@echo "Building stock congress activity..."
	@$(PYTHON) scripts/congress_build_analytics_stock_activity.py

build-congress-member-stats: ## Compute member legislative + trading stats
	@echo "Computing member stats..."
	@$(PYTHON) scripts/congress_compute_agg_member_stats.py

build-congress-analytics: build-congress-analytics-trade-windows build-congress-analytics-stock-activity build-congress-member-stats ## Build all Congress analytics
	@echo "✓ Congress analytics build complete"

##@ Bill Industry & Correlation Analysis (Epic 2)

analyze-bill-industry: ## Analyze bills for industry impact and generate tags
	@echo "Analyzing bills for industry impact..."
	@$(PYTHON) scripts/analyze_bill_industry_impact.py

analyze-bill-industry-congress: ## Analyze specific congress only (Usage: CONGRESS=118)
	@echo "Analyzing congress $(CONGRESS) bills..."
	@$(PYTHON) scripts/analyze_bill_industry_impact.py --congress $(CONGRESS)

analyze-bill-industry-test: ## Test industry analysis (first 10 bills)
	@echo "Testing industry analysis..."
	@$(PYTHON) scripts/analyze_bill_industry_impact.py --test

compute-bill-trade-correlation: ## Compute bill-trade correlation scores
	@echo "Computing bill-trade correlations..."
	@$(PYTHON) scripts/compute_agg_bill_trade_correlation.py

compute-bill-trade-correlation-congress: ## Compute correlations for specific congress (Usage: CONGRESS=118)
	@echo "Computing correlations for congress $(CONGRESS)..."
	@$(PYTHON) scripts/compute_agg_bill_trade_correlation.py --congress $(CONGRESS)

compute-bill-trade-correlation-strict: ## Compute correlations with stricter threshold (min score 40)
	@echo "Computing correlations (strict threshold)..."
	@$(PYTHON) scripts/compute_agg_bill_trade_correlation.py --min-score 40

build-bill-correlation-pipeline: analyze-bill-industry compute-bill-trade-correlation ## Full Epic 2 pipeline (industry + correlation)
	@echo "✓ Bill correlation pipeline complete"

##@ Congress Pipeline Orchestration

run-congress-pipeline: ## Run Congress pipeline (aggregate mode by default)
	@$(PYTHON) scripts/run_congress_pipeline.py --mode aggregate

run-congress-pipeline-full: ## Run full Congress pipeline (ingestion + processing)
	@$(PYTHON) scripts/run_congress_pipeline.py --mode full --congress 118

run-congress-pipeline-incremental: ## Run incremental Congress pipeline
	@$(PYTHON) scripts/run_congress_pipeline.py --mode incremental

pipeline: ## Smart Pipeline: End-to-end execution with interactive mode (Full/Incremental/Reprocess)
	@$(PYTHON) scripts/run_smart_pipeline.py

incremental: ## True Incremental Pipeline: Only process NEW data since last run (RECOMMENDED)
	@$(PYTHON) scripts/run_true_incremental_pipeline.py

incremental-force: ## Force incremental pipeline (treat as first run)
	@$(PYTHON) scripts/run_true_incremental_pipeline.py --force

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

##@ Lobbying Data Integration (Epic 5)

ingest-lobbying-filings: ## Ingest LDA lobbying filings (Usage: make ingest-lobbying-filings YEAR=2024)
	@if [ -z "$(YEAR)" ]; then \
		echo "Error: YEAR variable required. Usage: make ingest-lobbying-filings YEAR=2024"; \
		exit 1; \
	fi
	@echo "Ingesting lobbying filings for $(YEAR)..."
	@$(PYTHON) scripts/trigger_lda_ingestion.py --year $(YEAR) --type filings

ingest-lobbying-contributions: ## Ingest LDA political contributions (Usage: make ingest-lobbying-contributions YEAR=2024)
	@if [ -z "$(YEAR)" ]; then \
		echo "Error: YEAR variable required. Usage: make ingest-lobbying-contributions YEAR=2024"; \
		exit 1; \
	fi
	@echo "Ingesting lobbying contributions for $(YEAR)..."
	@$(PYTHON) scripts/trigger_lda_ingestion.py --year $(YEAR) --type contributions

ingest-lobbying-all: ## Ingest both filings and contributions (Usage: make ingest-lobbying-all YEAR=2024)
	@if [ -z "$(YEAR)" ]; then \
		echo "Error: YEAR variable required. Usage: make ingest-lobbying-all YEAR=2024"; \
		exit 1; \
	fi
	@echo "Ingesting all lobbying data for $(YEAR)..."
	@$(PYTHON) scripts/trigger_lda_ingestion.py --year $(YEAR) --type all

build-lobbying-silver-filings: ## Build lobbying Silver filings table
	@echo "Building lobbying Silver filings..."
	@$(PYTHON) scripts/lobbying_build_silver_filings.py

build-lobbying-silver-registrants: ## Build lobbying Silver registrants table
	@echo "Building lobbying Silver registrants..."
	@$(PYTHON) scripts/lobbying_build_silver_registrants.py

build-lobbying-silver-clients: ## Build lobbying Silver clients table
	@echo "Building lobbying Silver clients..."
	@$(PYTHON) scripts/lobbying_build_silver_clients.py

build-lobbying-silver-lobbyists: ## Build lobbying Silver lobbyists table
	@echo "Building lobbying Silver lobbyists..."
	@$(PYTHON) scripts/lobbying_build_silver_lobbyists.py

build-lobbying-silver-activities: ## Build lobbying Silver activities table
	@echo "Building lobbying Silver activities..."
	@$(PYTHON) scripts/lobbying_build_silver_activities.py

build-lobbying-silver-government-entities: ## Build lobbying Silver government_entities table
	@echo "Building lobbying Silver government_entities..."
	@$(PYTHON) scripts/lobbying_build_silver_government_entities.py

build-lobbying-silver-activity-bills: ## Build lobbying Silver activity_bills table (NLP extraction)
	@echo "Building lobbying Silver activity_bills..."
	@$(PYTHON) scripts/lobbying_build_silver_activity_bills.py

build-lobbying-silver-contributions: ## Build lobbying Silver contributions table
	@echo "Building lobbying Silver contributions..."
	@$(PYTHON) scripts/lobbying_build_silver_contributions.py

build-lobbying-silver-all: build-lobbying-silver-filings build-lobbying-silver-registrants build-lobbying-silver-clients build-lobbying-silver-lobbyists build-lobbying-silver-activities build-lobbying-silver-government-entities build-lobbying-silver-activity-bills build-lobbying-silver-contributions ## Build all lobbying Silver tables
	@echo "✓ Lobbying Silver layer build complete"

build-lobbying-gold-fact: ## Build lobbying Gold fact_lobbying_activity
	@echo "Building lobbying Gold fact_lobbying_activity..."
	@$(PYTHON) scripts/lobbying_build_fact_activity.py

build-lobbying-gold-dim-client: ## Build lobbying Gold dim_client
	@echo "Building lobbying Gold dim_client..."
	@$(PYTHON) scripts/lobbying_build_dim_client.py

build-lobbying-gold-dim-registrant: ## Build lobbying Gold dim_registrant
	@echo "Building lobbying Gold dim_registrant..."
	@$(PYTHON) scripts/lobbying_build_dim_registrant.py

build-lobbying-gold-dim-lobbyist: ## Build lobbying Gold dim_lobbyist
	@echo "Building lobbying Gold dim_lobbyist..."
	@$(PYTHON) scripts/lobbying_build_dim_lobbyist.py

build-lobbying-gold-all: build-lobbying-gold-fact build-lobbying-gold-dim-client build-lobbying-gold-dim-registrant build-lobbying-gold-dim-lobbyist ## Build all lobbying Gold tables
	@echo "✓ Lobbying Gold layer build complete"

compute-lobbying-bill-correlation: ## Compute bill-lobbying correlation aggregate
	@echo "Computing bill-lobbying correlations..."
	@$(PYTHON) scripts/compute_agg_bill_lobbying_correlation.py

compute-lobbying-member-network: ## Compute member-lobbyist network aggregate
	@echo "Computing member-lobbyist network..."
	@$(PYTHON) scripts/compute_agg_member_lobbyist_network.py

compute-lobbying-triple-correlation: ## Compute triple correlation (Trade-Bill-Lobbying) - STAR FEATURE
	@echo "Computing triple correlations..."
	@$(PYTHON) scripts/compute_agg_triple_correlation.py

compute-lobbying-network-metrics: ## Compute social network analysis metrics (centrality, communities, influence)
	@echo "Computing lobbying network metrics..."
	@$(PYTHON) scripts/compute_lobbying_network_metrics.py 2024

compute-lobbying-all: compute-lobbying-bill-correlation compute-lobbying-member-network compute-lobbying-triple-correlation compute-lobbying-network-metrics ## Compute all lobbying aggregates
	@echo "✓ Lobbying aggregates computation complete"

build-lobbying-pipeline: build-lobbying-silver-all build-lobbying-gold-all compute-lobbying-all ## Full lobbying data pipeline (Silver → Gold → Aggregates)
	@echo "✓ Full lobbying pipeline complete"

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

# API Lambdas
API_LAMBDAS = get_members get_member get_member_trades get_member_portfolio \
              get_trades get_stock get_stock_activity get_stocks \
              get_top_traders get_trending_stocks get_sector_activity \
              get_compliance get_trading_timeline get_summary \
              search get_filings get_filing get_aws_costs

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

verify-api: ## Verify API health (30+ endpoints)
	@echo "🏥 Running API health checks..."
	@$(PYTHON) scripts/verify_api_health.py

verify-api-critical: ## Verify critical API endpoints only
	@echo "🔴 Checking critical endpoints..."
	@$(PYTHON) scripts/verify_api_health.py --critical-only

verify-api-version: ## Verify /v1/version endpoint returns correct version
	@echo "🔍 Checking API version..."
	@$(PYTHON) scripts/verify_api_health.py --endpoint /v1/version

verify-gold: ## Validate Gold layer data integrity
	@echo "💎 Validating Gold layer..."
	@$(PYTHON) scripts/validate_gold_layer.py

verify-gold-strict: ## Validate Gold layer (fail on warnings)
	@echo "💎 Validating Gold layer (strict mode)..."
	@$(PYTHON) scripts/validate_gold_layer.py --strict

audit-handlers: ## Audit all Lambda handlers for response patterns
	@echo "🔍 Auditing Lambda handlers..."
	@$(PYTHON) scripts/audit_response_patterns.py

audit-handlers-json: ## Audit handlers and output JSON
	@$(PYTHON) scripts/audit_response_patterns.py --json

verify-deployment: verify-api verify-gold audit-handlers ## Complete deployment verification
	@echo ""
	@echo "✅ DEPLOYMENT VERIFICATION COMPLETE"
	@echo "   - API health checks passed"
	@echo "   - Gold layer validated"
	@echo "   - Handler audit passed"

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

package-congress-orchestrator: ## Package Congress Orchestrator Lambda
	@echo "Packaging Congress Orchestrator Lambda..."
	@rm -rf $(LAMBDA_DIR)/congress_api_ingest_orchestrator/package $(LAMBDA_DIR)/congress_api_ingest_orchestrator/function.zip
	@mkdir -p $(LAMBDA_DIR)/congress_api_ingest_orchestrator/package
	$(PIP) install -r $(LAMBDA_DIR)/congress_api_ingest_orchestrator/requirements.txt -t $(LAMBDA_DIR)/congress_api_ingest_orchestrator/package
	@cp $(LAMBDA_DIR)/congress_api_ingest_orchestrator/handler.py $(LAMBDA_DIR)/congress_api_ingest_orchestrator/package/
	@cp -r ingestion/lib $(LAMBDA_DIR)/congress_api_ingest_orchestrator/package/lib
	@cd $(LAMBDA_DIR)/congress_api_ingest_orchestrator/package && zip -r ../function.zip . > /dev/null
	@rm -rf $(LAMBDA_DIR)/congress_api_ingest_orchestrator/package
	@echo "✓ Lambda package created: $(LAMBDA_DIR)/congress_api_ingest_orchestrator/function.zip"
	@ls -lh $(LAMBDA_DIR)/congress_api_ingest_orchestrator/function.zip | awk '{print "  Package size:", $$5}'
