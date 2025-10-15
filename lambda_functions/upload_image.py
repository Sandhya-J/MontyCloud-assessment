import json
import base64
import os
from datetime import datetime
from PIL import Image
import io
import uuid
from common import s3_client, dynamodb, BUCKET_NAME, TABLE_NAME, create_table_if_not_exists, create_bucket_if_not_exists

def lambda_handler(event, context):
    """
    Upload image with metadata to S3 and DynamoDB
    """
    try:
        # Initialize resources
        create_table_if_not_exists()
        create_bucket_if_not_exists()
        
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract required fields
        user_id = body.get('user_id')
        image_data = body.get('image_data')  # Base64 encoded image
        title = body.get('title', '')
        description = body.get('description', '')
        tags = body.get('tags', [])
        
        if not user_id or not image_data:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'user_id and image_data are required'
                })
            }
        
        # Generate unique image ID
        image_id = str(uuid.uuid4())
        
        # Decode and validate image
        try:
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Get image metadata
            width, height = image.size
            format_type = image.format or 'UNKNOWN'
            
            # Convert to JPEG for consistency
            output = io.BytesIO()
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            image.save(output, format='JPEG', quality=85)
            image_bytes = output.getvalue()
            
        except Exception as e:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': f'Invalid image data: {str(e)}'
                })
            }
        
        # Upload to S3
        s3_key = f"images/{user_id}/{image_id}.jpg"
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=image_bytes,
            ContentType='image/jpeg',
            Metadata={
                'user_id': user_id,
                'title': title,
                'description': description
            }
        )
        
        # Save metadata to DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        metadata = {
            'image_id': image_id,
            'user_id': user_id,
            'title': title,
            'description': description,
            'tags': tags,
            's3_key': s3_key,
            'width': width,
            'height': height,
            'format': format_type,
            'file_size': len(image_bytes),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=metadata)
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Image uploaded successfully',
                'image_id': image_id,
                'metadata': metadata
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
