#!/usr/bin/env python3
"""
Comprehensive backend testing for KYC features in Multi-Tenant SaaS Billing Platform.
Tests KYC fields in registration, admin operator creation, operator updates, and validation.
"""

import requests
import json
import uuid
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

class KYCTestSuite:
    def __init__(self):
        self.admin_token = None
        self.plan_id = None
        self.test_results = {}
        
    def get_headers(self, token=None):
        """Get request headers with optional authorization."""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    def log_test_result(self, test_name, success, message):
        """Log and store test results."""
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{status} - {test_name}: {message}")
        self.test_results[test_name] = {"success": success, "message": message}
    
    def setup_admin_auth(self):
        """Authenticate as admin and get necessary data."""
        try:
            # Seed data first
            seed_response = requests.post(f"{BACKEND_URL}/seed")
            if seed_response.status_code == 200:
                logger.info("✅ Data seeded successfully")
            
            # Admin login
            login_data = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                logger.info("✅ Admin authentication successful")
                
                # Get a SaaS plan ID for operator creation
                plans_response = requests.get(
                    f"{BACKEND_URL}/admin/saas-plans", 
                    headers=self.get_headers(self.admin_token)
                )
                if plans_response.status_code == 200:
                    plans = plans_response.json()
                    if plans:
                        self.plan_id = plans[0]["id"]
                        logger.info(f"✅ Got plan ID: {self.plan_id}")
                    else:
                        raise Exception("No SaaS plans found")
                else:
                    raise Exception("Failed to get SaaS plans")
                
                return True
            else:
                raise Exception(f"Admin login failed: {response.status_code} {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Admin setup failed: {str(e)}")
            return False

    def test_kyc_registration_init(self):
        """Test 1: KYC Fields in Registration API (POST /api/auth/register-init)"""
        try:
            timestamp = int(datetime.now().timestamp())
            registration_data = {
                "company_name": "Test KYC Company",
                "owner_name": "Test Owner",
                "email": f"testkyc{timestamp}@example.com",
                "phone": "9876543210",
                "password": "test123",
                "business_type": "Private Limited",
                "gst_number": "22AAAAA0000A1Z5",
                "pan_number": "ABCDE1234F",
                "address": "123 Test Street, Mumbai",
                "charge_gst": True,
                "bank_account_name": "Test Account",
                "bank_name": "Test Bank",
                "bank_account_number": "1234567890",
                "bank_ifsc": "SBIN0001234"
            }
            
            response = requests.post(f"{BACKEND_URL}/auth/register-init", json=registration_data)
            
            if response.status_code == 200:
                data = response.json()
                if "registration_id" in data:
                    self.log_test_result(
                        "KYC Registration Init", 
                        True, 
                        f"Registration initiated successfully with ID: {data['registration_id']}"
                    )
                    
                    # Store for OTP verification test
                    self.registration_id = data["registration_id"]
                    self.test_email = registration_data["email"]
                    return True
                else:
                    self.log_test_result(
                        "KYC Registration Init", 
                        False, 
                        f"No registration_id in response: {data}"
                    )
            else:
                self.log_test_result(
                    "KYC Registration Init", 
                    False, 
                    f"Registration failed: {response.status_code} {response.text}"
                )
            return False
            
        except Exception as e:
            self.log_test_result("KYC Registration Init", False, f"Exception: {str(e)}")
            return False

    def test_kyc_registration_verification(self):
        """Test 1b: Verify OTP and complete registration"""
        try:
            if not hasattr(self, 'registration_id'):
                self.log_test_result("KYC Registration OTP", False, "No registration_id from previous test")
                return False
                
            verify_data = {
                "registration_id": self.registration_id,
                "otp": TEST_OTP
            }
            
            response = requests.post(f"{BACKEND_URL}/auth/verify-otp", json=verify_data)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.log_test_result(
                        "KYC Registration OTP", 
                        True, 
                        "OTP verification and registration completed successfully"
                    )
                    return True
                else:
                    self.log_test_result(
                        "KYC Registration OTP", 
                        False, 
                        f"No access_token in response: {data}"
                    )
            else:
                self.log_test_result(
                    "KYC Registration OTP", 
                    False, 
                    f"OTP verification failed: {response.status_code} {response.text}"
                )
            return False
            
        except Exception as e:
            self.log_test_result("KYC Registration OTP", False, f"Exception: {str(e)}")
            return False

    def test_kyc_admin_operator_creation(self):
        """Test 2: KYC Fields in Admin Operator Create (POST /api/admin/operators/create)"""
        try:
            if not self.admin_token or not self.plan_id:
                self.log_test_result("KYC Admin Operator Creation", False, "No admin token or plan ID")
                return False
            
            timestamp = int(datetime.now().timestamp())
            operator_data = {
                "company_name": "Admin KYC Test",
                "owner_name": "Admin Owner",
                "email": f"adminkyctest{timestamp}@test.com",
                "phone": "9876543215",
                "password": "test123",
                "business_type": "LLP",
                "gst_number": "33BBBBB0000B1Z6",
                "pan_number": "FGHIJ5678K",
                "address": "456 Admin Street, Delhi",
                "charge_gst": False,
                "bank_account_name": "Admin Account",
                "bank_name": "Admin Bank",
                "bank_account_number": "9876543210",
                "bank_ifsc": "HDFC0001234",
                "saas_plan_id": self.plan_id,
                "status": "active",
                "subscription_months": 1
            }
            
            response = requests.post(
                f"{BACKEND_URL}/admin/operators/create",
                json=operator_data,
                headers=self.get_headers(self.admin_token)
            )
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and data.get("business_type") == "LLP" and data.get("pan_number") == "FGHIJ5678K":
                    self.created_operator_id = data["id"]
                    self.log_test_result(
                        "KYC Admin Operator Creation", 
                        True, 
                        f"Operator created with KYC fields: ID={data['id']}, business_type={data.get('business_type')}, pan_number={data.get('pan_number')}"
                    )
                    return True
                else:
                    self.log_test_result(
                        "KYC Admin Operator Creation", 
                        False, 
                        f"Missing KYC fields in response: {data}"
                    )
            else:
                self.log_test_result(
                    "KYC Admin Operator Creation", 
                    False, 
                    f"Operator creation failed: {response.status_code} {response.text}"
                )
            return False
            
        except Exception as e:
            self.log_test_result("KYC Admin Operator Creation", False, f"Exception: {str(e)}")
            return False

    def test_kyc_operator_update(self):
        """Test 3: KYC Fields in Operator Update (PUT /api/admin/operators/{id})"""
        try:
            if not self.admin_token or not hasattr(self, 'created_operator_id'):
                self.log_test_result("KYC Operator Update", False, "No admin token or operator ID")
                return False
            
            update_data = {
                "business_type": "Public Limited",
                "pan_number": "LMNOP9012Q",
                "address": "789 Updated Street, Chennai"
            }
            
            response = requests.put(
                f"{BACKEND_URL}/admin/operators/{self.created_operator_id}",
                json=update_data,
                headers=self.get_headers(self.admin_token)
            )
            
            if response.status_code == 200:
                data = response.json()
                if (data.get("business_type") == "Public Limited" and 
                    data.get("pan_number") == "LMNOP9012Q" and 
                    "789 Updated Street, Chennai" in str(data.get("address", ""))):
                    
                    self.log_test_result(
                        "KYC Operator Update", 
                        True, 
                        f"Operator updated successfully with KYC fields: business_type={data.get('business_type')}, pan_number={data.get('pan_number')}"
                    )
                    return True
                else:
                    self.log_test_result(
                        "KYC Operator Update", 
                        False, 
                        f"KYC fields not updated correctly: {data}"
                    )
            else:
                self.log_test_result(
                    "KYC Operator Update", 
                    False, 
                    f"Update failed: {response.status_code} {response.text}"
                )
            return False
            
        except Exception as e:
            self.log_test_result("KYC Operator Update", False, f"Exception: {str(e)}")
            return False

    def test_kyc_validation_pan_invalid(self):
        """Test 4a: PAN number validation - invalid format should fail"""
        try:
            timestamp = int(datetime.now().timestamp())
            invalid_data = {
                "company_name": "Test Validation",
                "owner_name": "Test Owner",
                "email": f"testvalidation{timestamp}@example.com",
                "phone": "9876543211",
                "password": "test123",
                "business_type": "Partnership",
                "pan_number": "INVALID123",  # Invalid PAN format
                "address": "Test Address"
            }
            
            response = requests.post(f"{BACKEND_URL}/auth/register-init", json=invalid_data)
            
            if response.status_code == 422:  # Validation error expected
                self.log_test_result(
                    "KYC Validation - Invalid PAN", 
                    True, 
                    f"Correctly rejected invalid PAN format: {response.status_code}"
                )
                return True
            else:
                self.log_test_result(
                    "KYC Validation - Invalid PAN", 
                    False, 
                    f"Should have rejected invalid PAN but got: {response.status_code} {response.text}"
                )
            return False
            
        except Exception as e:
            self.log_test_result("KYC Validation - Invalid PAN", False, f"Exception: {str(e)}")
            return False

    def test_kyc_validation_business_type_invalid(self):
        """Test 4b: Business type validation - invalid type should fail"""
        try:
            if not self.admin_token or not self.plan_id:
                self.log_test_result("KYC Validation - Invalid Business Type", False, "No admin token or plan ID")
                return False
                
            timestamp = int(datetime.now().timestamp())
            invalid_data = {
                "company_name": "Test Validation BT",
                "owner_name": "Test Owner",
                "email": f"testvalidationbt{timestamp}@example.com",
                "phone": "9876543212",
                "password": "test123",
                "business_type": "InvalidType",  # Invalid business type
                "saas_plan_id": self.plan_id,
                "status": "active",
                "subscription_months": 1
            }
            
            response = requests.post(
                f"{BACKEND_URL}/admin/operators/create",
                json=invalid_data,
                headers=self.get_headers(self.admin_token)
            )
            
            if response.status_code == 422:  # Validation error expected
                self.log_test_result(
                    "KYC Validation - Invalid Business Type", 
                    True, 
                    f"Correctly rejected invalid business type: {response.status_code}"
                )
                return True
            else:
                self.log_test_result(
                    "KYC Validation - Invalid Business Type", 
                    False, 
                    f"Should have rejected invalid business type but got: {response.status_code} {response.text}"
                )
            return False
            
        except Exception as e:
            self.log_test_result("KYC Validation - Invalid Business Type", False, f"Exception: {str(e)}")
            return False

    def test_kyc_operator_response_fields(self):
        """Test 5: Operator Response Fields - GET /api/admin/operators should return KYC fields"""
        try:
            if not self.admin_token:
                self.log_test_result("KYC Operator Response Fields", False, "No admin token")
                return False
            
            response = requests.get(
                f"{BACKEND_URL}/admin/operators",
                headers=self.get_headers(self.admin_token)
            )
            
            if response.status_code == 200:
                operators = response.json()
                if operators and len(operators) > 0:
                    # Check if any operator has the required KYC fields
                    operator = operators[0]
                    required_fields = [
                        "business_type", "pan_number", "address", 
                        "bank_account_name", "bank_account_number", 
                        "bank_ifsc", "bank_name"
                    ]
                    
                    present_fields = [field for field in required_fields if field in operator]
                    
                    if len(present_fields) >= 4:  # At least most fields should be present
                        self.log_test_result(
                            "KYC Operator Response Fields", 
                            True, 
                            f"Operators response includes KYC fields: {present_fields}"
                        )
                        return True
                    else:
                        self.log_test_result(
                            "KYC Operator Response Fields", 
                            False, 
                            f"Missing KYC fields in operator response. Present: {present_fields}, Expected: {required_fields}"
                        )
                else:
                    self.log_test_result(
                        "KYC Operator Response Fields", 
                        False, 
                        "No operators found in response"
                    )
            else:
                self.log_test_result(
                    "KYC Operator Response Fields", 
                    False, 
                    f"Failed to get operators: {response.status_code} {response.text}"
                )
            return False
            
        except Exception as e:
            self.log_test_result("KYC Operator Response Fields", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all KYC tests in sequence."""
        logger.info("🎯 Starting comprehensive KYC backend testing...")
        logger.info("=" * 70)
        
        # Setup
        if not self.setup_admin_auth():
            logger.error("❌ Failed to setup admin authentication. Aborting tests.")
            return
        
        # Run tests
        tests = [
            self.test_kyc_registration_init,
            self.test_kyc_registration_verification,
            self.test_kyc_admin_operator_creation,
            self.test_kyc_operator_update,
            self.test_kyc_validation_pan_invalid,
            self.test_kyc_validation_business_type_invalid,
            self.test_kyc_operator_response_fields
        ]
        
        for test in tests:
            test()
            
        # Summary
        logger.info("=" * 70)
        logger.info("🏁 KYC TESTING COMPLETED")
        logger.info("=" * 70)
        
        passed = sum(1 for result in self.test_results.values() if result["success"])
        total = len(self.test_results)
        
        logger.info(f"📊 SUMMARY: {passed}/{total} tests passed ({passed/total*100:.1f}% success rate)")
        
        if passed == total:
            logger.info("🎉 ALL KYC FEATURES WORKING PERFECTLY!")
        else:
            logger.info("⚠️  SOME TESTS FAILED:")
            for test_name, result in self.test_results.items():
                if not result["success"]:
                    logger.info(f"   ❌ {test_name}: {result['message']}")

if __name__ == "__main__":
    test_suite = KYCTestSuite()
    test_suite.run_all_tests()