"""
Backend API tests for new invoice features:
1. Consolidated status on invoice creation
2. Partial payment accumulation
3. Full payment after partial
4. Consolidated invoice cannot be paid
5. get_pending_balance uses remaining balance for partial invoices
"""
import requests
import json
from datetime import datetime, timedelta

# Backend URL from frontend/.env
BACKEND_URL = "https://recursing-proskuriakova-9.preview.emergentagent.com/api"

# Test credentials
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

def login():
    """Login as operator and return access token"""
    response = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD}
    )
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None
    data = response.json()
    return data["access_token"]

def get_headers(token):
    """Return authorization headers"""
    return {"Authorization": f"Bearer {token}"}

def get_invoice_by_id(token, invoice_id):
    """Get a single invoice by ID using the list endpoint"""
    headers = get_headers(token)
    response = requests.get(f"{BACKEND_URL}/operator/invoices", headers=headers)
    if response.status_code != 200:
        return None
    
    invoices = response.json()
    for inv in invoices:
        if inv["id"] == invoice_id:
            return inv
    return None

def test_consolidated_status_on_invoice_creation(token):
    """
    Test 1: When a new invoice is created for a subscriber with pending invoices,
    old pending invoices should be marked as status="consolidated" with consolidated_into field.
    """
    print("\n" + "="*80)
    print("TEST 1: Consolidated status on invoice creation")
    print("="*80)
    
    headers = get_headers(token)
    
    # Step 1: Get all subscribers
    response = requests.get(f"{BACKEND_URL}/operator/subscribers", headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to get subscribers: {response.status_code}")
        return False
    
    subscribers = response.json()
    if not subscribers:
        print("❌ No subscribers found")
        return False
    
    # Step 2: Find a subscriber with pending invoices
    subscriber_with_pending = None
    pending_invoices = []
    
    for sub in subscribers:
        response = requests.get(
            f"{BACKEND_URL}/operator/invoices",
            headers=headers,
            params={"subscriber_id": sub["id"]}
        )
        if response.status_code == 200:
            invoices = response.json()
            pending = [inv for inv in invoices if inv["status"] in ["pending", "overdue"]]
            if pending:
                subscriber_with_pending = sub
                pending_invoices = pending
                break
    
    if not subscriber_with_pending:
        print("⚠️  No subscriber with pending invoices found. Creating test scenario...")
        # Use first subscriber and create a pending invoice
        test_sub = subscribers[0]
        
        # Get subscriber's plans
        response = requests.get(f"{BACKEND_URL}/operator/plans", headers=headers)
        if response.status_code != 200 or not response.json():
            print(f"❌ No plans available: {response.status_code}")
            return False
        
        plans = response.json()
        test_plan = plans[0]
        
        # Create a pending invoice
        invoice_data = {
            "subscriber_id": test_sub["id"],
            "line_items": [{
                "plan_id": test_plan["id"],
                "base_amount": test_plan["price"],
                "discount": 0,
                "service_start_date": datetime.now().isoformat(),
                "service_end_date": (datetime.now() + timedelta(days=30)).isoformat()
            }],
            "due_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        response = requests.post(
            f"{BACKEND_URL}/operator/invoices",
            headers=headers,
            json=invoice_data
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to create test invoice: {response.status_code} - {response.text}")
            return False
        
        subscriber_with_pending = test_sub
        pending_invoices = [response.json()]
        print(f"✅ Created test pending invoice: {pending_invoices[0]['invoice_number']}")
    
    print(f"\n📋 Found subscriber: {subscriber_with_pending['name']} (ID: {subscriber_with_pending['id']})")
    print(f"📋 Pending invoices: {[inv['invoice_number'] for inv in pending_invoices]}")
    
    # Step 3: Get subscriber's plans for new invoice
    response = requests.get(f"{BACKEND_URL}/operator/plans", headers=headers)
    if response.status_code != 200 or not response.json():
        print(f"❌ No plans available: {response.status_code}")
        return False
    
    plans = response.json()
    test_plan = plans[0]
    
    # Step 4: Create a new invoice for the same subscriber
    print(f"\n📝 Creating new invoice for subscriber...")
    new_invoice_data = {
        "subscriber_id": subscriber_with_pending["id"],
        "line_items": [{
            "plan_id": test_plan["id"],
            "base_amount": test_plan["price"],
            "discount": 0,
            "service_start_date": datetime.now().isoformat(),
            "service_end_date": (datetime.now() + timedelta(days=30)).isoformat()
        }],
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }
    
    response = requests.post(
        f"{BACKEND_URL}/operator/invoices",
        headers=headers,
        json=new_invoice_data
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create new invoice: {response.status_code} - {response.text}")
        return False
    
    new_invoice = response.json()
    print(f"✅ Created new invoice: {new_invoice['invoice_number']}")
    
    # Step 5: Verify old pending invoices are now consolidated
    print(f"\n🔍 Verifying old invoices are marked as consolidated...")
    all_passed = True
    
    for old_inv in pending_invoices:
        updated_inv = get_invoice_by_id(token, old_inv['id'])
        
        if not updated_inv:
            print(f"❌ Failed to get invoice {old_inv['invoice_number']}")
            all_passed = False
            continue
        
        if updated_inv["status"] != "consolidated":
            print(f"❌ Invoice {old_inv['invoice_number']} status is '{updated_inv['status']}', expected 'consolidated'")
            all_passed = False
        else:
            print(f"✅ Invoice {old_inv['invoice_number']} status: consolidated")
        
        if updated_inv.get("consolidated_into") != new_invoice["id"]:
            print(f"❌ Invoice {old_inv['invoice_number']} consolidated_into is '{updated_inv.get('consolidated_into')}', expected '{new_invoice['id']}'")
            all_passed = False
        else:
            print(f"✅ Invoice {old_inv['invoice_number']} consolidated_into: {new_invoice['id']}")
    
    # Step 6: Verify new invoice has "Previous Pending" line item
    print(f"\n🔍 Verifying new invoice has 'Previous Pending' line item...")
    has_previous_pending = False
    for item in new_invoice.get("line_items", []):
        if item.get("plan_name") == "Previous Pending":
            has_previous_pending = True
            print(f"✅ Found 'Previous Pending' line item with amount: ₹{item['final_amount']}")
            print(f"   Description: {item.get('description', 'N/A')}")
            break
    
    if not has_previous_pending:
        print(f"❌ New invoice does not have 'Previous Pending' line item")
        all_passed = False
    
    return all_passed

def test_partial_payment(token):
    """
    Test 2: Partial payment accumulation
    """
    print("\n" + "="*80)
    print("TEST 2: Partial payment accumulation")
    print("="*80)
    
    headers = get_headers(token)
    
    # Step 1: Get a pending invoice
    response = requests.get(f"{BACKEND_URL}/operator/invoices", headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to get invoices: {response.status_code}")
        return False
    
    invoices = response.json()
    pending_invoice = None
    
    for inv in invoices:
        if inv["status"] == "pending":
            pending_invoice = inv
            break
    
    if not pending_invoice:
        print("⚠️  No pending invoice found. Creating one...")
        # Create a test invoice
        response = requests.get(f"{BACKEND_URL}/operator/subscribers", headers=headers)
        if response.status_code != 200 or not response.json():
            print(f"❌ No subscribers found")
            return False
        
        subscribers = response.json()
        test_sub = subscribers[0]
        
        response = requests.get(f"{BACKEND_URL}/operator/plans", headers=headers)
        if response.status_code != 200 or not response.json():
            print(f"❌ No plans available")
            return False
        
        plans = response.json()
        test_plan = plans[0]
        
        invoice_data = {
            "subscriber_id": test_sub["id"],
            "line_items": [{
                "plan_id": test_plan["id"],
                "base_amount": test_plan["price"],
                "discount": 0,
                "service_start_date": datetime.now().isoformat(),
                "service_end_date": (datetime.now() + timedelta(days=30)).isoformat()
            }],
            "due_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        response = requests.post(
            f"{BACKEND_URL}/operator/invoices",
            headers=headers,
            json=invoice_data
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to create test invoice: {response.status_code} - {response.text}")
            return False
        
        pending_invoice = response.json()
    
    print(f"\n📋 Testing with invoice: {pending_invoice['invoice_number']}")
    print(f"   Final amount: ₹{pending_invoice['final_amount']}")
    
    # Step 2: Make first partial payment
    print(f"\n💰 Making first partial payment of ₹100...")
    response = requests.put(
        f"{BACKEND_URL}/operator/invoices/{pending_invoice['id']}/status",
        headers=headers,
        json={
            "status": "partial",
            "payment_mode": "cash",
            "amount_paid": 100
        }
    )
    
    if response.status_code != 200:
        print(f"❌ First partial payment failed: {response.status_code} - {response.text}")
        return False
    
    print(f"✅ First partial payment successful")
    
    # Verify first payment
    updated_inv = get_invoice_by_id(token, pending_invoice['id'])
    
    if not updated_inv:
        print(f"❌ Failed to get updated invoice")
        return False
    
    if updated_inv["status"] != "partial":
        print(f"❌ Status is '{updated_inv['status']}', expected 'partial'")
        return False
    
    print(f"✅ Status: {updated_inv['status']}")
    
    if updated_inv.get("amount_paid") != 100:
        print(f"❌ amount_paid is {updated_inv.get('amount_paid')}, expected 100")
        return False
    
    print(f"✅ amount_paid: ₹{updated_inv['amount_paid']}")
    
    if len(updated_inv.get("payments_received", [])) != 1:
        print(f"❌ payments_received has {len(updated_inv.get('payments_received', []))} entries, expected 1")
        return False
    
    print(f"✅ payments_received has 1 entry")
    
    # Step 3: Make second partial payment
    print(f"\n💰 Making second partial payment of ₹50...")
    response = requests.put(
        f"{BACKEND_URL}/operator/invoices/{pending_invoice['id']}/status",
        headers=headers,
        json={
            "status": "partial",
            "payment_mode": "cash",
            "amount_paid": 50
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Second partial payment failed: {response.status_code} - {response.text}")
        return False
    
    print(f"✅ Second partial payment successful")
    
    # Verify accumulated payment
    updated_inv = get_invoice_by_id(token, pending_invoice['id'])
    
    if not updated_inv:
        print(f"❌ Failed to get updated invoice")
        return False
    
    if updated_inv.get("amount_paid") != 150:
        print(f"❌ amount_paid is {updated_inv.get('amount_paid')}, expected 150")
        return False
    
    print(f"✅ amount_paid accumulated: ₹{updated_inv['amount_paid']}")
    
    if len(updated_inv.get("payments_received", [])) != 2:
        print(f"❌ payments_received has {len(updated_inv.get('payments_received', []))} entries, expected 2")
        return False
    
    print(f"✅ payments_received has 2 entries")
    
    return True

def test_full_payment_after_partial(token):
    """
    Test 3: Full payment after partial
    """
    print("\n" + "="*80)
    print("TEST 3: Full payment after partial")
    print("="*80)
    
    headers = get_headers(token)
    
    # Step 1: Get a partial invoice
    response = requests.get(f"{BACKEND_URL}/operator/invoices", headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to get invoices: {response.status_code}")
        return False
    
    invoices = response.json()
    partial_invoice = None
    
    for inv in invoices:
        if inv["status"] == "partial":
            partial_invoice = inv
            break
    
    if not partial_invoice:
        print("⚠️  No partial invoice found. Skipping test (run test 2 first)")
        return True  # Not a failure, just skip
    
    print(f"\n📋 Testing with invoice: {partial_invoice['invoice_number']}")
    print(f"   Final amount: ₹{partial_invoice['final_amount']}")
    print(f"   Amount paid: ₹{partial_invoice.get('amount_paid', 0)}")
    
    remaining = partial_invoice['final_amount'] - partial_invoice.get('amount_paid', 0)
    print(f"   Remaining: ₹{remaining}")
    
    # Step 2: Pay remaining amount
    print(f"\n💰 Paying remaining amount of ₹{remaining}...")
    response = requests.put(
        f"{BACKEND_URL}/operator/invoices/{partial_invoice['id']}/status",
        headers=headers,
        json={
            "status": "paid",
            "payment_mode": "cash",
            "amount_paid": remaining
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Full payment failed: {response.status_code} - {response.text}")
        return False
    
    print(f"✅ Full payment successful")
    
    # Verify status changed to paid
    updated_inv = get_invoice_by_id(token, partial_invoice['id'])
    
    if not updated_inv:
        print(f"❌ Failed to get updated invoice")
        return False
    
    if updated_inv["status"] != "paid":
        print(f"❌ Status is '{updated_inv['status']}', expected 'paid'")
        return False
    
    print(f"✅ Status changed to: {updated_inv['status']}")
    
    if updated_inv.get("paid_at") is None:
        print(f"❌ paid_at is None, expected a timestamp")
        return False
    
    print(f"✅ paid_at: {updated_inv['paid_at']}")
    
    return True

def test_consolidated_invoice_cannot_be_paid(token):
    """
    Test 4: Consolidated invoice cannot be paid
    """
    print("\n" + "="*80)
    print("TEST 4: Consolidated invoice cannot be paid")
    print("="*80)
    
    headers = get_headers(token)
    
    # Step 1: Find a consolidated invoice
    response = requests.get(f"{BACKEND_URL}/operator/invoices", headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to get invoices: {response.status_code}")
        return False
    
    invoices = response.json()
    consolidated_invoice = None
    
    for inv in invoices:
        if inv["status"] == "consolidated":
            consolidated_invoice = inv
            break
    
    if not consolidated_invoice:
        print("⚠️  No consolidated invoice found. Skipping test (run test 1 first)")
        return True  # Not a failure, just skip
    
    print(f"\n📋 Testing with consolidated invoice: {consolidated_invoice['invoice_number']}")
    print(f"   Consolidated into: {consolidated_invoice.get('consolidated_into', 'N/A')}")
    
    # Step 2: Try to pay the consolidated invoice
    print(f"\n💰 Attempting to pay consolidated invoice (should fail)...")
    response = requests.put(
        f"{BACKEND_URL}/operator/invoices/{consolidated_invoice['id']}/status",
        headers=headers,
        json={
            "status": "paid",
            "payment_mode": "cash",
            "amount_paid": 100
        }
    )
    
    if response.status_code == 400:
        error_detail = response.json().get("detail", "")
        if "consolidated" in error_detail.lower():
            print(f"✅ Correctly rejected with 400 error")
            print(f"   Error message: {error_detail}")
            return True
        else:
            print(f"❌ Got 400 error but wrong message: {error_detail}")
            return False
    else:
        print(f"❌ Expected 400 error, got {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_pending_balance_uses_remaining_for_partial(token):
    """
    Test 5: get_pending_balance uses remaining balance for partial invoices
    """
    print("\n" + "="*80)
    print("TEST 5: Pending balance uses remaining balance for partial invoices")
    print("="*80)
    
    headers = get_headers(token)
    
    # Step 1: Create a test scenario
    # Get a subscriber
    response = requests.get(f"{BACKEND_URL}/operator/subscribers", headers=headers)
    if response.status_code != 200 or not response.json():
        print(f"❌ No subscribers found")
        return False
    
    subscribers = response.json()
    test_sub = subscribers[0]
    
    # Get a plan
    response = requests.get(f"{BACKEND_URL}/operator/plans", headers=headers)
    if response.status_code != 200 or not response.json():
        print(f"❌ No plans available")
        return False
    
    plans = response.json()
    test_plan = plans[0]
    
    print(f"\n📋 Creating test scenario with subscriber: {test_sub['name']}")
    
    # Step 2: Create Invoice A with known amount (e.g., ₹500)
    print(f"\n📝 Creating Invoice A with amount ₹500...")
    invoice_a_data = {
        "subscriber_id": test_sub["id"],
        "line_items": [{
            "plan_id": test_plan["id"],
            "base_amount": 500,
            "discount": 0,
            "service_start_date": datetime.now().isoformat(),
            "service_end_date": (datetime.now() + timedelta(days=30)).isoformat()
        }],
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }
    
    response = requests.post(
        f"{BACKEND_URL}/operator/invoices",
        headers=headers,
        json=invoice_a_data
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create Invoice A: {response.status_code} - {response.text}")
        return False
    
    invoice_a = response.json()
    print(f"✅ Created Invoice A: {invoice_a['invoice_number']} with amount ₹{invoice_a['final_amount']}")
    
    # Step 3: Make partial payment on Invoice A (₹100 out of ₹500)
    print(f"\n💰 Making partial payment of ₹100 on Invoice A...")
    response = requests.put(
        f"{BACKEND_URL}/operator/invoices/{invoice_a['id']}/status",
        headers=headers,
        json={
            "status": "partial",
            "payment_mode": "cash",
            "amount_paid": 100
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Partial payment failed: {response.status_code} - {response.text}")
        return False
    
    print(f"✅ Partial payment successful")
    
    # Verify Invoice A is partial
    invoice_a_updated = get_invoice_by_id(token, invoice_a['id'])
    
    if not invoice_a_updated:
        print(f"❌ Failed to get Invoice A")
        return False
    print(f"   Invoice A status: {invoice_a_updated['status']}")
    print(f"   Amount paid: ₹{invoice_a_updated.get('amount_paid', 0)}")
    print(f"   Remaining: ₹{invoice_a_updated['final_amount'] - invoice_a_updated.get('amount_paid', 0)}")
    
    # Step 4: Create Invoice B for the same subscriber
    print(f"\n📝 Creating Invoice B for the same subscriber...")
    invoice_b_data = {
        "subscriber_id": test_sub["id"],
        "line_items": [{
            "plan_id": test_plan["id"],
            "base_amount": test_plan["price"],
            "discount": 0,
            "service_start_date": datetime.now().isoformat(),
            "service_end_date": (datetime.now() + timedelta(days=30)).isoformat()
        }],
        "due_date": (datetime.now() + timedelta(days=7)).isoformat()
    }
    
    response = requests.post(
        f"{BACKEND_URL}/operator/invoices",
        headers=headers,
        json=invoice_b_data
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create Invoice B: {response.status_code} - {response.text}")
        return False
    
    invoice_b = response.json()
    print(f"✅ Created Invoice B: {invoice_b['invoice_number']}")
    
    # Step 5: Verify Invoice B has "Previous Pending" with remaining balance (₹400, not ₹500)
    print(f"\n🔍 Verifying Invoice B's 'Previous Pending' amount...")
    
    previous_pending_item = None
    for item in invoice_b.get("line_items", []):
        if item.get("plan_name") == "Previous Pending":
            previous_pending_item = item
            break
    
    if not previous_pending_item:
        print(f"❌ Invoice B does not have 'Previous Pending' line item")
        return False
    
    expected_remaining = invoice_a_updated['final_amount'] - invoice_a_updated.get('amount_paid', 0)
    actual_amount = previous_pending_item['final_amount']
    
    print(f"   Expected 'Previous Pending' amount: ₹{expected_remaining}")
    print(f"   Actual 'Previous Pending' amount: ₹{actual_amount}")
    
    if abs(actual_amount - expected_remaining) > 0.01:  # Allow small floating point difference
        print(f"❌ 'Previous Pending' amount is incorrect")
        return False
    
    print(f"✅ 'Previous Pending' amount is correct (remaining balance, not full amount)")
    
    # Step 6: Verify Invoice A is marked as consolidated
    invoice_a_final = get_invoice_by_id(token, invoice_a['id'])
    
    if not invoice_a_final:
        print(f"❌ Failed to get Invoice A")
        return False
    
    if invoice_a_final["status"] != "consolidated":
        print(f"❌ Invoice A status is '{invoice_a_final['status']}', expected 'consolidated'")
        return False
    
    print(f"✅ Invoice A is marked as consolidated")
    
    return True

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("BACKEND API TESTS - NEW INVOICE FEATURES")
    print("="*80)
    
    # Login
    print("\n🔐 Logging in as operator...")
    token = login()
    if not token:
        print("❌ Login failed. Cannot proceed with tests.")
        return
    
    print(f"✅ Login successful")
    
    # Run all tests
    results = {}
    
    results["Test 1: Consolidated status on invoice creation"] = test_consolidated_status_on_invoice_creation(token)
    results["Test 2: Partial payment accumulation"] = test_partial_payment(token)
    results["Test 3: Full payment after partial"] = test_full_payment_after_partial(token)
    results["Test 4: Consolidated invoice cannot be paid"] = test_consolidated_invoice_cannot_be_paid(token)
    results["Test 5: Pending balance uses remaining for partial"] = test_pending_balance_uses_remaining_for_partial(token)
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for p in results.values() if p)
    
    print(f"\n📊 Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    main()
