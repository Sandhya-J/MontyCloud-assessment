# Image Service - Usage Instructions

## Prerequisites

Before running the Image Service, ensure you have the following installed:

- **Docker** and **Docker Compose**
- **AWS CLI** (for LocalStack interaction)
- **Python 3.7+**
- **pip** (Python package manager)

## Installation Steps

### 1. Clone and Setup

```bash
# Navigate to the project directory
cd MontyCloud-assessment1

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Start LocalStack

```bash
# Start LocalStack using Docker Compose
docker-compose up -d

# Wait for LocalStack to be ready (usually takes 30-60 seconds)
# You can check the logs with:
docker-compose logs -f localstack
```

### 3. Setup AWS Resources

```bash
# Run the setup script to create AWS resources and deploy Lambda functions
./setup_localstack.sh

# On Windows, you can also run:
# bash setup_localstack.sh
```

This script will:

- Create S3 bucket for image storage
- Create DynamoDB table for metadata
- Package and deploy Lambda functions
- Create API Gateway with all endpoints
- Set up proper integrations

### 4. Verify Setup

```bash
# Test all API endpoints
./test_api.sh

# On Windows:
# bash test_api.sh
```

## Manual Testing

### Using curl

After running the setup script, you'll get an API Gateway URL. Use it to test endpoints:

```bash
# Get the API Gateway URL from setup script output
API_URL="http://localhost:4566/restapis/{API_ID}/dev/_user_request_"

# 1. Upload an image
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

# 2. List images
curl $API_URL/images

# 3. List images by user
curl "$API_URL/images?user_id=test_user"

# 4. List images by tag
curl "$API_URL/images?tag=test"

# 5. View image (replace {image_id} with actual ID from upload response)
curl "$API_URL/images/{image_id}"

# 6. View metadata only
curl "$API_URL/images/{image_id}?metadata_only=true"

# 7. Delete image
curl -X DELETE "$API_URL/images/{image_id}"
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

# Get image ID from response
image_id = response.json()['image_id']

# List images
response = requests.get(f"{API_URL}/images")
print("List response:", response.json())

# View image
response = requests.get(f"{API_URL}/images/{image_id}")
print("View response keys:", response.json().keys())

# Delete image
response = requests.delete(f"{API_URL}/images/{image_id}")
print("Delete response:", response.json())
```

## Running Tests

### Unit Tests

```bash
# Run all unit tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=lambda_functions --cov-report=html

# Run specific test file
pytest tests/test_lambda_functions.py

# Run specific test class
pytest tests/test_lambda_functions.py::TestImageUpload
```

### Integration Tests

The `test_api.sh` script provides comprehensive integration testing:

```bash
# Run full integration test suite
./test_api.sh

# The script will test:
# - Image upload
# - Image listing (with filters)
# - Image viewing
# - Image deletion
# - Error handling
# - Pagination
```

## Troubleshooting

### Common Issues

1. **LocalStack not starting**

   ```bash
   # Check Docker is running
   docker ps

   # Check LocalStack logs
   docker-compose logs localstack

   # Restart LocalStack
   docker-compose restart
   ```

2. **AWS CLI not configured**

   ```bash
   # Configure AWS CLI for LocalStack
   aws configure set aws_access_key_id test
   aws configure set aws_secret_access_key test
   aws configure set default.region us-east-1
   ```

3. **Permission denied on scripts**

   ```bash
   # On Linux/Mac
   chmod +x setup_localstack.sh test_api.sh

   # On Windows, use Git Bash or WSL
   ```

4. **API Gateway not found**

   ```bash
   # Check if API was created
   aws --endpoint-url=http://localhost:4566 apigateway get-rest-apis

   # Re-run setup script
   ./setup_localstack.sh
   ```

5. **Lambda function errors**

   ```bash
   # Check Lambda logs
   aws --endpoint-url=http://localhost:4566 logs describe-log-groups

   # Check function status
   aws --endpoint-url=http://localhost:4566 lambda list-functions
   ```

### Debugging

1. **Enable debug logging**

   ```bash
   # Set debug environment variable
   export DEBUG=1
   docker-compose up -d
   ```

2. **Check resource status**

   ```bash
   # Check S3 bucket
   aws --endpoint-url=http://localhost:4566 s3 ls

   # Check DynamoDB table
   aws --endpoint-url=http://localhost:4566 dynamodb list-tables

   # Check Lambda functions
   aws --endpoint-url=http://localhost:4566 lambda list-functions
   ```

3. **Test individual components**

   ```bash
   # Test S3 directly
   aws --endpoint-url=http://localhost:4566 s3 cp test.txt s3://image-storage-bucket/

   # Test DynamoDB directly
   aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name image-metadata
   ```

## Performance Testing

### Load Testing with Apache Bench

```bash
# Install Apache Bench (if not available)
# Ubuntu/Debian: sudo apt-get install apache2-utils
# Mac: brew install httpd

# Test upload endpoint
ab -n 100 -c 10 -p upload_data.json -T application/json \
   http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images

# Test list endpoint
ab -n 1000 -c 50 \
   http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images
```

### Memory and CPU Monitoring

```bash
# Monitor Docker resources
docker stats

# Monitor LocalStack specifically
docker stats localstack-main
```

## Cleanup

### Stop Services

```bash
# Stop LocalStack
docker-compose down

# Remove volumes (optional - removes all data)
docker-compose down -v
```

### Reset Environment

```bash
# Complete reset
docker-compose down -v
docker-compose up -d
./setup_localstack.sh
```

## Production Deployment

For production deployment to AWS:

1. **Update environment variables** in Lambda functions
2. **Create IAM roles** with appropriate permissions
3. **Deploy using AWS SAM** or Serverless Framework
4. **Configure API Gateway** with authentication
5. **Set up monitoring** and alerting

Example AWS SAM template:

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31

Resources:
  ImageServiceFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: lambda_functions/
      Handler: upload_image.lambda_handler
      Runtime: python3.9
      Environment:
        Variables:
          BUCKET_NAME: !Ref ImageBucket
          TABLE_NAME: !Ref ImageTable
      Policies:
        - S3CrudPolicy:
            BucketName: !Ref ImageBucket
        - DynamoDBCrudPolicy:
            TableName: !Ref ImageTable
```

## Support

For additional help:

1. Check the API documentation in `API_DOCUMENTATION.md`
2. Review unit tests in `tests/test_lambda_functions.py`
3. Run the test script `test_api.sh` for examples
4. Check LocalStack documentation for AWS service specifics
