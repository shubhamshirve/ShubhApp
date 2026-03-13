#!/usr/bin/env python3
"""
Backend Testing Suite for Multi-Tenant SaaS Billing Platform
Testing specific changes mentioned in review request:
1. Form validation fix for empty optional fields
2. Addon merge - whatsapp_notifications vs payment_reminder
3. SaaS plans updated addon references
4. Reminder settings with whatsapp_notifications addon
"""

import requests
import json
import uuid
from datetime import datetime
import os
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BACKEND_URL = "https://admin-dashboard-v2-34.preview.emergentagent.com/api"

class BackendTester:
    def __init__(self):
        self.admin_token = None
        self.operator_token = None
        self.operator_id = None
        self.plan_id = None
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def log(self, message: str):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def make_request(self, method: str, endpoint: str, token: str = None, **kwargs) -> requests.Response:
        """Make authenticated request to backend"""
        url = f"{BACKEND_URL}{endpoint}"
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        try:
            response = self.session.request(method, url, headers=headers, **kwargs)
            return response
        except Exception as e:
            self.log(f"❌ Request failed: {e}")
            raise
            
    def test_seed_database(self) -> bool:
        """Test POST /api/seed to initialize database"""
        self.log("🌱 Testing database seeding...")
        try:
            response = self.make_request('POST', '/seed')
            if response.status_code == 200:
                self.log("✅ Database seeded successfully")
                return True
            else:
                self.log(f"❌ Seed failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Seed error: {e}")
            return False
            
    def test_admin_login(self) -> bool:
        """Test admin authentication"""
        self.log("🔐 Testing admin login...")
        try:
            login_data = {
                "email": "admin@saas.com",
                "password": "admin123"
            }
            response = self.make_request('POST', '/auth/login', json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get('access_token')
                self.log("✅ Admin login successful")
                return True
            else:
                self.log(f"❌ Admin login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Admin login error: {e}")
            return False
            
    def get_operator_and_plan(self) -> bool:
        """Get an operator to test with and a plan"""
        self.log("👥 Getting test operator and plan...")
        try:
            # Get operators
            response = self.make_request('GET', '/admin/operators', token=self.admin_token)
            if response.status_code == 200:
                operators = response.json()
                if operators:
                    self.operator_id = operators[0]['id']
                    self.log(f"✅ Found operator: {self.operator_id}")
                else:
                    self.log("❌ No operators found")
                    return False
            else:
                self.log(f"❌ Failed to get operators: {response.status_code}")
                return False
                
            # Get SaaS plans first to get an operator token, then get operator plans
            response = self.make_request('GET', '/admin/saas-plans', token=self.admin_token)
            if response.status_code == 200:
                saas_plans = response.json()
                if saas_plans:
                    # We have SaaS plans, now let's get operator service plans after impersonation
                    self.log(f"✅ Found {len(saas_plans)} SaaS plans")
                    # We'll get the actual service plan ID after impersonation
                    return True
                else:
                    self.log("❌ No SaaS plans found")
                    return False
            else:
                self.log(f"❌ Failed to get plans: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ Error getting operator/plan: {e}")
            return False
            
    def test_impersonate_operator(self) -> bool:
        """Test admin impersonating operator"""
        self.log("🎭 Testing operator impersonation...")
        try:
            response = self.make_request('POST', f'/admin/operators/{self.operator_id}/impersonate', token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get('access_token')
                self.log("✅ Operator impersonation successful")
                
                # Now get operator service plans
                response = self.make_request('GET', '/operator/plans', token=self.operator_token)
                if response.status_code == 200:
                    plans = response.json()
                    if plans:
                        self.plan_id = plans[0]['id']
                        self.log(f"✅ Found operator service plan: {self.plan_id}")
                        return True
                    else:
                        self.log("❌ No operator service plans found")
                        return False
                else:
                    self.log(f"❌ Failed to get operator plans: {response.status_code}")
                    return False
            else:
                self.log(f"❌ Impersonation failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Impersonation error: {e}")
            return False

    def test_form_validation_empty_fields(self) -> Dict[str, bool]:
        """Test 1: Form validation fix for empty optional fields"""
        self.log("\n🧪 TEST 1: Form validation fix - empty optional fields")
        results = {}
        
        if not self.plan_id:
            self.log("❌ No plan ID available for testing")
            return {"empty_strings": False, "null_values": False}
            
        # Test 1a: Empty strings for optional fields
        self.log("  Testing empty strings for email/address...")
        try:
            subscriber_data = {
                "name": "Test Empty Fields",
                "whatsapp_number": "9876543210",
                "email": "",  # Empty string
                "address": "",  # Empty string
                "plan_id": self.plan_id,
                "billing_date": 1,
                "discount": 0
            }
            
            response = self.make_request('POST', '/operator/subscribers', 
                                       token=self.operator_token, json=subscriber_data)
            
            if response.status_code in [200, 201]:
                self.log("  ✅ Empty strings accepted (should become null)")
                results["empty_strings"] = True
            else:
                self.log(f"  ❌ Empty strings rejected: {response.status_code} - {response.text}")
                results["empty_strings"] = False
                
        except Exception as e:
            self.log(f"  ❌ Empty strings test error: {e}")
            results["empty_strings"] = False
            
        # Test 1b: Null values for optional fields
        self.log("  Testing null values for email/address...")
        try:
            subscriber_data = {
                "name": "Test Null Fields",
                "whatsapp_number": "9876543211",
                "email": None,  # Null value
                "address": None,  # Null value
                "plan_id": self.plan_id,
                "billing_date": 1,
                "discount": 0
            }
            
            response = self.make_request('POST', '/operator/subscribers', 
                                       token=self.operator_token, json=subscriber_data)
            
            if response.status_code in [200, 201]:
                self.log("  ✅ Null values accepted")
                results["null_values"] = True
            else:
                self.log(f"  ❌ Null values rejected: {response.status_code} - {response.text}")
                results["null_values"] = False
                
        except Exception as e:
            self.log(f"  ❌ Null values test error: {e}")
            results["null_values"] = False
            
        return results

    def test_addon_merge_features(self) -> Dict[str, bool]:
        """Test 2: Addon merge - features endpoint"""
        self.log("\n🧪 TEST 2: Addon merge - features endpoint")
        results = {}
        
        # Test features endpoint with admin or operator token
        self.log("  Testing GET /operator/features...")
        try:
            # Try with admin token first
            response = self.make_request('GET', '/operator/features', token=self.admin_token)
            
            if response.status_code != 200:
                # Try with operator token
                response = self.make_request('GET', '/operator/features', token=self.operator_token)
            
            if response.status_code == 200:
                features = response.json()
                self.log(f"  Features response: {features}")
                
                # Check for whatsapp_notifications (should exist)
                has_whatsapp_notifications = "whatsapp_notifications" in features
                # Check for payment_reminder (should NOT exist)
                has_payment_reminder = "payment_reminder" in features
                
                # Check expected feature keys
                expected_keys = [
                    "audit_log", "payment_gateway", "custom_payment_gateway", 
                    "announcement", "whatsapp_notifications", "staff_management"
                ]
                has_expected_keys = all(key in features for key in expected_keys)
                
                if has_whatsapp_notifications and not has_payment_reminder:
                    self.log("  ✅ Features endpoint shows whatsapp_notifications, NOT payment_reminder")
                    results["correct_addon_names"] = True
                else:
                    self.log(f"  ❌ Incorrect addon names - whatsapp_notifications: {has_whatsapp_notifications}, payment_reminder: {has_payment_reminder}")
                    results["correct_addon_names"] = False
                    
                if has_expected_keys:
                    self.log("  ✅ All expected feature keys present")
                    results["expected_keys"] = True
                else:
                    missing_keys = [key for key in expected_keys if key not in features]
                    self.log(f"  ❌ Missing expected keys: {missing_keys}")
                    results["expected_keys"] = False
                    
            else:
                self.log(f"  ❌ Features endpoint failed: {response.status_code} - {response.text}")
                results["correct_addon_names"] = False
                results["expected_keys"] = False
                
        except Exception as e:
            self.log(f"  ❌ Features test error: {e}")
            results["correct_addon_names"] = False
            results["expected_keys"] = False
            
        return results

    def test_saas_plans_addon_update(self) -> bool:
        """Test 3: SaaS plans updated"""
        self.log("\n🧪 TEST 3: SaaS plans updated")
        
        try:
            response = self.make_request('GET', '/admin/saas-plans', token=self.admin_token)
            
            if response.status_code == 200:
                plans = response.json()
                self.log(f"  Found {len(plans)} SaaS plans")
                
                all_correct = True
                for plan in plans:
                    plan_name = plan.get('name', 'Unknown')
                    included_addons = plan.get('included_addons', [])
                    
                    # Check if whatsapp_notifications is used instead of payment_reminder
                    has_whatsapp_notifications = "whatsapp_notifications" in included_addons
                    has_payment_reminder = "payment_reminder" in included_addons
                    
                    self.log(f"    Plan '{plan_name}': addons={included_addons}")
                    
                    if has_payment_reminder:
                        self.log(f"    ❌ Plan '{plan_name}' still uses 'payment_reminder'")
                        all_correct = False
                        
                if all_correct:
                    self.log("  ✅ All SaaS plans use 'whatsapp_notifications' (not 'payment_reminder')")
                    return True
                else:
                    self.log("  ❌ Some plans still use 'payment_reminder'")
                    return False
                    
            else:
                self.log(f"  ❌ Failed to get SaaS plans: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"  ❌ SaaS plans test error: {e}")
            return False

    def test_reminder_settings_with_whatsapp_addon(self) -> bool:
        """Test 4: Reminder settings uses whatsapp_notifications addon"""
        self.log("\n🧪 TEST 4: Reminder settings with whatsapp_notifications addon")
        
        try:
            # First, check if operator has whatsapp_notifications addon
            response = self.make_request('GET', '/operator/features', token=self.operator_token)
            
            if response.status_code == 200:
                features = response.json()
                has_whatsapp_notifications = features.get("whatsapp_notifications", False)
                self.log(f"  Operator has whatsapp_notifications addon: {has_whatsapp_notifications}")
                
                # Test reminder settings endpoint
                response = self.make_request('GET', '/operator/reminder-settings', token=self.operator_token)
                
                if has_whatsapp_notifications:
                    # Should return 200 if addon is enabled
                    if response.status_code == 200:
                        self.log("  ✅ Reminder settings accessible with whatsapp_notifications addon")
                        return True
                    else:
                        self.log(f"  ❌ Reminder settings not accessible despite having addon: {response.status_code}")
                        return False
                else:
                    # Should return 403 if addon is not enabled
                    if response.status_code == 403:
                        self.log("  ✅ Reminder settings correctly blocked without whatsapp_notifications addon")
                        return True
                    else:
                        self.log(f"  ❌ Unexpected response without addon: {response.status_code}")
                        return False
                        
            else:
                self.log(f"  ❌ Could not check features: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"  ❌ Reminder settings test error: {e}")
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        self.log("🚀 Starting Backend Testing Suite for SaaS Billing Platform")
        self.log(f"Backend URL: {BACKEND_URL}")
        
        # Initialize database and authentication
        if not self.test_seed_database():
            self.log("❌ Database seeding failed - aborting tests")
            return
            
        if not self.test_admin_login():
            self.log("❌ Admin authentication failed - aborting tests")
            return
            
        if not self.get_operator_and_plan():
            self.log("❌ Could not get operator/plan - aborting tests")
            return
            
        if not self.test_impersonate_operator():
            self.log("❌ Operator impersonation failed - aborting tests")
            return
        
        # Run the specific tests from review request
        results = {}
        
        # Test 1: Form validation fix
        results["form_validation"] = self.test_form_validation_empty_fields()
        
        # Test 2: Addon merge - features endpoint  
        results["addon_merge"] = self.test_addon_merge_features()
        
        # Test 3: SaaS plans updated
        results["saas_plans"] = self.test_saas_plans_addon_update()
        
        # Test 4: Reminder settings with whatsapp_notifications
        results["reminder_settings"] = self.test_reminder_settings_with_whatsapp_addon()
        
        # Summary
        self.log("\n📊 TEST SUMMARY")
        self.log("=" * 60)
        
        # Form validation results
        form_passed = results["form_validation"]["empty_strings"] and results["form_validation"]["null_values"]
        self.log(f"1. Form validation fix: {'✅ PASSED' if form_passed else '❌ FAILED'}")
        self.log(f"   - Empty strings: {'✅' if results['form_validation']['empty_strings'] else '❌'}")
        self.log(f"   - Null values: {'✅' if results['form_validation']['null_values'] else '❌'}")
        
        # Addon merge results
        addon_passed = results["addon_merge"]["correct_addon_names"] and results["addon_merge"]["expected_keys"]
        self.log(f"2. Addon merge - features: {'✅ PASSED' if addon_passed else '❌ FAILED'}")
        self.log(f"   - Correct addon names: {'✅' if results['addon_merge']['correct_addon_names'] else '❌'}")
        self.log(f"   - Expected keys present: {'✅' if results['addon_merge']['expected_keys'] else '❌'}")
        
        # SaaS plans results
        self.log(f"3. SaaS plans updated: {'✅ PASSED' if results['saas_plans'] else '❌ FAILED'}")
        
        # Reminder settings results
        self.log(f"4. Reminder settings: {'✅ PASSED' if results['reminder_settings'] else '❌ FAILED'}")
        
        # Overall results
        total_tests = 6  # 2 + 2 + 1 + 1
        passed_tests = sum([
            results["form_validation"]["empty_strings"],
            results["form_validation"]["null_values"],
            results["addon_merge"]["correct_addon_names"], 
            results["addon_merge"]["expected_keys"],
            results["saas_plans"],
            results["reminder_settings"]
        ])
        
        self.log(f"\nOVERALL: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
        
        if passed_tests == total_tests:
            self.log("🎉 ALL TESTS PASSED - Backend changes working correctly!")
        else:
            self.log("⚠️  Some tests failed - please review the results above")

if __name__ == "__main__":
    tester = BackendTester()
    tester.run_all_tests()