#!/bin/bash
#
# Package API Lambdas for Deployment
# 
# This script packages all API Lambda functions and the shared library layer
# for deployment via Terraform.

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Packaging API Lambdas for Congress Disclosures API ==="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create build directory
BUILD_DIR="$PROJECT_ROOT/build/api_lambdas"
mkdir -p "$BUILD_DIR"

# ============================================================================
# 1. Build Lambda Layer (Shared Libraries)
# ============================================================================

echo -e "${BLUE}[1/3] Building Lambda Layer (shared libraries)...${NC}"

LAYER_DIR="$BUILD_DIR/layer"
mkdir -p "$LAYER_DIR/python/api"

# Copy shared library code
cp -r "$PROJECT_ROOT/api/lib" "$LAYER_DIR/python/api/"

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r "$PROJECT_ROOT/api/layers/shared_libs/requirements.txt" \
    -t "$LAYER_DIR/python/" \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --upgrade

# Create layer ZIP
cd "$LAYER_DIR"
zip -r "../api_shared_layer.zip" python/ > /dev/null
cd "$PROJECT_ROOT"

echo -e "${GREEN}✓ Layer built: build/api_lambdas/api_shared_layer.zip${NC}"

# ============================================================================
# 2. Package Individual Lambda Functions
# ============================================================================

echo -e "${BLUE}[2/3] Packaging Lambda functions...${NC}"

# List of Lambda functions to package
LAMBDA_FUNCTIONS=(
    "get_members"
    "get_member"
    "get_member_trades"
    "get_trades"
    "get_stock"
    "get_stocks"
    "get_summary"
    "search"
)

for FUNC in "${LAMBDA_FUNCTIONS[@]}"; do
    echo "Packaging $FUNC..."
    
    FUNC_DIR="$BUILD_DIR/functions/$FUNC"
    mkdir -p "$FUNC_DIR"
    
    # Copy handler
    cp "$PROJECT_ROOT/api/lambdas/$FUNC/handler.py" "$FUNC_DIR/"
    
    # Create ZIP
    cd "$FUNC_DIR"
    zip -r "../../${FUNC}.zip" . > /dev/null
    cd "$PROJECT_ROOT"
    
    echo -e "${GREEN}  ✓ $FUNC.zip${NC}"
done

# ============================================================================
# 3. Upload to S3 (optional - Terraform will handle this)
# ============================================================================

echo -e "${BLUE}[3/3] Package summary${NC}"
echo "Built artifacts:"
ls -lh "$BUILD_DIR"/*.zip | awk '{print "  " $9 " (" $5 ")"}'

echo ""
echo -e "${GREEN}=== Packaging Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Run: cd infra/terraform"
echo "2. Run: terraform plan"
echo "3. Run: terraform apply"
echo ""
echo "Lambda packages are in: $BUILD_DIR"
