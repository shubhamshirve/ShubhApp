#!/usr/bin/env python3
"""
Backend Testing Script for Multi-Tenant SaaS Billing Platform
Tests the new features requested in the review.
"""
import requests
import json
import sys
import os
from typing import Dict, Any, Optional

# Configuration
BACKEND_URL = "https://checkout-error-trace.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"

class BackendTester:
    def __init__(self):
        self.admin_token = None
        self.operator_token = None
        self.operator_id = None
        self.created_gateway_id = None
        self.created_template_id = None
        
    def make_request(self, method: str, endpoint: str, token: Optional[str] = None, 
                    data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request with proper headers"""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        url = f"{BACKEND_URL}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, params=params)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)
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
    
    def test_seed(self):
        """Test 1: Seed database"""
        print("🌱 Testing seed endpoint...")
        result = self.make_request("POST", "/seed")
        if result["success"]:
            print("✅ Seed endpoint working")
            return True
        else:
            print(f"❌ Seed failed: {result['data']}")
            return False
    
    def test_admin_login(self):
        """Test 2: Admin login"""
        print("🔑 Testing admin login...")
        result = self.make_request("POST", "/auth/login", data={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if result["success"]:
            self.admin_token = result["data"]["access_token"]
            print("✅ Admin login successful")
            return True
        else:
            print(f"❌ Admin login failed: {result['data']}")
            return False
    
    def test_platform_gateway_creation(self):
        """Test 3: Create platform payment gateway"""
        print("💳 Testing platform gateway creation...")
        gateway_data = {
            "gateway_type": "razorpay",
            "api_key": "rzp_test_sFaXdx3kATIGiw",
            "api_secret": "dOvQqMbfE2sPkYulgTeU2SpW",
            "is_active": True,
            "for_operator_id": None  # This makes it a platform gateway
        }
        result = self.make_request("POST", "/admin/payment-gateways", self.admin_token, gateway_data)
        if result["success"]:
            self.created_gateway_id = result["data"].get("id")
            print("✅ Platform gateway created successfully")
            return True
        else:
            print(f"❌ Platform gateway creation failed: {result['data']}")
            return False
    
    def test_gateway_platform_flag(self):
        """Test 4: Verify platform gateway has is_platform_gateway=True"""
        print("🔍 Testing platform gateway flag...")
        result = self.make_request("GET", "/admin/payment-gateways", self.admin_token)
        if result["success"]:
            gateways = result["data"]
            platform_gateway = None
            for gw in gateways:
                if gw.get("is_platform_gateway") == True and gw.get("gateway_type") == "razorpay":
                    platform_gateway = gw
                    break
            
            if platform_gateway:
                print("✅ Platform gateway found with is_platform_gateway=True")
                return True
            else:
                print("❌ Platform gateway not found or missing is_platform_gateway=True flag")
                return False
        else:
            print(f"❌ Failed to get gateways: {result['data']}")
            return False
    
    def test_create_operator(self):
        """Test 5: Create or get operator for testing"""
        print("👤 Getting operator for testing...")
        
        # First try to get an existing operator
        result = self.make_request("GET", "/admin/operators", self.admin_token)
        if result["success"] and result["data"]:
            # Use the first operator
            operator = result["data"][0]
            self.operator_id = operator["id"]
            print(f"✅ Using existing operator: {operator.get('company_name', 'Unknown')}")
            return True
        
        # If no operators, create one manually
        print("📝 Creating new operator...")
        # Get a paid SaaS plan first
        plans_result = self.make_request("GET", "/admin/saas-plans", self.admin_token)
        if not plans_result["success"]:
            print(f"❌ Failed to get SaaS plans: {plans_result['data']}")
            return False
        
        paid_plan = None
        for plan in plans_result["data"]:
            if plan.get("monthly_price", 0) > 0:
                paid_plan = plan
                break
        
        if not paid_plan:
            print("❌ No paid SaaS plan found")
            return False
        
        operator_data = {
            "company_name": "Test Broadband Co",
            "owner_name": "Test Owner",
            "email": "testop@broadband.com",
            "phone": "9876543210",
            "password": "testpass123",
            "saas_plan_id": paid_plan["id"],
            "subscription_months": 1,
            "status": "active"
        }
        
        create_result = self.make_request("POST", "/admin/operators/create", self.admin_token, operator_data)
        if create_result["success"]:
            self.operator_id = create_result["data"]["id"]
            print(f"✅ Created operator: {create_result['data']['company_name']}")
            return True
        else:
            print(f"❌ Operator creation failed: {create_result['data']}")
            return False
    
    def test_operator_impersonation(self):
        """Test 6: Impersonate operator to get operator token"""
        print("🎭 Testing operator impersonation...")
        result = self.make_request("POST", f"/admin/operators/{self.operator_id}/impersonate", self.admin_token)
        if result["success"]:
            self.operator_token = result["data"]["access_token"]
            print("✅ Operator impersonation successful")
            return True
        else:
            print(f"❌ Operator impersonation failed: {result['data']}")
            return False
    
    def test_checkout_with_platform_gateway(self):
        """Test 7: Test checkout using platform DB gateway instead of env vars"""
        print("💰 Testing checkout with platform gateway...")
        
        # First get a paid plan
        plans_result = self.make_request("GET", "/admin/saas-plans", self.admin_token)
        if not plans_result["success"]:
            print(f"❌ Failed to get SaaS plans: {plans_result['data']}")
            return False
        
        paid_plan = None
        for plan in plans_result["data"]:
            if plan.get("monthly_price", 0) > 0:
                paid_plan = plan
                break
        
        if not paid_plan:
            print("❌ No paid SaaS plan found for checkout")
            return False
        
        # Try checkout
        checkout_params = {
            "item_type": "subscription",
            "plan_id": paid_plan["id"],
            "months": 1
        }
        result = self.make_request("POST", "/operator/checkout/create-order", self.operator_token, params=checkout_params)
        
        if result["success"]:
            if result["data"].get("razorpay_order_id"):
                print("✅ Checkout successful - using platform DB gateway keys")
                return True
            else:
                print("❌ Checkout success but no razorpay_order_id returned")
                return False
        else:
            print(f"❌ Checkout failed: {result['data']}")
            return False
    
    def test_mutual_exclusion_payment_gateway(self):
        """Test 8: Test mutual exclusion of payment_gateway vs custom_payment_gateway"""
        print("🔄 Testing payment gateway mutual exclusion...")
        
        # Step 1: Assign payment_gateway addon
        result = self.make_request("POST", f"/admin/operators/{self.operator_id}/addons/payment_gateway", self.admin_token)
        if not result["success"]:
            print(f"❌ Failed to assign payment_gateway addon: {result['data']}")
            return False
        print(f"📝 payment_gateway addon assignment response: {result['data']}")
        
        # Step 2: Check operator has payment_gateway but NOT custom_payment_gateway
        op_result = self.make_request("GET", f"/admin/operators/{self.operator_id}", self.admin_token)
        if not op_result["success"]:
            print(f"❌ Failed to get operator: {op_result['data']}")
            return False
        
        active_addons = op_result["data"].get("active_addons") or []
        print(f"📋 Active addons after payment_gateway assignment: {active_addons}")
        if "payment_gateway" in active_addons and "custom_payment_gateway" not in active_addons:
            print("✅ Step 1 passed: payment_gateway assigned, custom_payment_gateway not present")
        else:
            print(f"❌ Step 1 failed: active_addons = {active_addons}")
            return False
        
        # Step 3: Assign custom_payment_gateway addon  
        result = self.make_request("POST", f"/admin/operators/{self.operator_id}/addons/custom_payment_gateway", self.admin_token)
        if not result["success"]:
            print(f"❌ Failed to assign custom_payment_gateway addon: {result['data']}")
            return False
        print(f"📝 custom_payment_gateway addon assignment response: {result['data']}")
        
        # Step 4: Check operator has custom_payment_gateway but NOT payment_gateway
        op_result = self.make_request("GET", f"/admin/operators/{self.operator_id}", self.admin_token)
        if not op_result["success"]:
            print(f"❌ Failed to get operator: {op_result['data']}")
            return False
        
        active_addons = op_result["data"].get("active_addons") or []
        print(f"📋 Active addons after custom_payment_gateway assignment: {active_addons}")
        if "custom_payment_gateway" in active_addons and "payment_gateway" not in active_addons:
            print("✅ Mutual exclusion working: custom_payment_gateway assigned, payment_gateway removed")
            return True
        else:
            print(f"❌ Mutual exclusion failed: active_addons = {active_addons}")
            return False
    
    def test_whatsapp_templates_crud(self):
        """Test 9: Test WhatsApp Templates CRUD operations"""
        print("📱 Testing WhatsApp Templates CRUD...")
        
        # Step 1: Create a template
        template_data = {
            "template_name": "invoice_notification",
            "display_name": "Invoice Notification", 
            "template_type": "invoice_notification",
            "language_code": "en",
            "description": "Used for sending invoice to customers",
            "body_variables": ["customer_name", "invoice_number", "amount", "due_date"],
            "has_payment_button": True,
            "is_active": True
        }
        
        create_result = self.make_request("POST", "/admin/whatsapp-templates", self.admin_token, template_data)
        if not create_result["success"]:
            print(f"❌ Template creation failed: {create_result['data']}")
            return False
        
        self.created_template_id = create_result["data"]["id"]
        print("✅ Template created successfully")
        
        # Step 2: List all templates
        list_result = self.make_request("GET", "/admin/whatsapp-templates", self.admin_token)
        if not list_result["success"]:
            print(f"❌ Template listing failed: {list_result['data']}")
            return False
        
        templates = list_result["data"]
        found_template = None
        for template in templates:
            if template["id"] == self.created_template_id:
                found_template = template
                break
        
        if not found_template:
            print("❌ Created template not found in list")
            return False
        print("✅ Template found in list")
        
        # Step 3: Get single template
        get_result = self.make_request("GET", f"/admin/whatsapp-templates/{self.created_template_id}", self.admin_token)
        if not get_result["success"]:
            print(f"❌ Template get failed: {get_result['data']}")
            return False
        print("✅ Single template retrieved successfully")
        
        # Step 4: Update template
        update_data = {"description": "Updated description"}
        update_result = self.make_request("PUT", f"/admin/whatsapp-templates/{self.created_template_id}", self.admin_token, update_data)
        if not update_result["success"]:
            print(f"❌ Template update failed: {update_result['data']}")
            return False
        
        if update_result["data"]["description"] == "Updated description":
            print("✅ Template updated successfully")
        else:
            print("❌ Template update didn't apply changes")
            return False
        
        # Step 5: Toggle template status
        toggle_result = self.make_request("PATCH", f"/admin/whatsapp-templates/{self.created_template_id}/toggle", self.admin_token)
        if not toggle_result["success"]:
            print(f"❌ Template toggle failed: {toggle_result['data']}")
            return False
        print("✅ Template status toggled successfully")
        
        # Step 6: Try to create duplicate template (should fail)
        duplicate_result = self.make_request("POST", "/admin/whatsapp-templates", self.admin_token, template_data)
        if duplicate_result["status_code"] == 400:
            print("✅ Duplicate template creation correctly rejected with 400")
        else:
            print(f"❌ Duplicate template should have failed with 400, got {duplicate_result['status_code']}")
            return False
        
        # Step 7: Delete template
        delete_result = self.make_request("DELETE", f"/admin/whatsapp-templates/{self.created_template_id}", self.admin_token)
        if not delete_result["success"]:
            print(f"❌ Template deletion failed: {delete_result['data']}")
            return False
        print("✅ Template deleted successfully")
        
        return True
    
    def test_configure_payment_gateway_addon_required(self):
        """Test 10: Test that configure_payment_gateway requires custom_payment_gateway addon"""
        print("🔧 Testing payment gateway configuration addon requirement...")
        
        # First, remove custom_payment_gateway addon if present and ensure operator only has payment_gateway
        result = self.make_request("POST", f"/admin/operators/{self.operator_id}/addons/payment_gateway", self.admin_token)
        if not result["success"]:
            print(f"❌ Failed to assign payment_gateway addon: {result['data']}")
            return False
        
        # Try to configure payment gateway (should fail without custom_payment_gateway addon)
        gateway_config = {
            "gateway_type": "razorpay",
            "api_key": "test_key",
            "api_secret": "test_secret"
        }
        
        config_result = self.make_request("POST", "/operator/payment-gateway", self.operator_token, gateway_config)
        if config_result["status_code"] == 403:
            print("✅ Payment gateway config correctly rejected without custom_payment_gateway addon (403)")
        else:
            print(f"❌ Expected 403, got {config_result['status_code']}: {config_result['data']}")
            return False
        
        # Now assign custom_payment_gateway addon
        addon_result = self.make_request("POST", f"/admin/operators/{self.operator_id}/addons/custom_payment_gateway", self.admin_token)
        if not addon_result["success"]:
            print(f"❌ Failed to assign custom_payment_gateway addon: {addon_result['data']}")
            return False
        
        # Try to configure payment gateway again (should succeed now)
        config_result2 = self.make_request("POST", "/operator/payment-gateway", self.operator_token, gateway_config)
        if config_result2["success"]:
            print("✅ Payment gateway config successful with custom_payment_gateway addon")
            return True
        else:
            print(f"❌ Payment gateway config failed even with custom_payment_gateway addon: {config_result2['data']}")
            return False

def main():
    """Main test runner"""
    print("🚀 Starting Backend Testing for Multi-Tenant SaaS Billing Platform")
    print("=" * 70)
    
    tester = BackendTester()
    
    tests = [
        ("Seed Database", tester.test_seed),
        ("Admin Login", tester.test_admin_login),
        ("Create Platform Payment Gateway", tester.test_platform_gateway_creation),
        ("Verify Platform Gateway Flag", tester.test_gateway_platform_flag),
        ("Get/Create Operator", tester.test_create_operator), 
        ("Operator Impersonation", tester.test_operator_impersonation),
        ("Checkout with Platform Gateway", tester.test_checkout_with_platform_gateway),
        ("Payment Gateway Mutual Exclusion", tester.test_mutual_exclusion_payment_gateway),
        ("WhatsApp Templates CRUD", tester.test_whatsapp_templates_crud),
        ("Payment Gateway Config Addon Requirement", tester.test_configure_payment_gateway_addon_required)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 50)
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if success:
            passed += 1
        else:
            failed += 1
    
    total = len(results)
    print(f"\n📈 RESULTS: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {failed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())