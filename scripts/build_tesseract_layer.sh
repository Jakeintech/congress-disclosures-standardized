#!/bin/bash
# Build Tesseract Lambda Layer
# This creates a Lambda layer containing Tesseract OCR binaries and dependencies

set -e

LAYER_NAME="tesseract-ocr"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$REPO_ROOT/build/layers/$LAYER_NAME"
LAYER_ZIP="$BUILD_DIR/layer.zip"

echo "============================================"
echo "Building Tesseract Lambda Layer"
echo "============================================"

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Create Dockerfile for layer build
cat > "$BUILD_DIR/Dockerfile" << 'EOF'
FROM public.ecr.aws/lambda/python:3.11

# Install Tesseract and dependencies, then copy to /opt
RUN yum update -y && \
    yum install -y tesseract poppler-utils && \
    mkdir -p /opt/bin /opt/lib /opt/share && \
    cp /usr/bin/tesseract /opt/bin/ && \
    cp /usr/bin/pdftotext /opt/bin/ && \
    cp /usr/bin/pdftoppm /opt/bin/ && \
    ldd /usr/bin/tesseract | grep "=> /" | awk '{print $3}' | xargs -I '{}' cp -v '{}' /opt/lib/ || true && \
    cp -r /usr/share/tesseract /opt/share/ || true && \
    yum clean all

WORKDIR /opt
EOF

# Build Docker image
echo "Building Docker image..."
cd "$BUILD_DIR"
docker build -t "$LAYER_NAME:latest" .

# Extract layer contents
echo "Extracting layer contents..."
CONTAINER_ID=$(docker create "$LAYER_NAME:latest")
docker cp "$CONTAINER_ID:/opt" "$BUILD_DIR/layer"
docker rm "$CONTAINER_ID"

# Create layer zip
echo "Creating layer.zip..."
cd "$BUILD_DIR/layer"
zip -r "$LAYER_ZIP" . > /dev/null

# Get size
ZIP_SIZE=$(du -h "$LAYER_ZIP" | cut -f1)
echo "Layer size: $ZIP_SIZE"

echo ""
echo "============================================"
echo "✅ Layer built successfully!"
echo "============================================"
echo "Layer zip: $LAYER_ZIP"
echo ""
echo "Next steps:"
echo "1. Publish layer: aws lambda publish-layer-version --layer-name $LAYER_NAME --zip-file fileb://$LAYER_ZIP --compatible-runtimes python3.11"
echo "2. Note the LayerVersionArn from output"
echo "3. Update Terraform: var.tesseract_layer_arn = \"<LayerVersionArn>\""
