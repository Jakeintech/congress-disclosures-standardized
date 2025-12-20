#!/bin/bash

# Exit on error
set -e

# Ensure we are in the website directory
cd "$(dirname "$0")/.."

echo "Generating TypeScript types from OpenAPI spec..."

# Run openapi-typescript
npx openapi-typescript ../docs/openapi.yaml \
  -o src/lib/generated/api-schema.ts \
  --alphabetize

echo "Successfully generated src/lib/generated/api-schema.ts"
