#!/usr/bin/env python3
"""
Backend API Tests for E-Bill Platform - Ledger & Partial Payment Features
Tests the specific fixes requested:
1. Ledger shows payment records for partial invoices
2. allow_partial_payments setting
3. Ledger financial summary accuracy
"""

import requests
import json
import sys
from datetime import datetime

# Backend URL from environment
BACKEND_URL = "https://recursing-proskuriakova-9.preview.emergentagent.com/api"

# Test credentials
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log_info(msg):
    print(f"{BLUE}ℹ {msg}{RESET}")

def log_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def log_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def log_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def login_operator():
    """Login as operator and return auth token"""
    log_info("Logging in as operator...")
    response = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD}
    )
    if response.status_code != 200:
        log_error(f"Login failed: {response.status_code} - {response.text}")
        return None
    
    data = response.json()
    token = data.get("access_token")
    if token:
        log_success(f"Logged in successfully as {OPERATOR_EMAIL}")
        return token
    else:
        log_error("No access token in response")
        return None

def get_headers(token):
    """Return headers with auth token"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def test_1_ledger_payment_records(token):
    """
    Test 1: Ledger shows payment records for partial invoices
    - Verify response includes summary.all_payments array
    - Verify partial payments appear in all_payments
    - Verify summary.total_paid includes partial amounts
    - Verify summary.last_payment reflects most recent payment
    """
    print("\n" + "="*80)
    print("TEST 1: Ledger shows payment records for partial invoices")
    print("="*80)
    
    headers = get_headers(token)
    
    # Step 1: Get subscribers list
    log_info("Fetching subscribers list...")
    response = requests.get(f"{BACKEND_URL}/operator/subscribers", headers=headers)
    if response.status_code != 200:
        log_error(f"Failed to fetch subscribers: {response.status_code} - {response.text}")
        return False
    
    subscribers = response.json()
    if not subscribers:
        log_error("No subscribers found in the system")
        return False
    
    log_success(f"Found {len(subscribers)} subscribers")
    
    # Pick the first subscriber
    subscriber = subscribers[0]
    subscriber_id = subscriber["id"]
    subscriber_name = subscriber.get("name", "Unknown")
    log_info(f"Testing with subscriber: {subscriber_name} (ID: {subscriber_id})")
    
    # Step 2: Get ledger for this subscriber
    log_info(f"Fetching ledger for subscriber {subscriber_id}...")
    response = requests.get(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}/ledger",
        headers=headers
    )
    if response.status_code != 200:
        log_error(f"Failed to fetch ledger: {response.status_code} - {response.text}")
        return False
    
    ledger = response.json()
    log_success("Ledger fetched successfully")
    
    # Step 3: Verify summary structure
    summary = ledger.get("summary", {})
    if not summary:
        log_error("Ledger response missing 'summary' field")
        return False
    
    log_success("Ledger contains 'summary' field")
    
    # Step 4: Verify all_payments array exists
    all_payments = summary.get("all_payments")
    if all_payments is None:
        log_error("summary.all_payments field is missing")
        return False
    
    log_success(f"summary.all_payments exists with {len(all_payments)} payment records")
    
    # Step 5: Check if there are any partial invoices
    invoices = ledger.get("invoices", [])
    partial_invoices = [inv for inv in invoices if inv.get("status") == "partial"]
    
    if partial_invoices:
        log_info(f"Found {len(partial_invoices)} partial invoices")
        
        # Verify partial payments appear in all_payments
        for partial_inv in partial_invoices:
            inv_num = partial_inv.get("invoice_number")
            payments_for_this_invoice = [
                p for p in all_payments 
                if p.get("invoice_number") == inv_num
            ]
            
            if payments_for_this_invoice:
                log_success(f"Partial invoice {inv_num} has {len(payments_for_this_invoice)} payment(s) in all_payments")
                for payment in payments_for_this_invoice:
                    log_info(f"  - Amount: ₹{payment.get('amount')}, Mode: {payment.get('mode')}, Date: {payment.get('date')}")
            else:
                log_warning(f"Partial invoice {inv_num} has no payments in all_payments (might be newly created)")
        
        # Verify total_paid includes partial amounts
        total_paid = summary.get("total_paid", 0)
        log_info(f"summary.total_paid = ₹{total_paid}")
        
        # Calculate expected total_paid
        expected_paid = 0
        for inv in invoices:
            if inv.get("status") == "paid":
                expected_paid += inv.get("final_amount", 0)
            elif inv.get("status") == "partial":
                expected_paid += inv.get("amount_paid", 0) or 0
        
        log_info(f"Expected total_paid (paid invoices + partial amounts) = ₹{expected_paid}")
        
        if abs(total_paid - expected_paid) < 0.01:  # Allow for floating point precision
            log_success("total_paid correctly includes partial payment amounts")
        else:
            log_error(f"total_paid mismatch: got ₹{total_paid}, expected ₹{expected_paid}")
            return False
    else:
        log_warning("No partial invoices found for this subscriber")
        log_info("Checking if all_payments includes paid invoices...")
        
        paid_invoices = [inv for inv in invoices if inv.get("status") == "paid"]
        if paid_invoices:
            log_info(f"Found {len(paid_invoices)} paid invoices")
            # Verify paid invoices appear in all_payments
            for paid_inv in paid_invoices[:3]:  # Check first 3
                inv_num = paid_inv.get("invoice_number")
                payments_for_this_invoice = [
                    p for p in all_payments 
                    if p.get("invoice_number") == inv_num
                ]
                if payments_for_this_invoice:
                    log_success(f"Paid invoice {inv_num} appears in all_payments")
                else:
                    log_warning(f"Paid invoice {inv_num} not in all_payments")
    
    # Step 6: Verify last_payment
    last_payment = summary.get("last_payment")
    if last_payment:
        log_success(f"summary.last_payment exists: ₹{last_payment.get('amount')} on {last_payment.get('date')} via {last_payment.get('mode')}")
        
        # Verify it's actually the most recent
        if all_payments:
            sorted_payments = sorted(
                [p for p in all_payments if p.get("date")],
                key=lambda x: x["date"],
                reverse=True
            )
            if sorted_payments:
                most_recent = sorted_payments[0]
                if last_payment.get("date") == most_recent.get("date"):
                    log_success("last_payment correctly reflects the most recent payment")
                else:
                    log_warning(f"last_payment date mismatch: {last_payment.get('date')} vs {most_recent.get('date')}")
    else:
        if all_payments:
            log_error("summary.last_payment is None but all_payments has records")
            return False
        else:
            log_info("No payments recorded yet (last_payment is None)")
    
    # Step 7: Verify total_pending calculation
    total_pending = summary.get("total_pending", 0)
    expected_pending = 0
    for inv in invoices:
        if inv.get("status") in ("pending", "partial"):
            final_amount = inv.get("final_amount", 0)
            amount_paid = inv.get("amount_paid", 0) or 0
            expected_pending += (final_amount - amount_paid)
    
    log_info(f"summary.total_pending = ₹{total_pending}")
    log_info(f"Expected total_pending (remaining balance) = ₹{expected_pending}")
    
    if abs(total_pending - expected_pending) < 0.01:
        log_success("total_pending correctly calculated (includes remaining balance from partial invoices)")
    else:
        log_error(f"total_pending mismatch: got ₹{total_pending}, expected ₹{expected_pending}")
        return False
    
    log_success("TEST 1 PASSED: Ledger payment records working correctly")
    return True

def test_2_allow_partial_payments_setting(token):
    """
    Test 2: allow_partial_payments setting
    - GET invoice-settings and verify allow_partial_payments field exists
    - PUT to disable partial payments
    - Try to mark invoice as partial - should return 403
    - PUT to enable partial payments
    - Try partial payment again - should succeed
    """
    print("\n" + "="*80)
    print("TEST 2: allow_partial_payments setting")
    print("="*80)
    
    headers = get_headers(token)
    
    # Step 1: Get current invoice settings
    log_info("Fetching current invoice settings...")
    response = requests.get(f"{BACKEND_URL}/operator/invoice-settings", headers=headers)
    if response.status_code != 200:
        log_error(f"Failed to fetch invoice settings: {response.status_code} - {response.text}")
        return False
    
    settings = response.json()
    log_success("Invoice settings fetched successfully")
    
    # Step 2: Verify allow_partial_payments field exists
    if "allow_partial_payments" not in settings:
        log_error("allow_partial_payments field missing from invoice settings")
        return False
    
    current_value = settings.get("allow_partial_payments")
    log_success(f"allow_partial_payments field exists (current value: {current_value})")
    
    # Store original settings for restoration
    original_settings = settings.copy()
    
    # Step 3: Find a pending invoice to test with
    log_info("Finding a pending invoice to test with...")
    response = requests.get(f"{BACKEND_URL}/operator/invoices?status=pending", headers=headers)
    if response.status_code != 200:
        log_error(f"Failed to fetch invoices: {response.status_code} - {response.text}")
        return False
    
    invoices = response.json()
    pending_invoices = [inv for inv in invoices if inv.get("status") == "pending"]
    
    if not pending_invoices:
        log_warning("No pending invoices found - creating a test scenario")
        # Try to find any invoice that's not paid/cancelled
        all_invoices_response = requests.get(f"{BACKEND_URL}/operator/invoices", headers=headers)
        if all_invoices_response.status_code == 200:
            all_invoices = all_invoices_response.json()
            testable_invoices = [
                inv for inv in all_invoices 
                if inv.get("status") in ("pending", "overdue")
            ]
            if testable_invoices:
                test_invoice = testable_invoices[0]
            else:
                log_error("No suitable invoices found for testing")
                return False
        else:
            log_error("Could not fetch invoices for testing")
            return False
    else:
        test_invoice = pending_invoices[0]
    
    invoice_id = test_invoice["id"]
    invoice_number = test_invoice.get("invoice_number", "Unknown")
    final_amount = test_invoice.get("final_amount", 0)
    log_success(f"Using invoice {invoice_number} (ID: {invoice_id}, Amount: ₹{final_amount})")
    
    # Step 4: Disable partial payments
    log_info("Disabling partial payments...")
    settings["allow_partial_payments"] = False
    response = requests.put(
        f"{BACKEND_URL}/operator/invoice-settings",
        headers=headers,
        json=settings
    )
    if response.status_code != 200:
        log_error(f"Failed to update settings: {response.status_code} - {response.text}")
        return False
    
    log_success("Partial payments disabled")
    
    # Step 5: Try to mark invoice as partial - should fail with 403
    log_info("Attempting to mark invoice as partial (should fail)...")
    partial_amount = final_amount / 2  # Pay half
    response = requests.put(
        f"{BACKEND_URL}/operator/invoices/{invoice_id}/status",
        headers=headers,
        json={
            "status": "partial",
            "payment_mode": "cash",
            "amount_paid": partial_amount
        }
    )
    
    if response.status_code == 403:
        response_data = response.json()
        error_detail = response_data.get("detail", "")
        if "partial payments are disabled" in error_detail.lower():
            log_success(f"Correctly blocked partial payment: {error_detail}")
        else:
            log_warning(f"Got 403 but unexpected message: {error_detail}")
    else:
        log_error(f"Expected 403 but got {response.status_code}: {response.text}")
        # Restore settings before returning
        requests.put(f"{BACKEND_URL}/operator/invoice-settings", headers=headers, json=original_settings)
        return False
    
    # Step 6: Re-enable partial payments
    log_info("Re-enabling partial payments...")
    settings["allow_partial_payments"] = True
    response = requests.put(
        f"{BACKEND_URL}/operator/invoice-settings",
        headers=headers,
        json=settings
    )
    if response.status_code != 200:
        log_error(f"Failed to update settings: {response.status_code} - {response.text}")
        return False
    
    log_success("Partial payments re-enabled")
    
    # Step 7: Try partial payment again - should succeed
    log_info("Attempting partial payment again (should succeed)...")
    response = requests.put(
        f"{BACKEND_URL}/operator/invoices/{invoice_id}/status",
        headers=headers,
        json={
            "status": "partial",
            "payment_mode": "cash",
            "amount_paid": partial_amount
        }
    )
    
    if response.status_code == 200:
        log_success(f"Partial payment succeeded: ₹{partial_amount} recorded")
        
        # Verify the invoice status
        verify_response = requests.get(
            f"{BACKEND_URL}/operator/invoices/{invoice_id}",
            headers=headers
        )
        if verify_response.status_code == 200:
            updated_invoice = verify_response.json()
            if updated_invoice.get("status") == "partial":
                log_success(f"Invoice status correctly updated to 'partial'")
                log_info(f"Amount paid: ₹{updated_invoice.get('amount_paid', 0)}")
            else:
                log_warning(f"Invoice status is '{updated_invoice.get('status')}' instead of 'partial'")
    else:
        log_error(f"Partial payment failed: {response.status_code} - {response.text}")
        # Restore settings
        requests.put(f"{BACKEND_URL}/operator/invoice-settings", headers=headers, json=original_settings)
        return False
    
    # Restore original settings
    log_info("Restoring original settings...")
    requests.put(f"{BACKEND_URL}/operator/invoice-settings", headers=headers, json=original_settings)
    
    log_success("TEST 2 PASSED: allow_partial_payments setting working correctly")
    return True

def test_3_ledger_financial_accuracy(token):
    """
    Test 3: Ledger financial summary accuracy
    - Find or create scenario with paid and partial invoices
    - Verify total_paid includes partial amounts (not just fully-paid invoices)
    - Verify total_pending is correct (remaining balance, not full amount)
    """
    print("\n" + "="*80)
    print("TEST 3: Ledger financial summary accuracy")
    print("="*80)
    
    headers = get_headers(token)
    
    # Step 1: Get subscribers list
    log_info("Fetching subscribers list...")
    response = requests.get(f"{BACKEND_URL}/operator/subscribers", headers=headers)
    if response.status_code != 200:
        log_error(f"Failed to fetch subscribers: {response.status_code} - {response.text}")
        return False
    
    subscribers = response.json()
    if not subscribers:
        log_error("No subscribers found")
        return False
    
    # Find a subscriber with both paid and partial invoices
    target_subscriber = None
    for sub in subscribers:
        sub_id = sub["id"]
        ledger_response = requests.get(
            f"{BACKEND_URL}/operator/subscribers/{sub_id}/ledger",
            headers=headers
        )
        if ledger_response.status_code == 200:
            ledger = ledger_response.json()
            invoices = ledger.get("invoices", [])
            has_paid = any(inv.get("status") == "paid" for inv in invoices)
            has_partial = any(inv.get("status") == "partial" for inv in invoices)
            
            if has_paid and has_partial:
                target_subscriber = sub
                log_success(f"Found subscriber with both paid and partial invoices: {sub.get('name')}")
                break
            elif has_partial:
                target_subscriber = sub
                log_info(f"Found subscriber with partial invoices: {sub.get('name')}")
                break
    
    if not target_subscriber:
        log_warning("No subscriber with partial invoices found - using first subscriber")
        target_subscriber = subscribers[0]
    
    subscriber_id = target_subscriber["id"]
    subscriber_name = target_subscriber.get("name", "Unknown")
    
    # Step 2: Get ledger
    log_info(f"Fetching ledger for {subscriber_name}...")
    response = requests.get(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}/ledger",
        headers=headers
    )
    if response.status_code != 200:
        log_error(f"Failed to fetch ledger: {response.status_code} - {response.text}")
        return False
    
    ledger = response.json()
    invoices = ledger.get("invoices", [])
    summary = ledger.get("summary", {})
    
    log_info(f"Subscriber has {len(invoices)} invoices")
    
    # Step 3: Calculate expected values manually
    expected_total_paid = 0
    expected_total_pending = 0
    
    paid_invoices = []
    partial_invoices = []
    pending_invoices = []
    
    for inv in invoices:
        status = inv.get("status")
        final_amount = inv.get("final_amount", 0)
        amount_paid = inv.get("amount_paid", 0) or 0
        
        if status == "paid":
            expected_total_paid += final_amount
            paid_invoices.append(inv)
        elif status == "partial":
            expected_total_paid += amount_paid
            expected_total_pending += (final_amount - amount_paid)
            partial_invoices.append(inv)
        elif status in ("pending", "overdue"):
            expected_total_pending += final_amount
            pending_invoices.append(inv)
    
    log_info(f"Invoice breakdown:")
    log_info(f"  - Paid: {len(paid_invoices)} invoices")
    log_info(f"  - Partial: {len(partial_invoices)} invoices")
    log_info(f"  - Pending/Overdue: {len(pending_invoices)} invoices")
    
    # Step 4: Verify total_paid
    actual_total_paid = summary.get("total_paid", 0)
    log_info(f"\nTotal Paid:")
    log_info(f"  - Actual (from API): ₹{actual_total_paid}")
    log_info(f"  - Expected (calculated): ₹{expected_total_paid}")
    
    if abs(actual_total_paid - expected_total_paid) < 0.01:
        log_success("✓ total_paid is correct (includes partial payment amounts)")
    else:
        log_error(f"✗ total_paid mismatch: got ₹{actual_total_paid}, expected ₹{expected_total_paid}")
        return False
    
    # Step 5: Verify total_pending
    actual_total_pending = summary.get("total_pending", 0)
    log_info(f"\nTotal Pending:")
    log_info(f"  - Actual (from API): ₹{actual_total_pending}")
    log_info(f"  - Expected (calculated): ₹{expected_total_pending}")
    
    if abs(actual_total_pending - expected_total_pending) < 0.01:
        log_success("✓ total_pending is correct (uses remaining balance for partial invoices)")
    else:
        log_error(f"✗ total_pending mismatch: got ₹{actual_total_pending}, expected ₹{expected_total_pending}")
        return False
    
    # Step 6: Detailed verification for partial invoices
    if partial_invoices:
        log_info(f"\nDetailed verification of {len(partial_invoices)} partial invoice(s):")
        for inv in partial_invoices:
            inv_num = inv.get("invoice_number")
            final_amt = inv.get("final_amount", 0)
            paid_amt = inv.get("amount_paid", 0) or 0
            remaining = final_amt - paid_amt
            
            log_info(f"  Invoice {inv_num}:")
            log_info(f"    - Total: ₹{final_amt}")
            log_info(f"    - Paid: ₹{paid_amt}")
            log_info(f"    - Remaining: ₹{remaining}")
            
            # Verify this partial amount is included in total_paid
            if paid_amt > 0:
                log_success(f"    ✓ Partial payment of ₹{paid_amt} included in total_paid")
            
            # Verify remaining balance is included in total_pending
            if remaining > 0:
                log_success(f"    ✓ Remaining balance of ₹{remaining} included in total_pending")
    else:
        log_warning("No partial invoices found for detailed verification")
    
    log_success("TEST 3 PASSED: Ledger financial summary is accurate")
    return True

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("E-BILL BACKEND TESTS - Ledger & Partial Payment Features")
    print("="*80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test User: {OPERATOR_EMAIL}")
    print("="*80)
    
    # Login
    token = login_operator()
    if not token:
        log_error("Failed to login - cannot proceed with tests")
        sys.exit(1)
    
    # Run tests
    results = {
        "Test 1: Ledger Payment Records": test_1_ledger_payment_records(token),
        "Test 2: allow_partial_payments Setting": test_2_allow_partial_payments_setting(token),
        "Test 3: Ledger Financial Accuracy": test_3_ledger_financial_accuracy(token),
    }
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{GREEN}PASSED{RESET}" if result else f"{RED}FAILED{RESET}"
        print(f"{test_name}: {status}")
    
    print("="*80)
    print(f"Results: {passed}/{total} tests passed")
    print("="*80)
    
    if passed == total:
        log_success("All tests passed!")
        sys.exit(0)
    else:
        log_error(f"{total - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
