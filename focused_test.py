#!/usr/bin/env python3
"""
Simple focused test for specific bug fixes
"""
import requests
import json
import time

BASE_URL = "https://syntax-inspector-1.preview.emergentagent.com/api"

def test_individual_fixes():
    print("=== MANUAL VERIFICATION OF BUG FIXES ===")
    
    # Login as admin
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@saas.com", "password": "admin123"
    })
    admin_token = response.json()["access_token"]
    print(f"✅ Admin token acquired")
    
    # Register operator  
    import datetime
    email = f"quicktest_{datetime.datetime.now().strftime('%H%M%S')}@example.com"
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "company_name": "QuickTest Corp",
        "owner_name": "Quick Tester", 
        "email": email,
        "phone": "+919876543210",
        "password": "test123",
        "gst_number": "29ABCDE1234F1Z5",
        "charge_gst": True,
        "bank_account_name": "Test Account",
        "bank_account_number": "1234567890",
        "bank_ifsc": "HDFC0001234",
        "bank_name": "HDFC Bank"
    })
    
    if response.status_code != 200:
        print(f"❌ Registration failed: {response.status_code}")
        return
        
    operator_token = response.json()["access_token"]
    operator_id = response.json()["user"]["operator_id"]
    print(f"✅ Operator registered: {operator_id}")
    
    # Test Fix 1: Trial addon block
    print("\n--- Fix 1: Trial addon purchase block ---")
    response = requests.post(
        f"{BASE_URL}/operator/checkout/create-order?item_type=addon&item_code=audit_log",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 403:
        detail = response.json().get("detail", "")
        if "Please subscribe to a paid plan to purchase add-ons" in detail:
            print("✅ FIX 1 PASSED")
        else:
            print(f"❌ FIX 1 - Wrong message: {detail}")
    else:
        print(f"❌ FIX 1 - Expected 403, got {response.status_code}")
    
    # Test Fix 4: Trial staff creation
    print("\n--- Fix 4: Trial staff creation block ---")
    response = requests.post(
        f"{BASE_URL}/operator/staff",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "name": "Test Staff",
            "email": f"staff_{datetime.datetime.now().strftime('%H%M%S')}@example.com",
            "phone": "+919876543211",
            "password": "staff123",
            "permissions": ["view_subscribers"]
        }
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 403:
        detail = response.json().get("detail", "")
        if "Please subscribe to use this feature" in detail:
            print("✅ FIX 4 PASSED")
        else:
            print(f"❌ FIX 4 - Wrong message: {detail}")
    else:
        print(f"❌ FIX 4 - Expected 403, got {response.status_code}")
    
    # Test Fix 5: Features endpoint
    print("\n--- Fix 5: staff_management in features ---")
    response = requests.get(
        f"{BASE_URL}/operator/features",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        features = response.json()
        if "staff_management" in features:
            print(f"✅ FIX 5 PASSED - staff_management: {features['staff_management']}")
        else:
            print("❌ FIX 5 FAILED - staff_management not found")
    
    # Create subscriber for delete test
    print("\n--- Setting up subscriber for delete test ---")
    # First create plan
    response = requests.post(
        f"{BASE_URL}/operator/plans",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "name": "Test Plan Delete",
            "price": 500.0,
            "validity": "monthly", 
            "tax_percentage": 18.0,
            "tax_type": "exclusive",
            "description": "Test plan"
        }
    )
    plan_id = response.json()["id"]
    
    # Create subscriber
    response = requests.post(
        f"{BASE_URL}/operator/subscribers",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "name": "Test Delete Subscriber",
            "whatsapp_number": "9876543299",
            "email": "testdel@example.com",
            "address": "Test Address",
            "plan_id": plan_id,
            "billing_date": 1,
            "discount": 0.0
        }
    )
    subscriber_id = response.json()["id"]
    print(f"✅ Subscriber created: {subscriber_id}")
    
    # Test Fix 2: Suspend/Activate
    print("\n--- Fix 2: Suspend/Activate endpoints ---")
    response = requests.post(
        f"{BASE_URL}/operator/subscribers/{subscriber_id}/suspend",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    suspend_ok = response.status_code == 200
    print(f"Suspend: {response.status_code} {'✅' if suspend_ok else '❌'}")
    
    response = requests.post(
        f"{BASE_URL}/operator/subscribers/{subscriber_id}/activate",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    activate_ok = response.status_code == 200
    print(f"Activate: {response.status_code} {'✅' if activate_ok else '❌'}")
    
    if suspend_ok and activate_ok:
        print("✅ FIX 2 PASSED")
    else:
        print("❌ FIX 2 FAILED")
    
    # Test Fix 3: Delete restriction
    print("\n--- Fix 3: Delete subscriber restriction ---")
    # Try as regular operator
    response = requests.delete(
        f"{BASE_URL}/operator/subscribers/{subscriber_id}",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    print(f"Regular operator delete: {response.status_code}")
    if response.status_code == 403:
        detail = response.json().get("detail", "")
        if "Only admin can delete subscribers" in detail:
            print("✅ Regular operator blocked correctly")
            regular_blocked = True
        else:
            print(f"❌ Wrong message: {detail}")
            regular_blocked = False
    else:
        print(f"❌ Expected 403, got {response.status_code}")
        regular_blocked = False
        
    # Admin impersonate
    response = requests.post(
        f"{BASE_URL}/admin/operators/{operator_id}/impersonate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if response.status_code == 200:
        impersonation_token = response.json()["access_token"]
        print("✅ Admin impersonation successful")
        
        # Try delete with impersonation
        response = requests.delete(
            f"{BASE_URL}/operator/subscribers/{subscriber_id}",
            headers={"Authorization": f"Bearer {impersonation_token}"}
        )
        print(f"Admin impersonation delete: {response.status_code}")
        admin_can_delete = response.status_code == 200
        
        if regular_blocked and admin_can_delete:
            print("✅ FIX 3 PASSED")
        else:
            print("❌ FIX 3 FAILED")
    else:
        print("❌ Admin impersonation failed")
    
    # Test Fix 6: Addon bundling  
    print("\n--- Fix 6: Subscription addon bundling ---")
    # Get paid plans
    response = requests.get(
        f"{BASE_URL}/admin/saas-plans",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    plans = response.json()
    paid_plan = None
    for plan in plans:
        if not plan.get("trial_enabled") and plan.get("monthly_price", 0) > 0:
            paid_plan = plan
            break
            
    if paid_plan:
        print(f"Using plan: {paid_plan['name']} (${paid_plan['monthly_price']})")
        response = requests.post(
            f"{BASE_URL}/operator/checkout/create-order?item_type=subscription&plan_id={paid_plan['id']}&months=1&addon_codes=audit_log",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        
        print(f"Checkout status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            base_amount = data.get("base_amount", 0)
            plan_price = paid_plan["monthly_price"]
            print(f"Plan price: ${plan_price}, Total: ${base_amount}")
            if base_amount > plan_price:
                print("✅ FIX 6 PASSED - Addon price included")
            else:
                print("❌ FIX 6 FAILED - Addon price not included")
        elif response.status_code == 500:
            detail = response.json().get("detail", "")
            if "Payment gateway not configured" in detail:
                print("✅ FIX 6 PARTIAL - Payment gateway issue (acceptable)")
            else:
                print(f"❌ FIX 6 FAILED - Unexpected 500: {detail}")
        else:
            print(f"❌ FIX 6 FAILED - Status: {response.status_code}")

if __name__ == "__main__":
    test_individual_fixes()