import json
import base64
import os
import re
import hashlib
import hmac
from datetime import datetime, timedelta
from PIL import Image
import io
import uuid
from typing import Dict, Any, Optional, Tuple
from common import s3_client, dynamodb, BUCKET_NAME, TABLE_NAME, create_table_if_not_exists, create_bucket_if_not_exists

# Security Configuration
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500
MAX_TAGS_COUNT = 10
ALLOWED_IMAGE_FORMATS = ['JPEG', 'PNG', 'GIF', 'WEBP']
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')

class SecurityError(Exception):
    """Custom exception for security-related errors"""
    pass

class InputValidator:
    """Secure input validation and sanitization"""
    
    @staticmethod
    def validate_user_id(user_id: str) -> str:
        """Validate and sanitize user ID"""
        if not user_id or not isinstance(user_id, str):
            raise SecurityError("Invalid user_id format")
        
        # Remove dangerous characters and limit length
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', user_id.strip())
        if len(sanitized) < 3 or len(sanitized) > 50:
            raise SecurityError("user_id must be 3-50 characters")
        
        return sanitized
    
    @staticmethod
    def validate_image_data(image_data: str) -> bytes:
        """Validate and decode image data"""
        if not image_data or not isinstance(image_data, str):
            raise SecurityError("Invalid image_data format")
        
        # Check base64 format
        if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', image_data):
            raise SecurityError("Invalid base64 format")
        
        try:
            decoded = base64.b64decode(image_data)
        except Exception:
            raise SecurityError("Invalid base64 data")
        
        # Check size limit
        if len(decoded) > MAX_IMAGE_SIZE:
            raise SecurityError(f"Image too large. Max size: {MAX_IMAGE_SIZE} bytes")
        
        return decoded
    
    @staticmethod
    def validate_text_field(text: str, field_name: str, max_length: int) -> str:
        """Validate and sanitize text fields"""
        if not isinstance(text, str):
            return ""
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', text.strip())
        
        if len(sanitized) > max_length:
            raise SecurityError(f"{field_name} too long. Max length: {max_length}")
        
        return sanitized
    
    @staticmethod
    def validate_tags(tags: list) -> list:
        """Validate and sanitize tags"""
        if not isinstance(tags, list):
            return []
        
        if len(tags) > MAX_TAGS_COUNT:
            raise SecurityError(f"Too many tags. Max count: {MAX_TAGS_COUNT}")
        
        sanitized_tags = []
        for tag in tags:
            if isinstance(tag, str):
                # Remove dangerous characters and limit length
                clean_tag = re.sub(r'[^a-zA-Z0-9_-]', '', tag.strip())
                if len(clean_tag) > 0 and len(clean_tag) <= 50:
                    sanitized_tags.append(clean_tag)
        
        return sanitized_tags

class ImageProcessor:
    """Secure image processing"""
    
    @staticmethod
    def process_image(image_bytes: bytes) -> Tuple[bytes, int, int, str]:
        """Process image with security checks"""
        try:
            # Validate image format
            image = Image.open(io.BytesIO(image_bytes))
            
            # Check if format is allowed
            if image.format not in ALLOWED_IMAGE_FORMATS:
                raise SecurityError(f"Unsupported image format: {image.format}")
            
            # Get dimensions
            width, height = image.size
            
            # Check dimensions (prevent extremely large images)
            if width > 4096 or height > 4096:
                raise SecurityError("Image dimensions too large")
            
            # Convert to JPEG for consistency and security
            output = io.BytesIO()
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            image.save(output, format='JPEG', quality=85, optimize=True)
            processed_bytes = output.getvalue()
            
            return processed_bytes, width, height, image.format or 'JPEG'
            
        except Exception as e:
            raise SecurityError(f"Invalid image data: {str(e)}")

class SecureS3Manager:
    """Secure S3 operations with path validation"""
    
    @staticmethod
    def generate_secure_key(user_id: str, image_id: str) -> str:
        """Generate secure S3 key preventing path traversal"""
        # Double sanitization
        safe_user_id = re.sub(r'[^a-zA-Z0-9_-]', '', user_id)
        safe_image_id = re.sub(r'[^a-zA-Z0-9_-]', '', image_id)
        
        # Generate hash-based path for additional security
        user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:8]
        
        return f"images/{user_hash}/{safe_user_id}/{safe_image_id}.jpg"
    
    @staticmethod
    def upload_image(key: str, image_bytes: bytes, metadata: Dict[str, str]) -> None:
        """Upload image with security headers"""
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=image_bytes,
            ContentType='image/jpeg',
            Metadata=metadata,
            ServerSideEncryption='AES256',  # Enable encryption
            CacheControl='private, max-age=3600'  # Security headers
        )

class SecureResponseFormatter:
    """Secure response formatting"""
    
    @staticmethod
    def success_response(data: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
        """Format success response with security headers"""
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://yourdomain.com'),
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
            },
            'body': json.dumps(data, ensure_ascii=False)
        }
    
    @staticmethod
    def error_response(error_message: str, status_code: int = 400) -> Dict[str, Any]:
        """Format error response without information disclosure"""
        # Log detailed error internally (not exposed to client)
        print(f"Error {status_code}: {error_message}")
        
        # Return generic error message to client
        generic_message = "An error occurred processing your request"
        if status_code == 400:
            generic_message = "Invalid request"
        elif status_code == 401:
            generic_message = "Unauthorized"
        elif status_code == 403:
            generic_message = "Forbidden"
        elif status_code == 413:
            generic_message = "Request too large"
        
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://yourdomain.com'),
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY'
            },
            'body': json.dumps({'error': generic_message})
        }

def validate_request_size(event: Dict[str, Any]) -> None:
    """Validate request size to prevent DoS attacks"""
    # Check if body is too large
    body = event.get('body', '')
    if isinstance(body, str) and len(body) > MAX_IMAGE_SIZE * 2:  # Base64 is ~33% larger
        raise SecurityError("Request too large")

def secure_lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Secure image upload handler with comprehensive security measures
    """
    try:
        # Initialize security components
        validator = InputValidator()
        processor = ImageProcessor()
        s3_manager = SecureS3Manager()
        formatter = SecureResponseFormatter()
        
        # Validate request size
        validate_request_size(event)
        
        # Initialize resources
        create_table_if_not_exists()
        create_bucket_if_not_exists()
        
        # Parse and validate request body
        if isinstance(event.get('body'), str):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                return formatter.error_response("Invalid JSON format", 400)
        else:
            body = event.get('body', {})
        
        if not isinstance(body, dict):
            return formatter.error_response("Invalid request format", 400)
        
        # Validate and sanitize all inputs
        try:
            user_id = validator.validate_user_id(body.get('user_id', ''))
            image_data = validator.validate_image_data(body.get('image_data', ''))
            title = validator.validate_text_field(body.get('title', ''), 'title', MAX_TITLE_LENGTH)
            description = validator.validate_text_field(body.get('description', ''), 'description', MAX_DESCRIPTION_LENGTH)
            tags = validator.validate_tags(body.get('tags', []))
        except SecurityError as e:
            return formatter.error_response(str(e), 400)
        
        # Process image securely
        try:
            processed_bytes, width, height, format_type = processor.process_image(image_data)
        except SecurityError as e:
            return formatter.error_response(str(e), 400)
        
        # Generate secure identifiers
        image_id = str(uuid.uuid4())
        s3_key = s3_manager.generate_secure_key(user_id, image_id)
        
        # Create metadata
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
            'file_size': len(processed_bytes),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Upload to S3 securely
        s3_manager.upload_image(
            s3_key,
            processed_bytes,
            {
                'user_id': user_id,
                'title': title,
                'description': description,
                'upload_time': metadata['created_at']
            }
        )
        
        # Save metadata to DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item=metadata)
        
        # Return success response
        return formatter.success_response({
            'message': 'Image uploaded successfully',
            'image_id': image_id,
            'metadata': {
                'image_id': image_id,
                'user_id': user_id,
                'title': title,
                'description': description,
                'tags': tags,
                'width': width,
                'height': height,
                'file_size': len(processed_bytes),
                'created_at': metadata['created_at']
            }
        }, 201)
        
    except SecurityError as e:
        return formatter.error_response(str(e), 400)
    except Exception as e:
        # Log error internally but don't expose details
        print(f"Unexpected error: {str(e)}")
        return formatter.error_response("Internal server error", 500)

# Export the secure handler
lambda_handler = secure_lambda_handler
