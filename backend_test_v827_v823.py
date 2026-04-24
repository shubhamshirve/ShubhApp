#!/usr/bin/env python3
"""
Backend API Testing for E-Bill Platform - V8.27 & V8.23 Features
Tests the newly implemented features:
1. V8.27: Admin Dashboard Subscriber Overview (new fields)
2. V8.23: GST Control Settings (gst_enabled_on_saas_plans, gst_enabled_on_wallet_topup)
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://changelog-review-13.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

class EBillTesterV827V823:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
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
                # Don't set Authorization header - use cookies instead
                # The login response sets httpOnly cookies automatically
                self.log_result("Admin Login", True, f"Token: {self.admin_token[:20]}...")
                return True
            else:
                self.log_result("Admin Login", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Admin Login", False, f"Exception: {str(e)}")
            return False
    
    def login_operator(self):
        """Login as operator and get token"""
        try:
            # Create a separate session for operator login to avoid interfering with admin session
            operator_session = requests.Session()
            
            response = operator_session.post(f"{BASE_URL}/auth/login", json={
                "email": OPERATOR_EMAIL,
                "password": OPERATOR_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                self.log_result("Operator Login", True, f"Token: {self.operator_token[:20]}...")
                return True
            else:
                self.log_result("Operator Login", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Operator Login", False, f"Exception: {str(e)}")
            return False
    
    def seed_data(self):
        """Call seed endpoint to ensure base data is present"""
        try:
            response = self.session.post(f"{BASE_URL}/seed")
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("Seed Data", True, f"Response: {data}")
                return True
            else:
                self.log_result("Seed Data", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Seed Data", False, f"Exception: {str(e)}")
            return False
    
    # V8.27 Tests: Admin Dashboard Subscriber Overview
    def test_admin_dashboard_new_fields(self):
        """Test 1: GET /api/admin/dashboard includes new subscriber fields"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/dashboard")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for new fields
                required_new_fields = [
                    "total_subscribers",
                    "active_subscribers", 
                    "suspended_subscribers",
                    "approx_monthly_revenue"
                ]
                
                missing_fields = [field for field in required_new_fields if field not in data]
                
                if not missing_fields:
                    # Verify field types
                    field_types_correct = True
                    type_errors = []
                    
                    for field in ["total_subscribers", "active_subscribers", "suspended_subscribers"]:
                        if not isinstance(data[field], int):
                            field_types_correct = False
                            type_errors.append(f"{field} is {type(data[field])}, expected int")
                    
                    if not isinstance(data["approx_monthly_revenue"], (int, float)):
                        field_types_correct = False
                        type_errors.append(f"approx_monthly_revenue is {type(data['approx_monthly_revenue'])}, expected float")
                    
                    if field_types_correct:
                        self.log_result("Admin Dashboard New Fields Present", True, 
                                      f"All fields present with correct types: {required_new_fields}")
                        return True, data
                    else:
                        self.log_result("Admin Dashboard New Fields Present", False, 
                                      f"Type errors: {type_errors}")
                        return False, data
                else:
                    self.log_result("Admin Dashboard New Fields Present", False, 
                                  f"Missing fields: {missing_fields}")
                    return False, data
            else:
                self.log_result("Admin Dashboard New Fields Present", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
                return False, None
        except Exception as e:
            self.log_result("Admin Dashboard New Fields Present", False, f"Exception: {str(e)}")
            return False, None
    
    def test_admin_dashboard_existing_fields(self):
        """Test 2: Verify existing fields are still present"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/dashboard")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for existing fields
                existing_fields = [
                    "total_operators",
                    "active_operators", 
                    "trial_operators",
                    "suspended_operators",
                    "expiring_operators",
                    "saas_revenue_this_month",
                    "total_saas_revenue",
                    "recent_payments"
                ]
                
                missing_fields = [field for field in existing_fields if field not in data]
                
                if not missing_fields:
                    self.log_result("Admin Dashboard Existing Fields Present", True, 
                                  f"All existing fields present: {existing_fields}")
                    return True
                else:
                    self.log_result("Admin Dashboard Existing Fields Present", False, 
                                  f"Missing existing fields: {missing_fields}")
                    return False
            else:
                self.log_result("Admin Dashboard Existing Fields Present", False, 
                              f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Admin Dashboard Existing Fields Present", False, f"Exception: {str(e)}")
            return False
    
    def test_subscriber_counts_logic(self, dashboard_data):
        """Test 3: Verify subscriber count values are logical"""
        try:
            total_subs = dashboard_data["total_subscribers"]
            active_subs = dashboard_data["active_subscribers"]
            suspended_subs = dashboard_data["suspended_subscribers"]
            
            # Basic logic checks
            if total_subs >= 10:  # Expected at least 10 from seeded data
                if active_subs >= 10:  # Expected 10 active from seeded data
                    if suspended_subs == 0:  # Expected 0 suspended initially
                        if active_subs + suspended_subs <= total_subs:  # Logic check
                            self.log_result("Subscriber Counts Logic", True, 
                                          f"Total: {total_subs}, Active: {active_subs}, Suspended: {suspended_subs}")
                            return True
                        else:
                            self.log_result("Subscriber Counts Logic", False, 
                                          f"Active + Suspended ({active_subs + suspended_subs}) > Total ({total_subs})")
                            return False
                    else:
                        self.log_result("Subscriber Counts Logic", False, 
                                      f"Expected 0 suspended initially, got {suspended_subs}")
                        return False
                else:
                    self.log_result("Subscriber Counts Logic", False, 
                                  f"Expected at least 10 active subscribers, got {active_subs}")
                    return False
            else:
                self.log_result("Subscriber Counts Logic", False, 
                              f"Expected at least 10 total subscribers, got {total_subs}")
                return False
        except Exception as e:
            self.log_result("Subscriber Counts Logic", False, f"Exception: {str(e)}")
            return False
    
    def test_monthly_revenue_field(self, dashboard_data):
        """Test 4: Verify approx_monthly_revenue is a valid number"""
        try:
            revenue = dashboard_data["approx_monthly_revenue"]
            
            if isinstance(revenue, (int, float)) and revenue >= 0:
                self.log_result("Monthly Revenue Field", True, 
                              f"Revenue: {revenue} (expected 0.0 since no plans with prices yet)")
                return True
            else:
                self.log_result("Monthly Revenue Field", False, 
                              f"Invalid revenue value: {revenue} (type: {type(revenue)})")
                return False
        except Exception as e:
            self.log_result("Monthly Revenue Field", False, f"Exception: {str(e)}")
            return False
    
    # V8.23 Tests: GST Control Settings
    def test_gst_settings_get(self):
        """Test 5: GET /api/admin/settings includes GST control fields"""
        try:
            response = self.session.get(f"{BASE_URL}/admin/settings")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for GST fields
                gst_fields = ["gst_enabled_on_saas_plans", "gst_enabled_on_wallet_topup"]
                missing_fields = [field for field in gst_fields if field not in data]
                
                if not missing_fields:
                    # Check default values (should be True)
                    gst_saas = data["gst_enabled_on_saas_plans"]
                    gst_wallet = data["gst_enabled_on_wallet_topup"]
                    
                    if isinstance(gst_saas, bool) and isinstance(gst_wallet, bool):
                        self.log_result("GST Settings GET", True, 
                                      f"GST fields present - SaaS: {gst_saas}, Wallet: {gst_wallet}")
                        return True, data
                    else:
                        self.log_result("GST Settings GET", False, 
                                      f"GST fields not boolean - SaaS: {type(gst_saas)}, Wallet: {type(gst_wallet)}")
                        return False, data
                else:
                    self.log_result("GST Settings GET", False, f"Missing GST fields: {missing_fields}")
                    return False, data
            else:
                self.log_result("GST Settings GET", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
                return False, None
        except Exception as e:
            self.log_result("GST Settings GET", False, f"Exception: {str(e)}")
            return False, None
    
    def test_gst_settings_update_wallet_false(self, current_settings):
        """Test 6: PUT /api/admin/settings with gst_enabled_on_wallet_topup=false"""
        try:
            # Update settings with wallet GST disabled
            update_data = {
                **current_settings,
                "gst_enabled_on_wallet_topup": False,
                "gst_enabled_on_saas_plans": True
            }
            
            response = self.session.put(f"{BASE_URL}/admin/settings", json=update_data)
            
            if response.status_code == 200:
                # Verify the change was saved
                verify_response = self.session.get(f"{BASE_URL}/admin/settings")
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    
                    if (verify_data["gst_enabled_on_wallet_topup"] == False and 
                        verify_data["gst_enabled_on_saas_plans"] == True):
                        self.log_result("GST Settings Update (Wallet False)", True, 
                                      "Wallet GST disabled, SaaS GST enabled")
                        return True
                    else:
                        self.log_result("GST Settings Update (Wallet False)", False, 
                                      f"Settings not saved correctly: Wallet={verify_data['gst_enabled_on_wallet_topup']}, SaaS={verify_data['gst_enabled_on_saas_plans']}")
                        return False
                else:
                    self.log_result("GST Settings Update (Wallet False)", False, 
                                  f"Verification GET failed: {verify_response.status_code}")
                    return False
            else:
                self.log_result("GST Settings Update (Wallet False)", False, 
                              f"PUT failed - Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("GST Settings Update (Wallet False)", False, f"Exception: {str(e)}")
            return False
    
    def test_gst_settings_update_both_false(self):
        """Test 7: PUT /api/admin/settings with both GST settings false"""
        try:
            # Get current settings first
            response = self.session.get(f"{BASE_URL}/admin/settings")
            if response.status_code != 200:
                self.log_result("GST Settings Update (Both False)", False, "Failed to get current settings")
                return False
            
            current_settings = response.json()
            
            # Update settings with both GST disabled
            update_data = {
                **current_settings,
                "gst_enabled_on_wallet_topup": False,
                "gst_enabled_on_saas_plans": False
            }
            
            response = self.session.put(f"{BASE_URL}/admin/settings", json=update_data)
            
            if response.status_code == 200:
                # Verify the change was saved
                verify_response = self.session.get(f"{BASE_URL}/admin/settings")
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    
                    if (verify_data["gst_enabled_on_wallet_topup"] == False and 
                        verify_data["gst_enabled_on_saas_plans"] == False):
                        self.log_result("GST Settings Update (Both False)", True, 
                                      "Both GST settings disabled")
                        return True
                    else:
                        self.log_result("GST Settings Update (Both False)", False, 
                                      f"Settings not saved correctly: Wallet={verify_data['gst_enabled_on_wallet_topup']}, SaaS={verify_data['gst_enabled_on_saas_plans']}")
                        return False
                else:
                    self.log_result("GST Settings Update (Both False)", False, 
                                  f"Verification GET failed: {verify_response.status_code}")
                    return False
            else:
                self.log_result("GST Settings Update (Both False)", False, 
                              f"PUT failed - Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("GST Settings Update (Both False)", False, f"Exception: {str(e)}")
            return False
    
    def test_gst_settings_restore_true(self):
        """Test 8: PUT /api/admin/settings to restore both GST settings to true"""
        try:
            # Get current settings first
            response = self.session.get(f"{BASE_URL}/admin/settings")
            if response.status_code != 200:
                self.log_result("GST Settings Restore (Both True)", False, "Failed to get current settings")
                return False
            
            current_settings = response.json()
            
            # Update settings with both GST enabled
            update_data = {
                **current_settings,
                "gst_enabled_on_wallet_topup": True,
                "gst_enabled_on_saas_plans": True
            }
            
            response = self.session.put(f"{BASE_URL}/admin/settings", json=update_data)
            
            if response.status_code == 200:
                # Verify the change was saved
                verify_response = self.session.get(f"{BASE_URL}/admin/settings")
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    
                    if (verify_data["gst_enabled_on_wallet_topup"] == True and 
                        verify_data["gst_enabled_on_saas_plans"] == True):
                        self.log_result("GST Settings Restore (Both True)", True, 
                                      "Both GST settings restored to enabled")
                        return True
                    else:
                        self.log_result("GST Settings Restore (Both True)", False, 
                                      f"Settings not saved correctly: Wallet={verify_data['gst_enabled_on_wallet_topup']}, SaaS={verify_data['gst_enabled_on_saas_plans']}")
                        return False
                else:
                    self.log_result("GST Settings Restore (Both True)", False, 
                                  f"Verification GET failed: {verify_response.status_code}")
                    return False
            else:
                self.log_result("GST Settings Restore (Both True)", False, 
                              f"PUT failed - Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("GST Settings Restore (Both True)", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting E-Bill Backend API Tests - V8.27 & V8.23 Features")
        print("=" * 70)
        
        # Seed data first
        self.seed_data()
        
        # Login as admin
        if not self.login_admin():
            print("❌ Cannot proceed without admin login")
            return False
        
        # Login as operator (for potential future tests)
        self.login_operator()
        
        print("\n📊 Testing V8.27: Admin Dashboard Subscriber Overview...")
        print("-" * 50)
        
        # Test admin dashboard new fields
        success, dashboard_data = self.test_admin_dashboard_new_fields()
        if success and dashboard_data:
            self.test_admin_dashboard_existing_fields()
            self.test_subscriber_counts_logic(dashboard_data)
            self.test_monthly_revenue_field(dashboard_data)
        
        print("\n⚙️ Testing V8.23: GST Control Settings...")
        print("-" * 50)
        
        # Test GST settings
        success, settings_data = self.test_gst_settings_get()
        if success and settings_data:
            self.test_gst_settings_update_wallet_false(settings_data)
            self.test_gst_settings_update_both_false()
            self.test_gst_settings_restore_true()
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
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
    tester = EBillTesterV827V823()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)