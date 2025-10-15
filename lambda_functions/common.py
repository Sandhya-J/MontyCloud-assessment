import os
import json
import boto3
from botocore.exceptions import ClientError
from PIL import Image
import io
import uuid
from datetime import datetime
import base64

# Initialize AWS clients
s3_client = boto3.client('s3', endpoint_url=os.environ.get('AWS_ENDPOINT_URL'))
dynamodb = boto3.resource('dynamodb', endpoint_url=os.environ.get('AWS_ENDPOINT_URL'))

# Environment variables
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'image-storage-bucket')
TABLE_NAME = os.environ.get('TABLE_NAME', 'image-metadata')

def create_table_if_not_exists():
    """Create DynamoDB table if it doesn't exist"""
    try:
        table = dynamodb.Table(TABLE_NAME)
        table.load()
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            table = dynamodb.create_table(
                TableName=TABLE_NAME,
                KeySchema=[
                    {
                        'AttributeName': 'image_id',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'image_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'user_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'created_at',
                        'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'user-id-index',
                        'KeySchema': [
                            {
                                'AttributeName': 'user_id',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'created_at',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        }
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            table.wait_until_exists()
        else:
            raise

def create_bucket_if_not_exists():
    """Create S3 bucket if it doesn't exist"""
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            s3_client.create_bucket(Bucket=BUCKET_NAME)
        else:
            raise
