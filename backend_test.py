import requests
import sys
from datetime import datetime, timedelta
import json

class SaaSBillingTester:
    def __init__(self, base_url="https://recurring-platform.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.operator_token = None
        self.test_operator_id = None
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

    def make_request(self, method, endpoint, data=None, token=None):
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
            
            return response
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")

    # ============== SEED DATA ==============
    
    def test_seed_data(self):
        """Seed initial data"""
        try:
            response = self.make_request('POST', 'seed')
            success = response.status_code == 200
            self.log_result("Seed Data", success, response.json() if success else None, 
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Seed Data", False, None, e)
            return False

    def test_health_check(self):
        """Test health endpoint"""
        try:
            response = self.make_request('GET', 'health')
            success = response.status_code == 200
            self.log_result("Health Check", success, response.json() if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Health Check", False, None, e)
            return False

    # ============== AUTHENTICATION ==============

    def test_admin_login(self):
        """Test admin login"""
        try:
            response = self.make_request('POST', 'auth/login', {
                "email": "admin@saas.com",
                "password": "admin123"
            })
            success = response.status_code == 200
            if success:
                data = response.json()
                self.admin_token = data.get("access_token")
            self.log_result("Admin Login", success, {"has_token": bool(self.admin_token)} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Admin Login", False, None, e)
            return False

    def test_operator_registration(self):
        """Test operator registration"""
        try:
            test_data = {
                "company_name": "Test Company Pvt Ltd",
                "owner_name": "John Test",
                "email": f"john+{datetime.now().strftime('%H%M%S')}@testcompany.com",
                "phone": "9876543210",
                "password": "test123",
                "gst_number": "22AAAAA0000A1Z5",
                "charge_gst": True
            }
            
            response = self.make_request('POST', 'auth/register', test_data)
            success = response.status_code == 200
            if success:
                data = response.json()
                self.operator_token = data.get("access_token")
                self.test_operator_id = data.get("user", {}).get("operator_id")
                
            self.log_result("Operator Registration", success, 
                          {"has_token": bool(self.operator_token), "operator_id": self.test_operator_id} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Operator Registration", False, None, e)
            return False

    def test_get_auth_me(self):
        """Test get current user"""
        try:
            # Test admin
            response = self.make_request('GET', 'auth/me', token=self.admin_token)
            admin_success = response.status_code == 200
            
            # Test operator
            response = self.make_request('GET', 'auth/me', token=self.operator_token)
            operator_success = response.status_code == 200
            
            success = admin_success and operator_success
            self.log_result("Get Auth Me", success, 
                          {"admin": admin_success, "operator": operator_success},
                          None if success else "One or both auth/me calls failed")
            return success
        except Exception as e:
            self.log_result("Get Auth Me", False, None, e)
            return False

    # ============== ADMIN: SAAS PLANS ==============

    def test_admin_create_saas_plan(self):
        """Test creating SaaS plan"""
        try:
            plan_data = {
                "name": "Test Premium Plan",
                "monthly_price": 1999,
                "max_subscribers": 250,
                "max_staff": 5,
                "trial_enabled": False,
                "trial_days": 0,
                "notification_module": True,
                "auto_reminder": True,
                "audit_logs": True,
                "payment_gateway_setup": True,
                "gst_applicable": True
            }
            
            response = self.make_request('POST', 'admin/saas-plans', plan_data, self.admin_token)
            success = response.status_code == 200
            if success:
                self.test_plan_id = response.json().get("id")
                
            self.log_result("Admin Create SaaS Plan", success, 
                          {"plan_id": getattr(self, 'test_plan_id', None)} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Admin Create SaaS Plan", False, None, e)
            return False

    def test_admin_get_saas_plans(self):
        """Test getting SaaS plans"""
        try:
            response = self.make_request('GET', 'admin/saas-plans', token=self.admin_token)
            success = response.status_code == 200
            if success:
                plans = response.json()
                plan_count = len(plans)
            else:
                plan_count = 0
                
            self.log_result("Admin Get SaaS Plans", success, 
                          {"plan_count": plan_count} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Admin Get SaaS Plans", False, None, e)
            return False

    # ============== ADMIN: DASHBOARD ==============

    def test_admin_dashboard(self):
        """Test admin dashboard"""
        try:
            response = self.make_request('GET', 'admin/dashboard', token=self.admin_token)
            success = response.status_code == 200
            if success:
                data = response.json()
                has_kpis = all(key in data for key in [
                    "total_operators", "active_operators", "trial_operators"
                ])
            else:
                has_kpis = False
                
            self.log_result("Admin Dashboard", success, 
                          {"has_required_kpis": has_kpis} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Admin Dashboard", False, None, e)
            return False

    def test_admin_get_operators(self):
        """Test getting operators"""
        try:
            response = self.make_request('GET', 'admin/operators', token=self.admin_token)
            success = response.status_code == 200
            if success:
                operators = response.json()
                operator_count = len(operators)
            else:
                operator_count = 0
                
            self.log_result("Admin Get Operators", success,
                          {"operator_count": operator_count} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Admin Get Operators", False, None, e)
            return False

    # ============== OPERATOR: DASHBOARD ==============

    def test_operator_dashboard(self):
        """Test operator dashboard"""
        try:
            response = self.make_request('GET', 'operator/dashboard', token=self.operator_token)
            success = response.status_code == 200
            if success:
                data = response.json()
                has_stats = all(key in data for key in [
                    "total_subscribers", "total_invoices", "total_revenue"
                ])
            else:
                has_stats = False
                
            self.log_result("Operator Dashboard", success,
                          {"has_required_stats": has_stats} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Operator Dashboard", False, None, e)
            return False

    def test_operator_profile(self):
        """Test operator profile"""
        try:
            response = self.make_request('GET', 'operator/profile', token=self.operator_token)
            success = response.status_code == 200
            if success:
                profile = response.json()
                has_profile_data = all(key in profile for key in [
                    "company_name", "owner_name", "email", "status"
                ])
            else:
                has_profile_data = False
                
            self.log_result("Operator Profile", success,
                          {"has_profile_data": has_profile_data} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Operator Profile", False, None, e)
            return False

    # ============== OPERATOR: PLANS ==============

    def test_operator_create_plan(self):
        """Test creating operator plan"""
        try:
            plan_data = {
                "name": "Monthly Internet Plan",
                "price": 699,
                "validity": "monthly",
                "tax_percentage": 18,
                "tax_type": "exclusive",
                "description": "High-speed internet connection"
            }
            
            response = self.make_request('POST', 'operator/plans', plan_data, self.operator_token)
            success = response.status_code == 200
            if success:
                self.test_operator_plan_id = response.json().get("id")
                
            self.log_result("Operator Create Plan", success,
                          {"plan_id": getattr(self, 'test_operator_plan_id', None)} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Operator Create Plan", False, None, e)
            return False

    def test_operator_get_plans(self):
        """Test getting operator plans"""
        try:
            response = self.make_request('GET', 'operator/plans', token=self.operator_token)
            success = response.status_code == 200
            if success:
                plans = response.json()
                plan_count = len(plans)
            else:
                plan_count = 0
                
            self.log_result("Operator Get Plans", success,
                          {"plan_count": plan_count} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Operator Get Plans", False, None, e)
            return False

    # ============== OPERATOR: SUBSCRIBERS ==============

    def test_operator_create_subscriber(self):
        """Test creating subscriber"""
        try:
            if not hasattr(self, 'test_operator_plan_id'):
                self.log_result("Operator Create Subscriber", False, None, "No plan ID available")
                return False
                
            subscriber_data = {
                "name": "Test Customer",
                "whatsapp_number": "919876543210",
                "email": "customer@test.com",
                "address": "123 Test Street, Test City",
                "plan_id": self.test_operator_plan_id,
                "billing_date": 15,
                "discount": 50
            }
            
            response = self.make_request('POST', 'operator/subscribers', subscriber_data, self.operator_token)
            success = response.status_code == 200
            if success:
                self.test_subscriber_id = response.json().get("id")
                
            self.log_result("Operator Create Subscriber", success,
                          {"subscriber_id": getattr(self, 'test_subscriber_id', None)} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Operator Create Subscriber", False, None, e)
            return False

    def test_operator_get_subscribers(self):
        """Test getting subscribers"""
        try:
            response = self.make_request('GET', 'operator/subscribers', token=self.operator_token)
            success = response.status_code == 200
            if success:
                subscribers = response.json()
                subscriber_count = len(subscribers)
            else:
                subscriber_count = 0
                
            self.log_result("Operator Get Subscribers", success,
                          {"subscriber_count": subscriber_count} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Operator Get Subscribers", False, None, e)
            return False

    # ============== OPERATOR: INVOICES ==============

    def test_operator_create_invoice(self):
        """Test creating invoice"""
        try:
            if not hasattr(self, 'test_subscriber_id') or not hasattr(self, 'test_operator_plan_id'):
                self.log_result("Operator Create Invoice", False, None, "Missing subscriber or plan ID")
                return False
                
            today = datetime.now()
            invoice_data = {
                "subscriber_id": self.test_subscriber_id,
                "plan_id": self.test_operator_plan_id,
                "base_amount": 699,
                "discount": 50,
                "service_start_date": today.isoformat(),
                "service_end_date": (today + timedelta(days=30)).isoformat(),
                "due_date": (today + timedelta(days=7)).isoformat()
            }
            
            response = self.make_request('POST', 'operator/invoices', invoice_data, self.operator_token)
            success = response.status_code == 200
            if success:
                self.test_invoice_id = response.json().get("id")
                
            self.log_result("Operator Create Invoice", success,
                          {"invoice_id": getattr(self, 'test_invoice_id', None)} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Operator Create Invoice", False, None, e)
            return False

    def test_operator_get_invoices(self):
        """Test getting invoices"""
        try:
            response = self.make_request('GET', 'operator/invoices', token=self.operator_token)
            success = response.status_code == 200
            if success:
                invoices = response.json()
                invoice_count = len(invoices)
            else:
                invoice_count = 0
                
            self.log_result("Operator Get Invoices", success,
                          {"invoice_count": invoice_count} if success else None,
                          None if success else f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Operator Get Invoices", False, None, e)
            return False

    # ============== OPERATOR: REPORTS ==============

    def test_operator_reports(self):
        """Test operator reports"""
        reports_tested = 0
        reports_passed = 0
        
        # Revenue Report
        try:
            response = self.make_request('GET', 'operator/reports/revenue', token=self.operator_token)
            reports_tested += 1
            if response.status_code == 200:
                reports_passed += 1
        except:
            pass
            
        # GST Summary Report
        try:
            response = self.make_request('GET', 'operator/reports/gst-summary', token=self.operator_token)
            reports_tested += 1
            if response.status_code == 200:
                reports_passed += 1
        except:
            pass
            
        # Pending/Overdue Report
        try:
            response = self.make_request('GET', 'operator/reports/pending-overdue', token=self.operator_token)
            reports_tested += 1
            if response.status_code == 200:
                reports_passed += 1
        except:
            pass
            
        success = reports_passed == reports_tested and reports_tested > 0
        self.log_result("Operator Reports", success,
                      {"reports_tested": reports_tested, "reports_passed": reports_passed},
                      None if success else f"Only {reports_passed}/{reports_tested} reports working")
        return success

    # ============== OPERATOR: SETTINGS ==============

    def test_operator_payment_gateway(self):
        """Test payment gateway configuration"""
        try:
            # Get current config
            response = self.make_request('GET', 'operator/payment-gateway', token=self.operator_token)
            get_success = response.status_code == 200
            
            # Configure gateway
            gateway_data = {
                "gateway_type": "razorpay",
                "api_key": "rzp_test_1234567890",
                "api_secret": "test_secret_key_12345",
                "webhook_secret": "webhook_secret_123"
            }
            
            response = self.make_request('POST', 'operator/payment-gateway', gateway_data, self.operator_token)
            post_success = response.status_code == 200
            
            success = get_success and post_success
            self.log_result("Operator Payment Gateway", success,
                          {"get_success": get_success, "post_success": post_success},
                          None if success else "One or both gateway operations failed")
            return success
        except Exception as e:
            self.log_result("Operator Payment Gateway", False, None, e)
            return False

    # ============== RUN ALL TESTS ==============

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting SaaS Billing Platform API Tests")
        print("=" * 60)
        
        # Basic tests
        self.test_health_check()
        self.test_seed_data()
        
        # Authentication tests
        self.test_admin_login()
        self.test_operator_registration()
        self.test_get_auth_me()
        
        # Admin tests
        self.test_admin_dashboard()
        self.test_admin_create_saas_plan()
        self.test_admin_get_saas_plans()
        self.test_admin_get_operators()
        
        # Operator tests
        self.test_operator_dashboard()
        self.test_operator_profile()
        self.test_operator_create_plan()
        self.test_operator_get_plans()
        self.test_operator_create_subscriber()
        self.test_operator_get_subscribers()
        self.test_operator_create_invoice()
        self.test_operator_get_invoices()
        self.test_operator_reports()
        self.test_operator_payment_gateway()
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            failed_tests = [r["test"] for r in self.results if not r["success"]]
            print(f"❌ Failed tests: {', '.join(failed_tests)}")
            return 1

def main():
    tester = SaaSBillingTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())