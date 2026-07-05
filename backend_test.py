"""
Backend Test for Previous Pending Invoice Feature
Tests the new feature where pending invoices are bundled into new invoices
"""
import requests
import json
from datetime import datetime, timedelta

# Backend URL
BASE_URL = "http://localhost:8001"
API_URL = f"{BASE_URL}/api"

# Test credentials from test_credentials.md
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def log_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def log_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def log_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def test_health():
    """Test backend health endpoint"""
    print("\n" + "="*80)
    print("TEST 1: Backend Health Check")
    print("="*80)
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            log_success(f"Backend is healthy: {response.json()}")
            return True
        else:
            log_error(f"Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        log_error(f"Health check failed: {str(e)}")
        return False

def login_operator():
    """Login as operator and get access token"""
    print("\n" + "="*80)
    print("TEST 2: Operator Login")
    print("="*80)
    
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                log_success(f"Login successful. Token: {token[:20]}...")
                return token
            else:
                log_error("No access_token in response")
                return None
        else:
            log_error(f"Login failed with status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        log_error(f"Login failed: {str(e)}")
        return None

def get_subscribers(token):
    """Get list of subscribers"""
    print("\n" + "="*80)
    print("TEST 3: Get Subscribers")
    print("="*80)
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_URL}/operator/subscribers", headers=headers, timeout=10)
        
        if response.status_code == 200:
            subscribers = response.json()
            log_success(f"Found {len(subscribers)} subscribers")
            if subscribers:
                log_info(f"First subscriber: {subscribers[0].get('name')} (ID: {subscribers[0].get('id')})")
            return subscribers
        else:
            log_error(f"Failed to get subscribers: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        log_error(f"Failed to get subscribers: {str(e)}")
        return []

def get_plans(token):
    """Get list of plans"""
    print("\n" + "="*80)
    print("TEST 4: Get Plans")
    print("="*80)
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_URL}/operator/plans", headers=headers, timeout=10)
        
        if response.status_code == 200:
            plans = response.json()
            log_success(f"Found {len(plans)} plans")
            if plans:
                log_info(f"First plan: {plans[0].get('name')} (ID: {plans[0].get('id')}, Price: {plans[0].get('price')})")
            return plans
        else:
            log_error(f"Failed to get plans: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        log_error(f"Failed to get plans: {str(e)}")
        return []

def get_invoices_for_subscriber(token, subscriber_id):
    """Get invoices for a specific subscriber"""
    print("\n" + "="*80)
    print(f"TEST 5: Get Invoices for Subscriber {subscriber_id}")
    print("="*80)
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_URL}/operator/invoices",
            params={"subscriber_id": subscriber_id},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            invoices = response.json()
            log_success(f"Found {len(invoices)} invoices for subscriber")
            
            pending_invoices = [inv for inv in invoices if inv.get('status') in ['pending', 'overdue']]
            log_info(f"Pending/Overdue invoices: {len(pending_invoices)}")
            
            for inv in pending_invoices:
                log_info(f"  - Invoice #{inv.get('invoice_number')}: Status={inv.get('status')}, Amount={inv.get('final_amount')}")
            
            return invoices, pending_invoices
        else:
            log_error(f"Failed to get invoices: {response.status_code} - {response.text}")
            return [], []
    except Exception as e:
        log_error(f"Failed to get invoices: {str(e)}")
        return [], []

def create_invoice(token, subscriber_id, plan_id):
    """Create a new invoice for a subscriber"""
    print("\n" + "="*80)
    print(f"TEST 6: Create New Invoice for Subscriber {subscriber_id}")
    print("="*80)
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Calculate service dates
        service_start = datetime.now()
        service_end = service_start + timedelta(days=30)
        due_date = datetime.now() + timedelta(days=60)  # Future due date
        
        payload = {
            "subscriber_id": subscriber_id,
            "line_items": [
                {
                    "plan_id": plan_id,
                    "base_amount": 500,
                    "discount": 0,
                    "service_start_date": service_start.isoformat() + "Z",
                    "service_end_date": service_end.isoformat() + "Z",
                    "is_custom": False
                }
            ],
            "due_date": due_date.isoformat() + "Z"
        }
        
        log_info(f"Creating invoice with payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{API_URL}/operator/invoices",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200 or response.status_code == 201:
            invoice = response.json()
            log_success(f"Invoice created successfully: #{invoice.get('invoice_number')}")
            log_info(f"Invoice ID: {invoice.get('id')}")
            log_info(f"Final Amount: {invoice.get('final_amount')}")
            log_info(f"Line Items Count: {len(invoice.get('line_items', []))}")
            
            return invoice
        else:
            log_error(f"Failed to create invoice: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        log_error(f"Failed to create invoice: {str(e)}")
        return None

def verify_previous_pending_feature(invoice, pending_invoices):
    """Verify that the Previous Pending feature is working correctly"""
    print("\n" + "="*80)
    print("TEST 7: Verify Previous Pending Feature")
    print("="*80)
    
    if not invoice:
        log_error("No invoice to verify")
        return False
    
    line_items = invoice.get('line_items', [])
    log_info(f"Invoice has {len(line_items)} line items")
    
    # Check if there's a "Previous Pending" line item
    previous_pending_item = None
    for item in line_items:
        log_info(f"  - Line Item: {item.get('plan_name')} | Amount: {item.get('final_amount')} | Custom: {item.get('is_custom')}")
        if item.get('plan_name') == 'Previous Pending':
            previous_pending_item = item
    
    if not pending_invoices:
        # No pending invoices, so there should be NO "Previous Pending" line item
        if previous_pending_item:
            log_error("Found 'Previous Pending' line item when there were no pending invoices!")
            return False
        else:
            log_success("Correctly no 'Previous Pending' line item (no prior pending invoices)")
            return True
    else:
        # There were pending invoices, so there SHOULD be a "Previous Pending" line item
        if not previous_pending_item:
            log_error("Missing 'Previous Pending' line item despite having pending invoices!")
            log_error(f"Expected to find pending invoices: {[inv.get('invoice_number') for inv in pending_invoices]}")
            return False
        
        log_success("Found 'Previous Pending' line item")
        
        # Verify the description contains invoice numbers
        description = previous_pending_item.get('description', '')
        log_info(f"Description: {description}")
        
        # Check if description contains comma-separated invoice numbers
        expected_invoice_numbers = [inv.get('invoice_number') for inv in pending_invoices]
        log_info(f"Expected invoice numbers in description: {expected_invoice_numbers}")
        
        all_found = True
        for inv_num in expected_invoice_numbers:
            if inv_num not in description:
                log_error(f"Invoice number {inv_num} not found in description")
                all_found = False
        
        if all_found:
            log_success("All pending invoice numbers found in description")
        
        # Verify the amount
        expected_pending_amount = sum(inv.get('final_amount', 0) for inv in pending_invoices)
        actual_pending_amount = previous_pending_item.get('final_amount', 0)
        
        log_info(f"Expected pending amount: {expected_pending_amount}")
        log_info(f"Actual pending amount in line item: {actual_pending_amount}")
        
        if abs(expected_pending_amount - actual_pending_amount) < 0.01:  # Allow small floating point differences
            log_success("Previous pending amount matches")
        else:
            log_error(f"Amount mismatch! Expected {expected_pending_amount}, got {actual_pending_amount}")
            all_found = False
        
        # Verify final_amount includes previous pending
        plan_items_total = sum(item.get('final_amount', 0) for item in line_items if item.get('plan_name') != 'Previous Pending')
        expected_final = plan_items_total + expected_pending_amount
        actual_final = invoice.get('final_amount', 0)
        
        log_info(f"Plan items total: {plan_items_total}")
        log_info(f"Expected final amount (plan + pending): {expected_final}")
        log_info(f"Actual final amount: {actual_final}")
        
        if abs(expected_final - actual_final) < 0.01:
            log_success("Final amount correctly includes previous pending")
        else:
            log_error(f"Final amount mismatch! Expected {expected_final}, got {actual_final}")
            all_found = False
        
        return all_found

def main():
    """Main test flow"""
    print("\n" + "="*80)
    print("PREVIOUS PENDING INVOICE FEATURE TEST")
    print("="*80)
    
    # Test 1: Health check
    if not test_health():
        log_error("Backend health check failed. Aborting tests.")
        return
    
    # Test 2: Login
    token = login_operator()
    if not token:
        log_error("Login failed. Aborting tests.")
        return
    
    # Test 3: Get subscribers
    subscribers = get_subscribers(token)
    if not subscribers:
        log_error("No subscribers found. Cannot proceed with tests.")
        return
    
    # Test 4: Get plans
    plans = get_plans(token)
    if not plans:
        log_error("No plans found. Cannot proceed with tests.")
        return
    
    # Select first subscriber and plan
    subscriber = subscribers[0]
    plan = plans[0]
    subscriber_id = subscriber.get('id')
    plan_id = plan.get('id')
    
    log_info(f"\nUsing Subscriber: {subscriber.get('name')} (ID: {subscriber_id})")
    log_info(f"Using Plan: {plan.get('name')} (ID: {plan_id})")
    
    # Test 5: Get existing invoices for subscriber
    all_invoices, pending_invoices = get_invoices_for_subscriber(token, subscriber_id)
    
    # Test 6: Create new invoice
    new_invoice = create_invoice(token, subscriber_id, plan_id)
    if not new_invoice:
        log_error("Failed to create invoice. Cannot verify feature.")
        return
    
    # Test 7: Verify Previous Pending feature
    success = verify_previous_pending_feature(new_invoice, pending_invoices)
    
    # Final summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if success:
        log_success("✓ All tests passed! Previous Pending feature is working correctly.")
    else:
        log_error("✗ Some tests failed. Please review the output above.")
    
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
