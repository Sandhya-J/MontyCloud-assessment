import json
import os
from datetime import datetime
from common import dynamodb, TABLE_NAME, create_table_if_not_exists

def lambda_handler(event, context):
    """
    List all images with filtering capabilities
    """
    try:
        # Initialize resources
        create_table_if_not_exists()
        
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        
        user_id = query_params.get('user_id')
        tag_filter = query_params.get('tag')
        limit = int(query_params.get('limit', 20))
        last_key = query_params.get('last_key')
        
        table = dynamodb.Table(TABLE_NAME)
        
        # Build query parameters
        if user_id:
            # Query by user_id using GSI
            query_params_db = {
                'IndexName': 'user-id-index',
                'KeyConditionExpression': 'user_id = :user_id',
                'ExpressionAttributeValues': {
                    ':user_id': user_id
                },
                'Limit': limit,
                'ScanIndexForward': False  # Sort by created_at descending
            }
            
            if last_key:
                query_params_db['ExclusiveStartKey'] = json.loads(last_key)
            
            response = table.query(**query_params_db)
        else:
            # Scan all items
            scan_params = {
                'Limit': limit
            }
            
            if last_key:
                scan_params['ExclusiveStartKey'] = json.loads(last_key)
            
            response = table.scan(**scan_params)
        
        # Filter by tag if specified
        items = response.get('Items', [])
        if tag_filter:
            items = [item for item in items if tag_filter in item.get('tags', [])]
        
        # Format response
        images = []
        for item in items:
            images.append({
                'image_id': item['image_id'],
                'user_id': item['user_id'],
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'tags': item.get('tags', []),
                'width': item.get('width'),
                'height': item.get('height'),
                'file_size': item.get('file_size'),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at')
            })
        
        # Prepare pagination info
        next_key = None
        if 'LastEvaluatedKey' in response:
            next_key = json.dumps(response['LastEvaluatedKey'])
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'images': images,
                'count': len(images),
                'next_key': next_key,
                'has_more': next_key is not None
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
