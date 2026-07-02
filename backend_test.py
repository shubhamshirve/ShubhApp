"""
Backend API Testing for E-Bill Platform
Test: Subscriber Ledger Endpoint
"""
import requests
import json
from datetime import datetime

# Backend URL from environment
BACKEND_URL = "https://health-scan-opt.preview.emergentagent.com/api"

# Test credentials
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def print_section(msg):
    print(f"\n{Colors.CYAN}{'='*80}")
    print(f"{msg}")
    print(f"{'='*80}{Colors.END}\n")

def login_as_operator():
    """Login as operator and return access token"""
    print_info("Logging in as operator...")
    response = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD}
    )
    if response.status_code == 200:
        data = response.json()
        print_success(f"Logged in as: {data['user']['name']}")
        return data["access_token"]
    else:
        print_error(f"Login failed: {response.status_code} - {response.text}")
        return None

def get_subscribers(token):
    """Get list of subscribers"""
    print_info("Fetching subscribers...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BACKEND_URL}/operator/subscribers", headers=headers)
    if response.status_code == 200:
        subscribers = response.json()
        print_success(f"Found {len(subscribers)} subscribers")
        return subscribers
    else:
        print_error(f"Failed to fetch subscribers: {response.status_code}")
        return []

def get_subscriber_ledger(token, subscriber_id):
    """Get subscriber ledger"""
    print_info(f"Fetching ledger for subscriber {subscriber_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}/ledger",
        headers=headers
    )
    
    if response.status_code == 200:
        ledger = response.json()
        print_success(f"Ledger fetched successfully")
        return ledger
    else:
        print_error(f"Failed to fetch ledger: {response.status_code} - {response.text}")
        return None

def verify_subscriber_object(subscriber):
    """Verify subscriber object structure"""
    print_info("Verifying subscriber object structure...")
    
    errors = []
    
    # Check required fields
    if "name" not in subscriber:
        errors.append("Missing 'name' field")
    else:
        print_success(f"Subscriber name: {subscriber['name']}")
    
    if "whatsapp_number" not in subscriber:
        errors.append("Missing 'whatsapp_number' field")
    else:
        print_success(f"WhatsApp number: {subscriber['whatsapp_number']}")
    
    if "plans" not in subscriber:
        errors.append("Missing 'plans' field")
    else:
        plans = subscriber["plans"]
        print_success(f"Plans array present with {len(plans)} plan(s)")
        
        # Verify each plan has days_remaining field
        for i, plan in enumerate(plans, 1):
            if "days_remaining" not in plan:
                errors.append(f"Plan {i} missing 'days_remaining' field")
            else:
                days_remaining = plan["days_remaining"]
                if days_remaining is None or isinstance(days_remaining, int):
                    print_success(f"  Plan {i}: days_remaining = {days_remaining} (type: {type(days_remaining).__name__})")
                else:
                    errors.append(f"Plan {i} 'days_remaining' is not null or int: {type(days_remaining).__name__}")
    
    return errors

def verify_invoices_array(invoices):
    """Verify invoices array structure"""
    print_info("Verifying invoices array structure...")
    
    errors = []
    
    if not isinstance(invoices, list):
        errors.append("'invoices' is not an array")
        return errors
    
    print_success(f"Invoices array present with {len(invoices)} invoice(s)")
    
    if len(invoices) > 0:
        # Verify each invoice has required fields
        for i, invoice in enumerate(invoices, 1):
            invoice_errors = []
            
            if "invoice_number" not in invoice:
                invoice_errors.append("Missing 'invoice_number'")
            
            if "status" not in invoice:
                invoice_errors.append("Missing 'status'")
            
            if "final_amount" not in invoice:
                invoice_errors.append("Missing 'final_amount'")
            
            if "line_items" not in invoice:
                invoice_errors.append("Missing 'line_items'")
            
            if invoice_errors:
                errors.append(f"Invoice {i} ({invoice.get('invoice_number', 'unknown')}): {', '.join(invoice_errors)}")
            else:
                print_success(f"  Invoice {i}: {invoice['invoice_number']} - {invoice['status']} - ₹{invoice['final_amount']} - {len(invoice['line_items'])} line item(s)")
    else:
        print_info("  No invoices found (empty array is valid)")
    
    return errors

def verify_summary_object(summary):
    """Verify summary object structure"""
    print_info("Verifying summary object structure...")
    
    errors = []
    required_fields = [
        "total_invoiced", "total_paid", "total_pending", "total_overdue",
        "invoice_count", "paid_count", "pending_count", "overdue_count",
        "last_payment"
    ]
    
    for field in required_fields:
        if field not in summary:
            errors.append(f"Missing '{field}' field")
        else:
            value = summary[field]
            if field == "last_payment":
                if value is None:
                    print_success(f"  {field}: null (no payments yet)")
                elif isinstance(value, dict):
                    print_success(f"  {field}: object with keys {list(value.keys())}")
                    # Verify last_payment object structure
                    if "date" not in value:
                        errors.append("last_payment missing 'date' field")
                    if "mode" not in value:
                        errors.append("last_payment missing 'mode' field")
                    if "amount" not in value:
                        errors.append("last_payment missing 'amount' field")
                    if "invoice_number" not in value:
                        errors.append("last_payment missing 'invoice_number' field")
                else:
                    errors.append(f"'last_payment' is not null or object: {type(value).__name__}")
            else:
                print_success(f"  {field}: {value}")
    
    return errors

def verify_ledger_response(ledger):
    """Verify complete ledger response structure"""
    print_section("VERIFYING LEDGER RESPONSE STRUCTURE")
    
    all_errors = []
    
    # Check top-level structure
    if "subscriber" not in ledger:
        all_errors.append("Missing 'subscriber' object")
    else:
        errors = verify_subscriber_object(ledger["subscriber"])
        all_errors.extend(errors)
    
    print()
    
    if "invoices" not in ledger:
        all_errors.append("Missing 'invoices' array")
    else:
        errors = verify_invoices_array(ledger["invoices"])
        all_errors.extend(errors)
    
    print()
    
    if "summary" not in ledger:
        all_errors.append("Missing 'summary' object")
    else:
        errors = verify_summary_object(ledger["summary"])
        all_errors.extend(errors)
    
    return all_errors

def print_ledger_summary(ledger, subscriber_name):
    """Print a formatted summary of the ledger"""
    print_section(f"LEDGER SUMMARY FOR: {subscriber_name}")
    
    subscriber = ledger.get("subscriber", {})
    invoices = ledger.get("invoices", [])
    summary = ledger.get("summary", {})
    
    print(f"Subscriber: {subscriber.get('name', 'N/A')}")
    print(f"WhatsApp: {subscriber.get('whatsapp_number', 'N/A')}")
    print(f"Plans: {len(subscriber.get('plans', []))}")
    
    for i, plan in enumerate(subscriber.get("plans", []), 1):
        days = plan.get("days_remaining")
        status = plan.get("status", "unknown")
        print(f"  Plan {i}: {status}, days_remaining: {days}")
    
    print(f"\nInvoices: {len(invoices)}")
    for i, invoice in enumerate(invoices[:5], 1):  # Show first 5
        print(f"  {i}. {invoice.get('invoice_number')} - {invoice.get('status')} - ₹{invoice.get('final_amount')}")
    
    if len(invoices) > 5:
        print(f"  ... and {len(invoices) - 5} more")
    
    print(f"\nFinancial Summary:")
    print(f"  Total Invoiced: ₹{summary.get('total_invoiced', 0)}")
    print(f"  Total Paid: ₹{summary.get('total_paid', 0)}")
    print(f"  Total Pending: ₹{summary.get('total_pending', 0)}")
    print(f"  Total Overdue: ₹{summary.get('total_overdue', 0)}")
    print(f"  Invoice Count: {summary.get('invoice_count', 0)}")
    print(f"  Paid Count: {summary.get('paid_count', 0)}")
    print(f"  Pending Count: {summary.get('pending_count', 0)}")
    print(f"  Overdue Count: {summary.get('overdue_count', 0)}")
    
    last_payment = summary.get('last_payment')
    if last_payment:
        print(f"  Last Payment: ₹{last_payment.get('amount')} on {last_payment.get('date')} via {last_payment.get('mode')} (Invoice: {last_payment.get('invoice_number')})")
    else:
        print(f"  Last Payment: None")
    
    print()

def main():
    print_section("E-BILL PLATFORM - SUBSCRIBER LEDGER ENDPOINT TEST")
    
    # Step 1: Login
    token = login_as_operator()
    if not token:
        print_error("Cannot proceed without authentication")
        return
    
    print()
    
    # Step 2: Get subscribers
    subscribers = get_subscribers(token)
    if not subscribers:
        print_error("No subscribers found")
        return
    
    print()
    
    # Test results
    test_results = []
    
    # Step 3: Test with first subscriber (may have no invoices)
    print_section("TEST 1: FIRST SUBSCRIBER (MAY HAVE NO INVOICES)")
    first_subscriber = subscribers[0]
    print_info(f"Testing with: {first_subscriber['name']} (ID: {first_subscriber['id']})")
    
    ledger1 = get_subscriber_ledger(token, first_subscriber["id"])
    if ledger1:
        errors1 = verify_ledger_response(ledger1)
        print_ledger_summary(ledger1, first_subscriber['name'])
        
        if errors1:
            print_error(f"Test 1 FAILED with {len(errors1)} error(s):")
            for error in errors1:
                print_error(f"  - {error}")
            test_results.append(("First Subscriber Ledger", False))
        else:
            print_success("Test 1 PASSED: All fields present and correct")
            test_results.append(("First Subscriber Ledger", True))
    else:
        print_error("Test 1 FAILED: Could not fetch ledger")
        test_results.append(("First Subscriber Ledger", False))
    
    # Step 4: Test with "Two Plan Invoice Test" subscriber if it exists
    two_plan_subscriber = None
    for sub in subscribers:
        if "Two Plan Invoice Test" in sub.get("name", ""):
            two_plan_subscriber = sub
            break
    
    if two_plan_subscriber:
        print_section("TEST 2: TWO PLAN INVOICE TEST SUBSCRIBER (HAS INVOICES)")
        print_info(f"Testing with: {two_plan_subscriber['name']} (ID: {two_plan_subscriber['id']})")
        
        ledger2 = get_subscriber_ledger(token, two_plan_subscriber["id"])
        if ledger2:
            errors2 = verify_ledger_response(ledger2)
            print_ledger_summary(ledger2, two_plan_subscriber['name'])
            
            if errors2:
                print_error(f"Test 2 FAILED with {len(errors2)} error(s):")
                for error in errors2:
                    print_error(f"  - {error}")
                test_results.append(("Two Plan Subscriber Ledger", False))
            else:
                print_success("Test 2 PASSED: All fields present and correct")
                test_results.append(("Two Plan Subscriber Ledger", True))
        else:
            print_error("Test 2 FAILED: Could not fetch ledger")
            test_results.append(("Two Plan Subscriber Ledger", False))
    else:
        print_warning("'Two Plan Invoice Test' subscriber not found, skipping Test 2")
    
    # Final summary
    print_section("FINAL TEST RESULTS")
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "PASS" if result else "FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status}{Colors.END} - {test_name}")
    
    print(f"\n{Colors.BLUE}Total: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}✓ ALL TESTS PASSED{Colors.END}\n")
    else:
        print(f"\n{Colors.RED}✗ SOME TESTS FAILED{Colors.END}\n")
    
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
