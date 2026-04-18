#!/usr/bin/env python3
"""
Backend API Testing for E-Bill Platform
Tests the newly implemented features:
1. Welcome Modal endpoint
2. Remove invoice limit 
3. New cron time field
4. WhatsApp template categories
5. Backend health
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://analyze-code-14.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"

class EBillTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.test_results = []
        
    def log_result(self, test_name, success, details=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "status": status
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def login_admin(self):
        """Login as admin and get token"""
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
                self.log_result("Admin Login", True, f"Token: {self.admin_token[:20]}...")
                return True
            else:
                self.log_result("Admin Login", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Admin Login", False, f"Exception: {str(e)}")
            return False
    
    def test_health_endpoint(self):
        """Test 5: Backend health endpoint"""
        try:
            response = self.session.get(f"{BASE_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_result("Health Endpoint", True, f"Response: {data}")
                    return True
                else:
                    self.log_result("Health Endpoint", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_result("Health Endpoint", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Health Endpoint", False, f"Exception: {str(e)}")
            return False
    
    def test_welcome_modal_get(self):
        """Test 1a: GET /admin/welcome-modal"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/welcome-modal")
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["enabled", "title", "content", "show_for", "version"]
                
                if all(field in data for field in required_fields):
                    self.log_result("Welcome Modal GET", True, f"Response: {data}")
                    return True, data
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_result("Welcome Modal GET", False, f"Missing fields: {missing}")
                    return False, None
            else:
                self.log_result("Welcome Modal GET", False, f"Status: {response.status_code}, Response: {response.text}")
                return False, None
        except Exception as e:
            self.log_result("Welcome Modal GET", False, f"Exception: {str(e)}")
            return False, None
    
    def test_settings_update(self):
        """Test 1b: PATCH /admin/settings (actually PUT based on code review)"""
        try:
            # First get current settings
            response = self.session.get(f"{BASE_URL}/admin/settings")
            if response.status_code != 200:
                self.log_result("Settings GET (for update)", False, f"Status: {response.status_code}")
                return False
            
            current_settings = response.json()
            
            # Update with welcome modal settings
            update_data = {
                **current_settings,
                "welcome_modal_enabled": True,
                "welcome_modal_title": "Test Announcement",
                "welcome_modal_content": "Hello operators!",
                "welcome_modal_version": 1,
                "welcome_modal_show_for": "all"
            }
            
            response = self.session.put(f"{BASE_URL}/admin/settings", json=update_data)
            
            if response.status_code == 200:
                self.log_result("Settings Update (PUT)", True, "Welcome modal settings saved")
                return True
            else:
                self.log_result("Settings Update (PUT)", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Settings Update (PUT)", False, f"Exception: {str(e)}")
            return False
    
    def test_welcome_modal_get_after_update(self):
        """Test 1c: GET /admin/welcome-modal again to confirm settings were saved"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/welcome-modal")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if our test values were saved
                expected = {
                    "enabled": True,
                    "title": "Test Announcement",
                    "content": "Hello operators!",
                    "show_for": "all",
                    "version": 1
                }
                
                success = all(data.get(k) == v for k, v in expected.items())
                
                if success:
                    self.log_result("Welcome Modal GET (after update)", True, f"Settings confirmed: {data}")
                    return True
                else:
                    self.log_result("Welcome Modal GET (after update)", False, f"Expected: {expected}, Got: {data}")
                    return False
            else:
                self.log_result("Welcome Modal GET (after update)", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Welcome Modal GET (after update)", False, f"Exception: {str(e)}")
            return False
    
    def test_cron_daily_report_time(self):
        """Test 3: GET /admin/settings should include cron_daily_report_time field"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/settings")
            
            if response.status_code == 200:
                data = response.json()
                
                if "cron_daily_report_time" in data:
                    cron_time = data["cron_daily_report_time"]
                    self.log_result("Cron Daily Report Time Field", True, f"Value: {cron_time}")
                    return True
                else:
                    self.log_result("Cron Daily Report Time Field", False, "Field not found in settings")
                    return False
            else:
                self.log_result("Cron Daily Report Time Field", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Cron Daily Report Time Field", False, f"Exception: {str(e)}")
            return False
    
    def test_whatsapp_templates_get(self):
        """Test 4a: GET /admin/whatsapp-templates"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/whatsapp-templates")
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("WhatsApp Templates GET", True, f"Found {len(data)} templates")
                return True, data
            else:
                self.log_result("WhatsApp Templates GET", False, f"Status: {response.status_code}, Response: {response.text}")
                return False, None
        except Exception as e:
            self.log_result("WhatsApp Templates GET", False, f"Exception: {str(e)}")
            return False, None
    
    def test_whatsapp_template_create(self, template_type, display_name):
        """Test 4b: POST /admin/whatsapp-templates"""
        try:
            template_data = {
                "template_name": f"test_{template_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "display_name": display_name,
                "template_type": template_type,
                "body_text": f"Test template for {template_type}",
                "header_text": f"Test Header for {template_type}",
                "footer_text": "Test Footer",
                "body_variables": [],
                "is_active": True
            }
            
            response = self.session.post(f"{BASE_URL}/admin/whatsapp-templates", json=template_data)
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                template_id = data.get("id")
                self.log_result(f"WhatsApp Template Create ({template_type})", True, f"Created template ID: {template_id}")
                return True, template_id
            else:
                self.log_result(f"WhatsApp Template Create ({template_type})", False, f"Status: {response.status_code}, Response: {response.text}")
                return False, None
        except Exception as e:
            self.log_result(f"WhatsApp Template Create ({template_type})", False, f"Exception: {str(e)}")
            return False, None
    
    def test_whatsapp_template_delete(self, template_id, template_type):
        """Test 4c: DELETE /admin/whatsapp-templates/{template_id}"""
        try:
            response = self.session.delete(f"{BASE_URL}/admin/whatsapp-templates/{template_id}")
            
            if response.status_code == 200:
                self.log_result(f"WhatsApp Template Delete ({template_type})", True, f"Deleted template ID: {template_id}")
                return True
            else:
                self.log_result(f"WhatsApp Template Delete ({template_type})", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result(f"WhatsApp Template Delete ({template_type})", False, f"Exception: {str(e)}")
            return False
    
    def test_invoice_creation_without_wallet_limit(self):
        """Test 2: Try creating an invoice without checking wallet balance"""
        try:
            # First, get a list of subscribers
            response = self.session.get(f"{BASE_URL}/operator/subscribers")
            
            if response.status_code == 200:
                subscribers = response.json()
                if not subscribers:
                    self.log_result("Invoice Creation (No Wallet Limit)", False, "No subscribers found to test with")
                    return False
                
                # Use the first subscriber
                subscriber = subscribers[0]
                subscriber_id = subscriber["id"]
                
                # Create an invoice
                invoice_data = {
                    "subscriber_id": subscriber_id,
                    "line_items": [
                        {
                            "description": "Test Service",
                            "amount": 100.0,
                            "quantity": 1
                        }
                    ],
                    "due_date": "2024-12-31"
                }
                
                response = self.session.post(f"{BASE_URL}/operator/invoices", json=invoice_data)
                
                if response.status_code == 200 or response.status_code == 201:
                    data = response.json()
                    invoice_id = data.get("id")
                    self.log_result("Invoice Creation (No Wallet Limit)", True, f"Created invoice ID: {invoice_id}")
                    return True
                else:
                    self.log_result("Invoice Creation (No Wallet Limit)", False, f"Status: {response.status_code}, Response: {response.text}")
                    return False
            else:
                self.log_result("Invoice Creation (No Wallet Limit)", False, f"Failed to get subscribers: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Invoice Creation (No Wallet Limit)", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting E-Bill Backend API Tests")
        print("=" * 50)
        
        # Test 5: Health check (no auth required)
        self.test_health_endpoint()
        
        # Login first
        if not self.login_admin():
            print("❌ Cannot proceed without admin login")
            return False
        
        # Test 1: Welcome Modal
        print("\n📋 Testing Welcome Modal Features...")
        self.test_welcome_modal_get()
        self.test_settings_update()
        self.test_welcome_modal_get_after_update()
        
        # Test 3: Cron time field
        print("\n⏰ Testing Cron Daily Report Time Field...")
        self.test_cron_daily_report_time()
        
        # Test 4: WhatsApp Templates
        print("\n📱 Testing WhatsApp Template Categories...")
        self.test_whatsapp_templates_get()
        
        # Create and delete test templates
        template_types = [
            ("operator_low_balance", "Operator Low Balance Alert"),
            ("operator_daily_report", "Operator Daily Report")
        ]
        
        created_templates = []
        for template_type, display_name in template_types:
            success, template_id = self.test_whatsapp_template_create(template_type, display_name)
            if success and template_id:
                created_templates.append((template_id, template_type))
        
        # Clean up created templates
        for template_id, template_type in created_templates:
            self.test_whatsapp_template_delete(template_id, template_type)
        
        # Test 2: Invoice creation (requires operator role, will test as admin)
        print("\n💰 Testing Invoice Creation Without Wallet Limit...")
        self.test_invoice_creation_without_wallet_limit()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for r in self.test_results if r["success"])
        total = len(self.test_results)
        
        for result in self.test_results:
            print(f"{result['status']}: {result['test']}")
        
        print(f"\n🎯 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed. Check details above.")
            return False

if __name__ == "__main__":
    tester = EBillTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)