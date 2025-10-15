# Image Service API Documentation

## Overview

The Image Service API is a scalable, serverless image upload and management system built for Instagram-like applications. It provides RESTful APIs for uploading, listing, viewing, and deleting images with metadata persistence.

## Architecture

- **API Gateway**: RESTful API endpoints
- **Lambda Functions**: Serverless compute for business logic
- **S3**: Image storage
- **DynamoDB**: Metadata storage with NoSQL capabilities
- **LocalStack**: Local development environment

## Prerequisites

- Docker and Docker Compose
- AWS CLI
- Python 3.7+
- pip

## Quick Start

### 1. Start LocalStack

```bash
docker-compose up -d
```

### 2. Setup AWS Resources

```bash
./setup_localstack.sh
```

### 3. Test the API

```bash
./test_api.sh
```

## API Endpoints

### Base URL

```
http://localhost:4566/restapis/{API_ID}/dev/_user_request_
```

### 1. Upload Image

**POST** `/images`

Upload an image with metadata to the service.

#### Request Body

```json
{
  "user_id": "string (required)",
  "image_data": "string (required, base64 encoded)",
  "title": "string (optional)",
  "description": "string (optional)",
  "tags": ["string"] (optional)
}
```

#### Example Request

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
    "title": "My Photo",
    "description": "A beautiful sunset",
    "tags": ["sunset", "nature", "photography"]
  }' \
  http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images
```

#### Response

```json
{
  "message": "Image uploaded successfully",
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "image_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user123",
    "title": "My Photo",
    "description": "A beautiful sunset",
    "tags": ["sunset", "nature", "photography"],
    "s3_key": "images/user123/550e8400-e29b-41d4-a716-446655440000.jpg",
    "width": 100,
    "height": 100,
    "format": "JPEG",
    "file_size": 1024,
    "created_at": "2023-12-01T10:00:00.000Z",
    "updated_at": "2023-12-01T10:00:00.000Z"
  }
}
```

### 2. List Images

**GET** `/images`

Retrieve a list of images with optional filtering and pagination.

#### Query Parameters

- `user_id` (optional): Filter by user ID
- `tag` (optional): Filter by tag
- `limit` (optional): Number of results per page (default: 20)
- `last_key` (optional): Pagination token for next page

#### Example Requests

```bash
# List all images
curl http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images

# Filter by user
curl "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images?user_id=user123"

# Filter by tag
curl "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images?tag=sunset"

# Pagination
curl "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images?limit=10&last_key=eyJpbWFnZV9pZCI6..."
```

#### Response

```json
{
  "images": [
    {
      "image_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "user123",
      "title": "My Photo",
      "description": "A beautiful sunset",
      "tags": ["sunset", "nature", "photography"],
      "width": 100,
      "height": 100,
      "file_size": 1024,
      "created_at": "2023-12-01T10:00:00.000Z",
      "updated_at": "2023-12-01T10:00:00.000Z"
    }
  ],
  "count": 1,
  "next_key": "eyJpbWFnZV9pZCI6...",
  "has_more": true
}
```

### 3. View/Download Image

**GET** `/images/{image_id}`

Retrieve an image and its metadata.

#### Path Parameters

- `image_id` (required): Unique identifier of the image

#### Query Parameters

- `metadata_only` (optional): If true, returns only metadata without image data

#### Example Requests

```bash
# Get image with data
curl http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images/550e8400-e29b-41d4-a716-446655440000

# Get metadata only
curl "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images/550e8400-e29b-41d4-a716-446655440000?metadata_only=true"
```

#### Response (with image data)

```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
  "content_type": "image/jpeg",
  "metadata": {
    "title": "My Photo",
    "description": "A beautiful sunset",
    "tags": ["sunset", "nature", "photography"],
    "width": 100,
    "height": 100,
    "file_size": 1024,
    "created_at": "2023-12-01T10:00:00.000Z"
  }
}
```

#### Response (metadata only)

```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "title": "My Photo",
  "description": "A beautiful sunset",
  "tags": ["sunset", "nature", "photography"],
  "width": 100,
  "height": 100,
  "file_size": 1024,
  "format": "JPEG",
  "created_at": "2023-12-01T10:00:00.000Z",
  "updated_at": "2023-12-01T10:00:00.000Z"
}
```

### 4. Delete Image

**DELETE** `/images/{image_id}`

Delete an image and its metadata.

#### Path Parameters

- `image_id` (required): Unique identifier of the image

#### Example Request

```bash
curl -X DELETE \
  http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images/550e8400-e29b-41d4-a716-446655440000
```

#### Response

```json
{
  "message": "Image deleted successfully",
  "image_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Error Responses

All endpoints return appropriate HTTP status codes and error messages:

### 400 Bad Request

```json
{
  "error": "user_id and image_data are required"
}
```

### 404 Not Found

```json
{
  "error": "Image not found"
}
```

### 500 Internal Server Error

```json
{
  "error": "Internal server error: [error details]"
}
```

## Data Models

### Image Metadata

```json
{
  "image_id": "string (UUID)",
  "user_id": "string",
  "title": "string",
  "description": "string",
  "tags": ["string"],
  "s3_key": "string",
  "width": "number",
  "height": "number",
  "format": "string",
  "file_size": "number",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

## Development

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run unit tests
pytest

# Run tests with coverage
pytest --cov=lambda_functions --cov-report=html
```

### Project Structure

```
├── lambda_functions/
│   ├── common.py           # Shared utilities
│   ├── upload_image.py     # Upload endpoint
│   ├── list_images.py      # List endpoint
│   ├── view_image.py       # View endpoint
│   └── delete_image.py     # Delete endpoint
├── tests/
│   └── test_lambda_functions.py
├── docker-compose.yml      # LocalStack configuration
├── setup_localstack.sh     # Setup script
├── test_api.sh            # API testing script
├── requirements.txt       # Python dependencies
└── pytest.ini           # Test configuration
```

## Scalability Features

1. **Serverless Architecture**: Auto-scaling Lambda functions
2. **NoSQL Storage**: DynamoDB with Global Secondary Indexes for efficient querying
3. **Object Storage**: S3 for scalable image storage
4. **Pagination**: Built-in pagination support for large datasets
5. **Filtering**: Multiple filter options for efficient data retrieval

## Security Considerations

1. **Input Validation**: All inputs are validated and sanitized
2. **Error Handling**: Comprehensive error handling without exposing sensitive information
3. **CORS**: Cross-origin resource sharing headers included
4. **Image Processing**: Images are converted to JPEG format for consistency and security

## Performance Optimizations

1. **Image Compression**: Automatic JPEG compression with 85% quality
2. **Metadata Indexing**: DynamoDB GSI for efficient user-based queries
3. **Lazy Loading**: Metadata-only responses when image data isn't needed
4. **Batch Operations**: Efficient batch processing for multiple operations

## Monitoring and Logging

- CloudWatch Logs integration (when deployed to AWS)
- Structured logging with request/response tracking
- Error monitoring and alerting capabilities

## Deployment to AWS

To deploy to AWS production environment:

1. Update environment variables in Lambda functions
2. Create IAM roles with appropriate permissions
3. Deploy using AWS SAM or Serverless Framework
4. Configure API Gateway with proper authentication
5. Set up CloudWatch monitoring and alerting

## Support

For issues or questions, please refer to the test scripts and unit tests for usage examples.
