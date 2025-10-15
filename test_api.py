#!/usr/bin/env python3
"""
Simple API Test Script for Image Service
Tests all endpoints with sample data
"""

import requests
import json
import base64
from PIL import Image
import io
import sys

def create_test_image():
    """Create a simple test image"""
    img = Image.new('RGB', (100, 100), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def test_api(api_base_url):
    """Test all API endpoints"""
    print(f"Testing API at: {api_base_url}")
    print("=" * 50)
    
    # Test data
    image_data = create_test_image()
    
    # Test 1: Upload Image
    print("\n1. Testing Image Upload...")
    upload_data = {
        "user_id": "test_user_123",
        "image_data": image_data,
        "title": "Test Image",
        "description": "A test image for API testing",
        "tags": ["test", "sample", "api"]
    }
    
    try:
        response = requests.post(f"{api_base_url}/images", json=upload_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print("✅ Upload successful!")
            print(f"Image ID: {result.get('image_id', 'N/A')}")
            image_id = result.get('image_id')
        else:
            print(f"❌ Upload failed: {response.text}")
            return
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return
    
    # Test 2: List Images
    print("\n2. Testing List Images...")
    try:
        response = requests.get(f"{api_base_url}/images")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ List successful!")
            print(f"Found {result.get('count', 0)} images")
        else:
            print(f"❌ List failed: {response.text}")
    except Exception as e:
        print(f"❌ List error: {str(e)}")
    
    # Test 3: List Images by User
    print("\n3. Testing List Images by User...")
    try:
        response = requests.get(f"{api_base_url}/images?user_id=test_user_123")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ User filter successful!")
            print(f"Found {result.get('count', 0)} images for user")
        else:
            print(f"❌ User filter failed: {response.text}")
    except Exception as e:
        print(f"❌ User filter error: {str(e)}")
    
    # Test 4: List Images by Tag
    print("\n4. Testing List Images by Tag...")
    try:
        response = requests.get(f"{api_base_url}/images?tag=test")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Tag filter successful!")
            print(f"Found {result.get('count', 0)} images with tag 'test'")
        else:
            print(f"❌ Tag filter failed: {response.text}")
    except Exception as e:
        print(f"❌ Tag filter error: {str(e)}")
    
    # Test 5: View Image (if we have an image_id)
    if image_id:
        print(f"\n5. Testing View Image (ID: {image_id})...")
        try:
            response = requests.get(f"{api_base_url}/images/{image_id}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ View successful!")
                print(f"Image data length: {len(result.get('image_data', ''))}")
            else:
                print(f"❌ View failed: {response.text}")
        except Exception as e:
            print(f"❌ View error: {str(e)}")
        
        # Test 6: View Metadata Only
        print(f"\n6. Testing View Metadata Only...")
        try:
            response = requests.get(f"{api_base_url}/images/{image_id}?metadata_only=true")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Metadata view successful!")
                print(f"Title: {result.get('title', 'N/A')}")
                print(f"Description: {result.get('description', 'N/A')}")
            else:
                print(f"❌ Metadata view failed: {response.text}")
        except Exception as e:
            print(f"❌ Metadata view error: {str(e)}")
        
        # Test 7: Delete Image
        print(f"\n7. Testing Delete Image...")
        try:
            response = requests.delete(f"{api_base_url}/images/{image_id}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Delete successful!")
                print(f"Message: {result.get('message', 'N/A')}")
            else:
                print(f"❌ Delete failed: {response.text}")
        except Exception as e:
            print(f"❌ Delete error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("API Testing Complete!")

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python test_api.py <API_BASE_URL>")
        print("Example: python test_api.py http://localhost:4566/restapis/abc123/dev/_user_request_")
        print("\nTo get the API URL:")
        print("1. Run the setup script first")
        print("2. Look for 'API Gateway URL' in the output")
        sys.exit(1)
    
    api_url = sys.argv[1]
    test_api(api_url)

if __name__ == "__main__":
    main()
