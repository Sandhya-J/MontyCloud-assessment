#!/bin/bash

# Setup script for LocalStack development environment
# This script sets up AWS resources and deploys Lambda functions

set -e

# Configuration
AWS_ENDPOINT="http://localhost:4566"
BUCKET_NAME="image-storage-bucket"
TABLE_NAME="image-metadata"
REGION="us-east-1"

echo "Setting up LocalStack development environment..."

# Configure AWS CLI for LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=$REGION

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
until aws --endpoint-url=$AWS_ENDPOINT sts get-caller-identity > /dev/null 2>&1; do
    echo "LocalStack not ready yet, waiting..."
    sleep 2
done

echo "LocalStack is ready!"

# Create S3 bucket
echo "Creating S3 bucket: $BUCKET_NAME"
aws --endpoint-url=$AWS_ENDPOINT s3 mb s3://$BUCKET_NAME || echo "Bucket might already exist"

# Create DynamoDB table
echo "Creating DynamoDB table: $TABLE_NAME"
aws --endpoint-url=$AWS_ENDPOINT dynamodb create-table \
    --table-name $TABLE_NAME \
    --attribute-definitions \
        AttributeName=image_id,AttributeType=S \
        AttributeName=user_id,AttributeType=S \
        AttributeName=created_at,AttributeType=S \
    --key-schema \
        AttributeName=image_id,KeyType=HASH \
    --global-secondary-indexes \
        IndexName=user-id-index,KeySchema='[{AttributeName=user_id,KeyType=HASH},{AttributeName=created_at,KeyType=RANGE}]',Projection='{ProjectionType=ALL}' \
    --billing-mode PAY_PER_REQUEST \
    || echo "Table might already exist"

# Wait for table to be active
echo "Waiting for DynamoDB table to be active..."
aws --endpoint-url=$AWS_ENDPOINT dynamodb wait table-exists --table-name $TABLE_NAME

# Create deployment packages for Lambda functions
echo "Creating Lambda deployment packages..."

# Create a temporary directory for packaging
mkdir -p temp_packages

# Package each Lambda function
for func in upload_image list_images view_image delete_image; do
    echo "Packaging $func..."
    
    # Create package directory
    mkdir -p temp_packages/$func
    
    # Copy function code
    cp lambda_functions/$func.py temp_packages/$func/
    cp lambda_functions/common.py temp_packages/$func/
    
    # Install dependencies
    pip install -r requirements.txt -t temp_packages/$func/
    
    # Create zip package
    cd temp_packages/$func
    zip -r ../${func}.zip .
    cd ../..
done

# Deploy Lambda functions
echo "Deploying Lambda functions..."

# Upload Image Lambda
aws --endpoint-url=$AWS_ENDPOINT lambda create-function \
    --function-name upload-image \
    --runtime python3.9 \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --handler upload_image.lambda_handler \
    --zip-file fileb://temp_packages/upload_image.zip \
    --environment Variables="{BUCKET_NAME=$BUCKET_NAME,TABLE_NAME=$TABLE_NAME,AWS_ENDPOINT_URL=$AWS_ENDPOINT}" \
    || echo "Function might already exist"

# List Images Lambda
aws --endpoint-url=$AWS_ENDPOINT lambda create-function \
    --function-name list-images \
    --runtime python3.9 \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --handler list_images.lambda_handler \
    --zip-file fileb://temp_packages/list_images.zip \
    --environment Variables="{BUCKET_NAME=$BUCKET_NAME,TABLE_NAME=$TABLE_NAME,AWS_ENDPOINT_URL=$AWS_ENDPOINT}" \
    || echo "Function might already exist"

# View Image Lambda
aws --endpoint-url=$AWS_ENDPOINT lambda create-function \
    --function-name view-image \
    --runtime python3.9 \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --handler view_image.lambda_handler \
    --zip-file fileb://temp_packages/view_image.zip \
    --environment Variables="{BUCKET_NAME=$BUCKET_NAME,TABLE_NAME=$TABLE_NAME,AWS_ENDPOINT_URL=$AWS_ENDPOINT}" \
    || echo "Function might already exist"

# Delete Image Lambda
aws --endpoint-url=$AWS_ENDPOINT lambda create-function \
    --function-name delete-image \
    --runtime python3.9 \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --handler delete_image.lambda_handler \
    --zip-file fileb://temp_packages/delete_image.zip \
    --environment Variables="{BUCKET_NAME=$BUCKET_NAME,TABLE_NAME=$TABLE_NAME,AWS_ENDPOINT_URL=$AWS_ENDPOINT}" \
    || echo "Function might already exist"

# Create API Gateway
echo "Creating API Gateway..."

# Create REST API
API_ID=$(aws --endpoint-url=$AWS_ENDPOINT apigateway create-rest-api \
    --name "image-service-api" \
    --description "Image upload and management service" \
    --query 'id' --output text)

echo "API Gateway ID: $API_ID"

# Get root resource ID
ROOT_RESOURCE_ID=$(aws --endpoint-url=$AWS_ENDPOINT apigateway get-resources \
    --rest-api-id $API_ID \
    --query 'items[0].id' --output text)

# Create resources and methods for each endpoint
create_api_endpoint() {
    local path=$1
    local method=$2
    local function_name=$3
    
    # Create resource
    RESOURCE_ID=$(aws --endpoint-url=$AWS_ENDPOINT apigateway create-resource \
        --rest-api-id $API_ID \
        --parent-id $ROOT_RESOURCE_ID \
        --path-part $path \
        --query 'id' --output text)
    
    # Create method
    aws --endpoint-url=$AWS_ENDPOINT apigateway put-method \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method $method \
        --authorization-type NONE
    
    # Get Lambda function ARN
    FUNCTION_ARN=$(aws --endpoint-url=$AWS_ENDPOINT lambda get-function \
        --function-name $function_name \
        --query 'Configuration.FunctionArn' --output text)
    
    # Create integration
    aws --endpoint-url=$AWS_ENDPOINT apigateway put-integration \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method $method \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$FUNCTION_ARN/invocations"
    
    echo "Created endpoint: $method /$path -> $function_name"
}

# Create API endpoints
create_api_endpoint "images" "POST" "upload-image"
create_api_endpoint "images" "GET" "list-images"
create_api_endpoint "images" "GET" "view-image"  # This will be overridden for the specific path
create_api_endpoint "images" "DELETE" "delete-image"

# Create specific resource for image ID in view and delete endpoints
IMAGE_RESOURCE_ID=$(aws --endpoint-url=$AWS_ENDPOINT apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_RESOURCE_ID \
    --path-part "images" \
    --query 'id' --output text)

ID_RESOURCE_ID=$(aws --endpoint-url=$AWS_ENDPOINT apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $IMAGE_RESOURCE_ID \
    --path-part "{image_id}" \
    --query 'id' --output text)

# Create GET method for view image
aws --endpoint-url=$AWS_ENDPOINT apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $ID_RESOURCE_ID \
    --http-method GET \
    --authorization-type NONE

VIEW_FUNCTION_ARN=$(aws --endpoint-url=$AWS_ENDPOINT lambda get-function \
    --function-name view-image \
    --query 'Configuration.FunctionArn' --output text)

aws --endpoint-url=$AWS_ENDPOINT apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $ID_RESOURCE_ID \
    --http-method GET \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$VIEW_FUNCTION_ARN/invocations"

# Create DELETE method for delete image
aws --endpoint-url=$AWS_ENDPOINT apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $ID_RESOURCE_ID \
    --http-method DELETE \
    --authorization-type NONE

DELETE_FUNCTION_ARN=$(aws --endpoint-url=$AWS_ENDPOINT lambda get-function \
    --function-name delete-image \
    --query 'Configuration.FunctionArn' --output text)

aws --endpoint-url=$AWS_ENDPOINT apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $ID_RESOURCE_ID \
    --http-method DELETE \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$DELETE_FUNCTION_ARN/invocations"

# Deploy API
echo "Deploying API Gateway..."
aws --endpoint-url=$AWS_ENDPOINT apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name dev

# Clean up temporary packages
rm -rf temp_packages

echo "Setup complete!"
echo "API Gateway URL: $AWS_ENDPOINT/restapis/$API_ID/dev/_user_request_/"
echo ""
echo "Available endpoints:"
echo "  POST   /images                    - Upload image"
echo "  GET    /images                    - List images"
echo "  GET    /images/{image_id}         - View/download image"
echo "  DELETE /images/{image_id}         - Delete image"
echo ""
echo "To test the API, use the base URL: $AWS_ENDPOINT/restapis/$API_ID/dev/_user_request_/"
