#!/usr/bin/env python3
"""
Backend API Testing Suite for Multi-Tenant SaaS Billing Platform
Test: Registration assigns lowest plan for 3-day trial
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Optional

# Test Configuration
BACKEND_URL = "https://checkout-error-trace.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"

class TestRunner:
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
        
    def test_get_saas_plans(self) -> Optional[dict]:
        """Test GET /api/admin/saas-plans and find lowest priced plan."""
        try:
            headers = self.get_admin_headers()
            response = requests.get(f"{BACKEND_URL}/admin/saas-plans", headers=headers)
            
            if response.status_code == 200:
                plans = response.json()
                if not plans:
                    self.log_test("Get SaaS Plans", False, "No plans found in system")
                    return None
                    
                # Find the plan with lowest monthly_price
                lowest_plan = min(plans, key=lambda x: x['monthly_price'])
                
                self.log_test("Get SaaS Plans", True, 
                    f"Found {len(plans)} plans. Lowest priced plan: '{lowest_plan['name']}' (${lowest_plan['monthly_price']})")
                return lowest_plan
            else:
                self.log_test("Get SaaS Plans", False, f"Status {response.status_code}: {response.text}")
                return None
        except Exception as e:
            self.log_test("Get SaaS Plans", False, f"Exception: {str(e)}")
            return None
            
    def test_operator_registration(self, lowest_plan: dict) -> Optional[dict]:
        """Test POST /api/auth/register with new operator registration."""
        try:
            # Generate unique email with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            registration_data = {
                "company_name": "Trial Test Company",
                "owner_name": "Trial User", 
                "email": f"trialtest123_{timestamp}@test.com",
                "phone": "9876543210",
                "password": "test123"
            }
            
            response = requests.post(f"{BACKEND_URL}/auth/register", json=registration_data)
            
            if response.status_code == 200:
                data = response.json()
                user_data = data.get("user", {})
                
                # Test the registration response - need to fetch operator details
                operator_token = data.get("access_token")
                if operator_token:
                    # Use operator token to get profile and verify subscription details
                    operator_headers = {"Authorization": f"Bearer {operator_token}"}
                    profile_response = requests.get(f"{BACKEND_URL}/auth/me", headers=operator_headers)
                    
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        operator_id = profile_data.get("operator_id")
                        
                        # Get operator details to verify subscription
                        admin_headers = self.get_admin_headers()
                        op_response = requests.get(f"{BACKEND_URL}/admin/operators/{operator_id}", 
                                                 headers=admin_headers)
                        
                        if op_response.status_code == 200:
                            operator_data = op_response.json()
                            
                            # Verify registration meets all requirements
                            checks = []
                            
                            # Check status is "trial"
                            status_check = operator_data.get("status") == "trial"
                            checks.append(("status = 'trial'", status_check, operator_data.get("status")))
                            
                            # Check subscription_ends_at is not null and approximately 3 days from now
                            sub_ends = operator_data.get("subscription_ends_at")
                            sub_ends_check = sub_ends is not None
                            checks.append(("subscription_ends_at NOT null", sub_ends_check, sub_ends))
                            
                            # Check trial_ends_at is not null and approximately 3 days from now
                            trial_ends = operator_data.get("trial_ends_at")
                            trial_ends_check = trial_ends is not None
                            checks.append(("trial_ends_at NOT null", trial_ends_check, trial_ends))
                            
                            # Check saas_plan_id matches lowest priced plan
                            plan_id_check = operator_data.get("saas_plan_id") == lowest_plan["id"]
                            checks.append(("saas_plan_id matches lowest plan", plan_id_check, 
                                         f"Got: {operator_data.get('saas_plan_id')}, Expected: {lowest_plan['id']}"))
                            
                            # Check saas_plan_name matches lowest plan name
                            plan_name_check = operator_data.get("saas_plan_name") == lowest_plan["name"]
                            checks.append(("saas_plan_name matches lowest plan", plan_name_check,
                                         f"Got: {operator_data.get('saas_plan_name')}, Expected: {lowest_plan['name']}"))
                            
                            # Verify dates are approximately 3 days from now if not null
                            now = datetime.now()
                            expected_trial_end = now + timedelta(days=3)
                            
                            date_verification = "N/A"
                            if sub_ends and trial_ends:
                                try:
                                    # Parse ISO format dates (they include timezone info)
                                    sub_end_dt = datetime.fromisoformat(sub_ends.replace('Z', '+00:00'))
                                    trial_end_dt = datetime.fromisoformat(trial_ends.replace('Z', '+00:00'))
                                    
                                    # Check if dates are within reasonable range (2-4 days from now)
                                    sub_diff = abs((sub_end_dt.replace(tzinfo=None) - expected_trial_end).days)
                                    trial_diff = abs((trial_end_dt.replace(tzinfo=None) - expected_trial_end).days)
                                    
                                    date_check = sub_diff <= 1 and trial_diff <= 1
                                    date_verification = f"Sub ends in ~{sub_diff} days, Trial ends in ~{trial_diff} days"
                                    checks.append(("dates approximately 3 days from now", date_check, date_verification))
                                except Exception as e:
                                    checks.append(("dates approximately 3 days from now", False, f"Date parse error: {str(e)}"))
                            
                            # Compile results
                            all_passed = all(check[1] for check in checks)
                            
                            details = f"Registration successful. Email: {registration_data['email']}. "
                            details += f"Checks: " + ", ".join([f"{check[0]}: {'✓' if check[1] else '✗'} ({check[2]})" for check in checks])
                            
                            self.log_test("Operator Registration", all_passed, details)
                            
                            # Return registration data for duplicate test
                            return {"email": registration_data["email"], "success": all_passed, "operator_data": operator_data}
                        else:
                            self.log_test("Operator Registration", False, 
                                f"Failed to get operator details: {op_response.status_code}")
                            return None
                    else:
                        self.log_test("Operator Registration", False, 
                            f"Failed to get operator profile: {profile_response.status_code}")
                        return None
                else:
                    self.log_test("Operator Registration", False, "No access token in registration response")
                    return None
            else:
                self.log_test("Operator Registration", False, 
                    f"Status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Operator Registration", False, f"Exception: {str(e)}")
            return None
            
    def test_duplicate_email_rejection(self, registration_result: dict):
        """Test that duplicate email registration is rejected."""
        if not registration_result or not registration_result.get("success"):
            self.log_test("Duplicate Email Test", False, "Cannot test - initial registration failed")
            return
            
        try:
            # Try to register again with the same email
            duplicate_data = {
                "company_name": "Duplicate Test Company",
                "owner_name": "Duplicate User", 
                "email": registration_result["email"],  # Same email as before
                "phone": "9876543210",
                "password": "test123"
            }
            
            response = requests.post(f"{BACKEND_URL}/auth/register", json=duplicate_data)
            
            # Should get 400 error with "Email already registered" message
            if response.status_code == 400:
                error_msg = response.json().get("detail", "")
                if "already registered" in error_msg.lower():
                    self.log_test("Duplicate Email Rejection", True, 
                        f"Correctly rejected with: '{error_msg}'")
                else:
                    self.log_test("Duplicate Email Rejection", False, 
                        f"Got 400 but wrong message: '{error_msg}'")
            else:
                self.log_test("Duplicate Email Rejection", False, 
                    f"Expected 400, got {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Duplicate Email Rejection", False, f"Exception: {str(e)}")
            
    def run_all_tests(self):
        """Run the complete test suite."""
        print("🎯 STARTING REGISTRATION TESTS FOR MULTI-TENANT SAAS BILLING PLATFORM")
        print("=" * 80)
        
        # Step 1: Get admin token
        if not self.get_admin_token():
            print("❌ Cannot continue without admin token")
            return
            
        # Step 2: Get SaaS plans and find lowest priced one
        lowest_plan = self.test_get_saas_plans()
        if not lowest_plan:
            print("❌ Cannot continue without SaaS plans")
            return
            
        # Step 3: Test operator registration
        registration_result = self.test_operator_registration(lowest_plan)
        
        # Step 4: Test duplicate email rejection
        self.test_duplicate_email_rejection(registration_result)
        
        # Summary
        print("\n" + "=" * 80)
        print("📋 TEST SUMMARY:")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if "✅ PASS" in r])
        
        for result in self.test_results:
            print(result)
            
        print(f"\n🎯 OVERALL RESULT: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED - Registration feature working correctly!")
        else:
            print("⚠️  Some tests failed - Review details above")

if __name__ == "__main__":
    runner = TestRunner()
    runner.run_all_tests()