# Use AWS Lambda Python 3.11 base image
FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.11

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Install system dependencies for OCR (Tesseract and Poppler) and OpenCV
# Install system dependencies for OCR (Tesseract and Poppler) and OpenCV
# Amazon Linux 2 uses yum
RUN yum update -y && \
    yum install -y tesseract poppler-utils mesa-libGL glib2 && \
    yum clean all

# Copy requirements file
COPY ingestion/lambdas/house_fd_extract_structured_code/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt --target ${LAMBDA_TASK_ROOT}

# Copy shared library code (from ingestion/lib)
COPY ingestion/lib/ ${LAMBDA_TASK_ROOT}/lib/

# Copy schemas (from ingestion/schemas)
# Note: structured code lambda might not need schemas if it doesn't validate, but good to have
COPY ingestion/schemas/ ${LAMBDA_TASK_ROOT}/schemas/

# Copy Lambda handler
COPY ingestion/lambdas/house_fd_extract_structured_code/handler.py ${LAMBDA_TASK_ROOT}/

# Optimize: Remove unnecessary files
RUN find ${LAMBDA_TASK_ROOT} -type d -name "tests" -exec rm -rf {} + || true && \
    find ${LAMBDA_TASK_ROOT} -type d -name "*.dist-info" -exec rm -rf {} + || true && \
    find ${LAMBDA_TASK_ROOT} -type f -name "*.pyc" -delete && \
    find ${LAMBDA_TASK_ROOT} -type d -name "__pycache__" -exec rm -rf {} + || true

# Set the CMD to your handler
CMD [ "handler.lambda_handler" ]
