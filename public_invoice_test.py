#!/usr/bin/env python3
"""
Public Invoice API Testing Suite
Testing the new public invoice endpoints that don't require authentication:
1. GET /api/public/invoice/{invoice_id}
2. POST /api/public/invoice/{invoice_id}/create-payment-order  
3. GET /api/public/invoice/{invoice_id}/pdf
4. POST /api/public/invoice/{invoice_id}/verify-payment

Test Data from review request:
- Unpaid Invoice (with GST): ID = ee556be3-2944-4560-be09-98a49f30a679
- Paid Invoice (with discount): ID = 680f1761-606d-449f-b61f-af27a33e2ad9
- Operator ID: aa881806-cc85-4d21-b2be-c416a1ecac02 (has payment_gateway addon)
"""

import requests
import json
from datetime import datetime
import sys
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BACKEND_URL = "https://otp-registration-1.preview.emergentagent.com/api"

# Test Data - Pre-existing invoices in the database
UNPAID_INVOICE_ID = "ee556be3-2944-4560-be09-98a49f30a679"
PAID_INVOICE_ID = "680f1761-606d-449f-b61f-af27a33e2ad9"
OPERATOR_ID = "aa881806-cc85-4d21-b2be-c416a1ecac02"
INVALID_INVOICE_ID = "fake-invoice-id-12345"

class PublicInvoiceTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = {}
        
    def log(self, message: str):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make request to backend (no auth required for public endpoints)"""
        url = f"{BACKEND_URL}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            return response
        except Exception as e:
            self.log(f"❌ Request failed: {e}")
            raise

    def test_get_public_invoice_unpaid(self) -> bool:
        """Test 1: GET /api/public/invoice/{invoice_id} with unpaid invoice"""
        self.log("\n🧪 TEST 1: GET /api/public/invoice/{unpaid_invoice_id}")
        
        try:
            response = self.make_request('GET', f'/public/invoice/{UNPAID_INVOICE_ID}')
            
            if response.status_code == 200:
                data = response.json()
                self.log("✅ Unpaid invoice retrieved successfully")
                
                # Check required sections are present
                required_sections = ['invoice', 'operator', 'subscriber', 'plan', 'invoice_settings', 'payment']
                missing_sections = [section for section in required_sections if section not in data]
                
                if missing_sections:
                    self.log(f"❌ Missing sections: {missing_sections}")
                    return False
                
                # Verify specific values for unpaid invoice
                invoice = data.get('invoice', {})
                plan = data.get('plan', {})
                payment = data.get('payment', {})
                
                # Check invoice details
                tax_amount = invoice.get('tax_amount')
                final_amount = invoice.get('final_amount')
                status = invoice.get('status')
                
                self.log(f"  Invoice status: {status}")
                self.log(f"  Tax amount: {tax_amount}")
                self.log(f"  Final amount: {final_amount}")
                
                # Check plan tax details  
                tax_percentage = plan.get('tax_percentage')
                tax_type = plan.get('tax_type')
                
                self.log(f"  Plan tax percentage: {tax_percentage}")
                self.log(f"  Plan tax type: {tax_type}")
                
                # Check payment availability
                payment_enabled = payment.get('enabled')
                razorpay_key = payment.get('razorpay_key')
                
                self.log(f"  Payment enabled: {payment_enabled}")
                self.log(f"  Razorpay key present: {razorpay_key is not None}")
                
                # Verify expected values from review request
                checks_passed = True
                
                # Expected values: tax_amount = 90.0, final_amount = 590.0
                if tax_amount != 90.0:
                    self.log(f"❌ Expected tax_amount=90.0, got {tax_amount}")
                    checks_passed = False
                    
                if final_amount != 590.0:
                    self.log(f"❌ Expected final_amount=590.0, got {final_amount}")
                    checks_passed = False
                
                # Expected: tax_percentage = 18, tax_type = "exclusive"
                if tax_percentage != 18:
                    self.log(f"❌ Expected tax_percentage=18, got {tax_percentage}")
                    checks_passed = False
                    
                if tax_type != "exclusive":
                    self.log(f"❌ Expected tax_type='exclusive', got '{tax_type}'")
                    checks_passed = False
                
                # Expected: payment.enabled = true, razorpay_key is not null
                if not payment_enabled:
                    self.log("❌ Expected payment.enabled=true")
                    checks_passed = False
                    
                if not razorpay_key:
                    self.log("❌ Expected razorpay_key to be not null")
                    checks_passed = False
                
                if checks_passed:
                    self.log("✅ All expected values verified correctly")
                    return True
                else:
                    self.log("❌ Some expected values don't match")
                    return False
                    
            else:
                self.log(f"❌ Failed to get unpaid invoice: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Test error: {e}")
            return False

    def test_get_public_invoice_paid(self) -> bool:
        """Test 2: GET /api/public/invoice/{invoice_id} with paid invoice"""
        self.log("\n🧪 TEST 2: GET /api/public/invoice/{paid_invoice_id}")
        
        try:
            response = self.make_request('GET', f'/public/invoice/{PAID_INVOICE_ID}')
            
            if response.status_code == 200:
                data = response.json()
                invoice = data.get('invoice', {})
                
                status = invoice.get('status')
                discount = invoice.get('discount')
                final_amount = invoice.get('final_amount')
                
                self.log(f"  Invoice status: {status}")
                self.log(f"  Discount: {discount}")
                self.log(f"  Final amount: {final_amount}")
                
                # Verify expected values from review request
                checks_passed = True
                
                # Expected: status = "paid"
                if status != "paid":
                    self.log(f"❌ Expected status='paid', got '{status}'")
                    checks_passed = False
                
                # Expected: discount = 50, final_amount = 450
                if discount != 50:
                    self.log(f"❌ Expected discount=50, got {discount}")
                    checks_passed = False
                    
                if final_amount != 450:
                    self.log(f"❌ Expected final_amount=450, got {final_amount}")
                    checks_passed = False
                
                if checks_passed:
                    self.log("✅ Paid invoice values verified correctly")
                    return True
                else:
                    self.log("❌ Some paid invoice values don't match")
                    return False
                    
            else:
                self.log(f"❌ Failed to get paid invoice: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Test error: {e}")
            return False

    def test_get_public_invoice_invalid(self) -> bool:
        """Test 3: GET /api/public/invoice/{invoice_id} with invalid ID"""
        self.log("\n🧪 TEST 3: GET /api/public/invoice/{invalid_id}")
        
        try:
            response = self.make_request('GET', f'/public/invoice/{INVALID_INVOICE_ID}')
            
            if response.status_code == 404:
                self.log("✅ Invalid invoice ID correctly returns 404")
                return True
            else:
                self.log(f"❌ Expected 404 for invalid ID, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Test error: {e}")
            return False

    def test_create_payment_order_unpaid(self) -> bool:
        """Test 4: POST /api/public/invoice/{invoice_id}/create-payment-order with unpaid invoice"""
        self.log("\n🧪 TEST 4: POST /api/public/invoice/{unpaid_invoice_id}/create-payment-order")
        
        try:
            response = self.make_request('POST', f'/public/invoice/{UNPAID_INVOICE_ID}/create-payment-order')
            
            if response.status_code == 200:
                data = response.json()
                self.log("✅ Payment order created successfully")
                
                # Check required fields in response
                required_fields = ['razorpay_order_id', 'razorpay_key', 'amount', 'currency', 'invoice_number']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log(f"❌ Missing required fields: {missing_fields}")
                    return False
                
                razorpay_order_id = data.get('razorpay_order_id')
                razorpay_key = data.get('razorpay_key')
                amount = data.get('amount')
                currency = data.get('currency')
                
                self.log(f"  Razorpay order ID: {razorpay_order_id}")
                self.log(f"  Razorpay key: {razorpay_key}")
                self.log(f"  Amount: {amount}")
                self.log(f"  Currency: {currency}")
                
                # Basic validation
                if not razorpay_order_id:
                    self.log("❌ razorpay_order_id is empty")
                    return False
                    
                if not razorpay_key:
                    self.log("❌ razorpay_key is empty")
                    return False
                    
                if currency != "INR":
                    self.log(f"❌ Expected currency='INR', got '{currency}'")
                    return False
                
                self.log("✅ Payment order fields validated correctly")
                return True
                
            else:
                self.log(f"❌ Failed to create payment order: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Test error: {e}")
            return False

    def test_create_payment_order_paid(self) -> bool:
        """Test 5: POST /api/public/invoice/{invoice_id}/create-payment-order with paid invoice"""
        self.log("\n🧪 TEST 5: POST /api/public/invoice/{paid_invoice_id}/create-payment-order")
        
        try:
            response = self.make_request('POST', f'/public/invoice/{PAID_INVOICE_ID}/create-payment-order')
            
            if response.status_code == 400:
                data = response.json()
                detail = data.get('detail', '')
                
                if "already paid" in detail.lower():
                    self.log("✅ Paid invoice correctly returns 400 'Invoice is already paid'")
                    return True
                else:
                    self.log(f"❌ Expected 'already paid' message, got: {detail}")
                    return False
            else:
                self.log(f"❌ Expected 400 for paid invoice, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Test error: {e}")
            return False

    def test_get_invoice_pdf(self) -> bool:
        """Test 6: GET /api/public/invoice/{invoice_id}/pdf"""
        self.log("\n🧪 TEST 6: GET /api/public/invoice/{invoice_id}/pdf")
        
        try:
            response = self.make_request('GET', f'/public/invoice/{UNPAID_INVOICE_ID}/pdf')
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type')
                content_disposition = response.headers.get('Content-Disposition')
                content_length = len(response.content)
                
                self.log(f"  Content-Type: {content_type}")
                self.log(f"  Content-Disposition: {content_disposition}")
                self.log(f"  Content length: {content_length} bytes")
                
                # Check if it's a PDF
                if content_type == "application/pdf":
                    self.log("✅ Correct Content-Type: application/pdf")
                else:
                    self.log(f"❌ Expected Content-Type: application/pdf, got {content_type}")
                    return False
                
                # Check if content disposition is attachment
                if content_disposition and "attachment" in content_disposition:
                    self.log("✅ Content-Disposition includes 'attachment'")
                else:
                    self.log(f"❌ Expected 'attachment' in Content-Disposition, got {content_disposition}")
                    return False
                
                # Check if we got actual PDF content (basic validation)
                if content_length > 100:  # A real PDF should be larger than 100 bytes
                    self.log("✅ PDF content size looks reasonable")
                else:
                    self.log(f"❌ PDF content too small: {content_length} bytes")
                    return False
                
                # Check if content starts with PDF magic bytes
                if response.content.startswith(b'%PDF'):
                    self.log("✅ Content starts with PDF magic bytes")
                    return True
                else:
                    self.log("❌ Content does not start with PDF magic bytes")
                    return False
                    
            else:
                self.log(f"❌ Failed to get PDF: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Test error: {e}")
            return False

    def test_verify_payment_already_paid(self) -> bool:
        """Test 7: POST /api/public/invoice/{invoice_id}/verify-payment with already paid invoice"""
        self.log("\n🧪 TEST 7: POST /api/public/invoice/{paid_invoice_id}/verify-payment")
        
        try:
            # Use dummy payment verification data for already paid invoice
            params = {
                'razorpay_order_id': 'order_dummy123',
                'razorpay_payment_id': 'pay_dummy123',
                'razorpay_signature': 'dummy_signature_123'
            }
            
            response = self.make_request('POST', f'/public/invoice/{PAID_INVOICE_ID}/verify-payment', params=params)
            
            if response.status_code == 200:
                data = response.json()
                message = data.get('message', '')
                
                if "already paid" in message.lower():
                    self.log("✅ Already paid invoice returns 'Invoice already paid' message")
                    return True
                else:
                    self.log(f"❌ Expected 'already paid' message, got: {message}")
                    return False
            else:
                self.log(f"❌ Expected 200 for already paid invoice, got {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Test error: {e}")
            return False

    def test_verify_payment_invalid_signature(self) -> bool:
        """Test 8: POST /api/public/invoice/{invoice_id}/verify-payment with invalid signature"""
        self.log("\n🧪 TEST 8: POST /api/public/invoice/{unpaid_invoice_id}/verify-payment (invalid signature)")
        
        try:
            # Use obviously invalid signature data
            params = {
                'razorpay_order_id': 'invalid_order_123',
                'razorpay_payment_id': 'invalid_payment_123', 
                'razorpay_signature': 'completely_invalid_signature_12345'
            }
            
            response = self.make_request('POST', f'/public/invoice/{UNPAID_INVOICE_ID}/verify-payment', params=params)
            
            if response.status_code == 400:
                data = response.json()
                detail = data.get('detail', '')
                
                if "verification failed" in detail.lower() or "failed" in detail.lower():
                    self.log("✅ Invalid signature correctly returns 400 with verification failure message")
                    return True
                else:
                    self.log(f"❌ Expected verification failure message, got: {detail}")
                    return False
            else:
                self.log(f"❌ Expected 400 for invalid signature, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Test error: {e}")
            return False

    def run_all_tests(self):
        """Run all public invoice API tests"""
        self.log("🚀 Starting Public Invoice API Testing Suite")
        self.log(f"Backend URL: {BACKEND_URL}")
        self.log(f"Test Data: Unpaid Invoice ID: {UNPAID_INVOICE_ID}")
        self.log(f"Test Data: Paid Invoice ID: {PAID_INVOICE_ID}")
        self.log(f"Test Data: Operator ID: {OPERATOR_ID}")
        
        # Run all tests
        test_functions = [
            ("GET unpaid invoice", self.test_get_public_invoice_unpaid),
            ("GET paid invoice", self.test_get_public_invoice_paid),
            ("GET invalid invoice", self.test_get_public_invoice_invalid),
            ("POST create payment order (unpaid)", self.test_create_payment_order_unpaid),
            ("POST create payment order (paid)", self.test_create_payment_order_paid),
            ("GET PDF download", self.test_get_invoice_pdf),
            ("POST verify payment (already paid)", self.test_verify_payment_already_paid),
            ("POST verify payment (invalid signature)", self.test_verify_payment_invalid_signature),
        ]
        
        results = []
        for test_name, test_function in test_functions:
            try:
                result = test_function()
                results.append((test_name, result))
                self.test_results[test_name] = result
            except Exception as e:
                self.log(f"❌ Test '{test_name}' crashed: {e}")
                results.append((test_name, False))
                self.test_results[test_name] = False
        
        # Summary
        self.log("\n📊 PUBLIC INVOICE API TEST SUMMARY")
        self.log("=" * 80)
        
        passed_count = 0
        for test_name, passed in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            self.log(f"{status:<12} {test_name}")
            if passed:
                passed_count += 1
        
        total_tests = len(results)
        pass_rate = (passed_count / total_tests) * 100 if total_tests > 0 else 0
        
        self.log(f"\nOVERALL RESULT: {passed_count}/{total_tests} tests passed ({pass_rate:.1f}%)")
        
        if passed_count == total_tests:
            self.log("🎉 ALL PUBLIC INVOICE API TESTS PASSED!")
            self.log("✅ Public invoice endpoints are working correctly")
        else:
            failed_count = total_tests - passed_count
            self.log(f"⚠️  {failed_count} test(s) failed - please review the results above")
            
        return pass_rate == 100.0

if __name__ == "__main__":
    tester = PublicInvoiceTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code for CI/automation
    sys.exit(0 if success else 1)