"""
Backend API Testing for E-Bill Platform
Test: One invoice per plan invoice flow
"""
import requests
import json
from datetime import datetime, timedelta

# Backend URL from environment
BACKEND_URL = "https://whatsapp-stats-view.preview.emergentagent.com/api"

# Test credentials
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

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

def get_plans(token):
    """Get operator plans"""
    print_info("Fetching operator plans...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BACKEND_URL}/operator/plans", headers=headers)
    if response.status_code == 200:
        plans = response.json()
        print_success(f"Found {len(plans)} plans")
        return plans
    else:
        print_error(f"Failed to fetch plans: {response.status_code}")
        return []

def create_test_plans_if_needed(token):
    """Create test plans with different validities if they don't exist"""
    plans = get_plans(token)
    
    # Check if we have monthly and quarterly plans
    monthly_plan = None
    quarterly_plan = None
    
    for plan in plans:
        if plan.get("validity") == "monthly" and not monthly_plan:
            monthly_plan = plan
        elif plan.get("validity") == "quarterly" and not quarterly_plan:
            quarterly_plan = plan
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create monthly plan if needed
    if not monthly_plan:
        print_info("Creating monthly test plan...")
        response = requests.post(
            f"{BACKEND_URL}/operator/plans",
            headers=headers,
            json={
                "name": "Monthly Test Plan",
                "price": 500,
                "validity": "monthly",
                "tax_percentage": 0,
                "tax_type": "none",
                "description": "Monthly test plan for invoice testing"
            }
        )
        if response.status_code == 200:
            monthly_plan = response.json()
            print_success(f"Created monthly plan: {monthly_plan['name']}")
        else:
            print_error(f"Failed to create monthly plan: {response.status_code}")
    
    # Create quarterly plan if needed
    if not quarterly_plan:
        print_info("Creating quarterly test plan...")
        response = requests.post(
            f"{BACKEND_URL}/operator/plans",
            headers=headers,
            json={
                "name": "Quarterly Test Plan",
                "price": 1400,
                "validity": "quarterly",
                "tax_percentage": 0,
                "tax_type": "none",
                "description": "Quarterly test plan for invoice testing"
            }
        )
        if response.status_code == 200:
            quarterly_plan = response.json()
            print_success(f"Created quarterly plan: {quarterly_plan['name']}")
        else:
            print_error(f"Failed to create quarterly plan: {response.status_code}")
    
    return monthly_plan, quarterly_plan

def create_subscriber_with_two_plans(token, monthly_plan, quarterly_plan):
    """Create subscriber with 2 plans and generate_first_invoice=true"""
    print_info("Creating subscriber with 2 plans (generate_first_invoice=true)...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Use 2026-06-01 as start date as per test requirements
    start_date = "2026-06-01"
    
    subscriber_data = {
        "name": "Two Plan Invoice Test",
        "whatsapp_number": "919700000001",
        "plans": [
            {
                "plan_id": monthly_plan["id"],
                "plan_start_date": start_date,
                "selected_validity": "monthly"
            },
            {
                "plan_id": quarterly_plan["id"],
                "plan_start_date": start_date,
                "selected_validity": "quarterly"
            }
        ],
        "generate_first_invoice": True
    }
    
    response = requests.post(
        f"{BACKEND_URL}/operator/subscribers",
        headers=headers,
        json=subscriber_data
    )
    
    if response.status_code == 200:
        subscriber = response.json()
        print_success(f"Created subscriber: {subscriber['name']} (ID: {subscriber['id']})")
        return subscriber
    else:
        print_error(f"Failed to create subscriber: {response.status_code} - {response.text}")
        return None

def get_invoices_for_subscriber(token, subscriber_id):
    """Get all invoices for a subscriber"""
    print_info(f"Fetching invoices for subscriber {subscriber_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BACKEND_URL}/operator/invoices",
        headers=headers,
        params={"subscriber_id": subscriber_id}
    )
    
    if response.status_code == 200:
        invoices = response.json()
        print_success(f"Found {len(invoices)} invoices")
        return invoices
    else:
        print_error(f"Failed to fetch invoices: {response.status_code}")
        return []

def get_subscriber_details(token, subscriber_id):
    """Get subscriber details"""
    print_info(f"Fetching subscriber details...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        subscriber = response.json()
        return subscriber
    else:
        print_error(f"Failed to fetch subscriber: {response.status_code}")
        return None

def get_expiry_audit(token, subscriber_id):
    """Get expiry audit trail for subscriber"""
    print_info(f"Fetching expiry audit trail...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BACKEND_URL}/operator/subscribers/{subscriber_id}/expiry-audit",
        headers=headers
    )
    
    if response.status_code == 200:
        audit = response.json()
        return audit
    else:
        print_error(f"Failed to fetch expiry audit: {response.status_code}")
        return None

def verify_invoice_count(invoices, expected_count):
    """Verify number of invoices created"""
    print_info(f"Verifying invoice count...")
    actual_count = len(invoices)
    if actual_count == expected_count:
        print_success(f"Invoice count correct: {actual_count} invoices (expected {expected_count})")
        return True
    else:
        print_error(f"Invoice count mismatch: {actual_count} invoices (expected {expected_count})")
        return False

def verify_line_items_per_invoice(invoices):
    """Verify each invoice has exactly 1 line item"""
    print_info(f"Verifying line items per invoice...")
    all_correct = True
    for i, invoice in enumerate(invoices, 1):
        line_items_count = len(invoice.get("line_items", []))
        if line_items_count == 1:
            print_success(f"Invoice {i} ({invoice['invoice_number']}): 1 line item ✓")
        else:
            print_error(f"Invoice {i} ({invoice['invoice_number']}): {line_items_count} line items (expected 1)")
            all_correct = False
    return all_correct

def verify_service_dates(invoices, subscriber, monthly_plan, quarterly_plan):
    """Verify service_end_date matches plan_expiry_date"""
    print_info(f"Verifying service dates match plan expiry dates...")
    
    # Get subscriber plan expiry dates
    plan_expiry_map = {}
    for plan in subscriber.get("plans", []):
        plan_id = plan.get("plan_id")
        plan_expiry_date = plan.get("plan_expiry_date")
        if plan_id and plan_expiry_date:
            plan_expiry_map[plan_id] = plan_expiry_date
    
    all_correct = True
    for invoice in invoices:
        line_items = invoice.get("line_items", [])
        if len(line_items) == 1:
            line_item = line_items[0]
            plan_id = line_item.get("plan_id")
            service_end_date = line_item.get("service_end_date", "")[:10]  # Get YYYY-MM-DD part
            
            if plan_id in plan_expiry_map:
                expected_expiry = plan_expiry_map[plan_id]
                if service_end_date == expected_expiry:
                    print_success(f"Invoice {invoice['invoice_number']}: service_end_date ({service_end_date}) matches plan_expiry_date ✓")
                else:
                    print_error(f"Invoice {invoice['invoice_number']}: service_end_date ({service_end_date}) != plan_expiry_date ({expected_expiry})")
                    all_correct = False
            else:
                print_warning(f"Invoice {invoice['invoice_number']}: plan_id {plan_id} not found in subscriber plans")
    
    return all_correct

def verify_due_dates(invoices):
    """Verify due_date = service_start_date - 1 day"""
    print_info(f"Verifying due dates...")
    
    all_correct = True
    for invoice in invoices:
        line_items = invoice.get("line_items", [])
        if len(line_items) == 1:
            line_item = line_items[0]
            service_start_str = line_item.get("service_start_date", "")[:10]
            due_date_str = invoice.get("due_date", "")[:10]
            
            try:
                service_start = datetime.strptime(service_start_str, "%Y-%m-%d")
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                expected_due_date = service_start - timedelta(days=1)
                
                if due_date == expected_due_date:
                    print_success(f"Invoice {invoice['invoice_number']}: due_date ({due_date_str}) = service_start - 1 day ✓")
                else:
                    print_error(f"Invoice {invoice['invoice_number']}: due_date ({due_date_str}) != service_start - 1 day (expected {expected_due_date.strftime('%Y-%m-%d')})")
                    all_correct = False
            except Exception as e:
                print_error(f"Invoice {invoice['invoice_number']}: Error parsing dates - {e}")
                all_correct = False
    
    return all_correct

def verify_expiry_audit_events(audit, expected_count):
    """Verify expiry audit trail has correct number of events"""
    print_info(f"Verifying expiry audit events...")
    
    events = audit.get("events", [])
    actual_count = len(events)
    
    if actual_count == expected_count:
        print_success(f"Expiry audit events correct: {actual_count} events (expected {expected_count})")
        return True
    else:
        print_error(f"Expiry audit events mismatch: {actual_count} events (expected {expected_count})")
        return False

def print_invoice_summary(invoices):
    """Print detailed invoice summary"""
    print("\n" + "="*80)
    print("INVOICE SUMMARY")
    print("="*80)
    
    for i, invoice in enumerate(invoices, 1):
        print(f"\nInvoice {i}:")
        print(f"  Invoice Number: {invoice['invoice_number']}")
        print(f"  Status: {invoice['status']}")
        print(f"  Due Date: {invoice.get('due_date', '')[:10]}")
        print(f"  Total Amount: ₹{invoice['final_amount']}")
        print(f"  Line Items: {len(invoice.get('line_items', []))}")
        
        for j, item in enumerate(invoice.get("line_items", []), 1):
            print(f"    Line Item {j}:")
            print(f"      Plan: {item.get('plan_name')}")
            print(f"      Validity: {item.get('selected_validity')}")
            print(f"      Amount: ₹{item.get('final_amount')}")
            print(f"      Service Start: {item.get('service_start_date', '')[:10]}")
            print(f"      Service End: {item.get('service_end_date', '')[:10]}")
    
    print("="*80 + "\n")

def print_subscriber_summary(subscriber):
    """Print subscriber plan details"""
    print("\n" + "="*80)
    print("SUBSCRIBER PLAN DETAILS")
    print("="*80)
    
    print(f"Subscriber: {subscriber['name']}")
    print(f"ID: {subscriber['id']}")
    print(f"Plans: {len(subscriber.get('plans', []))}")
    
    for i, plan in enumerate(subscriber.get("plans", []), 1):
        print(f"\n  Plan {i}:")
        print(f"    Plan ID: {plan.get('plan_id')}")
        print(f"    Validity: {plan.get('selected_validity')}")
        print(f"    Start Date: {plan.get('plan_start_date')}")
        print(f"    Expiry Date: {plan.get('plan_expiry_date')}")
        print(f"    Status: {plan.get('status')}")
    
    print("="*80 + "\n")

def main():
    print("\n" + "="*80)
    print("E-BILL PLATFORM - ONE INVOICE PER PLAN TEST")
    print("="*80 + "\n")
    
    # Step 1: Login
    token = login_as_operator()
    if not token:
        print_error("Cannot proceed without authentication")
        return
    
    print()
    
    # Step 2: Get/Create plans
    monthly_plan, quarterly_plan = create_test_plans_if_needed(token)
    if not monthly_plan or not quarterly_plan:
        print_error("Cannot proceed without both monthly and quarterly plans")
        return
    
    print_info(f"Using plans:")
    print(f"  - Monthly: {monthly_plan['name']} (ID: {monthly_plan['id']}, Price: ₹{monthly_plan['price']})")
    print(f"  - Quarterly: {quarterly_plan['name']} (ID: {quarterly_plan['id']}, Price: ₹{quarterly_plan['price']})")
    print()
    
    # Step 3: Create subscriber with 2 plans
    subscriber = create_subscriber_with_two_plans(token, monthly_plan, quarterly_plan)
    if not subscriber:
        print_error("Cannot proceed without subscriber")
        return
    
    print()
    
    # Step 4: Get invoices
    invoices = get_invoices_for_subscriber(token, subscriber["id"])
    if not invoices:
        print_error("No invoices found - test failed")
        return
    
    print()
    
    # Step 5: Get subscriber details
    subscriber_details = get_subscriber_details(token, subscriber["id"])
    if not subscriber_details:
        print_error("Cannot fetch subscriber details")
        return
    
    print()
    
    # Step 6: Get expiry audit
    audit = get_expiry_audit(token, subscriber["id"])
    
    print()
    
    # Print summaries
    print_invoice_summary(invoices)
    print_subscriber_summary(subscriber_details)
    
    # Run verifications
    print("\n" + "="*80)
    print("VERIFICATION RESULTS")
    print("="*80 + "\n")
    
    results = []
    
    # Test 1: Invoice count
    results.append(("Invoice Count (2 invoices)", verify_invoice_count(invoices, 2)))
    
    # Test 2: Line items per invoice
    results.append(("Line Items (1 per invoice)", verify_line_items_per_invoice(invoices)))
    
    # Test 3: Service dates match plan expiry
    results.append(("Service End Dates Match Plan Expiry", verify_service_dates(invoices, subscriber_details, monthly_plan, quarterly_plan)))
    
    # Test 4: Due dates
    results.append(("Due Dates (service_start - 1 day)", verify_due_dates(invoices)))
    
    # Test 5: Expiry audit events
    if audit:
        results.append(("Expiry Audit Events (2 events)", verify_expiry_audit_events(audit, 2)))
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL TEST RESULTS")
    print("="*80 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
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
