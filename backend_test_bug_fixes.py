"""
Backend API Test for Bug Fixes:
1. Multiple plans create ONE combined invoice (not separate invoices per validity)
2. Updating an invoice reflects changes in subscriber's plan dates
"""
import requests
import json
from datetime import datetime, timedelta

# Backend URL
BACKEND_URL = "https://billing-upgrade-11.preview.emergentagent.com/api"

# Test credentials
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print(f"{'=' * 80}")

def print_subsection(title):
    """Print a formatted subsection header"""
    print(f"\n{'-' * 80}")
    print(f"{title}")
    print(f"{'-' * 80}")

def test_bug_fixes():
    """Test both bug fixes"""
    
    print_section("BUG FIX TESTING - E-BILL PLATFORM")
    
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
    if len(plans) < 2:
        print(f"⚠️  Only {len(plans)} plan(s) found. Need at least 2 plans with different validities.")
        print("Creating additional plans for testing...")
        
        # Create plans with different validities if needed
        test_plans = []
        validities = ["monthly", "yearly"]
        
        for i, validity in enumerate(validities):
            if i < len(plans):
                test_plans.append(plans[i])
            else:
                # Create a new plan
                plan_data = {
                    "name": f"Test Plan {validity.capitalize()}",
                    "description": f"Test plan with {validity} validity",
                    "price": 1000 if validity == "monthly" else 10000,
                    "validity": validity,
                    "status": "active"
                }
                create_response = requests.post(
                    f"{BACKEND_URL}/operator/plans",
                    headers=headers,
                    json=plan_data
                )
                if create_response.status_code in [200, 201]:
                    new_plan = create_response.json()
                    test_plans.append(new_plan)
                    print(f"✅ Created plan: {new_plan['name']} ({validity})")
                else:
                    print(f"❌ Failed to create plan: {create_response.status_code}")
                    return
        
        plans = test_plans
    
    # Select 2 plans with different validities
    plan1 = plans[0]
    plan2 = plans[1] if len(plans) > 1 else plans[0]
    
    print(f"✅ Selected plans:")
    print(f"   Plan 1: {plan1['name']} (ID: {plan1['id']}, Validity: {plan1.get('validity', 'monthly')})")
    print(f"   Plan 2: {plan2['name']} (ID: {plan2['id']}, Validity: {plan2.get('validity', 'monthly')})")
    
    # ========================================================================
    # FIX 1: Multiple plans create ONE combined invoice
    # ========================================================================
    print_section("FIX 1: MULTIPLE PLANS CREATE ONE COMBINED INVOICE")
    
    print("\n3. Creating subscriber with 2 plans and generate_first_invoice=true...")
    
    service_start_date = "2026-05-11"
    
    subscriber_data = {
        "name": "Multi Plan Test User",
        "whatsapp_number": "919999999999",
        "email": "multiplan@test.com",
        "plans": [
            {
                "plan_id": plan1["id"],
                "plan_start_date": service_start_date
            },
            {
                "plan_id": plan2["id"],
                "plan_start_date": service_start_date
            }
        ],
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
    
    # Step 4: Fetch invoices for the subscriber
    print("\n4. Fetching invoices for subscriber...")
    invoices_response = requests.get(
        f"{BACKEND_URL}/operator/invoices",
        headers=headers,
        params={"subscriber_id": subscriber_id}
    )
    
    if invoices_response.status_code != 200:
        print(f"❌ Failed to fetch invoices: {invoices_response.status_code}")
        return
    
    invoices = invoices_response.json()
    
    print_subsection("FIX 1 VALIDATION")
    
    # Validation: Should have exactly 1 invoice
    invoice_count = len(invoices)
    print(f"\nNumber of invoices created: {invoice_count}")
    print(f"Expected: 1 invoice")
    
    if invoice_count == 1:
        print("✅ PASS: Only 1 invoice created (not separate invoices per validity)")
    else:
        print(f"❌ FAIL: {invoice_count} invoices created instead of 1")
    
    if not invoices:
        print("❌ No invoice was generated")
        return
    
    invoice = invoices[0]
    line_items = invoice.get("line_items", [])
    line_item_count = len(line_items)
    
    print(f"\nNumber of line items in invoice: {line_item_count}")
    print(f"Expected: 2 line items (one per plan)")
    
    if line_item_count == 2:
        print("✅ PASS: Invoice has 2 line items (one per plan)")
    else:
        print(f"❌ FAIL: Invoice has {line_item_count} line items instead of 2")
    
    # Display invoice details
    print_subsection("INVOICE DETAILS")
    print(f"Invoice Number: {invoice['invoice_number']}")
    print(f"Subscriber: {invoice['subscriber_name']}")
    print(f"Due Date: {invoice['due_date']}")
    print(f"Final Amount: ₹{invoice['final_amount']:.2f}")
    print(f"Status: {invoice['status']}")
    
    print("\nLine Items:")
    for idx, item in enumerate(line_items, 1):
        print(f"\n  Line Item #{idx}:")
        print(f"    Plan ID: {item.get('plan_id')}")
        print(f"    Plan Name: {item.get('plan_name')}")
        print(f"    Selected Validity: {item.get('selected_validity')}")
        print(f"    Service Start: {item.get('service_start_date')}")
        print(f"    Service End: {item.get('service_end_date')}")
        print(f"    Amount: ₹{item.get('final_amount', 0):.2f}")
    
    # Overall result for Fix 1
    fix1_pass = (invoice_count == 1 and line_item_count == 2)
    
    print_subsection("FIX 1 RESULT")
    if fix1_pass:
        print("✅ FIX 1 PASSED: Multiple plans create ONE combined invoice with multiple line items")
    else:
        print("❌ FIX 1 FAILED")
    
    # ========================================================================
    # FIX 2: Updating invoice reflects changes in subscriber's plan dates
    # ========================================================================
    print_section("FIX 2: UPDATING INVOICE REFLECTS CHANGES IN SUBSCRIBER PLAN DATES")
    
    print("\n5. Getting current subscriber plan dates...")
    subscriber_response = requests.get(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}",
        headers=headers
    )
    
    if subscriber_response.status_code != 200:
        print(f"❌ Failed to fetch subscriber: {subscriber_response.status_code}")
        return
    
    subscriber_data = subscriber_response.json()
    subscriber_plans = subscriber_data.get("plans", [])
    
    print("Current subscriber plans:")
    for sp in subscriber_plans:
        print(f"  Plan: {sp.get('plan_name')}")
        print(f"    Plan ID: {sp.get('plan_id')}")
        print(f"    Start Date: {sp.get('plan_start_date')}")
        print(f"    Expiry Date: {sp.get('plan_expiry_date')}")
    
    # Test 2a: Update invoice with EXTENDED service_end_date
    print("\n6. Updating invoice with EXTENDED service_end_date...")
    
    invoice_id = invoice["id"]
    new_service_end_date = "2026-07-15"  # Extended date
    
    # Build update payload
    update_line_items = []
    for item in line_items:
        update_line_items.append({
            "plan_id": item["plan_id"],
            "is_custom": False,
            "base_amount": item.get("base_amount", 0),
            "discount": item.get("discount", 0),
            "selected_validity": item.get("selected_validity", "monthly"),
            "service_start_date": service_start_date,
            "service_end_date": new_service_end_date  # Changed to extended date
        })
    
    update_payload = {
        "subscriber_id": subscriber_id,
        "due_date": "2026-06-01",
        "line_items": update_line_items
    }
    
    update_response = requests.put(
        f"{BACKEND_URL}/operator/invoices/{invoice_id}",
        headers=headers,
        json=update_payload
    )
    
    if update_response.status_code != 200:
        print(f"❌ Failed to update invoice: {update_response.status_code}")
        print(f"Response: {update_response.text}")
    else:
        print(f"✅ Invoice updated successfully")
    
    # Fetch subscriber again to check updated plan dates
    print("\n7. Fetching subscriber to verify plan_expiry_date changes...")
    subscriber_response = requests.get(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}",
        headers=headers
    )
    
    if subscriber_response.status_code != 200:
        print(f"❌ Failed to fetch subscriber: {subscriber_response.status_code}")
        return
    
    updated_subscriber = subscriber_response.json()
    updated_plans = updated_subscriber.get("plans", [])
    
    print("Updated subscriber plans:")
    for sp in updated_plans:
        print(f"  Plan: {sp.get('plan_name')}")
        print(f"    Plan ID: {sp.get('plan_id')}")
        print(f"    Start Date: {sp.get('plan_start_date')}")
        print(f"    Expiry Date: {sp.get('plan_expiry_date')}")
    
    # Validation: Check if plan_expiry_date matches new service_end_date
    print_subsection("FIX 2 VALIDATION (EXTENDED DATE)")
    
    fix2a_pass = True
    for sp in updated_plans:
        expiry = sp.get("plan_expiry_date")
        if expiry == new_service_end_date:
            print(f"✅ PASS: Plan '{sp.get('plan_name')}' expiry updated to {expiry}")
        else:
            print(f"❌ FAIL: Plan '{sp.get('plan_name')}' expiry is {expiry}, expected {new_service_end_date}")
            fix2a_pass = False
    
    # Test 2b: Update invoice with REDUCED service_end_date
    print("\n8. Updating invoice with REDUCED service_end_date...")
    
    reduced_service_end_date = "2026-05-20"  # Reduced date
    
    # Build update payload with reduced date
    update_line_items = []
    for item in line_items:
        update_line_items.append({
            "plan_id": item["plan_id"],
            "is_custom": False,
            "base_amount": item.get("base_amount", 0),
            "discount": item.get("discount", 0),
            "selected_validity": item.get("selected_validity", "monthly"),
            "service_start_date": service_start_date,
            "service_end_date": reduced_service_end_date  # Changed to reduced date
        })
    
    update_payload = {
        "subscriber_id": subscriber_id,
        "due_date": "2026-05-10",
        "line_items": update_line_items
    }
    
    update_response = requests.put(
        f"{BACKEND_URL}/operator/invoices/{invoice_id}",
        headers=headers,
        json=update_payload
    )
    
    if update_response.status_code != 200:
        print(f"❌ Failed to update invoice: {update_response.status_code}")
        print(f"Response: {update_response.text}")
    else:
        print(f"✅ Invoice updated successfully")
    
    # Fetch subscriber again to check updated plan dates
    print("\n9. Fetching subscriber to verify plan_expiry_date changes (reduced)...")
    subscriber_response = requests.get(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}",
        headers=headers
    )
    
    if subscriber_response.status_code != 200:
        print(f"❌ Failed to fetch subscriber: {subscriber_response.status_code}")
        return
    
    updated_subscriber = subscriber_response.json()
    updated_plans = updated_subscriber.get("plans", [])
    
    print("Updated subscriber plans (after reduction):")
    for sp in updated_plans:
        print(f"  Plan: {sp.get('plan_name')}")
        print(f"    Plan ID: {sp.get('plan_id')}")
        print(f"    Start Date: {sp.get('plan_start_date')}")
        print(f"    Expiry Date: {sp.get('plan_expiry_date')}")
    
    # Validation: Check if plan_expiry_date matches reduced service_end_date
    print_subsection("FIX 2 VALIDATION (REDUCED DATE)")
    
    fix2b_pass = True
    for sp in updated_plans:
        expiry = sp.get("plan_expiry_date")
        if expiry == reduced_service_end_date:
            print(f"✅ PASS: Plan '{sp.get('plan_name')}' expiry reduced to {expiry} (force=True applied)")
        else:
            print(f"❌ FAIL: Plan '{sp.get('plan_name')}' expiry is {expiry}, expected {reduced_service_end_date}")
            fix2b_pass = False
    
    fix2_pass = fix2a_pass and fix2b_pass
    
    print_subsection("FIX 2 RESULT")
    if fix2_pass:
        print("✅ FIX 2 PASSED: Updating invoice reflects changes in subscriber plan dates")
        print("   - Extended dates applied correctly")
        print("   - Reduced dates applied correctly (force=True working)")
    else:
        print("❌ FIX 2 FAILED")
        if not fix2a_pass:
            print("   - Extended date test failed")
        if not fix2b_pass:
            print("   - Reduced date test failed (force=True not working)")
    
    # Cleanup
    print("\n10. Cleaning up test data...")
    delete_response = requests.delete(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}",
        headers=headers
    )
    
    if delete_response.status_code == 200:
        print(f"✅ Test subscriber deleted")
    else:
        print(f"⚠️  Failed to delete subscriber: {delete_response.status_code}")
        print(f"   Subscriber ID: {subscriber_id} (manual cleanup may be required)")
    
    # ========================================================================
    # OVERALL SUMMARY
    # ========================================================================
    print_section("OVERALL TEST SUMMARY")
    
    print("\n✓ Fix 1: Multiple plans create ONE combined invoice")
    print(f"  Status: {'✅ PASSED' if fix1_pass else '❌ FAILED'}")
    print(f"  - Invoice count: {invoice_count} (expected: 1)")
    print(f"  - Line items: {line_item_count} (expected: 2)")
    
    print("\n✓ Fix 2: Updating invoice reflects changes in subscriber plan dates")
    print(f"  Status: {'✅ PASSED' if fix2_pass else '❌ FAILED'}")
    print(f"  - Extended date test: {'✅ PASSED' if fix2a_pass else '❌ FAILED'}")
    print(f"  - Reduced date test: {'✅ PASSED' if fix2b_pass else '❌ FAILED'}")
    
    if fix1_pass and fix2_pass:
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED - Both bug fixes verified successfully!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ SOME TESTS FAILED - Review the results above")
        print("=" * 80)
    
    print(f"\n")

if __name__ == "__main__":
    try:
        test_bug_fixes()
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
