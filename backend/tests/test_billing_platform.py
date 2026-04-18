"""
Multi-Tenant SaaS Billing Platform API Tests
Tests cover: Admin, Operator, Staff role restrictions, impersonation, and CRUD operations
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://analyze-code-14.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"
OPERATOR_EMAIL = "demo@democorp.com"
OPERATOR_PASSWORD = "demo123"
STAFF_EMAIL = "staff@democorp.com"
STAFF_PASSWORD = "staff123"

class TestHealthCheck:
    """Health check endpoint tests"""
    
    def test_health_endpoint(self):
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("Health check passed")


class TestAdminAuth:
    """Admin authentication and dashboard tests"""
    
    def test_admin_login_success(self):
        """Admin login with admin@saas.com/admin123"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"Admin login successful: {data['user']['name']}")
        return data["access_token"]
    
    def test_admin_dashboard_kpis(self):
        """Admin dashboard loads with KPIs"""
        token = self.test_admin_login_success()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify KPI fields exist
        assert "total_operators" in data
        assert "active_operators" in data
        assert "trial_operators" in data
        assert "suspended_operators" in data
        print(f"Admin Dashboard KPIs: Total={data['total_operators']}, Active={data['active_operators']}, Trial={data['trial_operators']}")


class TestAdminOperators:
    """Admin operators management tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_operators_list(self, admin_token):
        """Admin can view operators list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/operators", headers=headers)
        assert response.status_code == 200
        operators = response.json()
        assert isinstance(operators, list)
        print(f"Found {len(operators)} operators")
        return operators
    
    def test_impersonate_operator(self, admin_token):
        """Admin can impersonate operator (Login as Operator)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get operators list
        response = requests.get(f"{BASE_URL}/api/admin/operators", headers=headers)
        operators = response.json()
        
        if not operators:
            pytest.skip("No operators to impersonate")
        
        # Impersonate first operator
        operator_id = operators[0]["id"]
        response = requests.post(f"{BASE_URL}/api/admin/operators/{operator_id}/impersonate", headers=headers)
        assert response.status_code == 200, f"Impersonation failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["operator"]["id"] == operator_id
        print(f"Successfully impersonated operator: {data['operator']['company_name']}")
    
    def test_suspend_activate_operator(self, admin_token):
        """Admin can suspend and activate operators"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/operators", headers=headers)
        operators = response.json()
        
        if not operators:
            pytest.skip("No operators to suspend")
        
        operator_id = operators[0]["id"]
        original_status = operators[0]["status"]
        
        # Test suspend
        response = requests.post(f"{BASE_URL}/api/admin/operators/{operator_id}/suspend", headers=headers)
        assert response.status_code == 200
        print(f"Operator {operator_id} suspended")
        
        # Test activate
        response = requests.post(f"{BASE_URL}/api/admin/operators/{operator_id}/activate", headers=headers)
        assert response.status_code == 200
        print(f"Operator {operator_id} activated")


class TestAdminSettings:
    """Admin settings page tests - General, Payment Gateways, Add-ons tabs"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_global_settings(self, admin_token):
        """General tab - Get global settings"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/settings", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "active_payment_gateway" in data
        assert "gst_rate" in data
        print(f"Global settings: Gateway={data.get('active_payment_gateway')}, GST={data.get('gst_rate')}%")
    
    def test_get_payment_gateways(self, admin_token):
        """Payment Gateways tab - Get configured gateways"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/payment-gateways", headers=headers)
        assert response.status_code == 200
        gateways = response.json()
        assert isinstance(gateways, list)
        print(f"Found {len(gateways)} payment gateways configured")
    
    def test_get_addons(self, admin_token):
        """Add-ons tab - Get available addons"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/addons", headers=headers)
        assert response.status_code == 200
        addons = response.json()
        assert isinstance(addons, list)
        print(f"Found {len(addons)} add-ons")


class TestAdminReports:
    """Admin reports page tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_payment_reports(self, admin_token):
        """Payment reports with KPIs"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/reports/payments", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_invoices" in data
        assert "total_revenue" in data
        assert "total_tax" in data
        print(f"Payment Reports: Invoices={data['total_invoices']}, Revenue=₹{data['total_revenue']}")
    
    def test_get_saas_revenue(self, admin_token):
        """SaaS Revenue tab"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/reports/saas-revenue", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_payments" in data
        assert "total_revenue" in data
        print(f"SaaS Revenue: Payments={data['total_payments']}, Revenue=₹{data['total_revenue']}")


class TestOperatorAuth:
    """Operator authentication tests"""
    
    def test_operator_login_success(self):
        """Operator login with demo@democorp.com/demo123"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OPERATOR_EMAIL,
            "password": OPERATOR_PASSWORD
        })
        assert response.status_code == 200, f"Operator login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "operator"
        print(f"Operator login successful: {data['user']['name']}")
        return data["access_token"]
    
    def test_operator_dashboard(self):
        """Operator dashboard loads"""
        token = self.test_operator_login_success()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/operator/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_subscribers" in data
        assert "total_invoices" in data
        print(f"Operator Dashboard: Subscribers={data['total_subscribers']}, Invoices={data['total_invoices']}")


class TestOperatorCRUD:
    """Operator CRUD operations for subscribers, plans, invoices"""
    
    @pytest.fixture
    def operator_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OPERATOR_EMAIL,
            "password": OPERATOR_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_crud_plans(self, operator_token):
        """Create, Read, Update operator plans"""
        headers = {"Authorization": f"Bearer {operator_token}"}
        
        # Create plan
        plan_data = {
            "name": "TEST_Monthly Premium",
            "price": 999,
            "validity": "monthly",
            "tax_percentage": 18,
            "tax_type": "exclusive",
            "description": "Test plan"
        }
        response = requests.post(f"{BASE_URL}/api/operator/plans", json=plan_data, headers=headers)
        assert response.status_code == 200
        plan = response.json()
        plan_id = plan["id"]
        print(f"Created plan: {plan['name']} (ID: {plan_id})")
        
        # Read plans
        response = requests.get(f"{BASE_URL}/api/operator/plans", headers=headers)
        assert response.status_code == 200
        plans = response.json()
        assert any(p["id"] == plan_id for p in plans)
        print(f"Verified plan in list of {len(plans)} plans")
        
        # Update plan
        plan_data["name"] = "TEST_Updated Premium"
        plan_data["price"] = 1199
        response = requests.put(f"{BASE_URL}/api/operator/plans/{plan_id}", json=plan_data, headers=headers)
        assert response.status_code == 200
        updated = response.json()
        assert updated["price"] == 1199
        print(f"Updated plan price to ₹{updated['price']}")
        
        return plan_id
    
    def test_crud_subscribers(self, operator_token):
        """Create, Read, Update operator subscribers"""
        headers = {"Authorization": f"Bearer {operator_token}"}
        
        # Get a plan first
        response = requests.get(f"{BASE_URL}/api/operator/plans", headers=headers)
        plans = response.json()
        if not plans:
            pytest.skip("No plans available for subscriber creation")
        plan_id = plans[0]["id"]
        
        # Create subscriber
        sub_data = {
            "name": "TEST_John Doe",
            "whatsapp_number": "9876543210",
            "email": "test@example.com",
            "address": "123 Test Street",
            "plan_id": plan_id,
            "billing_date": 15,
            "discount": 50
        }
        response = requests.post(f"{BASE_URL}/api/operator/subscribers", json=sub_data, headers=headers)
        assert response.status_code == 200
        subscriber = response.json()
        sub_id = subscriber["id"]
        print(f"Created subscriber: {subscriber['name']}")
        
        # Read subscribers
        response = requests.get(f"{BASE_URL}/api/operator/subscribers", headers=headers)
        assert response.status_code == 200
        subscribers = response.json()
        assert any(s["id"] == sub_id for s in subscribers)
        print(f"Found {len(subscribers)} subscribers")
        
        return sub_id, plan_id
    
    def test_invoice_pdf_download(self, operator_token):
        """Test invoice PDF generation"""
        headers = {"Authorization": f"Bearer {operator_token}"}
        
        # Get invoices
        response = requests.get(f"{BASE_URL}/api/operator/invoices", headers=headers)
        assert response.status_code == 200
        invoices = response.json()
        
        if not invoices:
            pytest.skip("No invoices available for PDF test")
        
        invoice_id = invoices[0]["id"]
        
        # Download PDF
        response = requests.get(f"{BASE_URL}/api/operator/invoices/{invoice_id}/pdf", headers=headers)
        assert response.status_code == 200, f"PDF download failed: {response.status_code}"
        assert response.headers.get("content-type") == "application/pdf"
        print(f"PDF downloaded for invoice {invoice_id}")


class TestStaffRole:
    """Staff role restrictions tests"""
    
    def test_staff_login_success(self):
        """Staff login with staff@democorp.com/staff123"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        assert response.status_code == 200, f"Staff login failed: {response.text}"
        data = response.json()
        assert data["user"]["role"] == "staff"
        print(f"Staff login successful: {data['user']['name']}, role={data['user']['role']}")
        return data["access_token"]
    
    def test_staff_can_view_subscribers(self):
        """Staff can view subscribers"""
        token = self.test_staff_login_success()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/operator/subscribers", headers=headers)
        assert response.status_code == 200
        subscribers = response.json()
        print(f"Staff can view {len(subscribers)} subscribers")
    
    def test_staff_can_view_plans(self):
        """Staff can view plans"""
        token = self.test_staff_login_success()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/operator/plans", headers=headers)
        assert response.status_code == 200
        plans = response.json()
        print(f"Staff can view {len(plans)} plans")
    
    def test_staff_cannot_delete_plans(self):
        """Staff DELETE /api/operator/plans/{id} should return 403"""
        token = self.test_staff_login_success()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get plans list first
        response = requests.get(f"{BASE_URL}/api/operator/plans", headers=headers)
        plans = response.json()
        
        if not plans:
            pytest.skip("No plans to test delete restriction")
        
        plan_id = plans[0]["id"]
        
        # Try to delete - should get 403
        response = requests.delete(f"{BASE_URL}/api/operator/plans/{plan_id}", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Staff correctly blocked from deleting plan (403)")
    
    def test_staff_cannot_delete_subscribers(self):
        """Staff DELETE /api/operator/subscribers/{id} should return 403"""
        token = self.test_staff_login_success()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get subscribers list first
        response = requests.get(f"{BASE_URL}/api/operator/subscribers", headers=headers)
        subscribers = response.json()
        
        if not subscribers:
            pytest.skip("No subscribers to test delete restriction")
        
        subscriber_id = subscribers[0]["id"]
        
        # Try to delete - should get 403
        response = requests.delete(f"{BASE_URL}/api/operator/subscribers/{subscriber_id}", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Staff correctly blocked from deleting subscriber (403)")


class TestOperatorRegistration:
    """Operator registration tests"""
    
    def test_register_new_operator(self):
        """Register new operator at /register page"""
        unique_id = datetime.now().strftime("%H%M%S")
        reg_data = {
            "company_name": f"TEST_Company_{unique_id}",
            "owner_name": f"Test Owner {unique_id}",
            "email": f"test_{unique_id}@testcompany.com",
            "phone": "9999999999",
            "password": "testpass123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=reg_data)
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "operator"
        print(f"Registered new operator: {data['user']['name']}")


class TestLandingPage:
    """Landing page tests"""
    
    def test_landing_page_loads(self):
        """Landing page at / loads correctly"""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        print("Landing page loads successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
