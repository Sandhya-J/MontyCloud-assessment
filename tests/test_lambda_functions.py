import pytest
import json
import base64
import os
from unittest.mock import patch, MagicMock
from PIL import Image
import io
from moto import mock_s3, mock_dynamodb
import boto3

# Set environment variables for testing
os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
os.environ['BUCKET_NAME'] = 'test-bucket'
os.environ['TABLE_NAME'] = 'test-table'

from lambda_functions.upload_image import lambda_handler as upload_handler
from lambda_functions.list_images import lambda_handler as list_handler
from lambda_functions.view_image import lambda_handler as view_handler
from lambda_functions.delete_image import lambda_handler as delete_handler

class TestImageUpload:
    """Test cases for image upload functionality"""
    
    def create_test_image(self):
        """Create a test image and return base64 encoded data"""
        img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        img_data = buffer.getvalue()
        return base64.b64encode(img_data).decode('utf-8')
    
    @mock_s3
    @mock_dynamodb
    def test_upload_image_success(self):
        """Test successful image upload"""
        # Create mock AWS resources
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='test-bucket')
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-table',
            KeySchema=[{'AttributeName': 'image_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'image_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Test data
        image_data = self.create_test_image()
        event = {
            'body': json.dumps({
                'user_id': 'user123',
                'image_data': image_data,
                'title': 'Test Image',
                'description': 'A test image',
                'tags': ['test', 'sample']
            })
        }
        
        # Call handler
        response = upload_handler(event, {})
        
        # Assertions
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['message'] == 'Image uploaded successfully'
        assert 'image_id' in body
        assert body['metadata']['user_id'] == 'user123'
        assert body['metadata']['title'] == 'Test Image'
    
    def test_upload_image_missing_user_id(self):
        """Test upload with missing user_id"""
        event = {
            'body': json.dumps({
                'image_data': 'invalid_data'
            })
        }
        
        response = upload_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'user_id and image_data are required' in body['error']
    
    def test_upload_image_invalid_image_data(self):
        """Test upload with invalid image data"""
        event = {
            'body': json.dumps({
                'user_id': 'user123',
                'image_data': 'invalid_base64_data'
            })
        }
        
        response = upload_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid image data' in body['error']

class TestImageList:
    """Test cases for image listing functionality"""
    
    @mock_dynamodb
    def test_list_images_success(self):
        """Test successful image listing"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-table',
            KeySchema=[{'AttributeName': 'image_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'image_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[{
                'IndexName': 'user-id-index',
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add test data
        table.put_item(Item={
            'image_id': 'img1',
            'user_id': 'user123',
            'title': 'Test Image 1',
            'tags': ['test'],
            'created_at': '2023-01-01T00:00:00'
        })
        
        # Test without filters
        event = {'queryStringParameters': {}}
        response = list_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['images']) == 1
        assert body['images'][0]['image_id'] == 'img1'
    
    @mock_dynamodb
    def test_list_images_with_user_filter(self):
        """Test listing images with user filter"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-table',
            KeySchema=[{'AttributeName': 'image_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'image_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[{
                'IndexName': 'user-id-index',
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add test data
        table.put_item(Item={
            'image_id': 'img1',
            'user_id': 'user123',
            'title': 'Test Image 1',
            'tags': ['test'],
            'created_at': '2023-01-01T00:00:00'
        })
        
        # Test with user filter
        event = {'queryStringParameters': {'user_id': 'user123'}}
        response = list_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['images']) == 1
        assert body['images'][0]['user_id'] == 'user123'
    
    @mock_dynamodb
    def test_list_images_with_tag_filter(self):
        """Test listing images with tag filter"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-table',
            KeySchema=[{'AttributeName': 'image_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'image_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add test data
        table.put_item(Item={
            'image_id': 'img1',
            'user_id': 'user123',
            'title': 'Test Image 1',
            'tags': ['test', 'sample'],
            'created_at': '2023-01-01T00:00:00'
        })
        
        table.put_item(Item={
            'image_id': 'img2',
            'user_id': 'user123',
            'title': 'Test Image 2',
            'tags': ['other'],
            'created_at': '2023-01-02T00:00:00'
        })
        
        # Test with tag filter
        event = {'queryStringParameters': {'tag': 'test'}}
        response = list_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['images']) == 1
        assert body['images'][0]['image_id'] == 'img1'

class TestImageView:
    """Test cases for image viewing functionality"""
    
    @mock_s3
    @mock_dynamodb
    def test_view_image_success(self):
        """Test successful image viewing"""
        # Create mock AWS resources
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='test-bucket')
        s3_client.put_object(
            Bucket='test-bucket',
            Key='images/user123/img1.jpg',
            Body=b'test_image_data'
        )
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-table',
            KeySchema=[{'AttributeName': 'image_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'image_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        table.put_item(Item={
            'image_id': 'img1',
            'user_id': 'user123',
            's3_key': 'images/user123/img1.jpg',
            'title': 'Test Image'
        })
        
        # Test viewing image
        event = {'pathParameters': {'image_id': 'img1'}}
        response = view_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['image_id'] == 'img1'
        assert 'image_data' in body
    
    @mock_dynamodb
    def test_view_image_not_found(self):
        """Test viewing non-existent image"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-table',
            KeySchema=[{'AttributeName': 'image_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'image_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Test viewing non-existent image
        event = {'pathParameters': {'image_id': 'nonexistent'}}
        response = view_handler(event, {})
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'Image not found' in body['error']
    
    @mock_s3
    @mock_dynamodb
    def test_view_image_metadata_only(self):
        """Test viewing image metadata only"""
        # Create mock AWS resources
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='test-bucket')
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-table',
            KeySchema=[{'AttributeName': 'image_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'image_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        table.put_item(Item={
            'image_id': 'img1',
            'user_id': 'user123',
            's3_key': 'images/user123/img1.jpg',
            'title': 'Test Image',
            'description': 'Test description'
        })
        
        # Test viewing metadata only
        event = {
            'pathParameters': {'image_id': 'img1'},
            'queryStringParameters': {'metadata_only': 'true'}
        }
        response = view_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['image_id'] == 'img1'
        assert 'image_data' not in body
        assert body['title'] == 'Test Image'

class TestImageDelete:
    """Test cases for image deletion functionality"""
    
    @mock_s3
    @mock_dynamodb
    def test_delete_image_success(self):
        """Test successful image deletion"""
        # Create mock AWS resources
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='test-bucket')
        s3_client.put_object(
            Bucket='test-bucket',
            Key='images/user123/img1.jpg',
            Body=b'test_image_data'
        )
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-table',
            KeySchema=[{'AttributeName': 'image_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'image_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        table.put_item(Item={
            'image_id': 'img1',
            'user_id': 'user123',
            's3_key': 'images/user123/img1.jpg'
        })
        
        # Test deleting image
        event = {'pathParameters': {'image_id': 'img1'}}
        response = delete_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Image deleted successfully'
        assert body['image_id'] == 'img1'
    
    @mock_dynamodb
    def test_delete_image_not_found(self):
        """Test deleting non-existent image"""
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-table',
            KeySchema=[{'AttributeName': 'image_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'image_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Test deleting non-existent image
        event = {'pathParameters': {'image_id': 'nonexistent'}}
        response = delete_handler(event, {})
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'Image not found' in body['error']
    
    def test_delete_image_missing_id(self):
        """Test deleting image without providing image_id"""
        event = {'pathParameters': {}}
        response = delete_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'image_id is required' in body['error']

if __name__ == '__main__':
    pytest.main([__file__])
