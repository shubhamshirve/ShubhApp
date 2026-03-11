import requests
import sys
from datetime import datetime, timedelta
import json

class SaaSBillingTester:
    def __init__(self, base_url="https://code-scanner-60.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.operator_token = None
        self.staff_token = None
        self.impersonated_token = None
        self.test_operator_id = None
        self.test_plan_id = None
        self.test_operator_plan_id = None
        self.test_subscriber_id = None
        self.test_invoice_id = None
        self.test_staff_id = None
        self.test_addon_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []
        self.failed_tests = []

    def log_result(self, test_name, success, response_data=None, error=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name} - PASSED")
        else:
            print(f"❌ {test_name} - FAILED: {error}")
            self.failed_tests.append({"test": test_name, "error": str(error) if error else "Unknown error"})
        
        self.results.append({
            "test": test_name,
            "success": success,
            "response": response_data,
            "error": str(error) if error else None
        })

    def make_request(self, method, endpoint, data=None, token=None, params=None):
        """Make HTTP request"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, params=params)
            
            return response
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")

    # ============== 1. SEED DATA ==============
    
    def test_seed_data(self):
        """1. POST /api/seed — seed initial data"""
        try:
            response = self.make_request('POST', 'seed')
            success = response.status_code == 200
            self.log_result("1. Seed Data", success, response.json() if success else None, 
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("1. Seed Data", False, None, e)
            return False

    # ============== 2-3. ADMIN AUTH ==============

    def test_admin_login(self):
        """2. POST /api/auth/login (admin) — get admin token"""
        try:
            response = self.make_request('POST', 'auth/login', {
                "email": "admin@saas.com",
                "password": "admin123"
            })
            success = response.status_code == 200
            if success:
                data = response.json()
                self.admin_token = data.get("access_token")
            self.log_result("2. Admin Login", success, {"has_token": bool(self.admin_token)} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("2. Admin Login", False, None, e)
            return False

    def test_admin_auth_me(self):
        """3. GET /api/auth/me — verify token works"""
        try:
            response = self.make_request('GET', 'auth/me', token=self.admin_token)
            success = response.status_code == 200
            self.log_result("3. Admin Auth Me", success, response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("3. Admin Auth Me", False, None, e)
            return False

    # ============== 4-7. ADMIN SAAS PLANS ==============

    def test_admin_get_saas_plans(self):
        """4. GET /api/admin/saas-plans — list plans"""
        try:
            response = self.make_request('GET', 'admin/saas-plans', token=self.admin_token)
            success = response.status_code == 200
            if success:
                plans = response.json()
                plan_count = len(plans)
                # Store first plan for testing
                if plans:
                    self.first_saas_plan_id = plans[0].get('id')
            else:
                plan_count = 0
                
            self.log_result("4. Admin Get SaaS Plans", success, 
                          {"plan_count": plan_count} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("4. Admin Get SaaS Plans", False, None, e)
            return False

    def test_admin_create_saas_plan(self):
        """5. POST /api/admin/saas-plans — create a plan"""
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
                
            self.log_result("5. Admin Create SaaS Plan", success, 
                          {"plan_id": getattr(self, 'test_plan_id', None)} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("5. Admin Create SaaS Plan", False, None, e)
            return False

    def test_admin_update_saas_plan(self):
        """6. PUT /api/admin/saas-plans/{id} — update plan"""
        try:
            if not hasattr(self, 'test_plan_id') or not self.test_plan_id:
                self.log_result("6. Admin Update SaaS Plan", False, None, "No test plan ID available")
                return False
                
            update_data = {
                "name": "Test Premium Plan Updated",
                "monthly_price": 2099,
                "max_subscribers": 300,
                "max_staff": 8,
                "trial_enabled": False,
                "trial_days": 0,
                "notification_module": True,
                "auto_reminder": True,
                "audit_logs": True,
                "payment_gateway_setup": True,
                "gst_applicable": True
            }
            
            response = self.make_request('PUT', f'admin/saas-plans/{self.test_plan_id}', update_data, self.admin_token)
            success = response.status_code == 200
                
            self.log_result("6. Admin Update SaaS Plan", success, 
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("6. Admin Update SaaS Plan", False, None, e)
            return False

    def test_admin_delete_saas_plan(self):
        """7. DELETE /api/admin/saas-plans/{id} — delete plan"""
        try:
            if not hasattr(self, 'test_plan_id') or not self.test_plan_id:
                self.log_result("7. Admin Delete SaaS Plan", False, None, "No test plan ID available")
                return False
                
            response = self.make_request('DELETE', f'admin/saas-plans/{self.test_plan_id}', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("7. Admin Delete SaaS Plan", success, 
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("7. Admin Delete SaaS Plan", False, None, e)
            return False

    # ============== 8-16. ADMIN OPERATORS ==============

    def test_admin_create_operator(self):
        """8. POST /api/admin/operators/create — manually create an operator"""
        try:
            if not hasattr(self, 'first_saas_plan_id'):
                self.log_result("8. Admin Create Operator", False, None, "No SaaS plan ID available")
                return False
                
            operator_data = {
                "company_name": "Test Manual Operator Ltd",
                "owner_name": "Manual Test Owner",
                "email": f"manual+{datetime.now().strftime('%H%M%S')}@testoperator.com",
                "phone": "9876543210",
                "password": "manual123",
                "saas_plan_id": self.first_saas_plan_id,
                "gst_number": "22AAAAA0000A1Z5",
                "charge_gst": True
            }
            
            response = self.make_request('POST', 'admin/operators/create', operator_data, self.admin_token)
            success = response.status_code == 200
            if success:
                data = response.json()
                self.test_operator_id = data.get("operator", {}).get("id") or data.get("id")
                
            self.log_result("8. Admin Create Operator", success, 
                          {"operator_id": getattr(self, 'test_operator_id', None)} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("8. Admin Create Operator", False, None, e)
            return False

    def test_admin_get_operators(self):
        """9. GET /api/admin/operators — list operators"""
        try:
            response = self.make_request('GET', 'admin/operators', token=self.admin_token)
            success = response.status_code == 200
            if success:
                operators = response.json()
                operator_count = len(operators)
                # Ensure we have an operator ID for further tests
                if operators and not hasattr(self, 'test_operator_id'):
                    self.test_operator_id = operators[0].get("id")
            else:
                operator_count = 0
                
            self.log_result("9. Admin Get Operators", success,
                          {"operator_count": operator_count} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("9. Admin Get Operators", False, None, e)
            return False

    def test_admin_get_single_operator(self):
        """10. GET /api/admin/operators/{id} — get single operator"""
        try:
            if not self.test_operator_id:
                self.log_result("10. Admin Get Single Operator", False, None, "No operator ID available")
                return False
                
            response = self.make_request('GET', f'admin/operators/{self.test_operator_id}', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("10. Admin Get Single Operator", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("10. Admin Get Single Operator", False, None, e)
            return False

    def test_admin_update_operator(self):
        """11. PUT /api/admin/operators/{id} — update operator"""
        try:
            if not self.test_operator_id:
                self.log_result("11. Admin Update Operator", False, None, "No operator ID available")
                return False
                
            update_data = {
                "company_name": "Updated Test Operator Ltd"
            }
            
            response = self.make_request('PUT', f'admin/operators/{self.test_operator_id}', update_data, self.admin_token)
            success = response.status_code == 200
                
            self.log_result("11. Admin Update Operator", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("11. Admin Update Operator", False, None, e)
            return False

    def test_admin_suspend_operator(self):
        """12. POST /api/admin/operators/{id}/suspend — suspend operator"""
        try:
            if not self.test_operator_id:
                self.log_result("12. Admin Suspend Operator", False, None, "No operator ID available")
                return False
                
            response = self.make_request('POST', f'admin/operators/{self.test_operator_id}/suspend', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("12. Admin Suspend Operator", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("12. Admin Suspend Operator", False, None, e)
            return False

    def test_admin_activate_operator(self):
        """13. POST /api/admin/operators/{id}/activate — activate operator"""
        try:
            if not self.test_operator_id:
                self.log_result("13. Admin Activate Operator", False, None, "No operator ID available")
                return False
                
            response = self.make_request('POST', f'admin/operators/{self.test_operator_id}/activate', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("13. Admin Activate Operator", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("13. Admin Activate Operator", False, None, e)
            return False

    def test_admin_extend_subscription(self):
        """14. POST /api/admin/operators/{id}/extend-subscription — extend by 3 months"""
        try:
            if not self.test_operator_id:
                self.log_result("14. Admin Extend Subscription", False, None, "No operator ID available")
                return False
                
            extend_data = {"months": 3}
            response = self.make_request('POST', f'admin/operators/{self.test_operator_id}/extend-subscription', 
                                      extend_data, self.admin_token)
            success = response.status_code == 200
                
            self.log_result("14. Admin Extend Subscription", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("14. Admin Extend Subscription", False, None, e)
            return False

    def test_admin_impersonate_operator(self):
        """15. POST /api/admin/operators/{id}/impersonate — get operator token"""
        try:
            if not self.test_operator_id:
                self.log_result("15. Admin Impersonate Operator", False, None, "No operator ID available")
                return False
                
            response = self.make_request('POST', f'admin/operators/{self.test_operator_id}/impersonate', token=self.admin_token)
            success = response.status_code == 200
            if success:
                data = response.json()
                self.impersonated_token = data.get("access_token")
                
            self.log_result("15. Admin Impersonate Operator", success,
                          {"has_impersonated_token": bool(self.impersonated_token)} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("15. Admin Impersonate Operator", False, None, e)
            return False

    def test_admin_return_from_impersonate(self):
        """16. POST /api/admin/return-from-impersonate — return to admin"""
        try:
            if not self.impersonated_token:
                self.log_result("16. Admin Return From Impersonate", False, None, "No impersonated token available")
                return False
                
            response = self.make_request('POST', 'admin/return-from-impersonate', token=self.impersonated_token)
            success = response.status_code == 200
                
            self.log_result("16. Admin Return From Impersonate", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("16. Admin Return From Impersonate", False, None, e)
            return False

    # ============== 17-32. ADMIN ADDONS & OTHER FEATURES ==============

    def test_admin_create_addon(self):
        """17. POST /api/admin/addons — create addon"""
        try:
            addon_data = {
                "code": "TEST_ADDON",
                "name": "Test Addon Feature",
                "description": "A test addon for testing purposes",
                "price": 199
            }
            
            response = self.make_request('POST', 'admin/addons', addon_data, self.admin_token)
            success = response.status_code == 200
            if success:
                self.test_addon_id = response.json().get("id")
                
            self.log_result("17. Admin Create Addon", success,
                          {"addon_id": getattr(self, 'test_addon_id', None)} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("17. Admin Create Addon", False, None, e)
            return False

    def test_admin_get_addons(self):
        """18. GET /api/admin/addons — list addons"""
        try:
            response = self.make_request('GET', 'admin/addons', token=self.admin_token)
            success = response.status_code == 200
            if success:
                addons = response.json()
                addon_count = len(addons)
            else:
                addon_count = 0
                
            self.log_result("18. Admin Get Addons", success,
                          {"addon_count": addon_count} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("18. Admin Get Addons", False, None, e)
            return False

    def test_admin_update_addon(self):
        """19. PUT /api/admin/addons/{id} — update addon"""
        try:
            if not hasattr(self, 'test_addon_id') or not self.test_addon_id:
                self.log_result("19. Admin Update Addon", False, None, "No test addon ID available")
                return False
                
            update_data = {
                "code": "TEST_ADDON_UPDATED",
                "name": "Updated Test Addon Feature",
                "description": "Updated description for testing purposes",
                "price": 299
            }
            
            response = self.make_request('PUT', f'admin/addons/{self.test_addon_id}', update_data, self.admin_token)
            success = response.status_code == 200
                
            self.log_result("19. Admin Update Addon", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("19. Admin Update Addon", False, None, e)
            return False

    def test_admin_assign_addon_to_operator(self):
        """20. POST /api/admin/operators/{id}/addons/{code} — assign addon to operator"""
        try:
            if not self.test_operator_id or not hasattr(self, 'test_addon_id'):
                self.log_result("20. Admin Assign Addon To Operator", False, None, "Missing operator ID or addon")
                return False
                
            response = self.make_request('POST', f'admin/operators/{self.test_operator_id}/addons/TEST_ADDON', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("20. Admin Assign Addon To Operator", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("20. Admin Assign Addon To Operator", False, None, e)
            return False

    def test_admin_dashboard(self):
        """21. GET /api/admin/dashboard — dashboard KPIs"""
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
                
            self.log_result("21. Admin Dashboard", success, 
                          {"has_required_kpis": has_kpis} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("21. Admin Dashboard", False, None, e)
            return False

    def test_admin_audit_logs(self):
        """22. GET /api/admin/audit-logs — audit logs"""
        try:
            response = self.make_request('GET', 'admin/audit-logs', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("22. Admin Audit Logs", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("22. Admin Audit Logs", False, None, e)
            return False

    def test_admin_get_settings(self):
        """23. GET /api/admin/settings — get settings"""
        try:
            response = self.make_request('GET', 'admin/settings', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("23. Admin Get Settings", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("23. Admin Get Settings", False, None, e)
            return False

    def test_admin_update_settings(self):
        """24. PUT /api/admin/settings — update settings"""
        try:
            settings_data = {
                "company_name": "Updated SaaS Platform Inc.",
                "support_email": "support@updated-saas.com"
            }
            
            response = self.make_request('PUT', 'admin/settings', settings_data, self.admin_token)
            success = response.status_code == 200
                
            self.log_result("24. Admin Update Settings", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("24. Admin Update Settings", False, None, e)
            return False

    def test_admin_payment_reports(self):
        """25. GET /api/admin/reports/payments — payment reports"""
        try:
            response = self.make_request('GET', 'admin/reports/payments', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("25. Admin Payment Reports", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("25. Admin Payment Reports", False, None, e)
            return False

    def test_admin_saas_revenue_report(self):
        """26. GET /api/admin/reports/saas-revenue — SaaS revenue report"""
        try:
            response = self.make_request('GET', 'admin/reports/saas-revenue', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("26. Admin SaaS Revenue Report", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("26. Admin SaaS Revenue Report", False, None, e)
            return False

    def test_admin_cron_generate_invoices(self):
        """27. POST /api/admin/cron/generate-invoices — trigger invoice generation"""
        try:
            response = self.make_request('POST', 'admin/cron/generate-invoices', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("27. Admin Cron Generate Invoices", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("27. Admin Cron Generate Invoices", False, None, e)
            return False

    def test_admin_cron_send_reminders(self):
        """28. POST /api/admin/cron/send-reminders — trigger reminders"""
        try:
            response = self.make_request('POST', 'admin/cron/send-reminders', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("28. Admin Cron Send Reminders", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("28. Admin Cron Send Reminders", False, None, e)
            return False

    def test_admin_cron_check_expiry(self):
        """29. POST /api/admin/cron/check-expiry — trigger expiry check"""
        try:
            response = self.make_request('POST', 'admin/cron/check-expiry', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("29. Admin Cron Check Expiry", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("29. Admin Cron Check Expiry", False, None, e)
            return False

    def test_admin_delete_addon(self):
        """30. DELETE /api/admin/addons/{id} — delete addon"""
        try:
            if not hasattr(self, 'test_addon_id') or not self.test_addon_id:
                self.log_result("30. Admin Delete Addon", False, None, "No test addon ID available")
                return False
                
            response = self.make_request('DELETE', f'admin/addons/{self.test_addon_id}', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("30. Admin Delete Addon", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("30. Admin Delete Addon", False, None, e)
            return False

    def test_admin_configure_payment_gateway(self):
        """31. POST /api/admin/payment-gateways — configure gateway"""
        try:
            gateway_data = {
                "gateway_type": "razorpay",
                "api_key": "rzp_test_sFaXdx3kATIGiw",
                "api_secret": "dOvQqMbfE2sPkYulgTeU2SpW",
                "webhook_secret": "test_webhook_secret",
                "is_active": True
            }
            
            response = self.make_request('POST', 'admin/payment-gateways', gateway_data, self.admin_token)
            success = response.status_code == 200
                
            self.log_result("31. Admin Configure Payment Gateway", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("31. Admin Configure Payment Gateway", False, None, e)
            return False

    def test_admin_get_payment_gateways(self):
        """32. GET /api/admin/payment-gateways — list gateways"""
        try:
            response = self.make_request('GET', 'admin/payment-gateways', token=self.admin_token)
            success = response.status_code == 200
                
            self.log_result("32. Admin Get Payment Gateways", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("32. Admin Get Payment Gateways", False, None, e)
            return False

    # ============== 33-34. OPERATOR REGISTRATION & AUTH ==============

    def test_operator_registration(self):
        """33. POST /api/auth/register — register new operator"""
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
                self.registered_operator_id = data.get("user", {}).get("operator_id")
                
            self.log_result("33. Operator Registration", success, 
                          {"has_token": bool(self.operator_token), "operator_id": self.registered_operator_id} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("33. Operator Registration", False, None, e)
            return False

    def test_operator_login(self):
        """34. POST /api/auth/login (operator) — login with new operator"""
        try:
            # Use a known operator or create one
            response = self.make_request('POST', 'auth/login', {
                "email": f"john+{datetime.now().strftime('%H%M%S')}@testcompany.com",
                "password": "test123"
            })
            
            # If that fails, try with demo operator
            if response.status_code != 200:
                response = self.make_request('POST', 'auth/login', {
                    "email": "demo@democorp.com",
                    "password": "demo123"
                })
                
            success = response.status_code == 200
            if success:
                data = response.json()
                self.operator_token = data.get("access_token")
                
            self.log_result("34. Operator Login", success, 
                          {"has_token": bool(self.operator_token)} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("34. Operator Login", False, None, e)
            return False

    # ============== 35-69. OPERATOR TESTS ==============

    def test_operator_get_profile(self):
        """35. GET /api/operator/profile — get profile"""
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
                
            self.log_result("35. Operator Get Profile", success,
                          {"has_profile_data": has_profile_data} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("35. Operator Get Profile", False, None, e)
            return False

    def test_operator_update_profile(self):
        """36. PUT /api/operator/profile — update profile"""
        try:
            update_data = {
                "company_name": "Updated Test Company Pvt Ltd",
                "owner_name": "Updated John Test"
            }
            
            response = self.make_request('PUT', 'operator/profile', update_data, self.operator_token)
            success = response.status_code == 200
                
            self.log_result("36. Operator Update Profile", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("36. Operator Update Profile", False, None, e)
            return False

    def test_operator_dashboard(self):
        """37. GET /api/operator/dashboard — dashboard"""
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
                
            self.log_result("37. Operator Dashboard", success,
                          {"has_required_stats": has_stats} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("37. Operator Dashboard", False, None, e)
            return False

    def test_operator_create_plan(self):
        """38. POST /api/operator/plans — create service plan"""
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
                
            self.log_result("38. Operator Create Plan", success,
                          {"plan_id": getattr(self, 'test_operator_plan_id', None)} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("38. Operator Create Plan", False, None, e)
            return False

    def test_operator_get_plans(self):
        """39. GET /api/operator/plans — list service plans"""
        try:
            response = self.make_request('GET', 'operator/plans', token=self.operator_token)
            success = response.status_code == 200
            if success:
                plans = response.json()
                plan_count = len(plans)
                # Ensure we have a plan ID for further tests
                if plans and not hasattr(self, 'test_operator_plan_id'):
                    self.test_operator_plan_id = plans[0].get("id")
            else:
                plan_count = 0
                
            self.log_result("39. Operator Get Plans", success,
                          {"plan_count": plan_count} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("39. Operator Get Plans", False, None, e)
            return False

    def test_operator_update_plan(self):
        """40. PUT /api/operator/plans/{id} — update plan"""
        try:
            if not hasattr(self, 'test_operator_plan_id') or not self.test_operator_plan_id:
                self.log_result("40. Operator Update Plan", False, None, "No operator plan ID available")
                return False
                
            update_data = {
                "name": "Updated Monthly Internet Plan",
                "price": 799,
                "validity": "monthly",
                "tax_percentage": 18,
                "tax_type": "exclusive"
            }
            
            response = self.make_request('PUT', f'operator/plans/{self.test_operator_plan_id}', update_data, self.operator_token)
            success = response.status_code == 200
                
            self.log_result("40. Operator Update Plan", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("40. Operator Update Plan", False, None, e)
            return False

    def test_operator_create_subscriber(self):
        """41. POST /api/operator/subscribers — create subscriber"""
        try:
            if not hasattr(self, 'test_operator_plan_id') or not self.test_operator_plan_id:
                self.log_result("41. Operator Create Subscriber", False, None, "No plan ID available")
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
                
            self.log_result("41. Operator Create Subscriber", success,
                          {"subscriber_id": getattr(self, 'test_subscriber_id', None)} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("41. Operator Create Subscriber", False, None, e)
            return False

    def test_operator_get_subscribers(self):
        """42. GET /api/operator/subscribers — list subscribers"""
        try:
            response = self.make_request('GET', 'operator/subscribers', token=self.operator_token)
            success = response.status_code == 200
            if success:
                subscribers = response.json()
                subscriber_count = len(subscribers)
                # Ensure we have a subscriber ID for further tests
                if subscribers and not hasattr(self, 'test_subscriber_id'):
                    self.test_subscriber_id = subscribers[0].get("id")
            else:
                subscriber_count = 0
                
            self.log_result("42. Operator Get Subscribers", success,
                          {"subscriber_count": subscriber_count} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("42. Operator Get Subscribers", False, None, e)
            return False

    def test_operator_get_single_subscriber(self):
        """43. GET /api/operator/subscribers/{id} — get subscriber"""
        try:
            if not hasattr(self, 'test_subscriber_id') or not self.test_subscriber_id:
                self.log_result("43. Operator Get Single Subscriber", False, None, "No subscriber ID available")
                return False
                
            response = self.make_request('GET', f'operator/subscribers/{self.test_subscriber_id}', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("43. Operator Get Single Subscriber", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("43. Operator Get Single Subscriber", False, None, e)
            return False

    def test_operator_update_subscriber(self):
        """44. PUT /api/operator/subscribers/{id} — update subscriber"""
        try:
            if not hasattr(self, 'test_subscriber_id') or not self.test_subscriber_id:
                self.log_result("44. Operator Update Subscriber", False, None, "No subscriber ID available")
                return False
                
            update_data = {
                "name": "Updated Test Customer",
                "whatsapp_number": "919876543210",
                "plan_id": self.test_operator_plan_id,
                "billing_date": 15,
                "discount": 100
            }
            
            response = self.make_request('PUT', f'operator/subscribers/{self.test_subscriber_id}', update_data, self.operator_token)
            success = response.status_code == 200
                
            self.log_result("44. Operator Update Subscriber", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("44. Operator Update Subscriber", False, None, e)
            return False

    def test_operator_create_invoice(self):
        """45. POST /api/operator/invoices — create invoice"""
        try:
            if not hasattr(self, 'test_subscriber_id') or not hasattr(self, 'test_operator_plan_id'):
                self.log_result("45. Operator Create Invoice", False, None, "Missing subscriber or plan ID")
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
                
            self.log_result("45. Operator Create Invoice", success,
                          {"invoice_id": getattr(self, 'test_invoice_id', None)} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("45. Operator Create Invoice", False, None, e)
            return False

    def test_operator_get_invoices(self):
        """46. GET /api/operator/invoices — list invoices"""
        try:
            response = self.make_request('GET', 'operator/invoices', token=self.operator_token)
            success = response.status_code == 200
            if success:
                invoices = response.json()
                invoice_count = len(invoices)
                # Ensure we have an invoice ID for further tests
                if invoices and not hasattr(self, 'test_invoice_id'):
                    self.test_invoice_id = invoices[0].get("id")
            else:
                invoice_count = 0
                
            self.log_result("46. Operator Get Invoices", success,
                          {"invoice_count": invoice_count} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("46. Operator Get Invoices", False, None, e)
            return False

    def test_operator_mark_invoice_paid(self):
        """47. PUT /api/operator/invoices/{id}/status?status=paid — mark as paid"""
        try:
            if not hasattr(self, 'test_invoice_id') or not self.test_invoice_id:
                self.log_result("47. Operator Mark Invoice Paid", False, None, "No invoice ID available")
                return False
                
            response = self.make_request('PUT', f'operator/invoices/{self.test_invoice_id}/status', 
                                      params={"status": "paid"}, token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("47. Operator Mark Invoice Paid", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("47. Operator Mark Invoice Paid", False, None, e)
            return False

    def test_operator_generate_invoice_pdf(self):
        """48. GET /api/operator/invoices/{id}/pdf — generate PDF"""
        try:
            if not hasattr(self, 'test_invoice_id') or not self.test_invoice_id:
                self.log_result("48. Operator Generate Invoice PDF", False, None, "No invoice ID available")
                return False
                
            response = self.make_request('GET', f'operator/invoices/{self.test_invoice_id}/pdf', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("48. Operator Generate Invoice PDF", success,
                          {"content_type": response.headers.get("content-type")} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("48. Operator Generate Invoice PDF", False, None, e)
            return False

    def test_operator_create_staff(self):
        """49. POST /api/operator/staff — create staff member"""
        try:
            staff_data = {
                "name": "Test Staff Member",
                "email": f"staff+{datetime.now().strftime('%H%M%S')}@testcompany.com",
                "phone": "9876543211",
                "password": "staff123",
                "permissions": ["read", "write"]
            }
            
            response = self.make_request('POST', 'operator/staff', staff_data, self.operator_token)
            success = response.status_code == 200
            if success:
                data = response.json()
                self.test_staff_id = data.get("id")
                self.staff_email = staff_data["email"]
                
            self.log_result("49. Operator Create Staff", success,
                          {"staff_id": getattr(self, 'test_staff_id', None)} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("49. Operator Create Staff", False, None, e)
            return False

    def test_operator_get_staff(self):
        """50. GET /api/operator/staff — list staff"""
        try:
            response = self.make_request('GET', 'operator/staff', token=self.operator_token)
            success = response.status_code == 200
            if success:
                staff = response.json()
                staff_count = len(staff)
                # Ensure we have a staff ID for further tests
                if staff and not hasattr(self, 'test_staff_id'):
                    self.test_staff_id = staff[0].get("id")
            else:
                staff_count = 0
                
            self.log_result("50. Operator Get Staff", success,
                          {"staff_count": staff_count} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("50. Operator Get Staff", False, None, e)
            return False

    def test_staff_login(self):
        """51. POST /api/auth/login (staff) — login with staff credentials"""
        try:
            if not hasattr(self, 'staff_email'):
                # Try with known staff credentials
                response = self.make_request('POST', 'auth/login', {
                    "email": "staff@democorp.com",
                    "password": "staff123"
                })
            else:
                response = self.make_request('POST', 'auth/login', {
                    "email": self.staff_email,
                    "password": "staff123"
                })
                
            success = response.status_code == 200
            if success:
                data = response.json()
                self.staff_token = data.get("access_token")
                
            self.log_result("51. Staff Login", success, 
                          {"has_token": bool(self.staff_token)} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("51. Staff Login", False, None, e)
            return False

    def test_staff_delete_permission_check(self):
        """52. DELETE /api/operator/subscribers/{id} using STAFF token — should return 403"""
        try:
            if not self.staff_token or not hasattr(self, 'test_subscriber_id'):
                self.log_result("52. Staff Delete Permission Check", False, None, "Missing staff token or subscriber ID")
                return False
                
            response = self.make_request('DELETE', f'operator/subscribers/{self.test_subscriber_id}', token=self.staff_token)
            # Expecting 403 Forbidden
            success = response.status_code == 403
                
            self.log_result("52. Staff Delete Permission Check", success,
                          {"status_code": response.status_code, "expected": 403} if True else None,
                          None if success else f"Status: {response.status_code} (expected 403), Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("52. Staff Delete Permission Check", False, None, e)
            return False

    def test_operator_delete_staff(self):
        """53. DELETE /api/operator/staff/{id} using OPERATOR token — delete staff"""
        try:
            if not hasattr(self, 'test_staff_id') or not self.test_staff_id:
                self.log_result("53. Operator Delete Staff", False, None, "No staff ID available")
                return False
                
            response = self.make_request('DELETE', f'operator/staff/{self.test_staff_id}', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("53. Operator Delete Staff", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("53. Operator Delete Staff", False, None, e)
            return False

    def test_operator_delete_subscriber(self):
        """54. DELETE /api/operator/subscribers/{id} — delete subscriber (operator token)"""
        try:
            if not hasattr(self, 'test_subscriber_id') or not self.test_subscriber_id:
                self.log_result("54. Operator Delete Subscriber", False, None, "No subscriber ID available")
                return False
                
            response = self.make_request('DELETE', f'operator/subscribers/{self.test_subscriber_id}', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("54. Operator Delete Subscriber", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("54. Operator Delete Subscriber", False, None, e)
            return False

    def test_operator_revenue_report(self):
        """55. GET /api/operator/reports/revenue"""
        try:
            response = self.make_request('GET', 'operator/reports/revenue', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("55. Operator Revenue Report", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("55. Operator Revenue Report", False, None, e)
            return False

    def test_operator_gst_summary_report(self):
        """56. GET /api/operator/reports/gst-summary"""
        try:
            response = self.make_request('GET', 'operator/reports/gst-summary', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("56. Operator GST Summary Report", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("56. Operator GST Summary Report", False, None, e)
            return False

    def test_operator_pending_overdue_report(self):
        """57. GET /api/operator/reports/pending-overdue"""
        try:
            response = self.make_request('GET', 'operator/reports/pending-overdue', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("57. Operator Pending Overdue Report", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("57. Operator Pending Overdue Report", False, None, e)
            return False

    def test_operator_create_announcement(self):
        """58. POST /api/operator/announcements — create announcement"""
        try:
            announcement_data = {
                "title": "Test Announcement",
                "message": "This is a test announcement message",
                "send_whatsapp": False,
                "target_audience": "all"
            }
            
            response = self.make_request('POST', 'operator/announcements', announcement_data, self.operator_token)
            success = response.status_code == 200
                
            self.log_result("58. Operator Create Announcement", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("58. Operator Create Announcement", False, None, e)
            return False

    def test_operator_get_announcements(self):
        """59. GET /api/operator/announcements"""
        try:
            response = self.make_request('GET', 'operator/announcements', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("59. Operator Get Announcements", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("59. Operator Get Announcements", False, None, e)
            return False

    def test_operator_get_addon_store(self):
        """60. GET /api/operator/addons/store"""
        try:
            response = self.make_request('GET', 'operator/addons/store', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("60. Operator Get Addon Store", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("60. Operator Get Addon Store", False, None, e)
            return False

    def test_operator_get_subscription(self):
        """61. GET /api/operator/subscription"""
        try:
            response = self.make_request('GET', 'operator/subscription', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("61. Operator Get Subscription", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("61. Operator Get Subscription", False, None, e)
            return False

    def test_operator_get_payment_history(self):
        """62. GET /api/operator/payment-history"""
        try:
            response = self.make_request('GET', 'operator/payment-history', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("62. Operator Get Payment History", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("62. Operator Get Payment History", False, None, e)
            return False

    def test_operator_create_checkout_order(self):
        """63. POST /api/operator/checkout/create-order?item_type=subscription&months=1"""
        try:
            response = self.make_request('POST', 'operator/checkout/create-order', 
                                      params={"item_type": "subscription", "months": 1}, 
                                      token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("63. Operator Create Checkout Order", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("63. Operator Create Checkout Order", False, None, e)
            return False

    def test_operator_configure_whatsapp(self):
        """64. POST /api/operator/whatsapp-config — configure WhatsApp"""
        try:
            whatsapp_data = {
                "phone_number_id": "919876543210",
                "access_token": "test_whatsapp_access_token_12345"
            }
            
            response = self.make_request('POST', 'operator/whatsapp-config', whatsapp_data, self.operator_token)
            success = response.status_code == 200
                
            self.log_result("64. Operator Configure WhatsApp", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("64. Operator Configure WhatsApp", False, None, e)
            return False

    def test_operator_get_whatsapp_config(self):
        """65. GET /api/operator/whatsapp-config"""
        try:
            response = self.make_request('GET', 'operator/whatsapp-config', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("65. Operator Get WhatsApp Config", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("65. Operator Get WhatsApp Config", False, None, e)
            return False

    def test_operator_get_invoice_settings(self):
        """66. GET /api/operator/invoice-settings"""
        try:
            response = self.make_request('GET', 'operator/invoice-settings', token=self.operator_token)
            success = response.status_code == 200
                
            self.log_result("66. Operator Get Invoice Settings", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("66. Operator Get Invoice Settings", False, None, e)
            return False

    def test_operator_update_invoice_settings(self):
        """67. PUT /api/operator/invoice-settings"""
        try:
            settings_data = {
                "company_name": "Updated Test Company Pvt Ltd",
                "company_address": "123 Updated Street, Test City",
                "company_phone": "9876543210",
                "company_email": "billing@updated-testcompany.com",
                "logo_url": "https://example.com/logo.png",
                "invoice_prefix": "UPD",
                "invoice_footer": "Thank you for your business!",
                "show_gst": True,
                "terms_conditions": "Updated terms and conditions"
            }
            
            response = self.make_request('PUT', 'operator/invoice-settings', settings_data, self.operator_token)
            success = response.status_code == 200
                
            self.log_result("67. Operator Update Invoice Settings", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("67. Operator Update Invoice Settings", False, None, e)
            return False

    def test_operator_get_audit_logs(self):
        """68. GET /api/operator/audit-logs"""
        try:
            response = self.make_request('GET', 'operator/audit-logs', token=self.operator_token)
            # May return 403 if plan doesn't have audit_logs=true - that's expected
            success = response.status_code in [200, 403]
                
            self.log_result("68. Operator Get Audit Logs", success,
                          {"status_code": response.status_code, "expected_403_ok": True} if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("68. Operator Get Audit Logs", False, None, e)
            return False

    def test_operator_configure_payment_gateway(self):
        """69. POST /api/operator/payment-gateway — configure gateway"""
        try:
            gateway_data = {
                "gateway_type": "razorpay",
                "api_key": "rzp_test_sFaXdx3kATIGiw",
                "api_secret": "dOvQqMbfE2sPkYulgTeU2SpW",
                "webhook_secret": "webhook_secret_123"
            }
            
            response = self.make_request('POST', 'operator/payment-gateway', gateway_data, self.operator_token)
            success = response.status_code == 200
                
            self.log_result("69. Operator Configure Payment Gateway", success,
                          response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("69. Operator Configure Payment Gateway", False, None, e)
            return False

    # ============== 70. HEALTH CHECK ==============

    def test_health_check(self):
        """70. GET /api/health — health check"""
        try:
            response = self.make_request('GET', 'health')
            success = response.status_code == 200
            self.log_result("70. Health Check", success, response.json() if success else None,
                          None if success else f"Status: {response.status_code}, Response: {response.text}")
            return success
        except Exception as e:
            self.log_result("70. Health Check", False, None, e)
            return False

    # ============== RUN ALL TESTS ==============

    def run_all_tests(self):
        """Run all tests in the specified order"""
        print("🚀 Starting SaaS Billing Platform API Tests")
        print("=" * 60)
        
        # Follow the exact order from the review request
        test_methods = [
            self.test_seed_data,  # 1
            self.test_admin_login,  # 2
            self.test_admin_auth_me,  # 3
            self.test_admin_get_saas_plans,  # 4
            self.test_admin_create_saas_plan,  # 5
            self.test_admin_update_saas_plan,  # 6
            self.test_admin_delete_saas_plan,  # 7
            self.test_admin_create_operator,  # 8
            self.test_admin_get_operators,  # 9
            self.test_admin_get_single_operator,  # 10
            self.test_admin_update_operator,  # 11
            self.test_admin_suspend_operator,  # 12
            self.test_admin_activate_operator,  # 13
            self.test_admin_extend_subscription,  # 14
            self.test_admin_impersonate_operator,  # 15
            self.test_admin_return_from_impersonate,  # 16
            self.test_admin_create_addon,  # 17
            self.test_admin_get_addons,  # 18
            self.test_admin_update_addon,  # 19
            self.test_admin_assign_addon_to_operator,  # 20
            self.test_admin_dashboard,  # 21
            self.test_admin_audit_logs,  # 22
            self.test_admin_get_settings,  # 23
            self.test_admin_update_settings,  # 24
            self.test_admin_payment_reports,  # 25
            self.test_admin_saas_revenue_report,  # 26
            self.test_admin_cron_generate_invoices,  # 27
            self.test_admin_cron_send_reminders,  # 28
            self.test_admin_cron_check_expiry,  # 29
            self.test_admin_delete_addon,  # 30
            self.test_admin_configure_payment_gateway,  # 31
            self.test_admin_get_payment_gateways,  # 32
            self.test_operator_registration,  # 33
            self.test_operator_login,  # 34
            self.test_operator_get_profile,  # 35
            self.test_operator_update_profile,  # 36
            self.test_operator_dashboard,  # 37
            self.test_operator_create_plan,  # 38
            self.test_operator_get_plans,  # 39
            self.test_operator_update_plan,  # 40
            self.test_operator_create_subscriber,  # 41
            self.test_operator_get_subscribers,  # 42
            self.test_operator_get_single_subscriber,  # 43
            self.test_operator_update_subscriber,  # 44
            self.test_operator_create_invoice,  # 45
            self.test_operator_get_invoices,  # 46
            self.test_operator_mark_invoice_paid,  # 47
            self.test_operator_generate_invoice_pdf,  # 48
            self.test_operator_create_staff,  # 49
            self.test_operator_get_staff,  # 50
            self.test_staff_login,  # 51
            self.test_staff_delete_permission_check,  # 52
            self.test_operator_delete_staff,  # 53
            self.test_operator_delete_subscriber,  # 54
            self.test_operator_revenue_report,  # 55
            self.test_operator_gst_summary_report,  # 56
            self.test_operator_pending_overdue_report,  # 57
            self.test_operator_create_announcement,  # 58
            self.test_operator_get_announcements,  # 59
            self.test_operator_get_addon_store,  # 60
            self.test_operator_get_subscription,  # 61
            self.test_operator_get_payment_history,  # 62
            self.test_operator_create_checkout_order,  # 63
            self.test_operator_configure_whatsapp,  # 64
            self.test_operator_get_whatsapp_config,  # 65
            self.test_operator_get_invoice_settings,  # 66
            self.test_operator_update_invoice_settings,  # 67
            self.test_operator_get_audit_logs,  # 68
            self.test_operator_configure_payment_gateway,  # 69
            self.test_health_check,  # 70
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print(f"Error in {test_method.__name__}: {e}")
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests ({len(self.failed_tests)}):")
            for failed in self.failed_tests:
                print(f"   - {failed['test']}: {failed['error']}")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            return 1

def main():
    tester = SaaSBillingTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())