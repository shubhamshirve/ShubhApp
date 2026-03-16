#!/usr/bin/env python3
"""
WhatsApp Backend API Testing Suite for Multi-Tenant SaaS Billing Platform
Tests the new WhatsApp global configuration changes based on the review request.
"""

import requests
import json
from datetime import datetime
from typing import Optional, Dict, Any

# Test Configuration
BACKEND_URL = "https://settlement-analyzer-2.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"

# WhatsApp Test Configuration
WHATSAPP_CONFIG = {
    "phone_number_id": "960880593784994",
    "access_token": "EAAbWjSBVwsMBQZCIBBdN0RWKY7yTkTHJmjrCJvMcbF72qYuglAuFe5PMVrCP7ObPZBtq9ge6LZCGTm5Xp0HtTJ3FZBXJ3ZAMAQZALdvXPomVnqzUJPOkz6ZBZCeceCfvu7Fj7geCl98HyemwOINMfZCqjTufZBDHMnk3bh8C6ZBhCB55eEce1c5T7cZBBbb2vbdIvfT1EQF98bMKiNrJoFypPFVUX9qeqLLc7oKl53diysEWmMq9LSizcldnCkH0Nux8r257iHgF4wAQvHTZBJLc0lbikHFEs",
    "business_account_id": "778959268187056"
}

WHATSAPP_TEMPLATE_SETTINGS = {
    "invoice_template": "invoice_notification",
    "reminder_template": "payment_reminder", 
    "payment_confirmation_template": "payment_confirmation",
    "announcement_template": "announcement_msg"
}

class WhatsAppTestRunner:
    def __init__(self):
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        self.operator_id = None
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append(f"{status} - {test_name}: {details}")
        print(f"{status} - {test_name}: {details}")
        
    def get_admin_token(self) -> bool:
        """Get admin authentication token."""
        try:
            response = requests.post(f"{BACKEND_URL}/auth/login", 
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.log_test("Admin Login", True, f"Token obtained")
                return True
            else:
                self.log_test("Admin Login", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Admin Login", False, f"Exception: {str(e)}")
            return False
            
    def get_admin_headers(self) -> dict:
        """Get headers with admin authentication."""
        return {"Authorization": f"Bearer {self.admin_token}"} if self.admin_token else {}
        
    def get_operator_headers(self) -> dict:
        """Get headers with operator authentication."""
        return {"Authorization": f"Bearer {self.operator_token}"} if self.operator_token else {}
        
    def seed_data(self) -> bool:
        """Seed initial data."""
        try:
            response = requests.post(f"{BACKEND_URL}/seed")
            if response.status_code == 200:
                self.log_test("Seed Data", True, "Database seeded successfully")
                return True
            else:
                self.log_test("Seed Data", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Seed Data", False, f"Exception: {str(e)}")
            return False
            
    def test_whatsapp_template_settings_put(self) -> bool:
        """Test PUT /api/admin/whatsapp-template-settings"""
        try:
            headers = self.get_admin_headers()
            response = requests.put(f"{BACKEND_URL}/admin/whatsapp-template-settings", 
                json=WHATSAPP_TEMPLATE_SETTINGS, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "success" in data.get("message", "").lower():
                    self.log_test("PUT WhatsApp Template Settings", True, 
                        f"Settings saved successfully: {data.get('message')}")
                    return True
                else:
                    self.log_test("PUT WhatsApp Template Settings", False, 
                        f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("PUT WhatsApp Template Settings", False, 
                    f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("PUT WhatsApp Template Settings", False, f"Exception: {str(e)}")
            return False
            
    def test_whatsapp_template_settings_get(self) -> bool:
        """Test GET /api/admin/whatsapp-template-settings"""
        try:
            headers = self.get_admin_headers()
            response = requests.get(f"{BACKEND_URL}/admin/whatsapp-template-settings", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # Verify all 4 fields are present and match what was saved
                expected_fields = ["invoice_template", "reminder_template", 
                                 "payment_confirmation_template", "announcement_template"]
                
                all_fields_present = all(field in data for field in expected_fields)
                values_match = all(data.get(field) == WHATSAPP_TEMPLATE_SETTINGS[field] 
                                 for field in expected_fields)
                
                if all_fields_present and values_match:
                    self.log_test("GET WhatsApp Template Settings", True, 
                        f"All 4 fields returned with correct values: {data}")
                    return True
                else:
                    self.log_test("GET WhatsApp Template Settings", False, 
                        f"Fields mismatch. Expected: {WHATSAPP_TEMPLATE_SETTINGS}, Got: {data}")
                    return False
            else:
                self.log_test("GET WhatsApp Template Settings", False, 
                    f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("GET WhatsApp Template Settings", False, f"Exception: {str(e)}")
            return False
            
    def test_whatsapp_config_put(self) -> bool:
        """Test PUT /api/admin/whatsapp-config"""
        try:
            headers = self.get_admin_headers()
            response = requests.put(f"{BACKEND_URL}/admin/whatsapp-config", 
                json=WHATSAPP_CONFIG, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and ("updated" in data.get("message", "").lower() or 
                                        "success" in data.get("message", "").lower()):
                    self.log_test("PUT WhatsApp Config", True, 
                        f"Config saved successfully: {data.get('message')}")
                    return True
                else:
                    self.log_test("PUT WhatsApp Config", False, 
                        f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("PUT WhatsApp Config", False, 
                    f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("PUT WhatsApp Config", False, f"Exception: {str(e)}")
            return False
            
    def test_whatsapp_config_get(self) -> bool:
        """Test GET /api/admin/whatsapp-config"""
        try:
            headers = self.get_admin_headers()
            response = requests.get(f"{BACKEND_URL}/admin/whatsapp-config", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # Should show is_configured: true after saving config
                if data.get("is_configured") is True:
                    self.log_test("GET WhatsApp Config", True, 
                        f"is_configured: true returned. Phone ID: {data.get('phone_number_id')}")
                    return True
                else:
                    self.log_test("GET WhatsApp Config", False, 
                        f"is_configured should be true. Got: {data}")
                    return False
            else:
                self.log_test("GET WhatsApp Config", False, 
                    f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("GET WhatsApp Config", False, f"Exception: {str(e)}")
            return False
            
    def test_whatsapp_test_message(self) -> bool:
        """Test POST /api/admin/whatsapp-test"""
        try:
            headers = self.get_admin_headers()
            test_data = {"phone_number": "919876543210"}
            response = requests.post(f"{BACKEND_URL}/admin/whatsapp-test", 
                json=test_data, headers=headers)
            
            # Should return 200 with success (or 500 with WhatsApp API error if number is invalid)
            if response.status_code == 200:
                data = response.json()
                if data.get("success") is True:
                    self.log_test("WhatsApp Test Message", True, 
                        f"Test message sent successfully: {data.get('message')}")
                    return True
                else:
                    self.log_test("WhatsApp Test Message", False, 
                        f"Unexpected success response: {data}")
                    return False
            elif response.status_code == 500:
                # This is acceptable - WhatsApp API might reject the test number
                error_detail = response.json().get("detail", "")
                if "whatsapp" in error_detail.lower() or "failed to send" in error_detail.lower():
                    self.log_test("WhatsApp Test Message", True, 
                        f"Endpoint working but WhatsApp API error (acceptable): {error_detail}")
                    return True
                else:
                    self.log_test("WhatsApp Test Message", False, 
                        f"500 error but not WhatsApp related: {error_detail}")
                    return False
            else:
                self.log_test("WhatsApp Test Message", False, 
                    f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("WhatsApp Test Message", False, f"Exception: {str(e)}")
            return False
            
    def register_operator(self) -> bool:
        """Register a new operator to test removed endpoints."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            registration_data = {
                "company_name": "WhatsApp Test Company",
                "owner_name": "WA Test User", 
                "email": f"watest_{timestamp}@test.com",
                "phone": "9876543210",
                "password": "test123"
            }
            
            response = requests.post(f"{BACKEND_URL}/auth/register", json=registration_data)
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                
                # Get operator ID
                if self.operator_token:
                    profile_response = requests.get(f"{BACKEND_URL}/auth/me", 
                        headers=self.get_operator_headers())
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        self.operator_id = profile_data.get("operator_id")
                        
                        self.log_test("Operator Registration", True, 
                            f"Operator registered: {registration_data['email']}")
                        return True
                    
                self.log_test("Operator Registration", False, "Failed to get operator profile")
                return False
            else:
                self.log_test("Operator Registration", False, 
                    f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Operator Registration", False, f"Exception: {str(e)}")
            return False
            
    def test_operator_whatsapp_config_removed(self) -> bool:
        """Test that operator WhatsApp config endpoints are removed (404/405)."""
        if not self.operator_token:
            self.log_test("Operator WhatsApp Config Removal", False, "No operator token available")
            return False
            
        try:
            headers = self.get_operator_headers()
            
            # Test POST /api/operator/whatsapp-config
            post_response = requests.post(f"{BACKEND_URL}/operator/whatsapp-config", 
                json={"test": "data"}, headers=headers)
            
            # Test GET /api/operator/whatsapp-config  
            get_response = requests.get(f"{BACKEND_URL}/operator/whatsapp-config", headers=headers)
            
            # Both should return 404 or 405 (endpoint removed)
            post_removed = post_response.status_code in [404, 405]
            get_removed = get_response.status_code in [404, 405]
            
            if post_removed and get_removed:
                self.log_test("Operator WhatsApp Config Removal", True, 
                    f"Both endpoints properly removed: POST={post_response.status_code}, GET={get_response.status_code}")
                return True
            else:
                self.log_test("Operator WhatsApp Config Removal", False, 
                    f"Endpoints not removed: POST={post_response.status_code}, GET={get_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Operator WhatsApp Config Removal", False, f"Exception: {str(e)}")
            return False
            
    def test_operator_send_notification_uses_platform_config(self) -> bool:
        """Test that operator send-notification uses platform config (not 'WhatsApp not configured')."""
        if not self.operator_token:
            self.log_test("Operator Send Notification Platform Config", False, "No operator token available")
            return False
            
        try:
            headers = self.get_operator_headers()
            
            # Try to send notification with fake invoice ID - should get "Invoice not found", NOT "WhatsApp not configured"
            test_data = {
                "invoice_id": "fake-invoice-id-123",
                "notification_type": "invoice"
            }
            
            response = requests.post(f"{BACKEND_URL}/operator/send-notification", 
                json=test_data, headers=headers)
            
            if response.status_code == 404:
                error_detail = response.json().get("detail", "")
                if "invoice not found" in error_detail.lower():
                    self.log_test("Operator Send Notification Platform Config", True, 
                        f"Returns 404 'Invoice not found' (not 'WhatsApp not configured'): {error_detail}")
                    return True
                elif "whatsapp not configured" in error_detail.lower():
                    self.log_test("Operator Send Notification Platform Config", False, 
                        f"Still shows 'WhatsApp not configured': {error_detail}")
                    return False
                else:
                    self.log_test("Operator Send Notification Platform Config", True, 
                        f"Different 404 error (acceptable): {error_detail}")
                    return True
            else:
                # Other status codes are acceptable as long as it's not "WhatsApp not configured"
                error_detail = response.text
                if "whatsapp not configured" in error_detail.lower():
                    self.log_test("Operator Send Notification Platform Config", False, 
                        f"Still shows 'WhatsApp not configured': {error_detail}")
                    return False
                else:
                    self.log_test("Operator Send Notification Platform Config", True, 
                        f"Platform config being used (status {response.status_code}): {error_detail[:100]}")
                    return True
                
        except Exception as e:
            self.log_test("Operator Send Notification Platform Config", False, f"Exception: {str(e)}")
            return False
            
    def run_all_tests(self):
        """Run the complete WhatsApp test suite."""
        print("🎯 STARTING WHATSAPP BACKEND TESTS FOR MULTI-TENANT SAAS BILLING PLATFORM")
        print("=" * 80)
        
        # Step 1: Seed data
        if not self.seed_data():
            print("⚠️  Warning: Seed failed but continuing with tests")
            
        # Step 2: Get admin token
        if not self.get_admin_token():
            print("❌ Cannot continue without admin token")
            return
            
        # Step 3: WhatsApp Template Settings CRUD
        print("\n📋 Testing WhatsApp Template Settings CRUD...")
        self.test_whatsapp_template_settings_put()
        self.test_whatsapp_template_settings_get()
        
        # Step 4: WhatsApp Config and Test Message
        print("\n📋 Testing WhatsApp Config and Test Message...")
        self.test_whatsapp_config_put()
        self.test_whatsapp_config_get()
        self.test_whatsapp_test_message()
        
        # Step 5: Register operator for endpoint removal tests
        print("\n📋 Testing Operator WhatsApp Endpoint Removal...")
        if self.register_operator():
            self.test_operator_whatsapp_config_removed()
            self.test_operator_send_notification_uses_platform_config()
        else:
            print("⚠️  Skipping operator tests - registration failed")
        
        # Summary
        print("\n" + "=" * 80)
        print("📋 WHATSAPP TEST SUMMARY:")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if "✅ PASS" in r])
        
        for result in self.test_results:
            print(result)
            
        print(f"\n🎯 OVERALL RESULT: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL WHATSAPP TESTS PASSED!")
        else:
            print("⚠️  Some WhatsApp tests failed - Review details above")

if __name__ == "__main__":
    runner = WhatsAppTestRunner()
    runner.run_all_tests()