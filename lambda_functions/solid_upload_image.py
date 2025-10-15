# SOLID-Compliant Image Service Architecture

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import base64
from datetime import datetime
import uuid

# =============================================================================
# 1. SINGLE RESPONSIBILITY PRINCIPLE (SRP)
# =============================================================================

@dataclass
class ImageMetadata:
    """Single responsibility: Represent image metadata"""
    image_id: str
    user_id: str
    title: str
    description: str
    tags: List[str]
    s3_key: str
    width: int
    height: int
    format_type: str
    file_size: int
    created_at: str
    updated_at: str

class RequestValidator:
    """Single responsibility: Validate requests"""
    
    @staticmethod
    def validate_upload_request(body: Dict[str, Any]) -> tuple[bool, str]:
        if not body.get('user_id'):
            return False, "user_id is required"
        if not body.get('image_data'):
            return False, "image_data is required"
        return True, ""

class ImageProcessor:
    """Single responsibility: Process images"""
    
    @staticmethod
    def process_image(image_data: str) -> tuple[bytes, int, int, str]:
        """Process base64 image data and return processed bytes with metadata"""
        try:
            image_bytes = base64.b64decode(image_data)
            from PIL import Image
            import io
            
            image = Image.open(io.BytesIO(image_bytes))
            width, height = image.size
            format_type = image.format or 'UNKNOWN'
            
            # Convert to JPEG for consistency
            output = io.BytesIO()
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            image.save(output, format='JPEG', quality=85)
            processed_bytes = output.getvalue()
            
            return processed_bytes, width, height, format_type
        except Exception as e:
            raise ValueError(f"Invalid image data: {str(e)}")

class ResponseFormatter:
    """Single responsibility: Format responses"""
    
    @staticmethod
    def success_response(data: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(data)
        }
    
    @staticmethod
    def error_response(error_message: str, status_code: int = 400) -> Dict[str, Any]:
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': error_message})
        }

# =============================================================================
# 2. OPEN/CLOSED PRINCIPLE (OCP) & DEPENDENCY INVERSION PRINCIPLE (DIP)
# =============================================================================

class StorageInterface(ABC):
    """Interface for storage operations - follows DIP"""
    
    @abstractmethod
    def store_image(self, key: str, data: bytes, metadata: Dict[str, str]) -> None:
        pass
    
    @abstractmethod
    def retrieve_image(self, key: str) -> bytes:
        pass
    
    @abstractmethod
    def delete_image(self, key: str) -> None:
        pass

class MetadataRepositoryInterface(ABC):
    """Interface for metadata operations - follows DIP"""
    
    @abstractmethod
    def save_metadata(self, metadata: ImageMetadata) -> None:
        pass
    
    @abstractmethod
    def get_metadata(self, image_id: str) -> Optional[ImageMetadata]:
        pass
    
    @abstractmethod
    def list_metadata(self, filters: Dict[str, Any]) -> List[ImageMetadata]:
        pass
    
    @abstractmethod
    def delete_metadata(self, image_id: str) -> None:
        pass

# =============================================================================
# 3. LISKOV SUBSTITUTION PRINCIPLE (LSP)
# =============================================================================

class S3Storage(StorageInterface):
    """S3 implementation that can be substituted for any StorageInterface"""
    
    def __init__(self, bucket_name: str, s3_client):
        self.bucket_name = bucket_name
        self.s3_client = s3_client
    
    def store_image(self, key: str, data: bytes, metadata: Dict[str, str]) -> None:
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType='image/jpeg',
            Metadata=metadata
        )
    
    def retrieve_image(self, key: str) -> bytes:
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        return response['Body'].read()
    
    def delete_image(self, key: str) -> None:
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)

class DynamoDBMetadataRepository(MetadataRepositoryInterface):
    """DynamoDB implementation that can be substituted for any MetadataRepositoryInterface"""
    
    def __init__(self, table_name: str, dynamodb_resource):
        self.table_name = table_name
        self.table = dynamodb_resource.Table(table_name)
    
    def save_metadata(self, metadata: ImageMetadata) -> None:
        self.table.put_item(Item=metadata.__dict__)
    
    def get_metadata(self, image_id: str) -> Optional[ImageMetadata]:
        response = self.table.get_item(Key={'image_id': image_id})
        if 'Item' in response:
            return ImageMetadata(**response['Item'])
        return None
    
    def list_metadata(self, filters: Dict[str, Any]) -> List[ImageMetadata]:
        # Implementation for listing with filters
        if filters.get('user_id'):
            response = self.table.query(
                IndexName='user-id-index',
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': filters['user_id']}
            )
        else:
            response = self.table.scan()
        
        items = response.get('Items', [])
        if filters.get('tag'):
            items = [item for item in items if filters['tag'] in item.get('tags', [])]
        
        return [ImageMetadata(**item) for item in items]
    
    def delete_metadata(self, image_id: str) -> None:
        self.table.delete_item(Key={'image_id': image_id})

# =============================================================================
# 4. INTERFACE SEGREGATION PRINCIPLE (ISP)
# =============================================================================

class ImageUploadService:
    """Service that depends only on the interfaces it needs"""
    
    def __init__(self, 
                 storage: StorageInterface, 
                 metadata_repo: MetadataRepositoryInterface,
                 validator: RequestValidator,
                 processor: ImageProcessor,
                 formatter: ResponseFormatter):
        self.storage = storage
        self.metadata_repo = metadata_repo
        self.validator = validator
        self.processor = processor
        self.formatter = formatter
    
    def upload_image(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """Main business logic for image upload"""
        # Validate request
        is_valid, error_message = self.validator.validate_upload_request(request_body)
        if not is_valid:
            return self.formatter.error_response(error_message, 400)
        
        try:
            # Generate ID
            image_id = str(uuid.uuid4())
            
            # Process image
            processed_bytes, width, height, format_type = self.processor.process_image(
                request_body['image_data']
            )
            
            # Create metadata
            s3_key = f"images/{request_body['user_id']}/{image_id}.jpg"
            metadata = ImageMetadata(
                image_id=image_id,
                user_id=request_body['user_id'],
                title=request_body.get('title', ''),
                description=request_body.get('description', ''),
                tags=request_body.get('tags', []),
                s3_key=s3_key,
                width=width,
                height=height,
                format_type=format_type,
                file_size=len(processed_bytes),
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            
            # Store image and metadata
            self.storage.store_image(
                s3_key, 
                processed_bytes, 
                {
                    'user_id': metadata.user_id,
                    'title': metadata.title,
                    'description': metadata.description
                }
            )
            self.metadata_repo.save_metadata(metadata)
            
            return self.formatter.success_response({
                'message': 'Image uploaded successfully',
                'image_id': image_id,
                'metadata': metadata.__dict__
            }, 201)
            
        except ValueError as e:
            return self.formatter.error_response(str(e), 400)
        except Exception as e:
            return self.formatter.error_response(f'Internal server error: {str(e)}', 500)

# =============================================================================
# 5. FACTORY PATTERN FOR DEPENDENCY INJECTION
# =============================================================================

class ServiceFactory:
    """Factory to create services with proper dependencies"""
    
    @staticmethod
    def create_image_upload_service() -> ImageUploadService:
        # Create concrete implementations
        import boto3
        import os
        
        s3_client = boto3.client('s3', endpoint_url=os.environ.get('AWS_ENDPOINT_URL'))
        dynamodb_resource = boto3.resource('dynamodb', endpoint_url=os.environ.get('AWS_ENDPOINT_URL'))
        
        storage = S3Storage(os.environ.get('BUCKET_NAME', 'image-storage-bucket'), s3_client)
        metadata_repo = DynamoDBMetadataRepository(os.environ.get('TABLE_NAME', 'image-metadata'), dynamodb_resource)
        
        # Create service with injected dependencies
        return ImageUploadService(
            storage=storage,
            metadata_repo=metadata_repo,
            validator=RequestValidator(),
            processor=ImageProcessor(),
            formatter=ResponseFormatter()
        )

# =============================================================================
# 6. SOLID-COMPLIANT LAMBDA HANDLER
# =============================================================================

def lambda_handler(event, context):
    """SOLID-compliant Lambda handler"""
    try:
        # Parse request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Create service with injected dependencies
        service = ServiceFactory.create_image_upload_service()
        
        # Execute business logic
        return service.upload_image(body)
        
    except Exception as e:
        return ResponseFormatter.error_response(f'Internal server error: {str(e)}', 500)
