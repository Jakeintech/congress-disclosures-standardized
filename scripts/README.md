# Scripts

Organized by purpose:

## `setup/`
Environment setup, configuration sync, GitHub project setup

- `sync_terraform_outputs.sh` - Sync Terraform outputs to .env
- `sync-api-url.sh` - Update API Gateway URL in frontend config
- `setup_github_agile_complete.sh` - Complete GitHub Agile setup
- `setup_github_milestones.sh` - Create GitHub milestones
- `setup_github_labels.sh` - Create GitHub labels
- `setup_all.sh` - Run all setup scripts
- `create_github_project.sh` - Create GitHub project board

## `deployment/`
Lambda packaging, infrastructure deployment, layer building

### Packaging
- `package_gold_lambdas.sh` - Package Gold layer Lambda functions
- `package_api_lambdas.sh` - Package API Lambda functions
- `package_lambdas.sh` - Package all Lambda functions

### Building
- `build_lambda_docker.sh` - Build Lambda Docker image
- `build_lambda_local.sh` - Build Lambda locally
- `build_admin.sh` - Build admin interface
- `build_and_publish_custom_layer.sh` - Build and publish custom Lambda layer
- `build_api_lambda_layer.sh` - Build API Lambda layer
- `build_tesseract_layer.sh` - Build Tesseract OCR Lambda layer

### Deployment
- `deploy-week2.sh` - Week 2 deployment script
- `deploy_extractor.sh` - Deploy extraction Lambda
- `deploy_api_lambda.sh` - Deploy API Lambda
- `terraform_import.sh` - Import existing resources to Terraform

### Updates
- `update_extract_lambda_turbo.sh` - Quick update extraction Lambda
- `update_extract_lambda_turbo_v2.sh` - Quick update extraction Lambda v2
- `update_transaction_builder.sh` - Update transaction builder
- `update_api_lambda_codes.sh` - Update API Lambda code

### Utilities
- `push_lambda_docker.sh` - Push Lambda Docker image to ECR

## `data_operations/`
Data validation, pipeline management

- `run_full_pipeline.sh` - Run full data pipeline
- `test_pipeline.sh` - Test pipeline execution

## Root-level Scripts (in `backend/scripts/`)

All Python scripts remain in `backend/scripts/` for data operations:

- `run_smart_pipeline.py` - **Main entry point** for pipeline operations
- `build_*.py` - Dimension and fact table builders
- `compute_agg_*.py` - Aggregate computation scripts
- `congress_*.py` - Congress.gov API integration scripts
- `lobbying_*.py` - Lobbying data integration scripts
- `validate_*.py` - Data validation scripts
- Many more specialized scripts

See `backend/scripts/` for the complete list.
