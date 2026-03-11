#!/usr/bin/env python3
"""
Backend Testing for Two New Endpoints:
1. Backup Download - GET /api/admin/backup/download/{backup_id}
2. Change Password - PUT /api/auth/change-password

Testing multi-tenant SaaS billing platform backend APIs.
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Backend URL from frontend .env
BASE_URL = "https://syntax-inspector-1.preview.emergentagent.com/api"

# Admin credentials - try both possible emails from review request
ADMIN_EMAIL = "admin@saas.com"  # From seed data
ADMIN_EMAIL_ALT = "admin@system.com"  # From review request
ADMIN_PASSWORD = "admin123"

class BackendTester:
    def __init__(self):
        self.admin_token = None
        self.admin_email = None
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def log(self, message: str, status: str = "INFO"):
        """Log test messages with status."""
        print(f"[{status}] {message}")

    def make_request(self, method: str, endpoint: str, token: Optional[str] = None, 
                    data: Optional[Dict] = None, expect_json: bool = True) -> tuple:
        """Make HTTP request and return (status_code, response_data, headers)."""
        url = f"{BASE_URL}{endpoint}"
        headers = {}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
            
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            if expect_json:
                try:
                    return response.status_code, response.json(), response.headers
                except:
                    return response.status_code, {"error": "Invalid JSON response"}, response.headers
            else:
                return response.status_code, response.content, response.headers
                
        except Exception as e:
            self.log(f"Request error: {str(e)}", "ERROR")
            return 0, {"error": str(e)}, {}

    def login_admin(self) -> bool:
        """Login as admin and get JWT token."""
        self.log("=== ADMIN LOGIN ===")
        
        # Try both possible admin emails
        for email in [ADMIN_EMAIL, ADMIN_EMAIL_ALT]:
            login_data = {
                "email": email,
                "password": ADMIN_PASSWORD
            }
            
            status, response, _ = self.make_request('POST', '/auth/login', data=login_data)
            
            if status == 200 and 'access_token' in response:
                self.admin_token = response['access_token']
                self.admin_email = email  # Store successful email
                user_info = response.get('user', {})
                self.log(f"✅ Admin login successful - Email: {email}, Role: {user_info.get('role')}")
                return True
            else:
                self.log(f"Trying {email}... Status: {status}")
                
        self.log(f"❌ Admin login failed with both emails", "ERROR")
        return False

    def test_backup_download_endpoint(self):
        """Test backup creation and download functionality."""
        self.log("\n=== TESTING BACKUP DOWNLOAD ENDPOINT ===")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        # Step 1: Create a backup
        self.log("Step 1: Creating backup via POST /admin/backup/create")
        status, response, _ = self.make_request('POST', '/admin/backup/create', token=self.admin_token)
        
        if status != 200:
            self.log(f"❌ Backup creation failed - Status: {status}, Response: {response}", "ERROR")
            return False
            
        backup_info = response.get('backup', {})
        backup_id = backup_info.get('id')
        backup_filename = backup_info.get('filename')
        
        if not backup_id or not backup_filename:
            self.log(f"❌ Missing backup ID or filename - Response: {response}", "ERROR")
            return False
            
        self.log(f"✅ Backup created successfully - ID: {backup_id}, Filename: {backup_filename}")
        
        # Step 2: Download the backup
        self.log(f"Step 2: Downloading backup via GET /admin/backup/download/{backup_id}")
        status, content, headers = self.make_request('GET', f'/admin/backup/download/{backup_id}', 
                                                   token=self.admin_token, expect_json=False)
        
        # Verify response
        if status == 200:
            self.log("✅ Backup download successful (Status: 200)")
            
            # Check Content-Type
            content_type = headers.get('content-type', '')
            if 'application/gzip' in content_type:
                self.log("✅ Correct Content-Type: application/gzip")
            else:
                self.log(f"❌ Wrong Content-Type: {content_type} (expected: application/gzip)", "ERROR")
                
            # Check Content-Disposition header
            content_disposition = headers.get('content-disposition', '')
            if 'attachment' in content_disposition and backup_filename in content_disposition:
                self.log(f"✅ Correct Content-Disposition: {content_disposition}")
            else:
                self.log(f"❌ Wrong Content-Disposition: {content_disposition} (expected attachment with {backup_filename})", "ERROR")
                
            # Check content size (should be > 0)
            if isinstance(content, bytes) and len(content) > 0:
                self.log(f"✅ Downloaded content size: {len(content)} bytes")
            else:
                self.log("❌ Empty or invalid content downloaded", "ERROR")
                
        else:
            self.log(f"❌ Backup download failed - Status: {status}, Response: {content}", "ERROR")
            return False
            
        # Step 3: Test 404 for non-existent backup
        self.log("Step 3: Testing 404 for non-existent backup ID")
        fake_backup_id = "fake-id-999"
        status, response, _ = self.make_request('GET', f'/admin/backup/download/{fake_backup_id}', 
                                              token=self.admin_token)
        
        if status == 404:
            self.log("✅ Correctly returned 404 for non-existent backup ID")
        else:
            self.log(f"❌ Expected 404 but got {status} for non-existent backup", "ERROR")
            return False
            
        return True

    def test_change_password_endpoint(self):
        """Test change password functionality."""
        self.log("\n=== TESTING CHANGE PASSWORD ENDPOINT ===")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        original_password = ADMIN_PASSWORD
        new_password = "newpass123"
        
        # Step 1: Change password with correct current password
        self.log("Step 1: Changing password with correct current password")
        change_data = {
            "current_password": original_password,
            "new_password": new_password
        }
        
        status, response, _ = self.make_request('PUT', '/auth/change-password', 
                                              token=self.admin_token, data=change_data)
        
        if status == 200:
            self.log("✅ Password change successful with correct current password")
        else:
            self.log(f"❌ Password change failed - Status: {status}, Response: {response}", "ERROR")
            return False
            
        # Step 2: Change password back to original
        self.log("Step 2: Changing password back to original")
        change_back_data = {
            "current_password": new_password,
            "new_password": original_password
        }
        
        status, response, _ = self.make_request('PUT', '/auth/change-password', 
                                              token=self.admin_token, data=change_back_data)
        
        if status == 200:
            self.log("✅ Password changed back to original successfully")
        else:
            self.log(f"❌ Password change back failed - Status: {status}, Response: {response}", "ERROR")
            return False
            
        # Step 3: Test with wrong current password
        self.log("Step 3: Testing with wrong current password")
        wrong_password_data = {
            "current_password": "wrongpassword123",
            "new_password": "somepassword"
        }
        
        status, response, _ = self.make_request('PUT', '/auth/change-password', 
                                              token=self.admin_token, data=wrong_password_data)
        
        if status == 400 and "Current password is incorrect" in response.get('detail', ''):
            self.log("✅ Correctly returned 400 with 'Current password is incorrect' message")
        else:
            self.log(f"❌ Expected 400 with specific error message, got Status: {status}, Response: {response}", "ERROR")
            return False
            
        # Step 4: Test with short new password
        self.log("Step 4: Testing with new password less than 6 characters")
        short_password_data = {
            "current_password": original_password,
            "new_password": "abc"
        }
        
        status, response, _ = self.make_request('PUT', '/auth/change-password', 
                                              token=self.admin_token, data=short_password_data)
        
        if status == 400:
            self.log("✅ Correctly returned 400 for password less than 6 characters")
        else:
            self.log(f"❌ Expected 400 for short password, got Status: {status}, Response: {response}", "ERROR")
            return False
            
        return True

    def run_tests(self):
        """Run all endpoint tests."""
        self.log(f"Starting backend API testing for: {BASE_URL}")
        
        # Login first
        if not self.login_admin():
            self.log("❌ Could not authenticate admin user", "ERROR")
            return False
            
        # Run endpoint tests
        test_results = []
        
        # Test 1: Backup Download
        result1 = self.test_backup_download_endpoint()
        test_results.append(("Backup Download Endpoint", result1))
        
        # Test 2: Change Password
        result2 = self.test_change_password_endpoint()
        test_results.append(("Change Password Endpoint", result2))
        
        # Summary
        self.log("\n" + "="*60)
        self.log("FINAL TEST RESULTS")
        self.log("="*60)
        
        all_passed = True
        for test_name, passed in test_results:
            status_icon = "✅" if passed else "❌"
            self.log(f"{status_icon} {test_name}: {'PASSED' if passed else 'FAILED'}")
            if not passed:
                all_passed = False
                
        if all_passed:
            self.log("\n🎉 ALL TESTS PASSED - Both endpoints working correctly!")
        else:
            self.log("\n❌ SOME TESTS FAILED - Check individual test results above")
            
        return all_passed


if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_tests()
    sys.exit(0 if success else 1)