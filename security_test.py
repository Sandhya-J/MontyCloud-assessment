#!/usr/bin/env python3
"""
Security Testing Script for Image Service
Tests various security vulnerabilities and attack vectors
"""

import json
import base64
import requests
import time
from typing import Dict, Any, List

class SecurityTester:
    """Comprehensive security testing for the Image Service API"""
    
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
        self.test_results = []
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    Details: {details}")
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
    
    def test_path_traversal_attack(self):
        """Test for path traversal vulnerabilities"""
        print("\n🔍 Testing Path Traversal Attacks...")
        
        malicious_user_ids = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc//passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        for malicious_id in malicious_user_ids:
            payload = {
                "user_id": malicious_id,
                "image_data": self.create_test_image(),
                "title": "Test"
            }
            
            try:
                response = requests.post(f"{self.api_base_url}/images", json=payload)
                # Should be rejected with 400 error
                if response.status_code == 400:
                    self.log_test(f"Path traversal: {malicious_id}", True, "Properly rejected")
                else:
                    self.log_test(f"Path traversal: {malicious_id}", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Path traversal: {malicious_id}", False, f"Exception: {str(e)}")
    
    def test_sql_injection_attack(self):
        """Test for SQL injection vulnerabilities"""
        print("\n🔍 Testing SQL Injection Attacks...")
        
        malicious_inputs = [
            "'; DROP TABLE images; --",
            "1' OR '1'='1",
            "admin'--",
            "1' UNION SELECT * FROM users--"
        ]
        
        for malicious_input in malicious_inputs:
            # Test in user_id field
            payload = {
                "user_id": malicious_input,
                "image_data": self.create_test_image(),
                "title": "Test"
            }
            
            try:
                response = requests.post(f"{self.api_base_url}/images", json=payload)
                if response.status_code == 400:
                    self.log_test(f"SQL injection in user_id: {malicious_input}", True, "Properly rejected")
                else:
                    self.log_test(f"SQL injection in user_id: {malicious_input}", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"SQL injection in user_id: {malicious_input}", False, f"Exception: {str(e)}")
    
    def test_xss_attack(self):
        """Test for Cross-Site Scripting vulnerabilities"""
        print("\n🔍 Testing XSS Attacks...")
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//"
        ]
        
        for payload in xss_payloads:
            # Test in title field
            request_data = {
                "user_id": "test_user",
                "image_data": self.create_test_image(),
                "title": payload,
                "description": payload
            }
            
            try:
                response = requests.post(f"{self.api_base_url}/images", json=request_data)
                response_data = response.json()
                
                # Check if payload is sanitized in response
                if payload in str(response_data):
                    self.log_test(f"XSS in title: {payload}", False, "Payload not sanitized")
                else:
                    self.log_test(f"XSS in title: {payload}", True, "Payload properly sanitized")
            except Exception as e:
                self.log_test(f"XSS in title: {payload}", False, f"Exception: {str(e)}")
    
    def test_file_size_limits(self):
        """Test file size restrictions"""
        print("\n🔍 Testing File Size Limits...")
        
        # Create a large base64 string (simulating large image)
        large_data = "A" * (20 * 1024 * 1024)  # 20MB
        
        payload = {
            "user_id": "test_user",
            "image_data": large_data,
            "title": "Large Image Test"
        }
        
        try:
            response = requests.post(f"{self.api_base_url}/images", json=payload)
            if response.status_code == 413 or response.status_code == 400:
                self.log_test("File size limit", True, "Large file properly rejected")
            else:
                self.log_test("File size limit", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("File size limit", False, f"Exception: {str(e)}")
    
    def test_malicious_file_upload(self):
        """Test malicious file uploads"""
        print("\n🔍 Testing Malicious File Uploads...")
        
        # Create fake image headers for different file types
        malicious_files = [
            # Fake JPEG with embedded script
            base64.b64encode(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01<script>alert("XSS")</script>').decode(),
            # Fake PNG with embedded script
            base64.b64encode(b'\x89PNG\r\n\x1a\n<script>alert("XSS")</script>').decode(),
            # Plain text file
            base64.b64encode(b'This is not an image file').decode(),
            # Empty data
            "",
            # Invalid base64
            "This is not base64 data!!!"
        ]
        
        for i, malicious_data in enumerate(malicious_files):
            payload = {
                "user_id": "test_user",
                "image_data": malicious_data,
                "title": f"Malicious File {i}"
            }
            
            try:
                response = requests.post(f"{self.api_base_url}/images", json=payload)
                if response.status_code == 400:
                    self.log_test(f"Malicious file {i}", True, "Properly rejected")
                else:
                    self.log_test(f"Malicious file {i}", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Malicious file {i}", False, f"Exception: {str(e)}")
    
    def test_rate_limiting(self):
        """Test rate limiting (if implemented)"""
        print("\n🔍 Testing Rate Limiting...")
        
        # Send multiple requests rapidly
        success_count = 0
        for i in range(20):
            payload = {
                "user_id": f"rate_test_user_{i}",
                "image_data": self.create_test_image(),
                "title": f"Rate Test {i}"
            }
            
            try:
                response = requests.post(f"{self.api_base_url}/images", json=payload)
                if response.status_code == 200 or response.status_code == 201:
                    success_count += 1
                time.sleep(0.1)  # Small delay between requests
            except Exception:
                pass
        
        if success_count < 20:
            self.log_test("Rate limiting", True, f"Only {success_count}/20 requests succeeded")
        else:
            self.log_test("Rate limiting", False, "No rate limiting detected")
    
    def test_input_validation(self):
        """Test input validation"""
        print("\n🔍 Testing Input Validation...")
        
        invalid_inputs = [
            # Empty user_id
            {"user_id": "", "image_data": self.create_test_image()},
            # None user_id
            {"user_id": None, "image_data": self.create_test_image()},
            # Numeric user_id
            {"user_id": 123, "image_data": self.create_test_image()},
            # Very long user_id
            {"user_id": "a" * 1000, "image_data": self.create_test_image()},
            # Special characters in user_id
            {"user_id": "user@#$%^&*()", "image_data": self.create_test_image()},
        ]
        
        for i, invalid_input in enumerate(invalid_inputs):
            try:
                response = requests.post(f"{self.api_base_url}/images", json=invalid_input)
                if response.status_code == 400:
                    self.log_test(f"Input validation {i}", True, "Invalid input properly rejected")
                else:
                    self.log_test(f"Input validation {i}", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Input validation {i}", False, f"Exception: {str(e)}")
    
    def test_error_information_disclosure(self):
        """Test for information disclosure in error messages"""
        print("\n🔍 Testing Error Information Disclosure...")
        
        # Try to trigger various errors
        test_cases = [
            {"invalid": "data"},  # Invalid JSON structure
            {"user_id": "test", "image_data": "invalid_base64"},  # Invalid base64
            {"user_id": "test"},  # Missing required field
        ]
        
        for i, test_case in enumerate(test_cases):
            try:
                response = requests.post(f"{self.api_base_url}/images", json=test_case)
                response_data = response.json()
                
                # Check if error message contains sensitive information
                error_message = response_data.get('error', '')
                sensitive_patterns = [
                    'traceback', 'exception', 'stack', 'line', 'file',
                    'aws', 'dynamodb', 's3', 'lambda', 'internal'
                ]
                
                contains_sensitive = any(pattern in error_message.lower() for pattern in sensitive_patterns)
                
                if contains_sensitive:
                    self.log_test(f"Error disclosure {i}", False, f"Sensitive info leaked: {error_message}")
                else:
                    self.log_test(f"Error disclosure {i}", True, "No sensitive information disclosed")
            except Exception as e:
                self.log_test(f"Error disclosure {i}", False, f"Exception: {str(e)}")
    
    def create_test_image(self) -> str:
        """Create a small test image in base64 format"""
        from PIL import Image
        import io
        
        # Create a simple 10x10 red image
        img = Image.new('RGB', (10, 10), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def run_all_tests(self):
        """Run all security tests"""
        print("🔒 Starting Security Testing for Image Service API")
        print("=" * 60)
        
        self.test_path_traversal_attack()
        self.test_sql_injection_attack()
        self.test_xss_attack()
        self.test_file_size_limits()
        self.test_malicious_file_upload()
        self.test_rate_limiting()
        self.test_input_validation()
        self.test_error_information_disclosure()
        
        # Summary
        print("\n" + "=" * 60)
        print("🔒 Security Test Summary")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['passed'])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['details']}")
        
        return passed == total

def main():
    """Main function to run security tests"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python security_test.py <API_BASE_URL>")
        print("Example: python security_test.py http://localhost:4566/restapis/abc123/dev/_user_request_")
        sys.exit(1)
    
    api_url = sys.argv[1]
    tester = SecurityTester(api_url)
    
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ All security tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some security tests failed. Review the results above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
