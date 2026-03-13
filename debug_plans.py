#!/usr/bin/env python3
"""Debug script to check operator plans directly from MongoDB"""

import requests
import json

BACKEND_URL = "https://settlement-analyzer-2.preview.emergentagent.com/api"

def test_debug_plans():
    # Login as operator1
    login_data = {
        "email": "venkat@krishnacable.in",
        "password": "operator123"
    }
    response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
    
    if response.status_code == 200:
        token = response.json().get('access_token')
        print(f"✅ Operator1 login successful")
        
        # Test operator profile to get operator_id
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        response = requests.get(f"{BACKEND_URL}/operator/profile", headers=headers)
        
        if response.status_code == 200:
            profile = response.json()
            operator_id = profile['id']
            print(f"Operator ID: {operator_id}")
            
            # Test creating a plan first
            plan_data = {
                "name": "Test Monthly Plan",
                "price": 500.0,
                "validity": "monthly",
                "tax_percentage": 18.0,
                "tax_type": "exclusive",
                "description": "Test plan for debugging"
            }
            
            response = requests.post(f"{BACKEND_URL}/operator/plans", headers=headers, json=plan_data)
            print(f"Create plan: {response.status_code}")
            if response.status_code == 200:
                print(f"Plan created successfully")
            else:
                print(f"Plan creation response: {response.text}")
                
            # Now try to get plans again
            response = requests.get(f"{BACKEND_URL}/operator/plans", headers=headers)
            print(f"Get plans after creation: {response.status_code}")
            print(f"Response: {response.text}")
        else:
            print(f"❌ Profile failed: {response.status_code}")
    else:
        print(f"❌ Login failed: {response.status_code}")

if __name__ == "__main__":
    test_debug_plans()