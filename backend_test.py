#!/usr/bin/env python3

import requests
import json
import sys

# Backend URL
BASE_URL = "https://syntax-inspector-1.preview.emergentagent.com/api"

class TestRunner:
    def __init__(self):
        self.token = None
        self.passed_tests = 0
        self.total_tests = 0
        
    def log(self, message, color="white"):
        colors = {
            "green": "\033[92m",
            "red": "\033[91m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "white": "\033[97m",
            "reset": "\033[0m"
        }
        print(f"{colors.get(color, colors['white'])}{message}{colors['reset']}")

    def test_api_call(self, method, endpoint, data=None, params=None, description="", expected_status=200):
        """Make API call and validate response"""
        self.total_tests += 1
        
        url = f"{BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, params=params)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, params=params)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, params=params)
            else:
                self.log(f"❌ Test {self.total_tests}: {description} - Unsupported method {method}", "red")
                return None
                
            # Check status code
            if response.status_code == expected_status:
                self.passed_tests += 1
                self.log(f"✅ Test {self.total_tests}: {description} - Status {response.status_code}", "green")
                try:
                    return response.json()
                except:
                    return response.text
            else:
                self.log(f"❌ Test {self.total_tests}: {description} - Expected {expected_status}, got {response.status_code}", "red")
                self.log(f"   Response: {response.text}", "red")
                return None
                
        except Exception as e:
            self.log(f"❌ Test {self.total_tests}: {description} - Exception: {str(e)}", "red")
            return None

    def login_admin(self):
        """Login as admin and store token"""
        self.log("\n🔐 ADMIN LOGIN TEST", "blue")
        
        # Try first credential combination
        login_data = {
            "email": "admin@saas.com",
            "password": "admin123"
        }
        
        result = self.test_api_call(
            "POST", 
            "/auth/login", 
            data=login_data, 
            description="Admin login (admin@saas.com/admin123)"
        )
        
        if result and "access_token" in result:
            self.token = result["access_token"]
            self.log(f"   ✅ Token obtained: {self.token[:20]}...", "green")
            return True
            
        # Try alternative credential combination
        self.log("   Trying alternative credentials...", "yellow")
        login_data["email"] = "admin@system.com"
        
        result = self.test_api_call(
            "POST", 
            "/auth/login", 
            data=login_data, 
            description="Admin login (admin@system.com/admin123)"
        )
        
        if result and "access_token" in result:
            self.token = result["access_token"]
            self.log(f"   ✅ Token obtained: {self.token[:20]}...", "green")
            return True
        else:
            self.log("   ❌ Could not login with either credential set", "red")
            return False

    def test_audit_logs_endpoint(self):
        """Test basic audit logs endpoint"""
        self.log("\n📊 AUDIT LOGS BASIC TEST", "blue")
        
        result = self.test_api_call(
            "GET",
            "/admin/audit-logs",
            description="GET /api/admin/audit-logs (basic)"
        )
        
        if result:
            # Verify response is an object with logs and total keys
            if isinstance(result, dict) and "logs" in result and "total" in result:
                self.log(f"   ✅ Response is object with 'logs' and 'total' keys", "green")
                self.log(f"   📈 Total logs: {result['total']}, Returned: {len(result['logs'])}", "blue")
                return True
            else:
                self.log(f"   ❌ Response is not object with expected structure: {type(result)}", "red")
                if isinstance(result, list):
                    self.log(f"   ❌ ERROR: Response is plain array (should be object)", "red")
                return False
        return False

    def test_audit_logs_filters(self):
        """Test audit logs with various filters"""
        self.log("\n🔍 AUDIT LOGS FILTER TESTS", "blue")
        
        # Test 1: Search filter
        result = self.test_api_call(
            "GET",
            "/admin/audit-logs",
            params={"search": "admin"},
            description="GET /api/admin/audit-logs?search=admin"
        )
        
        if result and isinstance(result, dict) and "logs" in result:
            # Check if logs contain admin in user_name or module
            admin_found = False
            for log in result["logs"]:
                if ("admin" in str(log.get("user_name", "")).lower() or 
                    "admin" in str(log.get("module", "")).lower()):
                    admin_found = True
                    break
            
            if admin_found or len(result["logs"]) == 0:
                self.log(f"   ✅ Search filter working (found logs with 'admin')", "green")
            else:
                self.log(f"   ❌ Search filter not working properly", "red")

        # Test 2: Action filter
        result = self.test_api_call(
            "GET",
            "/admin/audit-logs",
            params={"action": "login"},
            description="GET /api/admin/audit-logs?action=login"
        )
        
        if result and isinstance(result, dict) and "logs" in result:
            # Check if all logs have action=login
            all_login = all(log.get("action") == "login" for log in result["logs"]) if result["logs"] else True
            if all_login:
                self.log(f"   ✅ Action filter working (all logs have action='login')", "green")
            else:
                self.log(f"   ❌ Action filter not working - found non-login actions", "red")

        # Test 3: Role filter  
        result = self.test_api_call(
            "GET",
            "/admin/audit-logs",
            params={"role": "admin"},
            description="GET /api/admin/audit-logs?role=admin"
        )
        
        if result and isinstance(result, dict) and "logs" in result:
            # Check if all logs have role=admin
            all_admin = all(log.get("role") == "admin" for log in result["logs"]) if result["logs"] else True
            if all_admin:
                self.log(f"   ✅ Role filter working (all logs have role='admin')", "green")
            else:
                self.log(f"   ❌ Role filter not working - found non-admin roles", "red")

        # Test 4: Limit and skip
        result = self.test_api_call(
            "GET",
            "/admin/audit-logs",
            params={"limit": 5, "skip": 0},
            description="GET /api/admin/audit-logs?limit=5&skip=0"
        )
        
        if result and isinstance(result, dict) and "logs" in result and "total" in result:
            logs_count = len(result["logs"])
            total_count = result["total"]
            
            if logs_count <= 5:
                self.log(f"   ✅ Limit working (returned {logs_count} logs, max 5)", "green")
            else:
                self.log(f"   ❌ Limit not working (returned {logs_count} logs, expected max 5)", "red")
                
            self.log(f"   📊 Total in DB: {total_count}, Page returned: {logs_count}", "blue")

        # Test 5: Date range filter
        result = self.test_api_call(
            "GET",
            "/admin/audit-logs",
            params={"date_from": "2025-01-01", "date_to": "2025-12-31"},
            description="GET /api/admin/audit-logs?date_from=2025-01-01&date_to=2025-12-31"
        )
        
        if result:
            self.log(f"   ✅ Date range filter accepted (no 500 error)", "green")

        # Test 6: Combined filters
        result = self.test_api_call(
            "GET",
            "/admin/audit-logs",
            params={"action": "login", "role": "admin", "limit": 10},
            description="GET /api/admin/audit-logs?action=login&role=admin&limit=10"
        )
        
        if result and isinstance(result, dict) and "logs" in result:
            # Verify combined filters work
            valid_entries = True
            for log in result["logs"]:
                if log.get("action") != "login" or log.get("role") != "admin":
                    valid_entries = False
                    break
            
            if valid_entries and len(result["logs"]) <= 10:
                self.log(f"   ✅ Combined filters working correctly", "green")
            else:
                self.log(f"   ❌ Combined filters not working properly", "red")

    def test_auto_invoice_cron(self):
        """Test auto invoice generation cron endpoint"""
        self.log("\n⏰ AUTO INVOICE CRON TEST", "blue")
        
        result = self.test_api_call(
            "POST",
            "/admin/cron/generate-invoices",
            description="POST /api/admin/cron/generate-invoices"
        )
        
        if result:
            # Check if it's an object (not 500 error)
            if isinstance(result, dict):
                self.log(f"   ✅ Cron endpoint returns object response (not 500 error)", "green")
                self.log(f"   📋 Response keys: {list(result.keys())}", "blue")
                
                # Look for results or similar key
                if "invoices_generated" in result or "results" in result or "generated" in result:
                    count = (result.get("invoices_generated", 0) or 
                            result.get("generated", 0) or
                            len(result.get("results", [])))
                    self.log(f"   📊 Invoices generated: {count}", "blue")
                else:
                    self.log(f"   📋 Full response: {json.dumps(result, indent=2)}", "blue")
                
                return True
            else:
                self.log(f"   ❌ Expected object response, got {type(result)}", "red")
                return False
        return False

    def run_all_tests(self):
        """Run all test scenarios"""
        self.log("🚀 STARTING AUDIT LOGS & CRON TESTING", "blue")
        self.log("=" * 60, "blue")
        
        # Step 1: Login as admin
        if not self.login_admin():
            self.log("\n❌ CRITICAL: Could not login as admin - stopping tests", "red")
            return
        
        # Step 2: Test audit logs basic functionality
        if not self.test_audit_logs_endpoint():
            self.log("\n❌ CRITICAL: Basic audit logs endpoint failed", "red")
        
        # Step 3: Test audit logs filters
        self.test_audit_logs_filters()
        
        # Step 4: Test auto invoice cron
        self.test_auto_invoice_cron()
        
        # Final summary
        self.log("\n" + "=" * 60, "blue")
        self.log("📊 FINAL TEST SUMMARY", "blue")
        self.log("=" * 60, "blue")
        
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        if success_rate >= 90:
            color = "green"
        elif success_rate >= 75:
            color = "yellow"
        else:
            color = "red"
            
        self.log(f"✅ Tests Passed: {self.passed_tests}/{self.total_tests} ({success_rate:.1f}%)", color)
        
        if self.passed_tests == self.total_tests:
            self.log("🎉 ALL TESTS PASSED! System ready for production.", "green")
        elif success_rate >= 75:
            self.log("⚠️  Most tests passed with minor issues.", "yellow")
        else:
            self.log("❌ Significant issues found requiring attention.", "red")

if __name__ == "__main__":
    runner = TestRunner()
    runner.run_all_tests()