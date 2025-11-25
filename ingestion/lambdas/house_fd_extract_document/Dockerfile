# Use AWS Lambda Python 3.11 base image
# This ensures dependencies are built for the correct Linux platform
# FREE TIER OPTIMIZED: Uses pypdf (free) instead of Textract
# IMPORTANT: Force x86_64/amd64 platform (not ARM64) for Lambda compatibility
FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.11

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements file
COPY ingestion/lambdas/house_fd_extract_document/requirements.txt .

# Install Python dependencies
# Using --no-cache-dir to reduce image size and stay within free tier
RUN pip install --no-cache-dir -r requirements.txt --target ${LAMBDA_TASK_ROOT}

# Copy shared library code (from ingestion/lib)
COPY ingestion/lib/ ${LAMBDA_TASK_ROOT}/lib/

# Copy schemas (from ingestion/schemas)
COPY ingestion/schemas/ ${LAMBDA_TASK_ROOT}/schemas/

# Copy Lambda handler
COPY ingestion/lambdas/house_fd_extract_document/handler.py ${LAMBDA_TASK_ROOT}/

# Optimize: Remove unnecessary files to reduce package size
RUN find ${LAMBDA_TASK_ROOT} -type d -name "tests" -exec rm -rf {} + || true && \
    find ${LAMBDA_TASK_ROOT} -type d -name "*.dist-info" -exec rm -rf {} + || true && \
    find ${LAMBDA_TASK_ROOT} -type f -name "*.pyc" -delete && \
    find ${LAMBDA_TASK_ROOT} -type d -name "__pycache__" -exec rm -rf {} + || true

# Set the CMD to your handler
CMD [ "handler.lambda_handler" ]
