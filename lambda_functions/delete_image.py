import json
import os
from datetime import datetime
from common import s3_client, dynamodb, BUCKET_NAME, TABLE_NAME, create_table_if_not_exists

def lambda_handler(event, context):
    """
    Delete image from S3 and DynamoDB
    """
    try:
        # Initialize resources
        create_table_if_not_exists()
        
        # Parse path parameters
        image_id = event.get('pathParameters', {}).get('image_id')
        
        if not image_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'image_id is required'
                })
            }
        
        # Get metadata from DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={'image_id': image_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Image not found'
                })
            }
        
        item = response['Item']
        s3_key = item['s3_key']
        
        # Delete from S3
        try:
            s3_client.delete_object(Bucket=BUCKET_NAME, Key=s3_key)
        except Exception as e:
            # Continue with DynamoDB deletion even if S3 deletion fails
            print(f"Warning: Failed to delete from S3: {str(e)}")
        
        # Delete from DynamoDB
        table.delete_item(Key={'image_id': image_id})
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Image deleted successfully',
                'image_id': image_id
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }
