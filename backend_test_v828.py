#!/usr/bin/env python3
"""
Backend Test Suite for V8.28 Changes
Tests the new admin dashboard fields:
1. approx_monthly_revenue - NEW calculation logic
2. invoice_value_this_month - NEW field
"""

import requests
import json
from datetime import datetime, timedelta
import sys

# Configuration
BACKEND_URL = "https://changelog-review-13.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

class TestRunner:
    def __init__(self):
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        self.failed_tests = []

    def log_test(self, test_name, passed, details=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   {details}")
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        
        if not passed:
            self.failed_tests.append(test_name)

    def seed_data(self):
        """Seed test data"""
        try:
            response = requests.post(f"{BACKEND_URL}/seed", timeout=30)
            if response.status_code == 200:
                self.log_test("Seed Data", True, "Data seeding successful (idempotent)")
                return True
            else:
                self.log_test("Seed Data", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Seed Data", False, f"Exception: {str(e)}")
            return False

    def login_admin(self):
        """Login as admin and get token"""
        try:
            response = requests.post(
                f"{BACKEND_URL}/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.log_test("Admin Login", True, f"Successfully authenticated as {ADMIN_EMAIL}")
                return True
            else:
                self.log_test("Admin Login", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Admin Login", False, f"Exception: {str(e)}")
            return False

    def login_operator(self):
        """Login as operator and get token"""
        try:
            response = requests.post(
                f"{BACKEND_URL}/auth/login",
                json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                self.log_test("Operator Login", True, f"Successfully authenticated as {OPERATOR_EMAIL}")
                return True
            else:
                self.log_test("Operator Login", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Operator Login", False, f"Exception: {str(e)}")
            return False

    def test_dashboard_new_fields(self):
        """Test that dashboard has both new V8.28 fields"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{BACKEND_URL}/admin/dashboard", headers=headers, timeout=10)
            
            if response.status_code != 200:
                self.log_test("Dashboard New Fields", False, f"Status: {response.status_code}")
                return False
            
            data = response.json()
            
            # Check for approx_monthly_revenue
            if "approx_monthly_revenue" not in data:
                self.log_test("Dashboard New Fields", False, "Missing approx_monthly_revenue field")
                return False
            
            # Check for invoice_value_this_month
            if "invoice_value_this_month" not in data:
                self.log_test("Dashboard New Fields", False, "Missing invoice_value_this_month field")
                return False
            
            # Verify data types
            if not isinstance(data["approx_monthly_revenue"], (int, float)):
                self.log_test("Dashboard New Fields", False, f"approx_monthly_revenue is not a number: {type(data['approx_monthly_revenue'])}")
                return False
            
            if not isinstance(data["invoice_value_this_month"], (int, float)):
                self.log_test("Dashboard New Fields", False, f"invoice_value_this_month is not a number: {type(data['invoice_value_this_month'])}")
                return False
            
            # Check existing fields are still present
            required_fields = [
                "total_operators", "active_operators", "total_subscribers", 
                "active_subscribers", "suspended_subscribers", "saas_revenue_this_month", "recent_payments"
            ]
            
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                self.log_test("Dashboard New Fields", False, f"Missing existing fields: {missing_fields}")
                return False
            
            self.log_test("Dashboard New Fields", True, 
                         f"approx_monthly_revenue: {data['approx_monthly_revenue']}, "
                         f"invoice_value_this_month: {data['invoice_value_this_month']}")
            return data
            
        except Exception as e:
            self.log_test("Dashboard New Fields", False, f"Exception: {str(e)}")
            return False

    def test_approx_monthly_revenue_logic(self, dashboard_data):
        """Test approx_monthly_revenue calculation logic"""
        try:
            # According to the review request:
            # Currently seeded: 1 active operator with 10 active subscribers and no SaaS plan (defaults to per_invoice_price=10.0)
            # Expected: approx_monthly_revenue = 10 * 10 = 100.0
            
            expected_revenue = 100.0
            actual_revenue = dashboard_data["approx_monthly_revenue"]
            
            if actual_revenue == expected_revenue:
                self.log_test("Approx Monthly Revenue Logic", True, 
                             f"Calculation correct: {actual_revenue} (1 operator × 10 subscribers × ₹10 per invoice)")
                return True
            else:
                self.log_test("Approx Monthly Revenue Logic", False, 
                             f"Expected: {expected_revenue}, Got: {actual_revenue}")
                return False
                
        except Exception as e:
            self.log_test("Approx Monthly Revenue Logic", False, f"Exception: {str(e)}")
            return False

    def test_invoice_value_this_month_initial(self, dashboard_data):
        """Test invoice_value_this_month initial state"""
        try:
            # The value should be a number (could be 0.0 or higher if invoices exist from previous tests)
            actual_value = dashboard_data["invoice_value_this_month"]
            
            if isinstance(actual_value, (int, float)) and actual_value >= 0:
                self.log_test("Invoice Value This Month (Initial)", True, 
                             f"Initial value: {actual_value} (valid number >= 0)")
                return True
            else:
                self.log_test("Invoice Value This Month (Initial)", False, 
                             f"Invalid value: {actual_value} (should be number >= 0)")
                return False
                
        except Exception as e:
            self.log_test("Invoice Value This Month (Initial)", False, f"Exception: {str(e)}")
            return False

    def get_subscriber_id(self):
        """Get a subscriber ID for invoice creation"""
        try:
            headers = {"Authorization": f"Bearer {self.operator_token}"}
            response = requests.get(f"{BACKEND_URL}/operator/subscribers", headers=headers, timeout=10)
            
            if response.status_code == 200:
                subscribers = response.json()
                if subscribers:
                    return subscribers[0]["id"]
            return None
        except Exception:
            return None

    def get_operator_id(self):
        """Get the operator ID from the test operator"""
        try:
            headers = {"Authorization": f"Bearer {self.operator_token}"}
            response = requests.get(f"{BACKEND_URL}/operator/profile", headers=headers, timeout=10)
            
            if response.status_code == 200:
                profile = response.json()
                return profile.get("id")
            return None
        except Exception:
            return None

    def credit_operator_wallet(self, operator_id, amount=100.0):
        """Credit operator wallet using admin privileges"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.post(
                f"{BACKEND_URL}/admin/wallets/{operator_id}/credit",
                json={
                    "amount": amount,
                    "reason": "Test credit for invoice creation"
                },
                headers=headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def create_test_invoice(self, amount=500.0):
        """Create a test invoice"""
        try:
            subscriber_id = self.get_subscriber_id()
            if not subscriber_id:
                return None, "No subscribers found"
            
            # Create invoice with future due date
            due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            service_start = datetime.now().strftime("%Y-%m-%d")
            service_end = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            
            invoice_data = {
                "subscriber_id": subscriber_id,
                "due_date": due_date,
                "line_items": [
                    {
                        "description": "Test Service",
                        "is_custom": True,
                        "base_amount": amount,
                        "discount": 0,
                        "tax_amount": 0,
                        "service_start_date": service_start,
                        "service_end_date": service_end
                    }
                ]
            }
            
            headers = {"Authorization": f"Bearer {self.operator_token}"}
            response = requests.post(
                f"{BACKEND_URL}/operator/invoices",
                json=invoice_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return response.json(), None
            else:
                return None, f"Status: {response.status_code}, Response: {response.text}"
                
        except Exception as e:
            return None, f"Exception: {str(e)}"

    def test_invoice_value_this_month_with_invoice(self):
        """Test invoice_value_this_month after creating an invoice"""
        try:
            # First, credit the operator wallet so they can create invoices
            operator_id = self.get_operator_id()
            if not operator_id:
                self.log_test("Invoice Value This Month (With Invoice)", False, "Could not get operator ID")
                return False
            
            if not self.credit_operator_wallet(operator_id, 100.0):
                self.log_test("Invoice Value This Month (With Invoice)", False, "Failed to credit operator wallet")
                return False
            
            # Create an invoice
            invoice, error = self.create_test_invoice(500.0)
            if not invoice:
                self.log_test("Invoice Value This Month (With Invoice)", False, f"Failed to create invoice: {error}")
                return False
            
            invoice_id = invoice.get("id")
            invoice_amount = invoice.get("final_amount", 0)
            
            # Get updated dashboard data
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{BACKEND_URL}/admin/dashboard", headers=headers, timeout=10)
            
            if response.status_code != 200:
                self.log_test("Invoice Value This Month (With Invoice)", False, f"Dashboard request failed: {response.status_code}")
                return False
            
            data = response.json()
            new_invoice_value = data["invoice_value_this_month"]
            
            # The invoice_value_this_month should now include our new invoice amount
            if new_invoice_value >= invoice_amount:
                self.log_test("Invoice Value This Month (With Invoice)", True, 
                             f"Value increased to {new_invoice_value} after creating ₹{invoice_amount} invoice")
                return invoice_id, new_invoice_value
            else:
                self.log_test("Invoice Value This Month (With Invoice)", False, 
                             f"Expected at least ₹{invoice_amount}, got ₹{new_invoice_value}")
                return False
                
        except Exception as e:
            self.log_test("Invoice Value This Month (With Invoice)", False, f"Exception: {str(e)}")
            return False

    def cancel_invoice(self, invoice_id):
        """Cancel an invoice"""
        try:
            headers = {"Authorization": f"Bearer {self.operator_token}"}
            response = requests.put(
                f"{BACKEND_URL}/operator/invoices/{invoice_id}/status",
                json={"status": "cancelled"},
                headers=headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def test_cancelled_invoices_excluded(self):
        """Test that cancelled invoices are excluded from invoice_value_this_month"""
        try:
            # Ensure operator has wallet balance
            operator_id = self.get_operator_id()
            if not operator_id:
                self.log_test("Cancelled Invoices Excluded", False, "Could not get operator ID")
                return False
            
            if not self.credit_operator_wallet(operator_id, 100.0):
                self.log_test("Cancelled Invoices Excluded", False, "Failed to credit operator wallet")
                return False
            
            # Create another invoice
            invoice, error = self.create_test_invoice(300.0)
            if not invoice:
                self.log_test("Cancelled Invoices Excluded", False, f"Failed to create invoice: {error}")
                return False
            
            invoice_id = invoice.get("id")
            invoice_amount = invoice.get("final_amount", 0)
            
            # Get dashboard value before cancellation
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{BACKEND_URL}/admin/dashboard", headers=headers, timeout=10)
            if response.status_code != 200:
                self.log_test("Cancelled Invoices Excluded", False, "Failed to get dashboard before cancellation")
                return False
            
            before_cancel = response.json()["invoice_value_this_month"]
            
            # Cancel the invoice
            if not self.cancel_invoice(invoice_id):
                self.log_test("Cancelled Invoices Excluded", False, "Failed to cancel invoice")
                return False
            
            # Get dashboard value after cancellation
            response = requests.get(f"{BACKEND_URL}/admin/dashboard", headers=headers, timeout=10)
            if response.status_code != 200:
                self.log_test("Cancelled Invoices Excluded", False, "Failed to get dashboard after cancellation")
                return False
            
            after_cancel = response.json()["invoice_value_this_month"]
            
            # The value should decrease by the cancelled invoice amount
            expected_decrease = invoice_amount
            actual_decrease = before_cancel - after_cancel
            
            if abs(actual_decrease - expected_decrease) < 0.01:  # Allow for small floating point differences
                self.log_test("Cancelled Invoices Excluded", True, 
                             f"Value correctly decreased by ₹{actual_decrease} after cancelling ₹{invoice_amount} invoice")
                return True
            else:
                self.log_test("Cancelled Invoices Excluded", False, 
                             f"Expected decrease of ₹{expected_decrease}, got ₹{actual_decrease}")
                return False
                
        except Exception as e:
            self.log_test("Cancelled Invoices Excluded", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all V8.28 tests"""
        print("=" * 60)
        print("V8.28 E-Bill Platform Backend Tests")
        print("=" * 60)
        
        # Setup
        if not self.seed_data():
            return False
        
        if not self.login_admin():
            return False
        
        if not self.login_operator():
            return False
        
        # Test 1: Dashboard has both new fields
        dashboard_data = self.test_dashboard_new_fields()
        if not dashboard_data:
            return False
        
        # Test 2: approx_monthly_revenue logic
        self.test_approx_monthly_revenue_logic(dashboard_data)
        
        # Test 3: invoice_value_this_month initial state
        self.test_invoice_value_this_month_initial(dashboard_data)
        
        # Test 4: invoice_value_this_month with invoice
        result = self.test_invoice_value_this_month_with_invoice()
        
        # Test 5: Cancelled invoices excluded
        self.test_cancelled_invoices_excluded()
        
        return True

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["passed"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        
        if self.failed_tests:
            print(f"\nFailed Tests:")
            for test in self.failed_tests:
                print(f"  - {test}")
        
        print(f"\nSuccess Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        return failed_tests == 0

def main():
    """Main test execution"""
    runner = TestRunner()
    
    try:
        runner.run_all_tests()
        success = runner.print_summary()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()