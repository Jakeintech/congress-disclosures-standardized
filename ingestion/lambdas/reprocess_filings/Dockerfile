# Use AWS Lambda Python 3.11 base image
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY handler.py ${LAMBDA_TASK_ROOT}/

# Copy shared libraries
COPY ../../lib ${LAMBDA_TASK_ROOT}/lib/

# Set handler
CMD ["handler.lambda_handler"]
