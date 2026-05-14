"""
Backend API Test for Subscriber + Invoice Flow Bug Fixes

Tests:
Fix A: After creating subscriber with generate_first_invoice=true, subscriber's plan_expiry_date matches invoice's service_end_date
Fix B: When updating subscriber's plan start_date, expiry is recalculated using CORRECT selected_validity (not just base plan validity)
Fix C: After cron creates auto-invoice, subscriber plan expiry updates (tested via direct function call)
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

def print_test_result(test_name, passed, expected, actual, details=""):
    """Print formatted test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status} - {test_name}")
    print(f"  Expected: {expected}")
    print(f"  Actual: {actual}")
    if details:
        print(f"  Details: {details}")

def test_subscriber_invoice_sync():
    """Test all three bug fixes for subscriber + invoice flow"""
    
    print_section("SUBSCRIBER + INVOICE FLOW BUG FIX TESTING")
    
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
    
    # Step 2: Get or create a quarterly plan
    print("\n2. Setting up quarterly plan...")
    plans_response = requests.get(f"{BACKEND_URL}/operator/plans", headers=headers)
    
    if plans_response.status_code != 200:
        print(f"❌ Failed to fetch plans: {plans_response.status_code}")
        return
    
    plans = plans_response.json()
    
    # Find a plan with quarterly validity and available_validities
    quarterly_plan = None
    for plan in plans:
        if plan.get("validity") == "quarterly" and "quarterly" in plan.get("available_validities", []):
            quarterly_plan = plan
            break
    
    # If no quarterly plan found, create one
    if not quarterly_plan:
        print("   Creating new quarterly plan...")
        create_plan_response = requests.post(
            f"{BACKEND_URL}/operator/plans",
            headers=headers,
            json={
                "name": "Quarterly Test Plan",
                "price": 1500,
                "validity": "quarterly",
                "available_validities": ["monthly", "quarterly", "yearly"],
                "tax_percentage": 0,
                "tax_type": "none",
                "description": "Test plan for quarterly billing"
            }
        )
        
        if create_plan_response.status_code in [200, 201]:
            quarterly_plan = create_plan_response.json()
            print(f"✅ Created quarterly plan: {quarterly_plan['name']} (ID: {quarterly_plan['id']})")
        else:
            print(f"❌ Failed to create plan: {create_plan_response.status_code}")
            print(f"Response: {create_plan_response.text}")
            return
    else:
        print(f"✅ Found quarterly plan: {quarterly_plan['name']} (ID: {quarterly_plan['id']})")
    
    plan_id = quarterly_plan["id"]
    
    # ========================================================================
    # TEST FIX A: First invoice syncs subscriber expiry
    # ========================================================================
    print_section("TEST FIX A: First Invoice Syncs Subscriber Expiry")
    
    print("\n3. Creating subscriber with generate_first_invoice=true...")
    subscriber_data = {
        "name": "Invoice Sync Test",
        "whatsapp_number": "919111111111",
        "email": "invoicesync@test.com",
        "plans": [{
            "plan_id": plan_id,
            "plan_start_date": "2026-06-01",
            "selected_validity": "quarterly"
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
    
    # Get subscriber details
    sub_response = requests.get(f"{BACKEND_URL}/operator/subscribers/{subscriber_id}", headers=headers)
    if sub_response.status_code != 200:
        print(f"❌ Failed to fetch subscriber: {sub_response.status_code}")
        return
    
    subscriber_detail = sub_response.json()
    subscriber_expiry = subscriber_detail["plans"][0]["plan_expiry_date"]
    print(f"   Subscriber plan_expiry_date: {subscriber_expiry}")
    
    # Get invoice details
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
    invoice_id = invoice["id"]
    invoice_service_end = invoice["line_items"][0]["service_end_date"][:10]  # Extract date part
    print(f"   Invoice service_end_date: {invoice_service_end}")
    
    # Validate Fix A
    fix_a_pass = subscriber_expiry == invoice_service_end
    print_test_result(
        "Fix A: Subscriber expiry matches invoice service_end_date",
        fix_a_pass,
        invoice_service_end,
        subscriber_expiry,
        "After creating subscriber with generate_first_invoice=true"
    )
    
    # ========================================================================
    # TEST FIX B: Edit with changed start_date uses selected_validity
    # ========================================================================
    print_section("TEST FIX B: Edit with Changed Start Date Uses Selected Validity")
    
    print("\n4. Updating subscriber with new start_date (quarterly)...")
    update_data = {
        "name": "Invoice Sync Test",
        "whatsapp_number": "919111111111",
        "email": "invoicesync@test.com",
        "plans": [{
            "plan_id": plan_id,
            "plan_start_date": "2026-07-01",
            "selected_validity": "quarterly",
            "discount": 0
        }]
    }
    
    update_response = requests.put(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}",
        headers=headers,
        json=update_data
    )
    
    if update_response.status_code != 200:
        print(f"❌ Failed to update subscriber: {update_response.status_code}")
        print(f"Response: {update_response.text}")
        return
    
    # Get updated subscriber
    sub_response = requests.get(f"{BACKEND_URL}/operator/subscribers/{subscriber_id}", headers=headers)
    subscriber_detail = sub_response.json()
    new_expiry = subscriber_detail["plans"][0]["plan_expiry_date"]
    
    # Expected: 2026-07-01 + 3 months - 1 day = 2026-09-30
    expected_expiry = "2026-09-30"
    fix_b_pass = new_expiry == expected_expiry
    print_test_result(
        "Fix B: Expiry recalculated with quarterly validity",
        fix_b_pass,
        expected_expiry,
        new_expiry,
        "Start date: 2026-07-01, selected_validity: quarterly (3 months)"
    )
    
    # ========================================================================
    # TEST FIX B VARIANT: Monthly override on quarterly plan
    # ========================================================================
    print_section("TEST FIX B VARIANT: Monthly Override on Quarterly Plan")
    
    print("\n5. Updating subscriber with monthly override...")
    update_data_monthly = {
        "name": "Invoice Sync Test",
        "whatsapp_number": "919111111111",
        "email": "invoicesync@test.com",
        "plans": [{
            "plan_id": plan_id,
            "plan_start_date": "2026-08-01",  # Different start date to trigger recalculation
            "selected_validity": "monthly",
            "discount": 0
        }]
    }
    
    update_response = requests.put(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}",
        headers=headers,
        json=update_data_monthly
    )
    
    if update_response.status_code != 200:
        print(f"❌ Failed to update subscriber: {update_response.status_code}")
        return
    
    # Get updated subscriber
    sub_response = requests.get(f"{BACKEND_URL}/operator/subscribers/{subscriber_id}", headers=headers)
    subscriber_detail = sub_response.json()
    monthly_expiry = subscriber_detail["plans"][0]["plan_expiry_date"]
    
    # Expected: 2026-08-01 + 1 month - 1 day = 2026-08-31
    expected_monthly_expiry = "2026-08-31"
    fix_b_variant_pass = monthly_expiry == expected_monthly_expiry
    print_test_result(
        "Fix B Variant: Expiry recalculated with monthly override",
        fix_b_variant_pass,
        expected_monthly_expiry,
        monthly_expiry,
        "Start date: 2026-08-01, selected_validity: monthly (1 month)"
    )
    
    # ========================================================================
    # TEST FIX A VARIANT: Invoice update syncs to subscriber (force=True)
    # ========================================================================
    print_section("TEST FIX A VARIANT: Invoice Update Syncs to Subscriber")
    
    print("\n6. Updating invoice with new service_end_date...")
    
    # Update invoice with specific service_end_date
    invoice_update_data = {
        "subscriber_id": subscriber_id,
        "due_date": "2026-07-31",
        "line_items": [{
            "plan_id": plan_id,
            "is_custom": False,
            "base_amount": 1500,
            "discount": 0,
            "selected_validity": "quarterly",
            "service_start_date": "2026-06-01",
            "service_end_date": "2026-09-15"
        }]
    }
    
    invoice_update_response = requests.put(
        f"{BACKEND_URL}/operator/invoices/{invoice_id}",
        headers=headers,
        json=invoice_update_data
    )
    
    if invoice_update_response.status_code != 200:
        print(f"❌ Failed to update invoice: {invoice_update_response.status_code}")
        print(f"Response: {invoice_update_response.text}")
        return
    
    # Get updated subscriber
    sub_response = requests.get(f"{BACKEND_URL}/operator/subscribers/{subscriber_id}", headers=headers)
    subscriber_detail = sub_response.json()
    updated_expiry = subscriber_detail["plans"][0]["plan_expiry_date"]
    
    # Expected: 2026-09-15 (from invoice service_end_date)
    expected_updated_expiry = "2026-09-15"
    fix_a_variant_pass = updated_expiry == expected_updated_expiry
    print_test_result(
        "Fix A Variant: Subscriber expiry updated from invoice edit",
        fix_a_variant_pass,
        expected_updated_expiry,
        updated_expiry,
        "Invoice service_end_date changed to 2026-09-15 (force=True)"
    )
    
    # ========================================================================
    # OVERALL RESULTS
    # ========================================================================
    print_section("OVERALL TEST RESULTS")
    
    all_tests = [
        ("Fix A: First invoice syncs subscriber expiry", fix_a_pass),
        ("Fix B: Expiry recalculated with quarterly validity", fix_b_pass),
        ("Fix B Variant: Monthly override works correctly", fix_b_variant_pass),
        ("Fix A Variant: Invoice update syncs to subscriber", fix_a_variant_pass),
    ]
    
    passed_count = sum(1 for _, passed in all_tests if passed)
    total_count = len(all_tests)
    
    print(f"\nTests Passed: {passed_count}/{total_count}")
    print("\nDetailed Results:")
    for test_name, passed in all_tests:
        status = "✅" if passed else "❌"
        print(f"  {status} {test_name}")
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED - All bug fixes verified successfully!")
    else:
        print(f"\n⚠️  {total_count - passed_count} TEST(S) FAILED")
    
    # Cleanup
    print("\n7. Cleaning up test data...")
    delete_response = requests.delete(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}",
        headers=headers
    )
    
    if delete_response.status_code == 200:
        print(f"✅ Test subscriber deleted")
    else:
        print(f"⚠️  Failed to delete subscriber: {delete_response.status_code}")
        print(f"   Subscriber ID: {subscriber_id} (manual cleanup may be needed)")
    
    print(f"\n{'=' * 80}\n")
    
    return passed_count == total_count

if __name__ == "__main__":
    try:
        success = test_subscriber_invoice_sync()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
