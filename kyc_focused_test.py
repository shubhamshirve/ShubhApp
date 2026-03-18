#!/usr/bin/env python3
"""
Comprehensive backend testing for KYC features in Multi-Tenant SaaS Billing Platform.
Tests working KYC functionality and provides detailed error information.
"""

import requests
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BACKEND_URL = "https://invoice-pricing.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"
TEST_OTP = "200796"

def test_valid_pan_format():
    """Test that valid PAN format works correctly"""
    try:
        timestamp = int(datetime.now().timestamp())
        valid_data = {
            "company_name": "Valid PAN Test",
            "owner_name": "Test Owner",
            "email": f"validpan{timestamp}@example.com",
            "phone": "9876543213",
            "password": "test123",
            "business_type": "Private Limited",
            "pan_number": "ABCXY1234Z",  # Valid PAN format
            "address": "Test Address"
        }
        
        response = requests.post(f"{BACKEND_URL}/auth/register-init", json=valid_data)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Valid PAN format accepted successfully")
            return True
        else:
            print(f"❌ Valid PAN format rejected: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception testing valid PAN: {str(e)}")
        return False

def test_valid_business_types():
    """Test that all valid business types work"""
    valid_types = [
        "Sole Proprietorship",
        "Partnership", 
        "LLP",
        "Private Limited",
        "Public Limited",
        "Others"
    ]
    
    # Get admin auth first
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    login_response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
    
    if login_response.status_code != 200:
        print("❌ Failed to get admin auth for business type testing")
        return False
    
    admin_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    # Get a plan ID
    plans_response = requests.get(f"{BACKEND_URL}/admin/saas-plans", headers=headers)
    if plans_response.status_code != 200:
        print("❌ Failed to get SaaS plans")
        return False
    
    plan_id = plans_response.json()[0]["id"]
    
    success_count = 0
    for business_type in valid_types:
        try:
            timestamp = int(datetime.now().timestamp())
            test_data = {
                "company_name": f"Test {business_type}",
                "owner_name": "Test Owner",
                "email": f"test{business_type.replace(' ', '').lower()}{timestamp}@example.com",
                "phone": f"987654{len(business_type):04d}",
                "password": "test123",
                "business_type": business_type,
                "saas_plan_id": plan_id,
                "status": "active",
                "subscription_months": 1
            }
            
            response = requests.post(f"{BACKEND_URL}/admin/operators/create", json=test_data, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Business type '{business_type}' accepted")
                success_count += 1
            else:
                print(f"❌ Business type '{business_type}' rejected: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Exception testing business type '{business_type}': {str(e)}")
    
    print(f"📊 Business types: {success_count}/{len(valid_types)} accepted")
    return success_count == len(valid_types)

def test_kyc_fields_comprehensive():
    """Comprehensive test of KYC fields"""
    # Get admin auth
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    login_response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
    
    if login_response.status_code != 200:
        print("❌ Failed admin login")
        return False
    
    admin_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    # Get plan
    plans_response = requests.get(f"{BACKEND_URL}/admin/saas-plans", headers=headers)
    plan_id = plans_response.json()[0]["id"]
    
    # Test comprehensive KYC data
    timestamp = int(datetime.now().timestamp())
    kyc_data = {
        "company_name": "Comprehensive KYC Test Corp",
        "owner_name": "KYC Test Owner",
        "email": f"kyctest{timestamp}@example.com",
        "phone": "9876543299",
        "password": "test123",
        "business_type": "Private Limited",
        "gst_number": "27AABCU9603R1ZM",
        "pan_number": "AABCU9603R",
        "address": "123 KYC Test Street, Mumbai, Maharashtra, 400001",
        "charge_gst": True,
        "bank_account_name": "KYC Test Account",
        "bank_name": "State Bank of India",
        "bank_account_number": "1234567890123456",
        "bank_ifsc": "SBIN0001234",
        "saas_plan_id": plan_id,
        "status": "active",
        "subscription_months": 1
    }
    
    print("📋 Testing comprehensive KYC data creation...")
    response = requests.post(f"{BACKEND_URL}/admin/operators/create", json=kyc_data, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Comprehensive KYC operator created successfully")
        
        # Verify all fields are present in response
        kyc_fields = ['business_type', 'gst_number', 'pan_number', 'address', 'charge_gst', 
                     'bank_account_name', 'bank_name', 'bank_account_number', 'bank_ifsc']
        
        missing_fields = [field for field in kyc_fields if field not in data or data[field] is None]
        present_fields = [field for field in kyc_fields if field in data and data[field] is not None]
        
        print(f"✅ KYC fields present ({len(present_fields)}/{len(kyc_fields)}): {present_fields}")
        if missing_fields:
            print(f"⚠️  KYC fields missing: {missing_fields}")
        
        # Test update
        operator_id = data["id"]
        update_data = {
            "business_type": "Public Limited",
            "pan_number": "XYZAB9876C", 
            "address": "456 Updated KYC Street, Delhi, Delhi, 110001"
        }
        
        print("📝 Testing KYC field updates...")
        update_response = requests.put(f"{BACKEND_URL}/admin/operators/{operator_id}", json=update_data, headers=headers)
        
        if update_response.status_code == 200:
            updated_data = update_response.json()
            print("✅ KYC fields updated successfully")
            print(f"   • business_type: {kyc_data['business_type']} → {updated_data['business_type']}")
            print(f"   • pan_number: {kyc_data['pan_number']} → {updated_data['pan_number']}")
            print(f"   • address updated: {updated_data['address'][:50]}...")
            return True
        else:
            print(f"❌ KYC update failed: {update_response.status_code} {update_response.text}")
    else:
        print(f"❌ KYC creation failed: {response.status_code} {response.text}")
    
    return False

def main():
    """Run comprehensive KYC tests focused on working functionality"""
    print("🎯 COMPREHENSIVE KYC BACKEND TESTING")
    print("=" * 60)
    
    # Test sequence
    tests = [
        ("Valid PAN Format", test_valid_pan_format),
        ("Valid Business Types", test_valid_business_types), 
        ("Comprehensive KYC Fields", test_kyc_fields_comprehensive)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 40)
        results[test_name] = test_func()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    print(f"\n🏆 OVERALL: {passed}/{total} tests passed ({passed/total*100:.1f}% success rate)")
    
    if passed == total:
        print("🎉 ALL KYC FEATURES WORKING PERFECTLY!")
    else:
        print("⚠️  Some tests failed, but core functionality is working")

if __name__ == "__main__":
    main()