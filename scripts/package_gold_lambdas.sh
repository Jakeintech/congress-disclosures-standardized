#!/bin/bash
#
# Package all Gold Layer Lambda functions (Sprint 2)
#
# This script packages all 8 Gold layer Lambda functions:
# - 3 Dimension builders
# - 3 Fact builders
# - 2 Aggregate computations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LAMBDA_DIR="$PROJECT_ROOT/ingestion/lambdas"
BUILD_DIR="$PROJECT_ROOT/build"

echo "🔨 Packaging Gold Layer Lambda Functions (Sprint 2)"
echo "=" * 80

# Create build directory
mkdir -p "$BUILD_DIR"

# List of Gold layer Lambdas
GOLD_LAMBDAS=(
    "build_dim_members"
    "build_dim_assets"
    "build_dim_bills"
    "build_fact_transactions"
    "build_fact_filings"
    "build_fact_lobbying"
    "compute_trending_stocks"
    "compute_member_stats"
)

# Package each Lambda
for lambda_name in "${GOLD_LAMBDAS[@]}"; do
    echo ""
    echo "📦 Packaging $lambda_name..."

    lambda_path="$LAMBDA_DIR/$lambda_name"
    package_dir="$lambda_path/package"
    zip_file="$BUILD_DIR/${lambda_name}.zip"

    # Clean previous package
    rm -rf "$package_dir" "$zip_file"
    mkdir -p "$package_dir"

    # No dependencies - handler only (pandas from Klayers public layer)
    echo "  Copying handler.py only (dependencies from public Klayers pandas layer)..."
    cp "$lambda_path/handler.py" "$package_dir/"

    # Create ZIP (use deterministic method for consistent hashes)
    echo "  Creating ZIP package..."
    cd "$package_dir"
    zip -q -r "$zip_file" . > /dev/null
    cd "$PROJECT_ROOT"

    # Get file size
    size=$(du -h "$zip_file" | cut -f1)
    echo "  ✓ Created: $zip_file ($size)"

    # Cleanup package directory
    rm -rf "$package_dir"
done

echo ""
echo "=" * 80
echo "✅ All Gold Layer Lambda functions packaged!"
echo ""
echo "Next steps:"
echo "  1. terraform apply  # Deploy infrastructure"
echo "  2. Lambdas will be deployed from build/*.zip files"
echo ""
echo "Test deployment:"
echo "  aws lambda invoke --function-name congress-disclosures-build-dim-members \\"
echo "    --payload '{}' response.json"
