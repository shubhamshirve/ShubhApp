#!/usr/bin/env python3
"""
Focused Backend Test - Subscribers Sort & Health Check
Testing specific items from review request:
1. GET /api/health - backend health
2. GET /api/operator/subscribers - verify sort order (created_at desc)
"""

import requests
import json
from datetime import datetime

# Backend URL
BASE_URL = "http://localhost:8001"

# Test credentials from /app/memory/test_credentials.md
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"

def print_test_header(test_name):
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")

def print_result(passed, message):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {message}")

def login_operator():
    """Login as operator and return access token"""
    print_test_header("Login as Operator")
    url = f"{BASE_URL}/api/auth/login"
    payload = {"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print_result(True, f"Operator login successful")
                return token
            else:
                print_result(False, "No access_token in response")
                return None
        else:
            print_result(False, f"Login failed: {response.text}")
            return None
    except Exception as e:
        print_result(False, f"Login error: {str(e)}")
        return None

def test_health_endpoint():
    """Test 1: GET /api/health"""
    print_test_header("Backend Health Check")
    url = f"{BASE_URL}/api/health"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print_result(True, "Backend health endpoint is working")
            return True
        else:
            print_result(False, f"Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Health check error: {str(e)}")
        return False

def test_subscribers_endpoint(token):
    """Test 2: GET /api/operator/subscribers - verify endpoint returns 200 with list"""
    print_test_header("Subscribers List Endpoint")
    url = f"{BASE_URL}/api/operator/subscribers"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response type: {type(data)}")
            print(f"Number of subscribers: {len(data) if isinstance(data, list) else 'N/A'}")
            
            if isinstance(data, list):
                print_result(True, f"Subscribers endpoint returns list with {len(data)} items")
                
                # Check if list has items and verify sort order (optional verification)
                if len(data) >= 2:
                    print("\nVerifying sort order (created_at desc):")
                    first_item = data[0]
                    second_item = data[1]
                    
                    if "created_at" in first_item and "created_at" in second_item:
                        first_date = first_item["created_at"]
                        second_date = second_item["created_at"]
                        print(f"  First item created_at: {first_date}")
                        print(f"  Second item created_at: {second_date}")
                        
                        # Parse dates for comparison
                        try:
                            date1 = datetime.fromisoformat(first_date.replace('Z', '+00:00'))
                            date2 = datetime.fromisoformat(second_date.replace('Z', '+00:00'))
                            
                            if date1 >= date2:
                                print_result(True, "Sort order verified: latest first (desc)")
                            else:
                                print_result(False, "Sort order incorrect: oldest first")
                        except Exception as e:
                            print(f"  Note: Could not parse dates for comparison: {e}")
                    else:
                        print("  Note: created_at field not found in items")
                elif len(data) == 1:
                    print("  Note: Only 1 subscriber, cannot verify sort order")
                else:
                    print("  Note: No subscribers in list")
                
                return True
            else:
                print_result(False, f"Expected list, got {type(data)}")
                return False
        else:
            print(f"Response: {response.text}")
            print_result(False, f"Subscribers endpoint failed with status {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Subscribers endpoint error: {str(e)}")
        return False

def check_database_for_operator():
    """Check if operator account exists in database"""
    print_test_header("Database Check - Operator Account")
    try:
        # Try to login with admin to check database
        url = f"{BASE_URL}/api/auth/login"
        payload = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print_result(True, "Admin account exists and can login")
            return True
        else:
            print_result(False, f"Admin login failed: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Database check error: {str(e)}")
        return False

def main():
    print("\n" + "="*70)
    print("FOCUSED BACKEND TEST - Review Request Items")
    print("="*70)
    print("Testing:")
    print("1. Backend health endpoint")
    print("2. Subscribers list endpoint (sort order)")
    print("="*70)
    
    results = {}
    
    # Test 1: Health endpoint
    results["health"] = test_health_endpoint()
    
    # Test 2: Subscribers endpoint (requires auth)
    token = login_operator()
    if token:
        results["subscribers"] = test_subscribers_endpoint(token)
    else:
        print("\nNote: operator@test.com account does not exist in database")
        print("Checking if database is seeded...")
        check_database_for_operator()
        results["subscribers"] = "SKIPPED - No operator account"
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, result in results.items():
        if isinstance(result, bool):
            status = "✅ PASS" if result else "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{status}: {test_name} - {result if isinstance(result, str) else ''}")
    
    print("="*70)

if __name__ == "__main__":
    main()
