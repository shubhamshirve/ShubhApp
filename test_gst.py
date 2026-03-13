#!/usr/bin/env python3
"""Test GST validation with better debugging"""

import requests
import json

BACKEND_URL = "https://settlement-analyzer-2.preview.emergentagent.com/api"

def test_gst_validation():
    # Login as operator2 (Basic plan)
    login_data = {
        "email": "sagar@sagarbroadband.com",
        "password": "operator123"
    }
    response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
    
    if response.status_code == 200:
        token = response.json().get('access_token')
        print(f"✅ Operator2 login successful")
        
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        
        # Step 1: Clear GST settings
        print("\n1. Clearing GST settings...")
        clear_data = {"gst_number": "", "charge_gst": False}
        response = requests.put(f"{BACKEND_URL}/operator/profile", headers=headers, json=clear_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Step 2: Try to enable GST without GSTIN
        print("\n2. Trying to enable GST without GSTIN...")
        enable_gst_data = {"charge_gst": True}
        response = requests.put(f"{BACKEND_URL}/operator/profile", headers=headers, json=enable_gst_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Step 3: Try with valid GSTIN
        print("\n3. Trying with valid GSTIN...")
        valid_gst_data = {"gst_number": "27AABCS5678E1ZP", "charge_gst": True}
        response = requests.put(f"{BACKEND_URL}/operator/profile", headers=headers, json=valid_gst_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    else:
        print(f"❌ Login failed: {response.status_code}")

if __name__ == "__main__":
    test_gst_validation()