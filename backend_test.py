"""
Backend API Test for Auto-Invoice Bug Fixes
Tests:
1. Auto-generated invoices include plan_description in line items
2. Auto-generated invoice due date = 1 day BEFORE service start date
"""
import requests
import json
from datetime import datetime, timedelta

# Backend URL
BACKEND_URL = "https://whatsapp-stats-view.preview.emergentagent.com/api"

# Test credentials
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print(f"{'=' * 80}")

def test_auto_invoice_fixes():
    """Test both auto-invoice bug fixes via API"""
    
    print_section("AUTO-INVOICE BUG FIX TESTING")
    
    # Step 1: Login as operator
    print("\n1. Logging in as operator...")
    login_response = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful")
    
    # Step 2: Get list of plans
    print("\n2. Fetching operator plans...")
    plans_response = requests.get(f"{BACKEND_URL}/operator/plans", headers=headers)
    
    if plans_response.status_code != 200:
        print(f"❌ Failed to fetch plans: {plans_response.status_code}")
        return
    
    plans = plans_response.json()
    if not plans:
        print("❌ No plans found")
        return
    
    plan = plans[0]
    plan_id = plan["id"]
    plan_name = plan["name"]
    plan_description = plan.get("description", "")
    
    print(f"✅ Found plan: {plan_name} (ID: {plan_id})")
    print(f"   Current description: {repr(plan_description)}")
    
    # Step 3: Add description to plan if missing
    if not plan_description:
        print("\n3. Adding description to plan...")
        test_description = "High-speed fiber broadband plan with unlimited data and 24/7 support"
        update_response = requests.patch(
            f"{BACKEND_URL}/operator/plans/{plan_id}",
            headers=headers,
            json={"description": test_description}
        )
        
        if update_response.status_code == 200:
            plan_description = test_description
            print(f"✅ Description added: {test_description}")
        else:
            print(f"⚠️  Failed to add description: {update_response.status_code}")
    else:
        print(f"\n3. Plan already has description: {plan_description}")
    
    # Step 4: Create subscriber with generate_first_invoice=true
    print("\n4. Creating subscriber with auto-invoice generation...")
    
    # Use a future date for service start
    service_start_date = "2026-05-15"
    
    subscriber_data = {
        "name": "Test Auto Invoice User",
        "whatsapp_number": "919876543210",
        "email": "testautoinv@example.com",
        "plans": [{
            "plan_id": plan_id,
            "plan_start_date": service_start_date
        }],
        "generate_first_invoice": True
    }
    
    create_response = requests.post(
        f"{BACKEND_URL}/operator/subscribers",
        headers=headers,
        json=subscriber_data
    )
    
    if create_response.status_code not in [200, 201]:
        print(f"❌ Failed to create subscriber: {create_response.status_code}")
        print(f"Response: {create_response.text}")
        return
    
    subscriber = create_response.json()
    subscriber_id = subscriber["id"]
    print(f"✅ Subscriber created: {subscriber['name']} (ID: {subscriber_id})")
    
    # Step 5: Fetch invoices for the subscriber
    print("\n5. Fetching invoices for subscriber...")
    invoices_response = requests.get(
        f"{BACKEND_URL}/operator/invoices",
        headers=headers,
        params={"subscriber_id": subscriber_id}
    )
    
    if invoices_response.status_code != 200:
        print(f"❌ Failed to fetch invoices: {invoices_response.status_code}")
        return
    
    invoices = invoices_response.json()
    
    if not invoices:
        print("❌ No invoice was generated")
        return
    
    invoice = invoices[0]
    print(f"✅ Invoice found: {invoice['invoice_number']}")
    
    # Display invoice details
    print_section("INVOICE DETAILS")
    print(f"Invoice Number: {invoice['invoice_number']}")
    print(f"Subscriber: {invoice['subscriber_name']}")
    print(f"Due Date: {invoice['due_date']}")
    print(f"Final Amount: ₹{invoice['final_amount']:.2f}")
    print(f"Status: {invoice['status']}")
    
    # Display line items
    print_section("LINE ITEMS")
    for idx, item in enumerate(invoice.get("line_items", []), 1):
        print(f"\nLine Item #{idx}:")
        print(f"  Plan Name: {item.get('plan_name')}")
        print(f"  Plan Description: {repr(item.get('plan_description'))}")
        print(f"  Is Custom: {item.get('is_custom')}")
        print(f"  Selected Validity: {item.get('selected_validity')}")
        print(f"  Service Start Date: {item.get('service_start_date')}")
        print(f"  Service End Date: {item.get('service_end_date')}")
        print(f"  Base Amount: ₹{item.get('base_amount', 0):.2f}")
        print(f"  Final Amount: ₹{item.get('final_amount', 0):.2f}")
    
    # Validation
    print_section("VALIDATION RESULTS")
    
    if not invoice.get("line_items"):
        print("❌ No line items found in invoice")
        return
    
    item = invoice["line_items"][0]
    
    # Fix 1: plan_description present
    plan_desc = item.get('plan_description')
    fix1_pass = plan_desc is not None and plan_desc != ""
    
    print("\n✓ FIX 1: plan_description in line items")
    print(f"  Expected: Present (not None/empty)")
    print(f"  Actual: {repr(plan_desc)}")
    print(f"  Status: {'✅ PASS' if fix1_pass else '❌ FAIL'}")
    
    # Fix 2: due_date = service_start - 1 day
    service_start_str = item.get("service_start_date", "")
    due_date_str = invoice.get("due_date", "")
    
    if service_start_str and due_date_str:
        # Parse dates
        service_start = datetime.fromisoformat(service_start_str.replace('Z', '+00:00'))
        actual_due = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
        expected_due = service_start - timedelta(days=1)
        
        # Calculate difference
        date_diff = abs((actual_due.date() - expected_due.date()).days)
        fix2_pass = date_diff == 0
        
        print(f"\n✓ FIX 2: due_date = service_start - 1 day")
        print(f"  Service Start: {service_start.strftime('%Y-%m-%d')}")
        print(f"  Expected Due (start - 1): {expected_due.strftime('%Y-%m-%d')}")
        print(f"  Actual Due: {actual_due.strftime('%Y-%m-%d')}")
        print(f"  Date Difference: {date_diff} days")
        print(f"  Status: {'✅ PASS' if fix2_pass else '❌ FAIL'}")
    else:
        fix2_pass = False
        print(f"\n✓ FIX 2: due_date calculation")
        print(f"  Status: ❌ FAIL - Missing date fields")
    
    # Overall result
    print_section("OVERALL TEST RESULT")
    
    if fix1_pass and fix2_pass:
        print("✅ ALL TESTS PASSED - Both bug fixes verified successfully!")
        print("\nSummary:")
        print("  ✅ Fix 1: plan_description is present in line items")
        print("  ✅ Fix 2: due_date is correctly set to 1 day before service start")
    else:
        print("❌ SOME TESTS FAILED")
        if not fix1_pass:
            print("  ❌ Fix 1 (plan_description) FAILED")
        if not fix2_pass:
            print("  ❌ Fix 2 (due_date calculation) FAILED")
    
    # Cleanup
    print("\n6. Cleaning up test data...")
    delete_response = requests.delete(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}",
        headers=headers
    )
    
    if delete_response.status_code == 200:
        print(f"✅ Test subscriber deleted")
    else:
        print(f"⚠️  Failed to delete subscriber: {delete_response.status_code}")
    
    print(f"\n{'=' * 80}\n")

if __name__ == "__main__":
    try:
        test_auto_invoice_fixes()
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
