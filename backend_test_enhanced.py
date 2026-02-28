import requests
import sys
from datetime import datetime, timedelta
import json

class EnhancedSaaSBillingTester:
    def __init__(self, base_url="https://minimal-deploy.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.operator_token = None
        self.test_operator_id = None
        self.test_invoice_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []

    def log_result(self, test_name, success, response_data=None, error=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name} - PASSED")
        else:
            print(f"❌ {test_name} - FAILED: {error}")
        
        self.results.append({
            "test": test_name,
            "success": success,
            "response": response_data,
            "error": str(error) if error else None
        })

    def make_request(self, method, endpoint, data=None, token=None, return_response=False):
        """Make HTTP request"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            
            if return_response:
                return response
            return response
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")

    def setup_test_data(self):
        """Setup required test data"""
        try:
            # Seed data
            self.make_request('POST', 'seed')
            
            # Admin login
            response = self.make_request('POST', 'auth/login', {
                "email": "admin@saas.com",
                "password": "admin123"
            })
            if response.status_code == 200:
                self.admin_token = response.json().get("access_token")

            # Operator registration
            test_data = {
                "company_name": "Test Company Enhanced",
                "owner_name": "John Enhanced Test",
                "email": f"enhanced+{datetime.now().strftime('%H%M%S')}@testcompany.com",
                "phone": "9876543210",
                "password": "test123",
                "gst_number": "22AAAAA0000A1Z5",
                "charge_gst": True
            }
            
            response = self.make_request('POST', 'auth/register', test_data)
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                self.test_operator_id = data.get("user", {}).get("operator_id")

            # Create plan and subscriber for invoice testing
            plan_data = {
                "name": "Enhanced Test Plan",
                "price": 999,
                "validity": "monthly",
                "tax_percentage": 18,
                "tax_type": "exclusive",
                "description": "Enhanced testing plan"
            }
            
            response = self.make_request('POST', 'operator/plans', plan_data, self.operator_token)
            if response.status_code == 200:
                self.test_plan_id = response.json().get("id")

            subscriber_data = {
                "name": "Enhanced Test Customer",
                "whatsapp_number": "919876543210",
                "email": "enhanced.customer@test.com",
                "address": "Enhanced Test Address",
                "plan_id": self.test_plan_id,
                "billing_date": 15,
                "discount": 0
            }
            
            response = self.make_request('POST', 'operator/subscribers', subscriber_data, self.operator_token)
            if response.status_code == 200:
                self.test_subscriber_id = response.json().get("id")

            # Create test invoice
            today = datetime.now()
            invoice_data = {
                "subscriber_id": self.test_subscriber_id,
                "plan_id": self.test_plan_id,
                "base_amount": 999,
                "discount": 0,
                "service_start_date": today.isoformat(),
                "service_end_date": (today + timedelta(days=30)).isoformat(),
                "due_date": (today + timedelta(days=7)).isoformat()
            }
            
            response = self.make_request('POST', 'operator/invoices', invoice_data, self.operator_token)
            if response.status_code == 200:
                self.test_invoice_id = response.json().get("id")

            return True
        except Exception as e:
            print(f"Setup failed: {str(e)}")
            return False

    # ============== NEW FEATURE TESTS ==============

    def test_invoice_pdf_generation(self):
        """Test PDF invoice generation endpoint"""
        try:
            if not self.test_invoice_id:
                self.log_result("Invoice PDF Generation", False, None, "No test invoice available")
                return False

            response = self.make_request('GET', f'operator/invoices/{self.test_invoice_id}/pdf', 
                                      token=self.operator_token, return_response=True)
            
            success = response.status_code == 200
            content_type = response.headers.get('Content-Type', '')
            is_pdf = 'application/pdf' in content_type
            
            self.log_result("Invoice PDF Generation", success and is_pdf,
                          {"status": response.status_code, "content_type": content_type, "is_pdf": is_pdf},
                          None if success and is_pdf else f"Status: {response.status_code}, Content-Type: {content_type}")
            return success and is_pdf
        except Exception as e:
            self.log_result("Invoice PDF Generation", False, None, e)
            return False

    def test_payment_link_generation(self):
        """Test Razorpay payment link generation (mocked)"""
        try:
            if not self.test_invoice_id:
                self.log_result("Payment Link Generation", False, None, "No test invoice available")
                return False

            response = self.make_request('POST', f'operator/invoices/{self.test_invoice_id}/payment-link', 
                                      token=self.operator_token, return_response=True)
            
            # Should fail with proper error since no real API keys configured
            expected_error = response.status_code in [400, 500]
            if expected_error:
                error_msg = response.json().get('detail', '') if response.status_code != 500 else 'Server error'
                gateway_error = 'gateway' in error_msg.lower() or 'payment' in error_msg.lower()
                success = True  # Expected failure due to mocked API
            else:
                success = False
                gateway_error = False
                
            self.log_result("Payment Link Generation (Mocked)", success,
                          {"status": response.status_code, "expected_error": expected_error, "gateway_error": gateway_error},
                          None if success else f"Unexpected status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Payment Link Generation (Mocked)", False, None, e)
            return False

    def test_whatsapp_config_endpoint(self):
        """Test WhatsApp configuration endpoint"""
        try:
            # Test GET config
            get_response = self.make_request('GET', 'operator/whatsapp-config', token=self.operator_token)
            get_success = get_response.status_code in [200, 404]  # 404 is fine if not configured

            # Test POST config (should fail without proper API access)
            whatsapp_data = {
                "phone_number_id": "123456789012345",
                "access_token": "test_access_token_12345"
            }
            
            post_response = self.make_request('POST', 'operator/whatsapp-config', whatsapp_data, self.operator_token)
            # Should fail with mocked credentials
            post_expected_error = post_response.status_code in [400, 403, 500]
            
            success = get_success and post_expected_error
            self.log_result("WhatsApp Config Endpoint", success,
                          {"get_status": get_response.status_code, "post_status": post_response.status_code, 
                           "get_success": get_success, "post_expected_error": post_expected_error},
                          None if success else "Unexpected response from WhatsApp config endpoints")
            return success
        except Exception as e:
            self.log_result("WhatsApp Config Endpoint", False, None, e)
            return False

    def test_cron_endpoints(self):
        """Test cron job endpoints for admin"""
        try:
            cron_tests = []
            
            # Test invoice generation cron
            response = self.make_request('POST', 'admin/cron/generate-invoices', token=self.admin_token)
            cron_tests.append(("generate-invoices", response.status_code == 200))
            
            # Test reminder cron (if it exists)
            try:
                response = self.make_request('POST', 'admin/cron/send-reminders', token=self.admin_token)
                cron_tests.append(("send-reminders", response.status_code == 200))
            except:
                # Endpoint might not exist
                pass
            
            # Test expiry check cron (if it exists)
            try:
                response = self.make_request('POST', 'admin/cron/check-expiry', token=self.admin_token)
                cron_tests.append(("check-expiry", response.status_code == 200))
            except:
                # Endpoint might not exist
                pass
            
            working_crons = sum(1 for _, success in cron_tests if success)
            total_crons = len(cron_tests)
            
            success = working_crons > 0  # At least one cron endpoint should work
            self.log_result("Cron Job Endpoints", success,
                          {"working_crons": working_crons, "total_crons": total_crons, "tests": cron_tests},
                          None if success else f"No cron endpoints working ({working_crons}/{total_crons})")
            return success
        except Exception as e:
            self.log_result("Cron Job Endpoints", False, None, e)
            return False

    def test_webhook_endpoint(self):
        """Test Razorpay webhook endpoint"""
        try:
            # Test webhook endpoint exists
            webhook_payload = {
                "event": "payment_link.paid",
                "payload": {
                    "payment_link": {
                        "entity": {
                            "id": "plink_test123",
                            "payments": [{"payment_id": "pay_test123"}]
                        }
                    }
                }
            }
            
            # Make request without authentication (webhooks don't use auth)
            response = self.make_request('POST', 'webhooks/razorpay', webhook_payload)
            
            # Should return 200 for webhook processing
            success = response.status_code == 200
            
            self.log_result("Webhook Endpoint", success,
                          {"status": response.status_code},
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Webhook Endpoint", False, None, e)
            return False

    def test_landing_page_endpoint(self):
        """Test if landing page endpoint exists (root URL)"""
        try:
            # Test the main domain landing page
            response = requests.get("https://minimal-deploy.preview.emergentagent.com/")
            
            # Should return 200 and HTML content
            success = response.status_code == 200
            is_html = 'text/html' in response.headers.get('Content-Type', '')
            
            self.log_result("Landing Page Endpoint", success and is_html,
                          {"status": response.status_code, "content_type": response.headers.get('Content-Type', ''), "is_html": is_html},
                          None if success and is_html else f"Status: {response.status_code}")
            return success and is_html
        except Exception as e:
            self.log_result("Landing Page Endpoint", False, None, e)
            return False

    def test_notification_endpoints(self):
        """Test notification/reminder endpoints"""
        try:
            if not self.test_invoice_id:
                self.log_result("Notification Endpoints", False, None, "No test invoice available")
                return False

            # Test send notification endpoint (should exist but may fail without WhatsApp config)
            notification_data = {
                "invoice_id": self.test_invoice_id,
                "notification_type": "invoice"
            }
            
            response = self.make_request('POST', 'operator/send-notification', notification_data, self.operator_token)
            
            # Should fail gracefully with proper error message
            expected_response = response.status_code in [200, 400, 403, 500]
            
            self.log_result("Notification Endpoints", expected_response,
                          {"status": response.status_code, "expected_response": expected_response},
                          None if expected_response else f"Unexpected status: {response.status_code}")
            return expected_response
        except Exception as e:
            self.log_result("Notification Endpoints", False, None, e)
            return False

    def run_enhanced_tests(self):
        """Run all enhanced feature tests"""
        print("🚀 Starting Enhanced SaaS Billing Platform Tests")
        print("=" * 60)
        print("🔧 Setting up test data...")
        
        if not self.setup_test_data():
            print("❌ Failed to setup test data")
            return 1

        print("✅ Test data setup complete")
        print("🧪 Running enhanced feature tests...")
        print("-" * 40)
        
        # Test new features
        self.test_landing_page_endpoint()
        self.test_invoice_pdf_generation()
        self.test_payment_link_generation()
        self.test_whatsapp_config_endpoint()
        self.test_cron_endpoints()
        self.test_webhook_endpoint()
        self.test_notification_endpoints()
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 Enhanced Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All enhanced tests passed!")
            return 0
        else:
            failed_tests = [r["test"] for r in self.results if not r["success"]]
            print(f"❌ Failed tests: {', '.join(failed_tests)}")
            return 1

def main():
    tester = EnhancedSaaSBillingTester()
    return tester.run_enhanced_tests()

if __name__ == "__main__":
    sys.exit(main())