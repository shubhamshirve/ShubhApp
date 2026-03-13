#!/usr/bin/env python3
"""
OTP Registration Flow Testing
Test the new OTP registration and uniqueness validation system
"""
import requests
import json
import time
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://admin-dashboard-v2-34.preview.emergentagent.com/api"

class OTPTestRunner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def log_test(self, test_name, status, details=""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {status} {test_name}")
        if details:
            print(f"    {details}")
            
    def test_seed_database(self):
        """First seed the database"""
        try:
            response = self.session.post(f"{BACKEND_URL}/seed")
            if response.status_code == 200:
                self.log_test("POST /api/seed", "✅ PASSED", "Database seeded successfully")
                return True
            else:
                self.log_test("POST /api/seed", "❌ FAILED", f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("POST /api/seed", "❌ ERROR", f"Exception: {str(e)}")
            return False
    
    def test_register_init_existing_email(self):
        """Test 1: Register Init - Email Uniqueness (existing email)"""
        test_data = {
            "company_name": "Test Co",
            "owner_name": "Test",
            "email": "admin@saas.com",
            "phone": "1234567890",
            "password": "test123"
        }
        
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/register-init", json=test_data)
            if response.status_code == 400 and "Email already registered" in response.text:
                self.log_test("Register Init - Email Uniqueness", "✅ PASSED", "Correctly rejected existing email (admin@saas.com)")
                return True
            else:
                self.log_test("Register Init - Email Uniqueness", "❌ FAILED", f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Register Init - Email Uniqueness", "❌ ERROR", f"Exception: {str(e)}")
            return False
    
    def test_register_init_success(self):
        """Test 2: Register Init - Success with unique data"""
        test_data = {
            "company_name": "New Test Co",
            "owner_name": "New Owner", 
            "email": "newotptest@test.com",
            "phone": "7777666655",
            "password": "test123"
        }
        
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/register-init", json=test_data)
            if response.status_code == 200:
                data = response.json()
                if "registration_id" in data and "phone_last4" in data and data["phone_last4"] == "6655":
                    self.log_test("Register Init - Success", "✅ PASSED", f"Registration ID: {data['registration_id']}, Phone last 4: {data['phone_last4']}")
                    return data["registration_id"]
                else:
                    self.log_test("Register Init - Success", "❌ FAILED", f"Missing required fields in response: {data}")
                    return None
            else:
                self.log_test("Register Init - Success", "❌ FAILED", f"Status: {response.status_code}, Response: {response.text}")
                return None
        except Exception as e:
            self.log_test("Register Init - Success", "❌ ERROR", f"Exception: {str(e)}")
            return None
    
    def test_verify_otp_wrong(self, registration_id):
        """Test 3: Verify OTP - Wrong OTP"""
        if not registration_id:
            self.log_test("Verify OTP - Wrong OTP", "⏭️ SKIPPED", "No registration_id from previous test")
            return False
            
        test_data = {
            "registration_id": registration_id,
            "otp": "000000"
        }
        
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/verify-otp", json=test_data)
            if response.status_code == 400 and "Invalid OTP" in response.text:
                self.log_test("Verify OTP - Wrong OTP", "✅ PASSED", "Correctly rejected wrong OTP with attempts remaining message")
                return True
            else:
                self.log_test("Verify OTP - Wrong OTP", "❌ FAILED", f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Verify OTP - Wrong OTP", "❌ ERROR", f"Exception: {str(e)}")
            return False
    
    def test_verify_otp_test_code(self, registration_id):
        """Test 4: Verify OTP - Test OTP (200796)"""
        if not registration_id:
            self.log_test("Verify OTP - Test Code", "⏭️ SKIPPED", "No registration_id from previous test")
            return None
            
        test_data = {
            "registration_id": registration_id,
            "otp": "200796"
        }
        
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/verify-otp", json=test_data)
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "user" in data:
                    self.log_test("Verify OTP - Test Code", "✅ PASSED", f"Registration completed, token received. User: {data['user']['email']}")
                    return data
                else:
                    self.log_test("Verify OTP - Test Code", "❌ FAILED", f"Missing access_token or user in response: {data}")
                    return None
            else:
                self.log_test("Verify OTP - Test Code", "❌ FAILED", f"Status: {response.status_code}, Response: {response.text}")
                return None
        except Exception as e:
            self.log_test("Verify OTP - Test Code", "❌ ERROR", f"Exception: {str(e)}")
            return None
    
    def test_duplicate_phone_after_registration(self):
        """Test 5: Verify duplicate phone after registration"""
        test_data = {
            "company_name": "Another Co",
            "owner_name": "Another Owner",
            "email": "another@test.com",
            "phone": "7777666655",  # Same phone as registered user
            "password": "test123"
        }
        
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/register-init", json=test_data)
            if response.status_code == 400 and "Phone number already registered" in response.text:
                self.log_test("Duplicate Phone Check", "✅ PASSED", "Correctly rejected duplicate phone number")
                return True
            else:
                self.log_test("Duplicate Phone Check", "❌ FAILED", f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Duplicate Phone Check", "❌ ERROR", f"Exception: {str(e)}")
            return False
    
    def test_duplicate_email_after_registration(self):
        """Test 6: Verify duplicate email after registration"""
        test_data = {
            "company_name": "Yet Another Co",
            "owner_name": "Yet Another Owner",
            "email": "newotptest@test.com",  # Same email as registered user
            "phone": "8888777766",
            "password": "test123"
        }
        
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/register-init", json=test_data)
            if response.status_code == 400 and "Email already registered" in response.text:
                self.log_test("Duplicate Email Check", "✅ PASSED", "Correctly rejected duplicate email")
                return True
            else:
                self.log_test("Duplicate Email Check", "❌ FAILED", f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Duplicate Email Check", "❌ ERROR", f"Exception: {str(e)}")
            return False
    
    def test_legacy_register_phone_uniqueness(self):
        """Test 7: Legacy register endpoint still checks phone uniqueness"""
        test_data = {
            "company_name": "Legacy",
            "owner_name": "Lg",
            "email": "legacy@test.com",
            "phone": "7777666655",  # Same phone as OTP registered user
            "password": "test123"
        }
        
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/register", json=test_data)
            if response.status_code == 400 and "Phone number already registered" in response.text:
                self.log_test("Legacy Register Phone Check", "✅ PASSED", "Legacy endpoint correctly rejected duplicate phone")
                return True
            else:
                self.log_test("Legacy Register Phone Check", "❌ FAILED", f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Legacy Register Phone Check", "❌ ERROR", f"Exception: {str(e)}")
            return False
    
    def run_comprehensive_tests(self):
        """Run all OTP registration tests"""
        print("\n🎯 OTP REGISTRATION FLOW TESTING STARTED")
        print("="*60)
        
        tests_results = []
        
        # Test 1: Seed Database
        seed_success = self.test_seed_database()
        tests_results.append(("Seed Database", seed_success))
        
        # Test 2: Email Uniqueness (existing email)
        email_unique_success = self.test_register_init_existing_email()
        tests_results.append(("Email Uniqueness Check", email_unique_success))
        
        # Test 3: Successful Registration Init
        registration_id = self.test_register_init_success()
        reg_init_success = registration_id is not None
        tests_results.append(("Registration Init Success", reg_init_success))
        
        # Test 4: Wrong OTP
        wrong_otp_success = self.test_verify_otp_wrong(registration_id)
        tests_results.append(("Wrong OTP Rejection", wrong_otp_success))
        
        # Test 5: Correct Test OTP
        verification_data = self.test_verify_otp_test_code(registration_id)
        otp_success = verification_data is not None
        tests_results.append(("Test OTP Verification", otp_success))
        
        # Test 6: Duplicate Phone Check
        dup_phone_success = self.test_duplicate_phone_after_registration()
        tests_results.append(("Duplicate Phone Check", dup_phone_success))
        
        # Test 7: Duplicate Email Check
        dup_email_success = self.test_duplicate_email_after_registration()
        tests_results.append(("Duplicate Email Check", dup_email_success))
        
        # Test 8: Legacy Register Phone Uniqueness
        legacy_success = self.test_legacy_register_phone_uniqueness()
        tests_results.append(("Legacy Register Phone Check", legacy_success))
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, success in tests_results if success)
        total = len(tests_results)
        
        for test_name, success in tests_results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status} {test_name}")
        
        print(f"\n🎯 OVERALL RESULT: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 ALL OTP REGISTRATION TESTS PASSED! System is working correctly.")
        else:
            print("⚠️ Some tests failed. Review the detailed logs above.")
        
        return passed == total

if __name__ == "__main__":
    tester = OTPTestRunner()
    tester.run_comprehensive_tests()