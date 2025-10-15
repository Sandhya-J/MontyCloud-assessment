@echo off
echo Starting Image Service Setup...
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo Step 1: Starting LocalStack...
docker-compose up -d

echo Waiting for LocalStack to start...
timeout /t 30 /nobreak >nul

echo Step 2: Configuring AWS CLI...
aws configure set aws_access_key_id test
aws configure set aws_secret_access_key test
aws configure set default.region us-east-1

echo Step 3: Setting up AWS resources...
echo This may take a few minutes...

REM Create S3 bucket
aws --endpoint-url=http://localhost:4566 s3 mb s3://image-storage-bucket

REM Create DynamoDB table
aws --endpoint-url=http://localhost:4566 dynamodb create-table --table-name image-metadata --attribute-definitions AttributeName=image_id,AttributeType=S AttributeName=user_id,AttributeType=S AttributeName=created_at,AttributeType=S --key-schema AttributeName=image_id,KeyType=HASH --global-secondary-indexes IndexName=user-id-index,KeySchema='[{AttributeName=user_id,KeyType=HASH},{AttributeName=created_at,KeyType=RANGE}]',Projection='{ProjectionType=ALL}' --billing-mode PAY_PER_REQUEST

echo.
echo Setup complete! 
echo.
echo To test the API, you can:
echo 1. Run: python test_api.py
echo 2. Or use curl/Postman with the API endpoints
echo.
echo API Base URL: http://localhost:4566/restapis/{API_ID}/dev/_user_request_/
echo.
pause
