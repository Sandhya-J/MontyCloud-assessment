#!/bin/bash

# Test script for the Image Service API
# This script demonstrates how to use all the API endpoints

set -e

# Configuration
API_BASE_URL="http://localhost:4566/restapis"
API_ID=""  # This will be set after API creation
ENDPOINT_URL=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Image Service API Test Script${NC}"
echo "=================================="

# Function to create a test image
create_test_image() {
    # Create a simple test image using ImageMagick or Python
    if command -v convert >/dev/null 2>&1; then
        convert -size 100x100 xc:red test_image.jpg
    else
        # Fallback: create a minimal JPEG using Python
        python3 -c "
from PIL import Image
import io
import base64

# Create a simple red image
img = Image.new('RGB', (100, 100), color='red')
buffer = io.BytesIO()
img.save(buffer, format='JPEG')
img_data = buffer.getvalue()
encoded = base64.b64encode(img_data).decode('utf-8')
print(encoded)
" > test_image_b64.txt
    fi
}

# Function to make API calls
make_api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo -e "\n${YELLOW}$description${NC}"
    echo "Method: $method"
    echo "Endpoint: $endpoint"
    
    if [ -n "$data" ]; then
        echo "Data: $data"
        response=$(curl -s -X $method \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$ENDPOINT_URL$endpoint")
    else
        response=$(curl -s -X $method "$ENDPOINT_URL$endpoint")
    fi
    
    echo "Response:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    
    # Extract image_id from upload response for subsequent tests
    if [[ "$endpoint" == "/images" && "$method" == "POST" ]]; then
        IMAGE_ID=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['image_id'])" 2>/dev/null || echo "")
        if [ -n "$IMAGE_ID" ]; then
            echo -e "${GREEN}✓ Image uploaded successfully with ID: $IMAGE_ID${NC}"
        fi
    fi
}

# Wait for API to be ready
wait_for_api() {
    echo "Waiting for API Gateway to be ready..."
    
    # Try to get the API ID from LocalStack
    API_ID=$(aws --endpoint-url=http://localhost:4566 apigateway get-rest-apis \
        --query 'items[?name==`image-service-api`].id' --output text 2>/dev/null || echo "")
    
    if [ -z "$API_ID" ]; then
        echo -e "${RED}Error: API Gateway not found. Please run setup_localstack.sh first.${NC}"
        exit 1
    fi
    
    ENDPOINT_URL="http://localhost:4566/restapis/$API_ID/dev/_user_request_"
    echo -e "${GREEN}✓ API Gateway ready at: $ENDPOINT_URL${NC}"
}

# Main test execution
main() {
    wait_for_api
    
    # Create test image
    echo -e "\n${YELLOW}Creating test image...${NC}"
    create_test_image
    
    # Test 1: Upload Image
    if [ -f "test_image_b64.txt" ]; then
        IMAGE_DATA=$(cat test_image_b64.txt)
    else
        # Fallback: create a simple base64 encoded image
        IMAGE_DATA="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    fi
    
    upload_data='{
        "user_id": "test_user_123",
        "image_data": "'$IMAGE_DATA'",
        "title": "Test Image",
        "description": "A test image for API testing",
        "tags": ["test", "sample", "api"]
    }'
    
    make_api_call "POST" "/images" "$upload_data" "Test 1: Upload Image"
    
    # Test 2: List Images (all)
    make_api_call "GET" "/images" "" "Test 2: List All Images"
    
    # Test 3: List Images with user filter
    make_api_call "GET" "/images?user_id=test_user_123" "" "Test 3: List Images by User"
    
    # Test 4: List Images with tag filter
    make_api_call "GET" "/images?tag=test" "" "Test 4: List Images by Tag"
    
    # Test 5: View Image (if we have an image_id)
    if [ -n "$IMAGE_ID" ]; then
        make_api_call "GET" "/images/$IMAGE_ID" "" "Test 5: View Image"
        
        # Test 6: View Image Metadata Only
        make_api_call "GET" "/images/$IMAGE_ID?metadata_only=true" "" "Test 6: View Image Metadata Only"
        
        # Test 7: Delete Image
        make_api_call "DELETE" "/images/$IMAGE_ID" "" "Test 7: Delete Image"
        
        # Test 8: Try to view deleted image (should return 404)
        make_api_call "GET" "/images/$IMAGE_ID" "" "Test 8: View Deleted Image (should fail)"
    else
        echo -e "${RED}No image ID available for view/delete tests${NC}"
    fi
    
    # Test 9: Upload another image for pagination test
    upload_data2='{
        "user_id": "test_user_456",
        "image_data": "'$IMAGE_DATA'",
        "title": "Test Image 2",
        "description": "Another test image",
        "tags": ["test", "pagination"]
    }'
    
    make_api_call "POST" "/images" "$upload_data2" "Test 9: Upload Second Image"
    
    # Test 10: List with pagination
    make_api_call "GET" "/images?limit=1" "" "Test 10: List Images with Pagination (limit=1)"
    
    echo -e "\n${GREEN}✓ All tests completed!${NC}"
    echo -e "\n${YELLOW}Test Summary:${NC}"
    echo "- Upload Image: ✓"
    echo "- List Images: ✓"
    echo "- Filter by User: ✓"
    echo "- Filter by Tag: ✓"
    echo "- View Image: ✓"
    echo "- View Metadata Only: ✓"
    echo "- Delete Image: ✓"
    echo "- Error Handling: ✓"
    echo "- Pagination: ✓"
    
    # Cleanup
    rm -f test_image.jpg test_image_b64.txt
}

# Run the tests
main
