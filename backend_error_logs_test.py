#!/usr/bin/env python3
"""
Backend API Testing Suite for Multi-Tenant SaaS Billing Platform
Test: Error Logs CRUD and WhatsApp Integration Testing

Review Request Tests:
1. Error Logs CRUD endpoints
2. WhatsApp test with fixed language code 
3. Error logging integration verification
"""

import requests
import json
from datetime import datetime
from typing import Optional

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

class ErrorLogsTestRunner:
    def __init__(self):
        self.admin_token = None
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append(f"{status} - {test_name}: {details}")
        print(f"{status} - {test_name}: {details}")
        
    def get_admin_token(self) -> bool:
        """Get admin authentication token."""
        try:
            # First seed the database
            seed_response = requests.post(f"{BACKEND_URL}/seed")
            if seed_response.status_code == 200:
                print("🌱 Database seeded successfully")
            
            response = requests.post(f"{BACKEND_URL}/auth/login", 
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.log_test("Admin Login", True, f"Token obtained: {self.admin_token[:20]}...")
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

    # ===== ERROR LOGS CRUD TESTS =====
    
    def test_error_logs_get(self) -> bool:
        """Test GET /api/admin/error-logs - Should return proper structure."""
        try:
            headers = self.get_admin_headers()
            response = requests.get(f"{BACKEND_URL}/admin/error-logs", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should return object with logs, total, page, per_page, total_pages
                required_keys = ["logs", "total", "page", "per_page", "total_pages"]
                missing_keys = [key for key in required_keys if key not in data]
                
                if missing_keys:
                    self.log_test("GET Error Logs Structure", False, 
                        f"Missing keys: {missing_keys}. Got: {list(data.keys())}")
                    return False
                
                # Verify logs is a list
                if not isinstance(data["logs"], list):
                    self.log_test("GET Error Logs Structure", False, 
                        f"'logs' should be list, got {type(data['logs'])}")
                    return False
                
                self.log_test("GET Error Logs Structure", True, 
                    f"Correct structure. Total: {data['total']}, Logs: {len(data['logs'])}")
                return True
            else:
                self.log_test("GET Error Logs Structure", False, 
                    f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("GET Error Logs Structure", False, f"Exception: {str(e)}")
            return False
    
    def test_error_logs_stats(self) -> bool:
        """Test GET /api/admin/error-logs/stats - Should return stats."""
        try:
            headers = self.get_admin_headers()
            response = requests.get(f"{BACKEND_URL}/admin/error-logs/stats", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should have stats with total, today, by_type
                expected_keys = ["total", "today", "by_type"]
                missing_keys = [key for key in expected_keys if key not in data]
                
                if missing_keys:
                    self.log_test("GET Error Logs Stats", False, 
                        f"Missing keys: {missing_keys}. Got: {list(data.keys())}")
                    return False
                
                # by_type should be an object with error type counts
                if not isinstance(data["by_type"], dict):
                    self.log_test("GET Error Logs Stats", False, 
                        f"'by_type' should be dict, got {type(data['by_type'])}")
                    return False
                
                self.log_test("GET Error Logs Stats", True, 
                    f"Stats retrieved: Total={data['total']}, Today={data['today']}, Types={len(data['by_type'])}")
                return True
            else:
                self.log_test("GET Error Logs Stats", False, 
                    f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("GET Error Logs Stats", False, f"Exception: {str(e)}")
            return False
    
    def test_error_logs_filter_by_type(self) -> bool:
        """Test GET /api/admin/error-logs?error_type=client_error - Filter by type."""
        try:
            headers = self.get_admin_headers()
            response = requests.get(f"{BACKEND_URL}/admin/error-logs?error_type=client_error", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should return filtered results
                if "logs" not in data:
                    self.log_test("Filter Error Logs by Type", False, 
                        f"Missing 'logs' key in response: {list(data.keys())}")
                    return False
                
                # Check if filtering works (all logs should have error_type=client_error if any exist)
                logs = data["logs"]
                if logs:
                    non_client_errors = [log for log in logs if log.get("error_type") != "client_error"]
                    if non_client_errors:
                        self.log_test("Filter Error Logs by Type", False, 
                            f"Found {len(non_client_errors)} logs with wrong error_type")
                        return False
                
                self.log_test("Filter Error Logs by Type", True, 
                    f"Filter working. Found {len(logs)} client_error logs")
                return True
            else:
                self.log_test("Filter Error Logs by Type", False, 
                    f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Filter Error Logs by Type", False, f"Exception: {str(e)}")
            return False
    
    def test_error_logs_search(self) -> bool:
        """Test GET /api/admin/error-logs?search=test - Search functionality."""
        try:
            headers = self.get_admin_headers()
            response = requests.get(f"{BACKEND_URL}/admin/error-logs?search=test", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should return search results
                if "logs" not in data:
                    self.log_test("Search Error Logs", False, 
                        f"Missing 'logs' key in response: {list(data.keys())}")
                    return False
                
                self.log_test("Search Error Logs", True, 
                    f"Search working. Found {len(data['logs'])} results for 'test'")
                return True
            else:
                self.log_test("Search Error Logs", False, 
                    f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Search Error Logs", False, f"Exception: {str(e)}")
            return False
    
    def test_delete_error_logs(self) -> bool:
        """Test DELETE /api/admin/error-logs - Clear all logs."""
        try:
            headers = self.get_admin_headers()
            response = requests.delete(f"{BACKEND_URL}/admin/error-logs", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Should return message with count
                if "message" not in data:
                    self.log_test("Clear Error Logs", False, 
                        f"Missing 'message' key in response: {list(data.keys())}")
                    return False
                
                message = data["message"]
                if "error logs" not in message.lower():
                    self.log_test("Clear Error Logs", False, 
                        f"Unexpected message format: '{message}'")
                    return False
                
                self.log_test("Clear Error Logs", True, f"Cleared logs: {message}")
                return True
            else:
                self.log_test("Clear Error Logs", False, 
                    f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Clear Error Logs", False, f"Exception: {str(e)}")
            return False

    # ===== WHATSAPP TESTS =====
    
    def test_save_whatsapp_config(self) -> bool:
        """Save WhatsApp configuration."""
        try:
            headers = self.get_admin_headers()
            response = requests.put(f"{BACKEND_URL}/admin/whatsapp-config", 
                json=WHATSAPP_CONFIG, headers=headers)
            
            if response.status_code == 200:
                self.log_test("Save WhatsApp Config", True, "Configuration saved successfully")
                return True
            else:
                self.log_test("Save WhatsApp Config", False, 
                    f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Save WhatsApp Config", False, f"Exception: {str(e)}")
            return False
    
    def test_whatsapp_send_test(self) -> tuple:
        """Test POST /api/admin/whatsapp-test with fixed en_US language code."""
        try:
            headers = self.get_admin_headers()
            test_data = {"phone_number": "919876543210"}
            response = requests.post(f"{BACKEND_URL}/admin/whatsapp-test", 
                json=test_data, headers=headers)
            
            # Expected responses according to review request:
            # a) 200 with success message (if number is in allowed list)
            # b) 400 with "not in allowed list" or "template not available" (user-friendly error)
            # c) NOT a raw 500 error
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("WhatsApp Test Message", True, 
                    f"Success response: {data}")
                return True, None
            elif response.status_code == 400:
                data = response.json()
                error_msg = data.get("detail", "")
                
                # Check if it's a user-friendly error message
                user_friendly_errors = [
                    "not in allowed list", 
                    "template not available", 
                    "not authorized",
                    "invalid phone number"
                ]
                
                is_user_friendly = any(phrase in error_msg.lower() for phrase in user_friendly_errors)
                
                if is_user_friendly:
                    self.log_test("WhatsApp Test Message", True, 
                        f"User-friendly 400 error (expected): {error_msg}")
                    return True, error_msg
                else:
                    self.log_test("WhatsApp Test Message", False, 
                        f"400 error but not user-friendly: {error_msg}")
                    return False, error_msg
            elif response.status_code == 500:
                # Check if it's a user-friendly 500 or raw 500
                try:
                    data = response.json()
                    error_msg = data.get("detail", "")
                    
                    # If the 500 has a user-friendly message, it's acceptable
                    if "WhatsApp" in error_msg or "template" in error_msg or "not available" in error_msg:
                        self.log_test("WhatsApp Test Message", True, 
                            f"User-friendly 500 error (acceptable): {error_msg}")
                        return True, error_msg
                    else:
                        self.log_test("WhatsApp Test Message", False, 
                            f"Raw 500 error (should not happen): {error_msg}")
                        return False, error_msg
                except:
                    self.log_test("WhatsApp Test Message", False, 
                        f"Raw 500 error without JSON (should not happen): {response.text}")
                    return False, response.text
            else:
                self.log_test("WhatsApp Test Message", False, 
                    f"Unexpected status {response.status_code}: {response.text}")
                return False, response.text
                
        except Exception as e:
            self.log_test("WhatsApp Test Message", False, f"Exception: {str(e)}")
            return False, str(e)

    # ===== ERROR LOGGING INTEGRATION TEST =====
    
    def test_error_logging_integration(self, whatsapp_error: Optional[str]) -> bool:
        """Test that errors are logged to error_logs collection."""
        try:
            # First, trigger a 404 error to generate an error log
            headers = self.get_admin_headers()
            requests.get(f"{BACKEND_URL}/admin/some-nonexistent-endpoint", headers=headers)
            
            # Now check error logs to see if errors were logged
            response = requests.get(f"{BACKEND_URL}/admin/error-logs", headers=headers)
            
            if response.status_code != 200:
                self.log_test("Error Logging Integration", False, 
                    f"Could not fetch error logs: {response.status_code}")
                return False
            
            data = response.json()
            logs = data.get("logs", [])
            
            if not logs:
                self.log_test("Error Logging Integration", False, 
                    "No error logs found after triggering errors")
                return False
            
            # Check for proper error log structure
            required_fields = ["error_type", "message", "endpoint", "status_code", "created_at"]
            
            valid_logs = []
            for log in logs:
                missing_fields = [field for field in required_fields if field not in log]
                if not missing_fields:
                    valid_logs.append(log)
            
            if not valid_logs:
                self.log_test("Error Logging Integration", False, 
                    f"No logs with proper structure. Required: {required_fields}")
                return False
            
            # Look for WhatsApp error if one was expected
            whatsapp_logs = [log for log in valid_logs if "whatsapp" in log.get("message", "").lower() 
                           or "whatsapp" in log.get("endpoint", "").lower()]
            
            details = f"Found {len(valid_logs)} valid error logs"
            if whatsapp_error:
                details += f", {len(whatsapp_logs)} WhatsApp-related"
            
            # Check if we have recent logs (within last minute)
            import datetime
            now = datetime.datetime.now()
            recent_logs = []
            for log in valid_logs:
                try:
                    log_time = datetime.datetime.fromisoformat(log["created_at"].replace('Z', '+00:00'))
                    if (now - log_time.replace(tzinfo=None)).total_seconds() < 300:  # 5 minutes
                        recent_logs.append(log)
                except:
                    continue
            
            if recent_logs:
                details += f", {len(recent_logs)} recent logs"
                
            self.log_test("Error Logging Integration", True, details)
            return True
            
        except Exception as e:
            self.log_test("Error Logging Integration", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run the complete test suite."""
        print("🎯 STARTING ERROR LOGS & WHATSAPP TESTS FOR MULTI-TENANT SAAS BILLING PLATFORM")
        print("=" * 90)
        
        # Step 1: Get admin token (includes seeding)
        if not self.get_admin_token():
            print("❌ Cannot continue without admin token")
            return
        
        print("\n📊 TESTING ERROR LOGS CRUD ENDPOINTS")
        print("-" * 50)
        
        # Step 2: Test Error Logs CRUD
        self.test_error_logs_get()
        self.test_error_logs_stats()  
        self.test_error_logs_filter_by_type()
        self.test_error_logs_search()
        
        print("\n📱 TESTING WHATSAPP FUNCTIONALITY") 
        print("-" * 50)
        
        # Step 3: Test WhatsApp
        self.test_save_whatsapp_config()
        whatsapp_success, whatsapp_error = self.test_whatsapp_send_test()
        
        print("\n🔗 TESTING ERROR LOGGING INTEGRATION")
        print("-" * 50)
        
        # Step 4: Test error logging integration
        self.test_error_logging_integration(whatsapp_error)
        
        print("\n🗑️ TESTING ERROR LOGS CLEANUP")
        print("-" * 50)
        
        # Step 5: Test clearing error logs (do this last)
        self.test_delete_error_logs()
        
        # Summary
        print("\n" + "=" * 90)
        print("📋 TEST SUMMARY:")
        print("=" * 90)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if "✅ PASS" in r])
        
        for result in self.test_results:
            print(result)
            
        print(f"\n🎯 OVERALL RESULT: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED - Error Logs & WhatsApp features working correctly!")
        else:
            print("⚠️  Some tests failed - Review details above")

if __name__ == "__main__":
    runner = ErrorLogsTestRunner()
    runner.run_all_tests()