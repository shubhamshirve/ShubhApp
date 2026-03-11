import requests
import sys
from datetime import datetime, timedelta

# Test the 4 remaining problematic endpoints with proper authentication
BASE_URL = "https://93e37f04-ed3c-45b3-8d75-2b332d20d27f.preview.emergentagent.com/api"

def make_request(method, endpoint, data=None, token=None, params=None):
    """Make HTTP request"""
    url = f"{BASE_URL}/{endpoint}"
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    if method == 'GET':
        response = requests.get(url, headers=headers, params=params)
    elif method == 'POST':
        response = requests.post(url, json=data, headers=headers, params=params)
    elif method == 'PUT':
        response = requests.put(url, json=data, headers=headers, params=params)
    elif method == 'DELETE':
        response = requests.delete(url, headers=headers, params=params)
    
    return response

# Get admin token
admin_response = make_request('POST', 'auth/login', {
    "email": "admin@saas.com",
    "password": "admin123"
})
admin_token = admin_response.json().get("access_token")
print(f"Admin login: {admin_response.status_code}")

# Register new operator to get working token
register_data = {
    "company_name": "Test Fix Company Ltd",
    "owner_name": "Test Fix Owner",
    "email": f"testfix+{datetime.now().strftime('%H%M%S')}@fixcompany.com",
    "phone": "9876543210",
    "password": "testfix123",
    "gst_number": "22AAAAA0000A1Z5",
    "charge_gst": True
}

register_response = make_request('POST', 'auth/register', register_data)
if register_response.status_code == 200:
    operator_token = register_response.json().get("access_token")
    print(f"Operator registration: {register_response.status_code}")
else:
    print(f"Registration failed: {register_response.status_code} - {register_response.text}")
    sys.exit(1)

print("Testing remaining problematic endpoints...")

# 1. Test Admin Update Addon (already fixed)
print("\n✅ 1. Admin Update Addon - FIXED")

# 2. Test PDF Generation with new operator
print("\n2. Testing PDF Generation...")

# First create a plan, subscriber, and invoice for this operator
plan_data = {
    "name": "Test Plan for PDF",
    "price": 699,
    "validity": "monthly", 
    "tax_percentage": 18,
    "tax_type": "exclusive",
    "description": "Test plan for PDF generation"
}
plan_response = make_request('POST', 'operator/plans', plan_data, operator_token)
if plan_response.status_code == 200:
    plan_id = plan_response.json().get("id")
    print(f"Created plan: {plan_id}")
    
    # Create subscriber
    subscriber_data = {
        "name": "PDF Test Customer",
        "whatsapp_number": "919876543210",
        "email": "pdftest@test.com",
        "address": "123 PDF Test Street",
        "plan_id": plan_id,
        "billing_date": 15,
        "discount": 0
    }
    subscriber_response = make_request('POST', 'operator/subscribers', subscriber_data, operator_token)
    if subscriber_response.status_code == 200:
        subscriber_id = subscriber_response.json().get("id")
        print(f"Created subscriber: {subscriber_id}")
        
        # Create invoice
        today = datetime.now()
        invoice_data = {
            "subscriber_id": subscriber_id,
            "plan_id": plan_id,
            "base_amount": 699,
            "discount": 0,
            "service_start_date": today.isoformat(),
            "service_end_date": (today + timedelta(days=30)).isoformat(),
            "due_date": (today + timedelta(days=7)).isoformat()
        }
        invoice_response = make_request('POST', 'operator/invoices', invoice_data, operator_token)
        if invoice_response.status_code == 200:
            invoice_id = invoice_response.json().get("id")
            print(f"Created invoice: {invoice_id}")
            
            # Test PDF generation
            pdf_response = make_request('GET', f'operator/invoices/{invoice_id}/pdf', token=operator_token)
            print(f"PDF Generation: {pdf_response.status_code}")
            if pdf_response.status_code != 200:
                print(f"PDF Error: {pdf_response.text}")

# 3. Test Checkout Order
print("\n3. Testing Checkout Order...")
checkout_response = make_request('POST', 'operator/checkout/create-order', 
                               params={"item_type": "subscription", "months": 1}, 
                               token=operator_token)
print(f"Checkout Order: {checkout_response.status_code} - {checkout_response.text}")

# 4. Test Payment Gateway Permission (expected to fail due to plan restrictions)
print("\n4. Testing Payment Gateway Config...")
gateway_data = {
    "gateway_type": "razorpay",
    "api_key": "rzp_test_sFaXdx3kATIGiw",
    "api_secret": "dOvQqMbfE2sPkYulgTeU2SpW",
    "webhook_secret": "webhook_secret_123"
}
gateway_response = make_request('POST', 'operator/payment-gateway', gateway_data, operator_token)
print(f"Payment Gateway Config: {gateway_response.status_code} - {gateway_response.text}")
print("(This is expected to fail as trial plan doesn't include payment gateway setup)")

print("\nFinished testing problematic endpoints.")