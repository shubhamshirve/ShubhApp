#!/usr/bin/env python3
"""
Quick test to check operator GST configuration and fix the tax calculation issue
"""

import requests
import json

# Configuration
BASE_URL = "https://changelog-review-13.preview.emergentagent.com/api"
OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"

def main():
    session = requests.Session()
    
    # Login
    response = session.post(f"{BASE_URL}/auth/login", json={
        "email": OPERATOR_EMAIL,
        "password": OPERATOR_PASSWORD
    })
    
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return
    
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Get operator profile
    response = session.get(f"{BASE_URL}/operator/profile")
    if response.status_code == 200:
        operator = response.json()
        print("Current operator GST settings:")
        print(f"charge_gst: {operator.get('charge_gst')}")
        print(f"gst_number: {operator.get('gst_number')}")
        
        # If GST is not enabled, enable it
        if not operator.get('charge_gst') or not operator.get('gst_number'):
            print("\nEnabling GST for operator...")
            update_data = {
                "charge_gst": True,
                "gst_number": "27ABCDE1234F1Z5"  # Valid GST format
            }
            
            response = session.put(f"{BASE_URL}/operator/profile", json=update_data)
            if response.status_code == 200:
                print("GST enabled successfully!")
                updated = response.json()
                print(f"Updated charge_gst: {updated.get('charge_gst')}")
                print(f"Updated gst_number: {updated.get('gst_number')}")
            else:
                print(f"Failed to update GST: {response.status_code} - {response.text}")
        else:
            print("GST is already properly configured")
    else:
        print(f"Failed to get operator profile: {response.status_code}")

if __name__ == "__main__":
    main()