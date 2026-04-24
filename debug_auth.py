#!/usr/bin/env python3
"""
Debug authentication issue for admin user
"""

import requests
import json

# Configuration
BASE_URL = "https://changelog-review-13.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"

def debug_auth():
    session = requests.Session()
    
    print("=== DEBUGGING ADMIN AUTHENTICATION ===")
    
    # Step 1: Login
    print("\n1. Attempting admin login...")
    login_response = session.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    print(f"Login Status: {login_response.status_code}")
    print(f"Login Response: {login_response.text}")
    
    if login_response.status_code != 200:
        print("❌ Login failed!")
        return
    
    login_data = login_response.json()
    access_token = login_data.get("access_token")
    print(f"Access Token: {access_token[:50]}..." if access_token else "No token received")
    
    # Step 2: Check user info from login response
    user_info = login_data.get("user", {})
    print(f"User Role: {user_info.get('role')}")
    print(f"User Email: {user_info.get('email')}")
    print(f"User ID: {user_info.get('id')}")
    
    # Step 3: Test with Bearer token
    print("\n2. Testing admin dashboard with Bearer token...")
    headers = {"Authorization": f"Bearer {access_token}"}
    dashboard_response = session.get(f"{BASE_URL}/admin/dashboard", headers=headers)
    
    print(f"Dashboard Status: {dashboard_response.status_code}")
    print(f"Dashboard Response: {dashboard_response.text}")
    
    # Step 4: Test with cookies (if any were set)
    print("\n3. Testing admin dashboard with session cookies...")
    dashboard_response_cookies = session.get(f"{BASE_URL}/admin/dashboard")
    
    print(f"Dashboard Status (cookies): {dashboard_response_cookies.status_code}")
    print(f"Dashboard Response (cookies): {dashboard_response_cookies.text}")
    
    # Step 5: Check cookies
    print(f"\n4. Session cookies: {session.cookies}")

if __name__ == "__main__":
    debug_auth()