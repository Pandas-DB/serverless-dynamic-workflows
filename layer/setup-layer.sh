#!/bin/bash

# Clean up any previous builds
rm -rf /home/sergi/Documents/prototypes/serverless-dynamic-workflows/layer/python/lib/python3.9/site-packages

# Create the correct directory structure
mkdir -p /home/sergi/Documents/prototypes/serverless-dynamic-workflows/layer/python/lib/python3.9/site-packages

# First install core dependencies that are always needed
pip install \
    aws-lambda-powertools \
    boto3 \
    -t /home/sergi/Documents/prototypes/serverless-dynamic-workflows/layer/python/lib/python3.9/site-packages \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.9 \
    --only-binary=:all: \
    --upgrade

# Now install requirements from all plugin sources
if [ -f "/home/sergi/Documents/prototypes/serverless-dynamic-workflows/layer/requirements.txt" ]; then
    pip install \
        -r /home/sergi/Documents/prototypes/serverless-dynamic-workflows/layer/requirements.txt \
        -t /home/sergi/Documents/prototypes/serverless-dynamic-workflows/layer/python/lib/python3.9/site-packages \
        --platform manylinux2014_x86_64 \
        --implementation cp \
        --python-version 3.9 \
        --only-binary=:all: \
        --upgrade
fi

# Remove unnecessary files
cd /home/sergi/Documents/prototypes/serverless-dynamic-workflows/layer/python/lib/python3.9/site-packages
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name "*.dist-info" -exec rm -rf {} +
find . -type d -name "*.egg-info" -exec rm -rf {} +
find . -type d -name "tests" -exec rm -rf {} +
find . -type d -name "test" -exec rm -rf {} +
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "*.pyd" -delete
find . -name "*.so" -exec strip {} + 2>/dev/null || true
cd ../../..
