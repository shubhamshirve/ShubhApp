#!/usr/bin/env python3
"""
E-Bill Platform V8.29 Testing Script

Tests two specific changes:
1. Remove invoice_value_this_month from GET /api/admin/dashboard
2. Calendar-month expiry date calculation for subscriber plans

Backend URL: https://changelog-review-13.preview.emergentagent.com/api
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://changelog-review-13.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

class TestRunner:
    def __init__(self):
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "status": status,
            "passed": passed,
            "details": details
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def make_request(self, method: str, endpoint: str, token: str = None, data: Dict = None) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return {
                "status_code": response.status_code,
                "data": response.json() if response.content else {},
                "success": 200 <= response.status_code < 300
            }
        except requests.exceptions.RequestException as e:
            return {
                "status_code": 0,
                "data": {"error": str(e)},
                "success": False
            }
        except json.JSONDecodeError:
            return {
                "status_code": response.status_code,
                "data": {"error": "Invalid JSON response"},
                "success": False
            }
    
    def authenticate(self) -> bool:
        """Authenticate admin and operator users"""
        print("🔐 Authenticating users...")
        
        # Seed data first
        seed_response = self.make_request("POST", "/seed")
        if not seed_response["success"]:
            self.log_test("Seed Data", False, f"Failed to seed: {seed_response['data']}")
            return False
        self.log_test("Seed Data", True, "Data seeding successful")
        
        # Admin login
        admin_response = self.make_request("POST", "/auth/login", data={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if not admin_response["success"]:
            self.log_test("Admin Login", False, f"Failed: {admin_response['data']}")
            return False
        
        self.admin_token = admin_response["data"].get("access_token")
        if not self.admin_token:
            self.log_test("Admin Login", False, "No access token received")
            return False
        self.log_test("Admin Login", True, f"Successfully authenticated as {ADMIN_EMAIL}")
        
        # Operator login
        operator_response = self.make_request("POST", "/auth/login", data={
            "email": OPERATOR_EMAIL,
            "password": OPERATOR_PASSWORD
        })
        if not operator_response["success"]:
            self.log_test("Operator Login", False, f"Failed: {operator_response['data']}")
            return False
        
        self.operator_token = operator_response["data"].get("access_token")
        if not self.operator_token:
            self.log_test("Operator Login", False, "No access token received")
            return False
        self.log_test("Operator Login", True, f"Successfully authenticated as {OPERATOR_EMAIL}")
        
        return True
    
    def test_change_1_dashboard_fields(self) -> bool:
        """Test CHANGE 1: Remove invoice_value_this_month from admin dashboard"""
        print("\n📊 Testing CHANGE 1: Admin Dashboard Fields...")
        
        response = self.make_request("GET", "/admin/dashboard", token=self.admin_token)
        if not response["success"]:
            self.log_test("Dashboard API Call", False, f"Failed: {response['data']}")
            return False
        
        dashboard_data = response["data"]
        
        # Check that invoice_value_this_month is NOT present
        if "invoice_value_this_month" in dashboard_data:
            self.log_test("Remove invoice_value_this_month", False, 
                         "Field 'invoice_value_this_month' is still present in dashboard response")
            return False
        
        self.log_test("Remove invoice_value_this_month", True, 
                     "Field 'invoice_value_this_month' successfully removed from dashboard")
        
        # Check that approx_monthly_revenue is still present
        if "approx_monthly_revenue" not in dashboard_data:
            self.log_test("Preserve approx_monthly_revenue", False, 
                         "Field 'approx_monthly_revenue' is missing from dashboard")
            return False
        
        self.log_test("Preserve approx_monthly_revenue", True, 
                     f"Field 'approx_monthly_revenue' present: {dashboard_data['approx_monthly_revenue']}")
        
        # Check other essential fields are preserved
        required_fields = [
            "total_operators", "active_operators", "total_subscribers", 
            "active_subscribers", "suspended_subscribers", "saas_revenue_this_month"
        ]
        
        missing_fields = [field for field in required_fields if field not in dashboard_data]
        if missing_fields:
            self.log_test("Preserve Other Dashboard Fields", False, 
                         f"Missing fields: {missing_fields}")
            return False
        
        self.log_test("Preserve Other Dashboard Fields", True, 
                     f"All essential fields present: {required_fields}")
        
        return True
    
    def test_change_2_calendar_month_expiry(self) -> bool:
        """Test CHANGE 2: Calendar-month expiry date calculation"""
        print("\n📅 Testing CHANGE 2: Calendar-Month Expiry Calculation...")
        
        # First, get or create a monthly plan
        plans_response = self.make_request("GET", "/operator/plans", token=self.operator_token)
        if not plans_response["success"]:
            self.log_test("Get Operator Plans", False, f"Failed: {plans_response['data']}")
            return False
        
        plans = plans_response["data"]
        monthly_plan = None
        quarterly_plan = None
        
        # Find existing monthly and quarterly plans
        for plan in plans:
            if plan.get("validity") == "monthly":
                monthly_plan = plan
            elif plan.get("validity") == "quarterly":
                quarterly_plan = plan
        
        # Create monthly plan if not exists
        if not monthly_plan:
            create_plan_response = self.make_request("POST", "/operator/plans", 
                                                   token=self.operator_token, data={
                "name": "Test Monthly Plan",
                "price": 500,
                "validity": "monthly",
                "tax_percentage": 18,
                "tax_type": "GST",
                "description": "Test monthly plan for expiry calculation"
            })
            if not create_plan_response["success"]:
                self.log_test("Create Monthly Plan", False, f"Failed: {create_plan_response['data']}")
                return False
            monthly_plan = create_plan_response["data"]
            self.log_test("Create Monthly Plan", True, f"Created plan: {monthly_plan['name']}")
        
        # Create quarterly plan if not exists
        if not quarterly_plan:
            create_quarterly_response = self.make_request("POST", "/operator/plans", 
                                                        token=self.operator_token, data={
                "name": "Test Quarterly Plan",
                "price": 1400,
                "validity": "quarterly",
                "tax_percentage": 18,
                "tax_type": "GST",
                "description": "Test quarterly plan for expiry calculation"
            })
            if not create_quarterly_response["success"]:
                self.log_test("Create Quarterly Plan", False, f"Failed: {create_quarterly_response['data']}")
                return False
            quarterly_plan = create_quarterly_response["data"]
            self.log_test("Create Quarterly Plan", True, f"Created plan: {quarterly_plan['name']}")
        
        # Test monthly plan expiry calculation (Apr 21 → May 20)
        monthly_result = self.test_plan_expiry_calculation(
            monthly_plan["id"], "monthly", "2026-04-21", "2026-05-20"
        )
        
        # Test quarterly plan expiry calculation (Apr 21 → Jul 20)
        quarterly_result = self.test_plan_expiry_calculation(
            quarterly_plan["id"], "quarterly", "2026-04-21", "2026-07-20"
        )
        
        # Test payment extension logic
        payment_extension_result = self.test_payment_extension_logic(monthly_plan["id"])
        
        return monthly_result and quarterly_result and payment_extension_result
    
    def test_plan_expiry_calculation(self, plan_id: str, validity: str, 
                                   start_date: str, expected_expiry: str) -> bool:
        """Test plan expiry calculation for a specific validity"""
        print(f"\n   Testing {validity} plan expiry calculation...")
        
        # Create subscriber with specific start date
        subscriber_data = {
            "name": f"Expiry Test Subscriber ({validity})",
            "whatsapp_number": f"910000000{len(self.test_results):02d}",
            "email": f"exptest{validity}@test.com",
            "address": "Test Address",
            "plans": [{
                "plan_id": plan_id,
                "plan_start_date": start_date,
                "discount": 0
            }],
            "generate_first_invoice": False
        }
        
        create_response = self.make_request("POST", "/operator/subscribers", 
                                          token=self.operator_token, data=subscriber_data)
        if not create_response["success"]:
            self.log_test(f"Create {validity.title()} Subscriber", False, 
                         f"Failed: {create_response['data']}")
            return False
        
        subscriber = create_response["data"]
        subscriber_id = subscriber["id"]
        
        # Verify expiry date calculation
        if not subscriber.get("plans") or len(subscriber["plans"]) == 0:
            self.log_test(f"{validity.title()} Plan Expiry Calculation", False, 
                         "No plans found in created subscriber")
            return False
        
        actual_expiry = subscriber["plans"][0].get("plan_expiry_date")
        if actual_expiry != expected_expiry:
            self.log_test(f"{validity.title()} Plan Expiry Calculation", False, 
                         f"Expected: {expected_expiry}, Got: {actual_expiry}")
            return False
        
        self.log_test(f"{validity.title()} Plan Expiry Calculation", True, 
                     f"Start: {start_date} → Expiry: {actual_expiry} ✓")
        
        # Clean up - delete the test subscriber
        delete_response = self.make_request("PUT", f"/operator/subscribers/{subscriber_id}", 
                                          token=self.operator_token, data={
            "name": subscriber["name"],
            "whatsapp_number": subscriber["whatsapp_number"],
            "email": subscriber["email"],
            "address": subscriber["address"],
            "plans": subscriber["plans"],
            "status": "active",
            "deleted_at": datetime.now().isoformat()
        })
        
        return True
    
    def test_payment_extension_logic(self, plan_id: str) -> bool:
        """Test that marking invoice as paid extends plan expiry correctly"""
        print("\n   Testing payment extension logic...")
        
        # Create subscriber for payment test
        subscriber_data = {
            "name": "Payment Extension Test",
            "whatsapp_number": "9100000099",
            "email": "paytest@test.com",
            "address": "Test Address",
            "plans": [{
                "plan_id": plan_id,
                "plan_start_date": "2026-04-21",
                "discount": 0
            }],
            "generate_first_invoice": True  # Generate first invoice
        }
        
        create_response = self.make_request("POST", "/operator/subscribers", 
                                          token=self.operator_token, data=subscriber_data)
        if not create_response["success"]:
            self.log_test("Create Payment Test Subscriber", False, 
                         f"Failed: {create_response['data']}")
            return False
        
        subscriber = create_response["data"]
        subscriber_id = subscriber["id"]
        original_expiry = subscriber["plans"][0]["plan_expiry_date"]  # Should be 2026-05-20
        
        # Get the generated invoice
        invoices_response = self.make_request("GET", "/operator/invoices", token=self.operator_token)
        if not invoices_response["success"]:
            self.log_test("Get Invoices", False, f"Failed: {invoices_response['data']}")
            return False
        
        # Find invoice for our subscriber
        test_invoice = None
        for invoice in invoices_response["data"]:
            if invoice.get("subscriber_id") == subscriber_id:
                test_invoice = invoice
                break
        
        if not test_invoice:
            self.log_test("Find Test Invoice", False, "No invoice found for test subscriber")
            return False
        
        # Mark invoice as paid
        payment_response = self.make_request("PUT", f"/operator/invoices/{test_invoice['id']}/status", 
                                           token=self.operator_token, data={
            "status": "paid",
            "payment_mode": "cash"
        })
        if not payment_response["success"]:
            self.log_test("Mark Invoice Paid", False, f"Failed: {payment_response['data']}")
            return False
        
        self.log_test("Mark Invoice Paid", True, f"Invoice {test_invoice['id']} marked as paid")
        
        # Get updated subscriber to check expiry extension
        updated_subscriber_response = self.make_request("GET", f"/operator/subscribers", 
                                                      token=self.operator_token)
        if not updated_subscriber_response["success"]:
            self.log_test("Get Updated Subscriber", False, 
                         f"Failed: {updated_subscriber_response['data']}")
            return False
        
        # Find our subscriber in the list
        updated_subscriber = None
        for sub in updated_subscriber_response["data"]:
            if sub["id"] == subscriber_id:
                updated_subscriber = sub
                break
        
        if not updated_subscriber:
            self.log_test("Find Updated Subscriber", False, "Subscriber not found after payment")
            return False
        
        new_expiry = updated_subscriber["plans"][0]["plan_expiry_date"]
        expected_new_expiry = "2026-06-20"  # Original 2026-05-20 + 1 month = 2026-06-20
        
        if new_expiry != expected_new_expiry:
            self.log_test("Payment Extension Calculation", False, 
                         f"Expected new expiry: {expected_new_expiry}, Got: {new_expiry}")
            return False
        
        self.log_test("Payment Extension Calculation", True, 
                     f"Original: {original_expiry} → Extended: {new_expiry} ✓")
        
        return True
    
    def run_all_tests(self):
        """Run all V8.29 tests"""
        print("🚀 Starting E-Bill Platform V8.29 Testing...")
        print(f"Backend URL: {BASE_URL}")
        print("=" * 60)
        
        # Authentication
        if not self.authenticate():
            print("\n❌ Authentication failed. Cannot proceed with tests.")
            return False
        
        # Test Change 1: Dashboard fields
        change1_success = self.test_change_1_dashboard_fields()
        
        # Test Change 2: Calendar-month expiry calculation
        change2_success = self.test_change_2_calendar_month_expiry()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = [t for t in self.test_results if t["passed"]]
        failed_tests = [t for t in self.test_results if not t["passed"]]
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {len(passed_tests)}")
        print(f"Failed: {len(failed_tests)}")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        print("\n✅ PASSED TESTS:")
        for test in passed_tests:
            print(f"   • {test['test']}")
        
        overall_success = len(failed_tests) == 0
        print(f"\n🎯 OVERALL RESULT: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        return overall_success

if __name__ == "__main__":
    runner = TestRunner()
    success = runner.run_all_tests()
    exit(0 if success else 1)