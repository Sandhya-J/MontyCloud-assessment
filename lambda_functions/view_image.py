import json
import os
from common import s3_client, dynamodb, BUCKET_NAME, TABLE_NAME, create_table_if_not_exists

def lambda_handler(event, context):
    """
    View/download image from S3
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
        
        # Get image from S3
        try:
            s3_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
            image_data = s3_response['Body'].read()
            
            # Check if client wants metadata only
            query_params = event.get('queryStringParameters') or {}
            metadata_only = query_params.get('metadata_only', 'false').lower() == 'true'
            
            if metadata_only:
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'image_id': item['image_id'],
                        'user_id': item['user_id'],
                        'title': item.get('title', ''),
                        'description': item.get('description', ''),
                        'tags': item.get('tags', []),
                        'width': item.get('width'),
                        'height': item.get('height'),
                        'file_size': item.get('file_size'),
                        'format': item.get('format'),
                        'created_at': item.get('created_at'),
                        'updated_at': item.get('updated_at')
                    })
                }
            else:
                # Return image with appropriate headers
                import base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'image_id': image_id,
                        'image_data': image_base64,
                        'content_type': 'image/jpeg',
                        'metadata': {
                            'title': item.get('title', ''),
                            'description': item.get('description', ''),
                            'tags': item.get('tags', []),
                            'width': item.get('width'),
                            'height': item.get('height'),
                            'file_size': item.get('file_size'),
                            'created_at': item.get('created_at')
                        }
                    })
                }
                
        except Exception as e:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': f'Image file not found: {str(e)}'
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
