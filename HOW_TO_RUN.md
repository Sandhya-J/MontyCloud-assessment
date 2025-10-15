# How to Run the Image Service

## Prerequisites

Before running the service, ensure you have:

- **Docker Desktop** installed and running
- **AWS CLI** installed
- **Python 3.7+** installed
- **Git** (for cloning if needed)

## Quick Start Guide

### Step 1: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install AWS CLI (if not already installed)
# Windows: Download from https://aws.amazon.com/cli/
# Mac: brew install awscli
# Linux: sudo apt-get install awscli
```

### Step 2: Start LocalStack

```bash
# Start LocalStack using Docker Compose
docker-compose up -d

# Wait for LocalStack to be ready (30-60 seconds)
# Check if it's running:
docker ps
```

### Step 3: Configure AWS CLI for LocalStack

```bash
# Configure AWS CLI to use LocalStack
aws configure set aws_access_key_id test
aws configure set aws_secret_access_key test
aws configure set default.region us-east-1
```

### Step 4: Setup AWS Resources

**For Windows (PowerShell):**

```powershell
# Run the setup script
bash setup_localstack.sh

# Or if bash is not available, run commands manually:
# (See manual setup instructions below)
```

**For Linux/Mac:**

```bash
# Make script executable and run
chmod +x setup_localstack.sh
./setup_localstack.sh
```

### Step 5: Test the API

**For Windows:**

```powershell
bash test_api.sh
```

**For Linux/Mac:**

```bash
chmod +x test_api.sh
./test_api.sh
```

## Manual Setup (if scripts don't work)

If the setup scripts don't work on your system, you can run the commands manually:

### 1. Create S3 Bucket

```bash
aws --endpoint-url=http://localhost:4566 s3 mb s3://image-storage-bucket
```

### 2. Create DynamoDB Table

```bash
aws --endpoint-url=http://localhost:4566 dynamodb create-table \
    --table-name image-metadata \
    --attribute-definitions \
        AttributeName=image_id,AttributeType=S \
        AttributeName=user_id,AttributeType=S \
        AttributeName=created_at,AttributeType=S \
    --key-schema \
        AttributeName=image_id,KeyType=HASH \
    --global-secondary-indexes \
        IndexName=user-id-index,KeySchema='[{AttributeName=user_id,KeyType=HASH},{AttributeName=created_at,KeyType=RANGE}]',Projection='{ProjectionType=ALL}' \
    --billing-mode PAY_PER_REQUEST
```

### 3. Package Lambda Functions

```bash
# Create packages directory
mkdir -p packages

# Package each function
for func in upload_image list_images view_image delete_image; do
    mkdir -p packages/$func
    cp lambda_functions/$func.py packages/$func/
    cp lambda_functions/common.py packages/$func/
    pip install -r requirements.txt -t packages/$func/
    cd packages/$func
    zip -r ../${func}.zip .
    cd ../..
done
```

### 4. Deploy Lambda Functions

```bash
# Upload Image Lambda
aws --endpoint-url=http://localhost:4566 lambda create-function \
    --function-name upload-image \
    --runtime python3.9 \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --handler upload_image.lambda_handler \
    --zip-file fileb://packages/upload_image.zip \
    --environment Variables="{BUCKET_NAME=image-storage-bucket,TABLE_NAME=image-metadata,AWS_ENDPOINT_URL=http://localhost:4566}"
```

## Testing the API

### Using curl

After setup, you'll get an API Gateway URL. Test with curl:

```bash
# Get the API Gateway URL from setup output
API_URL="http://localhost:4566/restapis/{API_ID}/dev/_user_request_"

# Upload an image
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
    "title": "Test Image",
    "description": "A test image",
    "tags": ["test", "sample"]
  }' \
  $API_URL/images

# List images
curl $API_URL/images
```

### Using Python

```python
import requests
import base64
from PIL import Image
import io

# Create a test image
img = Image.new('RGB', (100, 100), color='red')
buffer = io.BytesIO()
img.save(buffer, format='JPEG')
img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

# API base URL (replace with your actual API Gateway URL)
API_URL = "http://localhost:4566/restapis/{API_ID}/dev/_user_request_"

# Upload image
upload_data = {
    "user_id": "python_user",
    "image_data": img_data,
    "title": "Python Test Image",
    "description": "Created with Python",
    "tags": ["python", "test"]
}

response = requests.post(f"{API_URL}/images", json=upload_data)
print("Upload response:", response.json())
```

## Running Unit Tests

```bash
# Run all unit tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=lambda_functions --cov-report=html

# Run specific test file
pytest tests/test_lambda_functions.py
```

## Running Security Tests

```bash
# Run security tests (after API is running)
python security_test.py http://localhost:4566/restapis/{API_ID}/dev/_user_request_
```

## Troubleshooting

### Common Issues

1. **Docker not running**

   ```bash
   # Start Docker Desktop
   # Check if Docker is running:
   docker ps
   ```

2. **LocalStack not starting**

   ```bash
   # Check LocalStack logs
   docker-compose logs localstack

   # Restart LocalStack
   docker-compose restart
   ```

3. **AWS CLI not configured**

   ```bash
   # Configure AWS CLI
   aws configure set aws_access_key_id test
   aws configure set aws_secret_access_key test
   aws configure set default.region us-east-1
   ```

4. **Permission denied on scripts (Linux/Mac)**

   ```bash
   chmod +x setup_localstack.sh test_api.sh
   ```

5. **Scripts not working on Windows**
   - Use Git Bash or WSL
   - Or run commands manually (see manual setup above)

### Check Service Status

```bash
# Check if LocalStack is running
docker ps | grep localstack

# Check if AWS services are available
aws --endpoint-url=http://localhost:4566 sts get-caller-identity

# Check S3 bucket
aws --endpoint-url=http://localhost:4566 s3 ls

# Check DynamoDB table
aws --endpoint-url=http://localhost:4566 dynamodb list-tables

# Check Lambda functions
aws --endpoint-url=http://localhost:4566 lambda list-functions
```

## Cleanup

```bash
# Stop LocalStack
docker-compose down

# Remove volumes (removes all data)
docker-compose down -v

# Remove packages directory
rm -rf packages
```

## Production Deployment

For production deployment to AWS:

1. Update environment variables in Lambda functions
2. Create IAM roles with proper permissions
3. Deploy using AWS SAM or Serverless Framework
4. Configure API Gateway with authentication
5. Set up monitoring and alerting

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs localstack`
2. Verify Docker is running: `docker ps`
3. Check AWS CLI configuration: `aws configure list`
4. Review the API documentation in `API_DOCUMENTATION.md`
5. Run the test script for examples: `./test_api.sh`
