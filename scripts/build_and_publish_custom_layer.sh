#!/bin/bash
set -e

LAYER_NAME="python-custom-dependencies" # New layer name
S3_BUCKET="congress-disclosures-standardized"
LAYER_ZIP_KEY="lambda-layers/${LAYER_NAME}.zip"
BUILD_DIR="layer_builder"
OUTPUT_ZIP_PATH="${BUILD_DIR}/layer.zip"

echo "--- Building Custom Lambda Layer: ${LAYER_NAME} ---"

# Create build directory
mkdir -p ${BUILD_DIR}

# Copy requirements.txt to the build directory
cp infra/lambda_layers/python_shared/requirements.txt ${BUILD_DIR}/requirements.txt

# Create Dockerfile inside build directory
cat <<EOF > ${BUILD_DIR}/Dockerfile
FROM public.ecr.aws/lambda/python:3.11

# Install build tools (gcc, g++) and zip
RUN yum install -y gcc gcc-c++ zip

# Create a directory for the layer
RUN mkdir -p /asset/python

# Copy the requirements file
COPY requirements.txt .

# Install dependencies into the 'python' directory
RUN pip install --no-cache-dir -r requirements.txt -t /asset/python

# Clean up the installed packages
RUN find /asset/python -type d -name "__pycache__" -exec rm -r {} +
RUN find /asset/python -type f -name "*.pyc" -delete
RUN find /asset/python -type d -name "tests" -exec rm -r {} +
RUN find /asset/python -type d -name "test" -exec rm -r {} +
RUN find /asset/python -type d -name "testing" -exec rm -r {} +
EOF

# 1. Build Docker image
echo "Building Docker image..."
docker buildx build --platform linux/amd64 -t ${LAYER_NAME}-builder ${BUILD_DIR} --load

# 2. Run container and extract layer zip
echo "Running container and extracting layer zip..."
docker run --rm --entrypoint /bin/bash -v $(pwd)/${BUILD_DIR}:/host_mount ${LAYER_NAME}-builder -c \
    "cd /asset && zip -r /host_mount/layer.zip python"

# 3. Upload layer zip to S3
echo "Uploading layer zip to S3..."
aws s3 cp ${OUTPUT_ZIP_PATH} s3://${S3_BUCKET}/${LAYER_ZIP_KEY}

# 4. Publish new layer version
echo "Publishing new layer version..."
LAYER_VERSION_ARN=$(aws lambda publish-layer-version \
    --layer-name ${LAYER_NAME} \
    --content S3Bucket=${S3_BUCKET},S3Key=${LAYER_ZIP_KEY} \
    --compatible-runtimes python3.11 \
    --description "Custom dependencies for python3.11 (jsonschema, python-dateutil, defusedxml) built with official AWS Lambda image" \
    --query LayerVersionArn \
    --output text)

echo "--- Custom Layer published: ${LAYER_VERSION_ARN} ---"

# 5. Update Lambda function - THIS WILL BE DONE SEPARATELY, LATER
# We need to update with *both* layers.

# 6. Clean up
echo "Cleaning up..."
rm -f ${OUTPUT_ZIP_PATH}
rm -rf ${BUILD_DIR}

echo "Done."
