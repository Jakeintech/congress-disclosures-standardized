#!/usr/bin/env bash
#
# Generate TypeScript types from OpenAPI specification
#
# This script uses openapi-typescript to auto-generate TypeScript types
# from the OpenAPI 3.1 spec generated from Pydantic models.
#
# Usage:
#   ./scripts/generate-types.sh
#
# Output:
#   src/lib/generated/api-schema.ts - Auto-generated TypeScript types
#

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Generating TypeScript types from OpenAPI spec...${NC}"

# Paths
OPENAPI_SPEC="../docs/openapi.yaml"
OUTPUT_FILE="src/lib/generated/api-schema.ts"

# Check if OpenAPI spec exists
if [ ! -f "$OPENAPI_SPEC" ]; then
    echo -e "${YELLOW}⚠️  OpenAPI spec not found at $OPENAPI_SPEC${NC}"
    echo -e "${YELLOW}   Run: python3 ../scripts/generate_openapi_spec.py${NC}"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Generate types
echo -e "${BLUE}📝 Running openapi-typescript...${NC}"
npx openapi-typescript "$OPENAPI_SPEC" \
    --output "$OUTPUT_FILE" \
    --alphabetize \
    --path-params-as-types

echo -e "${GREEN}✅ TypeScript types generated successfully!${NC}"
echo -e "${GREEN}   Output: $OUTPUT_FILE${NC}"

# Show stats
LINES=$(wc -l < "$OUTPUT_FILE")
echo -e "${BLUE}📊 Generated ${LINES} lines of TypeScript${NC}"
