#!/bin/bash
set -e

echo "================================================================="
echo "   🚀 CONGRESS DISCLOSURES: FULL SYSTEM SETUP & EXECUTION"
echo "================================================================="
echo "This script will:"
echo "1. Deploy all infrastructure (Terraform)"
echo "2. Reset all data (S3 & SQS)"
echo "3. Run the full data pipeline"
echo "4. Validate pipeline integrity"
echo "5. Deploy the website"
echo "================================================================="

# Ensure we are in the project root
cd "$(dirname "$0")/.."

# Run the Make target
make reset-and-run-all
