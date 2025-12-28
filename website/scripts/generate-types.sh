#!/bin/bash

# Exit on error
set -e

# Ensure we are in the website directory
cd "$(dirname "$0")/.."

echo "Generating TypeScript types from OpenAPI spec..."

# Find OpenAPI spec (try multiple possible locations)
OPENAPI_PATH=""
if [ -f "../docs/openapi.yaml" ]; then
  OPENAPI_PATH="../docs/openapi.yaml"
elif [ -f "../../docs/openapi.yaml" ]; then
  OPENAPI_PATH="../../docs/openapi.yaml"
elif [ -f "docs/openapi.yaml" ]; then
  OPENAPI_PATH="docs/openapi.yaml"
else
  echo "Error: Could not find openapi.yaml"
  echo "Skipping type generation (types may be stale)"
  exit 0  # Exit with success to allow build to continue
fi

echo "Using OpenAPI spec at: $OPENAPI_PATH"

# Run openapi-typescript
npx openapi-typescript "$OPENAPI_PATH" \
  -o src/lib/generated/api-schema.ts \
  --alphabetize

echo "Successfully generated src/lib/generated/api-schema.ts"
