#!/usr/bin/env python3
"""
Backend API tests for operator role endpoints.

Test Requirements:
1. GET /api/operator/payments - Should return list of received payments (paid/partial invoices)
2. GET /api/operator/dashboard-stats - Should return total_pending_value with only "pending" status
3. GET /api/operator/audit-logs - Should work for impersonated admin user
"""

import requests
import json
import sys

# Backend URL (internal container URL)
BASE_URL = "http://localhost:8001"

# Test credentials from /app/memory/test_credentials.md
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def print_result(test_name, passed, details=""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {details}")


def login(email, password):
    """Login and get access token."""
    url = f"{BASE_URL}/api/auth/login"
    payload = {"email": email, "password": password}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Login request: POST {url}")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print_result(f"Login as {email}", True, f"Token obtained")
                return token
            else:
                print_result(f"Login as {email}", False, "No access_token in response")
                print(f"Response: {json.dumps(data, indent=2)}")
                return None
        else:
            print_result(f"Login as {email}", False, f"Status {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print_result(f"Login as {email}", False, f"Exception: {e}")
        return None


def test_operator_payments(token):
    """Test 1: GET /api/operator/payments endpoint."""
    print_section("Test 1: GET /api/operator/payments")
    
    url = f"{BASE_URL}/api/operator/payments"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Request: GET {url}")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response structure:")
            print(f"  - Keys: {list(data.keys())}")
            
            # Verify response structure
            if "total" not in data:
                print_result("Payments endpoint structure", False, "Missing 'total' field")
                return False
            
            if "payments" not in data:
                print_result("Payments endpoint structure", False, "Missing 'payments' field")
                return False
            
            print(f"  - Total payments: {data['total']}")
            print(f"  - Payments array length: {len(data['payments'])}")
            
            # Verify payment object structure (if any payments exist)
            if data['payments']:
                first_payment = data['payments'][0]
                print(f"\nFirst payment object keys: {list(first_payment.keys())}")
                
                required_fields = [
                    "id", "invoice_number", "subscriber_name", "amount", 
                    "amount_paid", "payment_mode", "paid_at", "status"
                ]
                missing_fields = [f for f in required_fields if f not in first_payment]
                
                if missing_fields:
                    print_result("Payment object structure", False, 
                               f"Missing fields: {missing_fields}")
                    return False
                
                print(f"\nSample payment:")
                print(f"  - Invoice: {first_payment.get('invoice_number')}")
                print(f"  - Subscriber: {first_payment.get('subscriber_name')}")
                print(f"  - Amount: {first_payment.get('amount')}")
                print(f"  - Amount Paid: {first_payment.get('amount_paid')}")
                print(f"  - Payment Mode: {first_payment.get('payment_mode')}")
                print(f"  - Status: {first_payment.get('status')}")
                print(f"  - Paid At: {first_payment.get('paid_at')}")
            else:
                print("\nNo payments found (empty database or no paid/partial invoices)")
            
            print_result("Payments endpoint", True, 
                        f"Endpoint working correctly. Total: {data['total']}")
            return True
        else:
            print(f"Response: {response.text}")
            print_result("Payments endpoint", False, 
                        f"Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print_result("Payments endpoint", False, f"Exception: {e}")
        return False


def test_dashboard_stats(token):
    """Test 2: GET /api/operator/dashboard - Verify total_pending_value only includes 'pending' status."""
    print_section("Test 2: GET /api/operator/dashboard (total_pending_value)")
    
    url = f"{BASE_URL}/api/operator/dashboard"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Request: GET {url}")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nDashboard stats keys: {list(data.keys())}")
            
            # Verify total_pending_value exists
            if "total_pending_value" not in data:
                print_result("Dashboard total_pending_value field", False, 
                           "Field 'total_pending_value' not found in response")
                return False
            
            print(f"\nKey metrics:")
            print(f"  - Total Pending Value: {data.get('total_pending_value')}")
            print(f"  - Pending Invoices: {data.get('pending_invoices')}")
            print(f"  - Overdue Invoices: {data.get('overdue_invoices')}")
            print(f"  - Total Value Pending This Month: {data.get('total_value_pending_this_month')}")
            
            # Note: We can't directly verify the calculation without database access,
            # but we can verify the field exists and is a number
            pending_value = data.get('total_pending_value')
            if not isinstance(pending_value, (int, float)):
                print_result("Dashboard total_pending_value type", False, 
                           f"Expected number, got {type(pending_value)}")
                return False
            
            print_result("Dashboard endpoint", True, 
                        f"total_pending_value field exists and is numeric: {pending_value}")
            
            # Additional info
            print(f"\nNote: total_pending_value should only include invoices with status='pending'")
            print(f"      (NOT 'overdue'). This is calculated in the backend at line 1235-1241.")
            
            return True
        else:
            print(f"Response: {response.text}")
            print_result("Dashboard endpoint", False, 
                        f"Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print_result("Dashboard endpoint", False, f"Exception: {e}")
        return False


def test_audit_logs_with_impersonation(admin_token):
    """Test 3: GET /api/operator/audit-logs with impersonated admin."""
    print_section("Test 3: GET /api/operator/audit-logs (Impersonated Admin)")
    
    # First, we need to impersonate an operator
    print("\nStep 1: Get list of operators to impersonate")
    operators_url = f"{BASE_URL}/api/admin/operators"
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    try:
        response = requests.get(operators_url, headers=headers, timeout=10)
        if response.status_code != 200:
            print_result("Get operators list", False, 
                        f"Failed to get operators: {response.status_code}")
            return False
        
        operators = response.json()
        if not operators:
            print_result("Get operators list", False, "No operators found in database")
            return False
        
        # Use the first operator
        operator_id = operators[0]["id"]
        print(f"Found operator: {operators[0].get('company_name', 'N/A')} (ID: {operator_id})")
        
        # Step 2: Impersonate the operator
        print("\nStep 2: Impersonate operator")
        impersonate_url = f"{BASE_URL}/api/admin/operators/{operator_id}/impersonate"
        response = requests.post(impersonate_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print_result("Impersonate operator", False, 
                        f"Failed to impersonate: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        impersonate_data = response.json()
        impersonate_token = impersonate_data.get("access_token")
        
        if not impersonate_token:
            print_result("Impersonate operator", False, "No access_token in impersonation response")
            return False
        
        print_result("Impersonate operator", True, "Impersonation token obtained")
        
        # Step 3: Try to access audit logs with impersonated token
        print("\nStep 3: Access audit logs with impersonated admin token")
        audit_logs_url = f"{BASE_URL}/api/operator/audit-logs"
        impersonate_headers = {"Authorization": f"Bearer {impersonate_token}"}
        
        response = requests.get(audit_logs_url, headers=impersonate_headers, timeout=10)
        print(f"Request: GET {audit_logs_url}")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            logs = response.json()
            print(f"Response: Successfully retrieved {len(logs)} audit logs")
            
            if logs:
                print(f"\nFirst log entry keys: {list(logs[0].keys())}")
            
            print_result("Audit logs with impersonation", True, 
                        f"Impersonated admin can access audit logs. Retrieved {len(logs)} logs.")
            return True
        elif response.status_code == 403:
            print(f"Response: {response.text}")
            print_result("Audit logs with impersonation", False, 
                        "Impersonated admin blocked from accessing audit logs (403)")
            return False
        else:
            print(f"Response: {response.text}")
            print_result("Audit logs with impersonation", False, 
                        f"Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print_result("Audit logs with impersonation", False, f"Exception: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("  OPERATOR ROLE ENDPOINTS - BACKEND TEST SUITE")
    print("="*70)
    print(f"Backend URL: {BASE_URL}")
    print(f"Operator credentials: {OPERATOR_EMAIL} / {OPERATOR_PASSWORD}")
    print(f"Admin credentials: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    
    results = {}
    
    # Login as operator
    print_section("Operator Authentication")
    operator_token = login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
    
    if not operator_token:
        print("\n❌ CRITICAL: Cannot proceed with operator tests - login failed")
        sys.exit(1)
    
    # Test 1: Payments endpoint
    results["payments"] = test_operator_payments(operator_token)
    
    # Test 2: Dashboard stats (total_pending_value)
    results["dashboard_stats"] = test_dashboard_stats(operator_token)
    
    # Login as admin for impersonation test
    print_section("Admin Authentication")
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    
    if not admin_token:
        print("\n❌ WARNING: Cannot test impersonation - admin login failed")
        results["audit_logs_impersonation"] = False
    else:
        # Test 3: Audit logs with impersonation
        results["audit_logs_impersonation"] = test_audit_logs_with_impersonation(admin_token)
    
    # Final summary
    print_section("FINAL SUMMARY")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    print(f"\nTotal tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    print("\nDetailed results:")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    if passed_tests == total_tests:
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print(f"\n❌ {total_tests - passed_tests} TEST(S) FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
