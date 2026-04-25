#!/usr/bin/env python3
"""
Backend API Testing for E-Bill Platform V8.32
Tests Multi-Tenure Plan Support features:
1. Plans with multiple available_validities
2. Subscriber plan assignment with selected_validity
3. Invoice line items with selected_validity and price scaling
4. Price formula implementation (Option B)
"""

import requests
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

# Configuration
BASE_URL = "https://changelog-review-13.preview.emergentagent.com/api"
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

class V832Tester:
    def __init__(self):
        self.session = requests.Session()
        self.operator_token = None
        self.test_results = []
        self.created_plan_id = None
        self.created_subscriber_id = None
        
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
    
    def login_operator(self):
        """Login as operator and get token"""
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json={
                "email": OPERATOR_EMAIL,
                "password": OPERATOR_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
                self.log_result("Operator Login", True, f"Token: {self.operator_token[:20]}...")
                return True
            else:
                self.log_result("Operator Login", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Operator Login", False, f"Exception: {str(e)}")
            return False
    
    def test_create_plan_with_multiple_validities(self):
        """Test Case 1: Create plan with multiple available_validities"""
        try:
            plan_data = {
                "name": "Broadband Pro",
                "price": 500,
                "validity": "monthly",
                "available_validities": ["monthly", "quarterly", "half_yearly", "yearly"],
                "tax_percentage": 18,
                "tax_type": "exclusive",
                "description": "Test plan for V8.32"
            }
            
            response = self.session.post(f"{BASE_URL}/operator/plans", json=plan_data)
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.created_plan_id = data.get("id")
                
                # Verify response structure
                expected_fields = ["id", "name", "price", "validity", "available_validities", "tax_percentage", "tax_type"]
                missing_fields = [f for f in expected_fields if f not in data]
                
                if missing_fields:
                    self.log_result("Create Plan - Response Structure", False, f"Missing fields: {missing_fields}")
                    return False
                
                # Verify specific values
                if (data.get("available_validities") == ["monthly", "quarterly", "half_yearly", "yearly"] and
                    data.get("validity") == "monthly" and
                    data.get("price") == 500):
                    self.log_result("Create Plan with Multiple Validities", True, 
                                  f"Plan created with ID: {self.created_plan_id}, available_validities: {data['available_validities']}")
                    return True
                else:
                    self.log_result("Create Plan with Multiple Validities", False, 
                                  f"Incorrect values - validity: {data.get('validity')}, price: {data.get('price')}, available_validities: {data.get('available_validities')}")
                    return False
            else:
                self.log_result("Create Plan with Multiple Validities", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Create Plan with Multiple Validities", False, f"Exception: {str(e)}")
            return False
    
    def test_get_plans_verify_available_validities(self):
        """Test Case 2: GET /api/operator/plans — verify available_validities returned"""
        try:
            response = self.session.get(f"{BASE_URL}/operator/plans")
            
            if response.status_code == 200:
                plans = response.json()
                
                if not plans:
                    self.log_result("GET Plans - Available Validities", False, "No plans found")
                    return False
                
                # Find our created plan
                created_plan = None
                for plan in plans:
                    if plan.get("id") == self.created_plan_id:
                        created_plan = plan
                        break
                
                if not created_plan:
                    self.log_result("GET Plans - Available Validities", False, "Created plan not found in list")
                    return False
                
                # Verify available_validities is present and correct
                available_validities = created_plan.get("available_validities")
                if available_validities == ["monthly", "quarterly", "half_yearly", "yearly"]:
                    self.log_result("GET Plans - Available Validities", True, 
                                  f"Plan has correct available_validities: {available_validities}")
                    
                    # Check for legacy plans (should have at least [plan.validity])
                    legacy_plans_ok = True
                    for plan in plans:
                        if not plan.get("available_validities"):
                            legacy_plans_ok = False
                            break
                        if plan.get("validity") not in plan.get("available_validities", []):
                            legacy_plans_ok = False
                            break
                    
                    if legacy_plans_ok:
                        self.log_result("GET Plans - Legacy Plans Check", True, "All plans have valid available_validities")
                    else:
                        self.log_result("GET Plans - Legacy Plans Check", False, "Some legacy plans missing available_validities")
                    
                    return True
                else:
                    self.log_result("GET Plans - Available Validities", False, 
                                  f"Incorrect available_validities: {available_validities}")
                    return False
            else:
                self.log_result("GET Plans - Available Validities", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("GET Plans - Available Validities", False, f"Exception: {str(e)}")
            return False
    
    def test_create_subscriber_with_yearly_tenure(self):
        """Test Case 3: Create subscriber with yearly tenure on monthly-priced plan"""
        try:
            if not self.created_plan_id:
                self.log_result("Create Subscriber - Yearly Tenure", False, "No plan ID available")
                return False
            
            subscriber_data = {
                "name": "Tenure Test Sub",
                "whatsapp_number": "9100000099",
                "email": "tenuretest@test.com",
                "address": "Test Address",
                "plans": [{
                    "plan_id": self.created_plan_id,
                    "selected_validity": "yearly",
                    "plan_start_date": "2026-04-21",
                    "discount": 0
                }],
                "generate_first_invoice": False
            }
            
            response = self.session.post(f"{BASE_URL}/operator/subscribers", json=subscriber_data)
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.created_subscriber_id = data.get("id")
                
                # Verify subscriber created
                if not self.created_subscriber_id:
                    self.log_result("Create Subscriber - Yearly Tenure", False, "No subscriber ID returned")
                    return False
                
                # Verify plan details
                plans = data.get("plans", [])
                if not plans:
                    self.log_result("Create Subscriber - Yearly Tenure", False, "No plans in subscriber response")
                    return False
                
                plan = plans[0]
                selected_validity = plan.get("selected_validity")
                plan_expiry_date = plan.get("plan_expiry_date")
                
                # Verify selected_validity
                if selected_validity != "yearly":
                    self.log_result("Create Subscriber - Yearly Tenure", False, 
                                  f"Incorrect selected_validity: {selected_validity}")
                    return False
                
                # Verify expiry date calculation (2026-04-21 + 12 months - 1 day = 2027-04-20)
                if plan_expiry_date != "2027-04-20":
                    self.log_result("Create Subscriber - Yearly Tenure", False, 
                                  f"Incorrect expiry date: {plan_expiry_date}, expected: 2027-04-20")
                    return False
                
                self.log_result("Create Subscriber - Yearly Tenure", True, 
                              f"Subscriber created with yearly tenure, expiry: {plan_expiry_date}")
                return True
            else:
                self.log_result("Create Subscriber - Yearly Tenure", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Create Subscriber - Yearly Tenure", False, f"Exception: {str(e)}")
            return False
    
    def test_price_scaling_in_invoice_creation(self):
        """Test Case 4: Price scaling in invoice creation"""
        try:
            if not self.created_subscriber_id or not self.created_plan_id:
                self.log_result("Invoice Price Scaling", False, "Missing subscriber or plan ID")
                return False
            
            # Create invoice with yearly tenure (price should be 500 * 12 = 6000)
            invoice_data = {
                "subscriber_id": self.created_subscriber_id,
                "line_items": [{
                    "plan_id": self.created_plan_id,
                    "selected_validity": "yearly",
                    "base_amount": 6000,
                    "discount": 0,
                    "service_start_date": "2026-04-21T00:00:00",
                    "service_end_date": "2027-04-20T00:00:00"
                }],
                "due_date": "2026-05-01T00:00:00"
            }
            
            response = self.session.post(f"{BASE_URL}/operator/invoices", json=invoice_data)
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                # Verify invoice created
                invoice_id = data.get("id")
                if not invoice_id:
                    self.log_result("Invoice Price Scaling", False, "No invoice ID returned")
                    return False
                
                # Verify line items
                line_items = data.get("line_items", [])
                if not line_items:
                    self.log_result("Invoice Price Scaling", False, "No line items in invoice")
                    return False
                
                line_item = line_items[0]
                base_amount = line_item.get("base_amount")
                selected_validity = line_item.get("selected_validity")
                
                # Verify base_amount is 6000 (500 * 12 months)
                if base_amount != 6000:
                    self.log_result("Invoice Price Scaling", False, 
                                  f"Incorrect base_amount: {base_amount}, expected: 6000")
                    return False
                
                # Verify selected_validity is stored
                if selected_validity != "yearly":
                    self.log_result("Invoice Price Scaling", False, 
                                  f"Incorrect selected_validity: {selected_validity}")
                    return False
                
                # Verify tax calculation (18% exclusive on 6000 = 1080)
                tax_amount = data.get("tax_amount", 0)
                expected_tax = 6000 * 0.18  # 1080
                if abs(tax_amount - expected_tax) > 0.01:
                    self.log_result("Invoice Price Scaling", False, 
                                  f"Incorrect tax_amount: {tax_amount}, expected: {expected_tax}")
                    return False
                
                self.log_result("Invoice Price Scaling", True, 
                              f"Invoice created with correct scaling - base: ₹{base_amount}, tax: ₹{tax_amount}")
                return True
            else:
                self.log_result("Invoice Price Scaling", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Invoice Price Scaling", False, f"Exception: {str(e)}")
            return False
    
    def test_quarterly_tenure_pricing(self):
        """Test Case 5: Test quarterly tenure (price=500/monthly → quarterly=1500)"""
        try:
            if not self.created_subscriber_id or not self.created_plan_id:
                self.log_result("Quarterly Tenure Pricing", False, "Missing subscriber or plan ID")
                return False
            
            # Create invoice with quarterly tenure (price should be 500 * 3 = 1500)
            invoice_data = {
                "subscriber_id": self.created_subscriber_id,
                "line_items": [{
                    "plan_id": self.created_plan_id,
                    "selected_validity": "quarterly",
                    "base_amount": 1500,
                    "discount": 0,
                    "service_start_date": "2026-04-21T00:00:00",
                    "service_end_date": "2026-07-20T00:00:00"
                }],
                "due_date": "2026-05-01T00:00:00"
            }
            
            response = self.session.post(f"{BASE_URL}/operator/invoices", json=invoice_data)
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                # Verify line items
                line_items = data.get("line_items", [])
                if not line_items:
                    self.log_result("Quarterly Tenure Pricing", False, "No line items in invoice")
                    return False
                
                line_item = line_items[0]
                base_amount = line_item.get("base_amount")
                selected_validity = line_item.get("selected_validity")
                
                # Verify base_amount is 1500 (500 * 3 months)
                if base_amount != 1500:
                    self.log_result("Quarterly Tenure Pricing", False, 
                                  f"Incorrect base_amount: {base_amount}, expected: 1500")
                    return False
                
                # Verify selected_validity is stored
                if selected_validity != "quarterly":
                    self.log_result("Quarterly Tenure Pricing", False, 
                                  f"Incorrect selected_validity: {selected_validity}")
                    return False
                
                self.log_result("Quarterly Tenure Pricing", True, 
                              f"Quarterly invoice created correctly - base: ₹{base_amount}")
                return True
            else:
                self.log_result("Quarterly Tenure Pricing", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Quarterly Tenure Pricing", False, f"Exception: {str(e)}")
            return False
    
    def test_update_plan_available_validities(self):
        """Test Case 6: Update plan — available_validities persisted"""
        try:
            if not self.created_plan_id:
                self.log_result("Update Plan Available Validities", False, "No plan ID available")
                return False
            
            # Update plan to remove quarterly and half_yearly
            update_data = {
                "name": "Broadband Pro",
                "price": 500,
                "validity": "monthly",
                "available_validities": ["monthly", "yearly"],
                "tax_percentage": 18,
                "tax_type": "exclusive",
                "description": "Updated plan for V8.32"
            }
            
            response = self.session.put(f"{BASE_URL}/operator/plans/{self.created_plan_id}", json=update_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify available_validities updated
                available_validities = data.get("available_validities")
                if available_validities == ["monthly", "yearly"]:
                    self.log_result("Update Plan Available Validities", True, 
                                  f"Plan updated with new available_validities: {available_validities}")
                    
                    # Verify by getting the plan again
                    get_response = self.session.get(f"{BASE_URL}/operator/plans")
                    if get_response.status_code == 200:
                        plans = get_response.json()
                        updated_plan = None
                        for plan in plans:
                            if plan.get("id") == self.created_plan_id:
                                updated_plan = plan
                                break
                        
                        if updated_plan and updated_plan.get("available_validities") == ["monthly", "yearly"]:
                            self.log_result("Update Plan Persistence Check", True, 
                                          "Updated available_validities persisted correctly")
                            return True
                        else:
                            self.log_result("Update Plan Persistence Check", False, 
                                          f"Persistence failed: {updated_plan.get('available_validities') if updated_plan else 'Plan not found'}")
                            return False
                    else:
                        self.log_result("Update Plan Persistence Check", False, 
                                      f"Failed to verify persistence: {get_response.status_code}")
                        return False
                else:
                    self.log_result("Update Plan Available Validities", False, 
                                  f"Incorrect available_validities after update: {available_validities}")
                    return False
            else:
                self.log_result("Update Plan Available Validities", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Update Plan Available Validities", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all V8.32 tests in sequence"""
        print("🚀 Starting E-Bill V8.32 Multi-Tenure Plan Support Tests")
        print("=" * 60)
        
        # Login first
        if not self.login_operator():
            print("❌ Cannot proceed without operator login")
            return False
        
        # Test 1: Create plan with multiple validities
        print("\n📋 Test 1: Create Plan with Multiple Available Validities...")
        self.test_create_plan_with_multiple_validities()
        
        # Test 2: Verify available_validities in GET response
        print("\n📋 Test 2: Verify Available Validities in GET Response...")
        self.test_get_plans_verify_available_validities()
        
        # Test 3: Create subscriber with yearly tenure
        print("\n👤 Test 3: Create Subscriber with Yearly Tenure...")
        self.test_create_subscriber_with_yearly_tenure()
        
        # Test 4: Price scaling in invoice creation
        print("\n💰 Test 4: Price Scaling in Invoice Creation...")
        self.test_price_scaling_in_invoice_creation()
        
        # Test 5: Quarterly tenure pricing
        print("\n💰 Test 5: Quarterly Tenure Pricing...")
        self.test_quarterly_tenure_pricing()
        
        # Test 6: Update plan available_validities
        print("\n📝 Test 6: Update Plan Available Validities...")
        self.test_update_plan_available_validities()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 V8.32 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results if r["success"])
        total = len(self.test_results)
        
        for result in self.test_results:
            print(f"{result['status']}: {result['test']}")
        
        print(f"\n🎯 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All V8.32 Multi-Tenure Plan Support tests passed!")
            return True
        else:
            print("⚠️  Some tests failed. Check details above.")
            return False

if __name__ == "__main__":
    tester = V832Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)