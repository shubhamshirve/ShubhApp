#!/usr/bin/env python3
"""
E-Bill Application - Review Request API Testing
Testing specific endpoints as requested:
1. Admin login fix verification
2. Custom items in invoice creation
3. WA Stats endpoint
4. Audit logs with cron_jobs filter
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Configuration
BASE_URL = "https://gst-invoice-display.preview.emergentagent.com/api"

class ReviewRequestTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        
    def log_result(self, test_name, success, details="", status_code=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "status": status,
            "status_code": status_code
        })
        print(f"{status}: {test_name}")
        if status_code:
            print(f"   Status Code: {status_code}")
        if details:
            print(f"   Details: {details}")
    
    def test_admin_login_fix(self):
        """Test 1: Admin Login Fix Verification"""
        print("\n🔐 Testing Admin Login Fix...")
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json={
                "email": "admin@saas.com",
                "password": "admin123"
            })
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                user = data.get("user", {})
                role = user.get("role")
                
                if access_token and role == "admin":
                    self.admin_token = access_token
                    # Set up session for admin requests
                    admin_session = requests.Session()
                    admin_session.headers.update({"Authorization": f"Bearer {access_token}"})
                    self.admin_session = admin_session
                    
                    self.log_result("Admin Login", True, 
                                  f"Token received, role={role}", response.status_code)
                    return True
                else:
                    self.log_result("Admin Login", False, 
                                  f"Missing token or incorrect role. Token: {bool(access_token)}, Role: {role}", 
                                  response.status_code)
                    return False
            else:
                self.log_result("Admin Login", False, 
                              f"Response: {response.text}", response.status_code)
                return False
        except Exception as e:
            self.log_result("Admin Login", False, f"Exception: {str(e)}")
            return False
    
    def test_operator_login(self):
        """Login as operator for invoice testing"""
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json={
                "email": "operator@test.com",
                "password": "test123"
            })
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                
                if access_token:
                    self.operator_token = access_token
                    # Set up session for operator requests
                    operator_session = requests.Session()
                    operator_session.headers.update({"Authorization": f"Bearer {access_token}"})
                    self.operator_session = operator_session
                    
                    self.log_result("Operator Login", True, 
                                  "Token received", response.status_code)
                    return True
                else:
                    self.log_result("Operator Login", False, 
                                  "No access token received", response.status_code)
                    return False
            else:
                self.log_result("Operator Login", False, 
                              f"Response: {response.text}", response.status_code)
                return False
        except Exception as e:
            self.log_result("Operator Login", False, f"Exception: {str(e)}")
            return False
    
    def test_custom_items_invoice_creation(self):
        """Test 2-5: Custom Items in Invoice Creation"""
        print("\n📄 Testing Custom Items in Invoice Creation...")
        
        if not hasattr(self, 'operator_session'):
            self.log_result("Custom Invoice Creation", False, "No operator session available")
            return False
        
        try:
            # Step 1: Get subscribers
            response = self.operator_session.get(f"{BASE_URL}/operator/subscribers")
            
            if response.status_code != 200:
                self.log_result("Get Subscribers", False, 
                              f"Response: {response.text}", response.status_code)
                return False
            
            subscribers = response.json()
            if not subscribers:
                self.log_result("Get Subscribers", False, "No subscribers found")
                return False
            
            subscriber_id = subscribers[0]["id"]
            self.log_result("Get Subscribers", True, 
                          f"Found {len(subscribers)} subscribers, using ID: {subscriber_id}", 
                          response.status_code)
            
            # Step 2: Get plans (optional, just to verify endpoint)
            response = self.operator_session.get(f"{BASE_URL}/operator/plans")
            
            if response.status_code == 200:
                plans = response.json()
                self.log_result("Get Plans", True, 
                              f"Found {len(plans)} plans", response.status_code)
            else:
                self.log_result("Get Plans", False, 
                              f"Response: {response.text}", response.status_code)
            
            # Step 2.5: Check wallet balance and add funds if needed
            response = self.operator_session.get(f"{BASE_URL}/operator/dashboard")
            if response.status_code == 200:
                dashboard = response.json()
                wallet_balance = dashboard.get("wallet_balance", 0)
                self.log_result("Check Wallet Balance", True, 
                              f"Current balance: ₹{wallet_balance}", response.status_code)
                
                # If balance is less than 50, add funds using admin session
                if wallet_balance < 50:
                    if hasattr(self, 'admin_session'):
                        # Get operator ID from the operator session token
                        me_response = self.operator_session.get(f"{BASE_URL}/auth/me")
                        if me_response.status_code == 200:
                            operator_data = me_response.json()
                            operator_id = operator_data.get("operator_id")
                            
                            if operator_id:
                                # Credit wallet with 100 rupees
                                credit_data = {
                                    "amount": 100.0,
                                    "reason": "Test credit for invoice creation testing"
                                }
                                credit_response = self.admin_session.post(
                                    f"{BASE_URL}/admin/wallets/{operator_id}/credit", 
                                    json=credit_data
                                )
                                
                                if credit_response.status_code == 200:
                                    self.log_result("Credit Wallet", True, 
                                                  f"Added ₹100 to wallet", credit_response.status_code)
                                else:
                                    self.log_result("Credit Wallet", False, 
                                                  f"Failed to credit wallet: {credit_response.text}", 
                                                  credit_response.status_code)
                                    return False
                            else:
                                self.log_result("Get Operator ID", False, "Could not get operator ID")
                                return False
                        else:
                            self.log_result("Get Operator Info", False, 
                                          f"Could not get operator info: {me_response.text}", 
                                          me_response.status_code)
                            return False
                    else:
                        self.log_result("Wallet Balance Check", False, 
                                      f"Insufficient balance (₹{wallet_balance}) and no admin session available")
                        return False
            else:
                self.log_result("Check Wallet Balance", False, 
                              f"Could not check wallet balance: {response.text}", response.status_code)
            
            # Step 3: Create invoice with custom line item
            today = datetime.now().isoformat()
            tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
            thirty_days = (datetime.now() + timedelta(days=30)).isoformat()
            
            invoice_data = {
                "subscriber_id": subscriber_id,
                "due_date": tomorrow,
                "line_items": [{
                    "is_custom": True,
                    "description": "Installation charge",
                    "base_amount": 500,
                    "discount": 0,
                    "service_start_date": today,
                    "service_end_date": thirty_days
                }]
            }
            
            response = self.operator_session.post(f"{BASE_URL}/operator/invoices", 
                                                json=invoice_data)
            
            if response.status_code == 200:
                invoice = response.json()
                invoice_id = invoice.get("id")
                line_items = invoice.get("line_items", [])
                
                # Verify custom line item is present
                custom_item_found = False
                for item in line_items:
                    if item.get("is_custom") and item.get("description") == "Installation charge":
                        custom_item_found = True
                        break
                
                if custom_item_found:
                    self.log_result("Create Custom Invoice", True, 
                                  f"Invoice created with ID: {invoice_id}, custom item verified", 
                                  response.status_code)
                    return True
                else:
                    self.log_result("Create Custom Invoice", False, 
                                  f"Invoice created but custom item not found in response", 
                                  response.status_code)
                    return False
            elif response.status_code == 402:
                # Payment required - wallet balance issue
                self.log_result("Create Custom Invoice", False, 
                              f"Wallet balance insufficient: {response.text}", response.status_code)
                return False
            else:
                self.log_result("Create Custom Invoice", False, 
                              f"Response: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("Custom Invoice Creation", False, f"Exception: {str(e)}")
            return False
    
    def test_wa_stats_endpoint(self):
        """Test 6-7: WA Stats endpoint"""
        print("\n📊 Testing WhatsApp Stats Endpoint...")
        
        if not hasattr(self, 'admin_session'):
            self.log_result("WhatsApp Stats", False, "No admin session available")
            return False
        
        try:
            response = self.admin_session.get(f"{BASE_URL}/admin/whatsapp-stats")
            
            if response.status_code == 200:
                stats = response.json()
                
                # Check for by_trigger breakdown
                has_by_trigger = "by_trigger" in stats
                
                self.log_result("WhatsApp Stats", True, 
                              f"Stats retrieved, has by_trigger: {has_by_trigger}, data: {json.dumps(stats, indent=2)}", 
                              response.status_code)
                return True
            else:
                self.log_result("WhatsApp Stats", False, 
                              f"Response: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("WhatsApp Stats", False, f"Exception: {str(e)}")
            return False
    
    def test_audit_logs_cron_filter(self):
        """Test 8: Audit Logs with cron_jobs filter"""
        print("\n📋 Testing Audit Logs with cron_jobs filter...")
        
        if not hasattr(self, 'admin_session'):
            self.log_result("Audit Logs Cron Filter", False, "No admin session available")
            return False
        
        try:
            response = self.admin_session.get(f"{BASE_URL}/admin/audit-logs?module=cron_jobs")
            
            if response.status_code == 200:
                logs = response.json()
                
                self.log_result("Audit Logs Cron Filter", True, 
                              f"Filtered results retrieved, count: {len(logs) if isinstance(logs, list) else 'N/A'}", 
                              response.status_code)
                return True
            else:
                self.log_result("Audit Logs Cron Filter", False, 
                              f"Response: {response.text}", response.status_code)
                return False
                
        except Exception as e:
            self.log_result("Audit Logs Cron Filter", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all review request tests"""
        print("🚀 Starting Review Request API Tests")
        print("=" * 60)
        
        # Test 1: Admin Login Fix
        admin_login_success = self.test_admin_login_fix()
        
        # Test 2-5: Custom Items (requires operator login and admin for wallet credit)
        operator_login_success = self.test_operator_login()
        if operator_login_success:
            self.test_custom_items_invoice_creation()
        
        # Test 6-7: WA Stats (requires admin login)
        if admin_login_success:
            self.test_wa_stats_endpoint()
            
            # Test 8: Audit Logs
            self.test_audit_logs_cron_filter()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 REVIEW REQUEST TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results if r["success"])
        total = len(self.test_results)
        
        for result in self.test_results:
            status_info = f" (HTTP {result['status_code']})" if result['status_code'] else ""
            print(f"{result['status']}: {result['test']}{status_info}")
        
        print(f"\n🎯 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed. Check details above.")
            return False

if __name__ == "__main__":
    tester = ReviewRequestTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)