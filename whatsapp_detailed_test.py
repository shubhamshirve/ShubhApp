#!/usr/bin/env python3
"""
Additional WhatsApp Test with specific phone numbers and error logging verification
"""

import requests
import json
from datetime import datetime

# Test Configuration
BACKEND_URL = "https://settlement-analyzer-2.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"

def get_admin_token():
    """Get admin token for testing."""
    response = requests.post(f"{BACKEND_URL}/auth/login", 
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def test_specific_whatsapp_scenarios():
    """Test specific WhatsApp scenarios as requested in review."""
    
    print("🧪 ADDITIONAL WHATSAPP SCENARIO TESTING")
    print("=" * 60)
    
    token = get_admin_token()
    if not token:
        print("❌ Could not get admin token")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: Check if WhatsApp config is saved
    print("\n1️⃣ Verifying WhatsApp configuration status...")
    config_response = requests.get(f"{BACKEND_URL}/admin/whatsapp-config", headers=headers)
    if config_response.status_code == 200:
        config = config_response.json()
        print(f"✅ WhatsApp configured: {config.get('is_configured', False)}")
        print(f"   Phone Number ID: {config.get('phone_number_id', 'Not set')}")
        print(f"   Business Account: {config.get('business_account_id', 'Not set')}")
        print(f"   Token Preview: {config.get('access_token_preview', 'Not set')}")
    else:
        print(f"❌ Could not get WhatsApp config: {config_response.status_code}")
    
    # Test 2: Test different phone number formats
    test_numbers = [
        "919876543210",  # Original test number
        "+919876543210", # With country code prefix
        "9876543210",    # Without country code
        "1234567890",    # US format
    ]
    
    print(f"\n2️⃣ Testing WhatsApp with different phone numbers...")
    
    for i, phone in enumerate(test_numbers, 1):
        print(f"\n   Test {i}: Phone number '{phone}'")
        test_response = requests.post(f"{BACKEND_URL}/admin/whatsapp-test", 
            json={"phone_number": phone}, headers=headers)
        
        print(f"   Status: {test_response.status_code}")
        if test_response.status_code in [200, 400, 500]:
            try:
                data = test_response.json()
                print(f"   Response: {data.get('detail', data)}")
            except:
                print(f"   Raw response: {test_response.text[:100]}...")
        
        # Small delay to avoid rate limiting
        import time
        time.sleep(0.5)
    
    # Test 3: Check error logs after WhatsApp tests
    print(f"\n3️⃣ Checking error logs after WhatsApp tests...")
    logs_response = requests.get(f"{BACKEND_URL}/admin/error-logs", headers=headers)
    if logs_response.status_code == 200:
        logs_data = logs_response.json()
        total_logs = logs_data.get("total", 0)
        recent_logs = logs_data.get("logs", [])
        
        print(f"   Total error logs in system: {total_logs}")
        print(f"   Recent logs retrieved: {len(recent_logs)}")
        
        # Look for WhatsApp related logs
        whatsapp_logs = [log for log in recent_logs 
                        if "whatsapp" in log.get("message", "").lower() 
                        or "whatsapp" in log.get("endpoint", "").lower()]
        
        print(f"   WhatsApp-related logs: {len(whatsapp_logs)}")
        
        if whatsapp_logs:
            print(f"\n   📋 Recent WhatsApp Error Log Details:")
            for i, log in enumerate(whatsapp_logs[:3], 1):  # Show first 3
                print(f"      {i}. Type: {log.get('error_type', 'Unknown')}")
                print(f"         Endpoint: {log.get('endpoint', 'Unknown')}")
                print(f"         Status: {log.get('status_code', 'Unknown')}")
                print(f"         Message: {log.get('message', 'No message')[:80]}...")
                print(f"         Time: {log.get('created_at', 'Unknown')}")
                print()
    else:
        print(f"   ❌ Could not get error logs: {logs_response.status_code}")

    # Test 4: Test error log filtering 
    print(f"\n4️⃣ Testing error log filtering...")
    
    # Test search by WhatsApp
    search_response = requests.get(f"{BACKEND_URL}/admin/error-logs?search=whatsapp", headers=headers)
    if search_response.status_code == 200:
        search_data = search_response.json()
        print(f"   Search 'whatsapp' found: {len(search_data.get('logs', []))} logs")
    
    # Test filter by error type
    filter_response = requests.get(f"{BACKEND_URL}/admin/error-logs?error_type=whatsapp_error", headers=headers)
    if filter_response.status_code == 200:
        filter_data = filter_response.json()
        print(f"   Filter 'whatsapp_error' found: {len(filter_data.get('logs', []))} logs")

    print(f"\n✅ Additional WhatsApp testing completed!")

if __name__ == "__main__":
    test_specific_whatsapp_scenarios()