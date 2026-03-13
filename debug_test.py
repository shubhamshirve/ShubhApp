#!/usr/bin/env python3
"""Debug script to investigate the 500 errors"""

import requests
import json

BACKEND_URL = "https://settlement-analyzer-2.preview.emergentagent.com/api"

def test_operator_plans():
    # Login as operator1
    login_data = {
        "email": "venkat@krishnacable.in",
        "password": "operator123"
    }
    response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
    
    if response.status_code == 200:
        token = response.json().get('access_token')
        print(f"✅ Operator1 login successful")
        
        # Test plans endpoint
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        response = requests.get(f"{BACKEND_URL}/operator/plans", headers=headers)
        
        print(f"Plans endpoint: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Test GST validation
        gst_data = {"charge_gst": True}
        response = requests.put(f"{BACKEND_URL}/operator/profile", headers=headers, json=gst_data)
        print(f"GST validation: {response.status_code}")
        print(f"Response: {response.text}")
    else:
        print(f"❌ Login failed: {response.status_code}")

if __name__ == "__main__":
    test_operator_plans()