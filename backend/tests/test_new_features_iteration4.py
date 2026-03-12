"""
Multi-Tenant SaaS Billing Platform - Iteration 4 Tests
Testing 5 NEW features requested by user:
1. Create Operator dialog field alignment
2. Delete operators from admin panel  
3. Add-ons to SaaS plans
4. Payment gateways config for Operator-to-Admin payments
5. Admin addon full CRUD (add, update, delete)
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://goofy-yonath-2.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"

class TestAdminAddonsCRUD:
    """Feature 5: Admin addon full CRUD - POST, GET, PUT, DELETE"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_create_addon(self, admin_token):
        """POST /api/admin/addons - Create a new addon"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        unique_code = f"test_addon_{datetime.now().strftime('%H%M%S')}"
        addon_data = {
            "name": "TEST Premium Feature",
            "code": unique_code,
            "price": 299,
            "description": "Test addon for premium features"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/addons", json=addon_data, headers=headers)
        assert response.status_code == 200, f"Create addon failed: {response.text}"
        
        addon = response.json()
        assert addon["name"] == "TEST Premium Feature"
        assert addon["code"] == unique_code
        assert addon["price"] == 299
        assert addon["description"] == "Test addon for premium features"
        print(f"PASS: Created addon '{addon['name']}' with code '{addon['code']}'")
        return addon["id"]
    
    def test_get_all_addons(self, admin_token):
        """GET /api/admin/addons - List all addons"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/addons", headers=headers)
        assert response.status_code == 200, f"Get addons failed: {response.text}"
        
        addons = response.json()
        assert isinstance(addons, list)
        print(f"PASS: Retrieved {len(addons)} addons")
        return addons
    
    def test_update_addon(self, admin_token):
        """PUT /api/admin/addons/{id} - Update addon name, price, description"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First create an addon to update
        unique_code = f"update_test_{datetime.now().strftime('%H%M%S')}"
        create_data = {
            "name": "To Be Updated",
            "code": unique_code,
            "price": 100,
            "description": "Original description"
        }
        create_resp = requests.post(f"{BASE_URL}/api/admin/addons", json=create_data, headers=headers)
        assert create_resp.status_code == 200
        addon_id = create_resp.json()["id"]
        
        # Now update it
        update_data = {
            "name": "Updated Addon Name",
            "code": unique_code,  # Code stays same
            "price": 399,
            "description": "Updated description with more info"
        }
        
        response = requests.put(f"{BASE_URL}/api/admin/addons/{addon_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Update addon failed: {response.text}"
        
        updated = response.json()
        assert updated["name"] == "Updated Addon Name"
        assert updated["price"] == 399
        assert updated["description"] == "Updated description with more info"
        print(f"PASS: Updated addon to name='{updated['name']}', price=₹{updated['price']}")
        return addon_id
    
    def test_delete_addon(self, admin_token):
        """DELETE /api/admin/addons/{id} - Soft delete addon"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First create an addon to delete
        unique_code = f"delete_test_{datetime.now().strftime('%H%M%S')}"
        create_data = {
            "name": "To Be Deleted",
            "code": unique_code,
            "price": 50,
            "description": "This addon will be deleted"
        }
        create_resp = requests.post(f"{BASE_URL}/api/admin/addons", json=create_data, headers=headers)
        assert create_resp.status_code == 200
        addon_id = create_resp.json()["id"]
        
        # Delete the addon
        response = requests.delete(f"{BASE_URL}/api/admin/addons/{addon_id}", headers=headers)
        assert response.status_code == 200, f"Delete addon failed: {response.text}"
        
        data = response.json()
        assert data["message"] == "Addon deleted"
        print(f"PASS: Deleted addon {addon_id}")
        
        # Verify it's no longer in list
        list_resp = requests.get(f"{BASE_URL}/api/admin/addons", headers=headers)
        addons = list_resp.json()
        addon_ids = [a["id"] for a in addons]
        assert addon_id not in addon_ids, "Deleted addon should not appear in list"
        print("PASS: Deleted addon no longer appears in addons list")


class TestDeleteOperator:
    """Feature 2: Admin can delete operators with DELETE /api/admin/operators/{id}"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_delete_operator_endpoint_exists(self, admin_token):
        """DELETE /api/admin/operators/{id} endpoint should exist"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First create a test operator to delete
        unique_id = datetime.now().strftime("%H%M%S")
        create_data = {
            "company_name": f"TEST_DeleteMe_{unique_id}",
            "owner_name": f"Test Owner {unique_id}",
            "email": f"delete_test_{unique_id}@test.com",
            "phone": "9999888877",
            "password": "testpass123",
            "saas_plan_id": None,  # Will need to get a valid plan
            "status": "active",
            "subscription_months": 1
        }
        
        # Get a plan ID first
        plans_resp = requests.get(f"{BASE_URL}/api/admin/saas-plans", headers=headers)
        plans = plans_resp.json()
        if plans:
            create_data["saas_plan_id"] = plans[0]["id"]
        else:
            pytest.skip("No SaaS plans available to create test operator")
        
        # Create operator
        create_resp = requests.post(f"{BASE_URL}/api/admin/operators/create", json=create_data, headers=headers)
        assert create_resp.status_code == 200, f"Create operator failed: {create_resp.text}"
        operator_id = create_resp.json()["id"]
        company_name = create_resp.json()["company_name"]
        print(f"Created test operator: {company_name} (ID: {operator_id})")
        
        # Now delete the operator
        delete_resp = requests.delete(f"{BASE_URL}/api/admin/operators/{operator_id}", headers=headers)
        assert delete_resp.status_code == 200, f"Delete operator failed: {delete_resp.text}"
        
        data = delete_resp.json()
        assert "message" in data
        assert "deleted" in data["message"].lower()
        print(f"PASS: DELETE /api/admin/operators/{operator_id} returned success: {data['message']}")
        
        # Verify operator is no longer in list
        list_resp = requests.get(f"{BASE_URL}/api/admin/operators", headers=headers)
        operators = list_resp.json()
        operator_ids = [o["id"] for o in operators]
        assert operator_id not in operator_ids, "Deleted operator should not appear in list"
        print("PASS: Deleted operator no longer appears in operators list")


class TestSaaSPlanWithAddons:
    """Feature 3: SaaS Plans can include addons (included_addons field)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_create_plan_with_included_addons(self, admin_token):
        """POST /api/admin/saas-plans with included_addons field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get existing addons
        addons_resp = requests.get(f"{BASE_URL}/api/admin/addons", headers=headers)
        addons = addons_resp.json()
        addon_codes = [a["code"] for a in addons[:2]] if addons else []  # Take first 2
        
        unique_name = f"TEST_Plan_With_Addons_{datetime.now().strftime('%H%M%S')}"
        plan_data = {
            "name": unique_name,
            "monthly_price": 2999,
            "max_subscribers": 500,
            "max_staff": 5,
            "trial_enabled": False,
            "trial_days": 0,
            "notification_module": True,
            "auto_reminder": True,
            "audit_logs": True,
            "payment_gateway_setup": True,
            "gst_applicable": True,
            "included_addons": addon_codes
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=plan_data, headers=headers)
        assert response.status_code == 200, f"Create plan failed: {response.text}"
        
        plan = response.json()
        assert plan["name"] == unique_name
        assert "included_addons" in plan
        assert plan["included_addons"] == addon_codes
        print(f"PASS: Created plan '{plan['name']}' with included_addons: {plan['included_addons']}")
        return plan["id"]
    
    def test_update_plan_with_addons(self, admin_token):
        """PUT /api/admin/saas-plans/{id} with included_addons field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get existing plans
        plans_resp = requests.get(f"{BASE_URL}/api/admin/saas-plans", headers=headers)
        plans = plans_resp.json()
        
        if not plans:
            pytest.skip("No plans to update")
        
        plan_id = plans[0]["id"]
        
        # Get addons
        addons_resp = requests.get(f"{BASE_URL}/api/admin/addons", headers=headers)
        addons = addons_resp.json()
        addon_codes = [a["code"] for a in addons[:3]] if addons else []
        
        # Update plan with addons
        update_data = {
            "name": plans[0]["name"],
            "monthly_price": plans[0]["monthly_price"],
            "max_subscribers": plans[0]["max_subscribers"],
            "max_staff": plans[0]["max_staff"],
            "trial_enabled": plans[0]["trial_enabled"],
            "trial_days": plans[0]["trial_days"],
            "notification_module": plans[0]["notification_module"],
            "auto_reminder": plans[0]["auto_reminder"],
            "audit_logs": plans[0]["audit_logs"],
            "payment_gateway_setup": plans[0]["payment_gateway_setup"],
            "gst_applicable": plans[0]["gst_applicable"],
            "included_addons": addon_codes
        }
        
        response = requests.put(f"{BASE_URL}/api/admin/saas-plans/{plan_id}", json=update_data, headers=headers)
        assert response.status_code == 200, f"Update plan failed: {response.text}"
        
        updated = response.json()
        assert "included_addons" in updated
        print(f"PASS: Updated plan '{updated['name']}' with included_addons: {updated['included_addons']}")


class TestPaymentGatewayConfig:
    """Feature 4: Payment gateway config for Operator-to-Admin SaaS payments"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_payment_gateways(self, admin_token):
        """GET /api/admin/payment-gateways"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/payment-gateways", headers=headers)
        assert response.status_code == 200, f"Get gateways failed: {response.text}"
        
        gateways = response.json()
        assert isinstance(gateways, list)
        print(f"PASS: Retrieved {len(gateways)} payment gateway configs")
        return gateways
    
    def test_create_payment_gateway(self, admin_token):
        """POST /api/admin/payment-gateways - Create payment gateway config"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        gateway_data = {
            "gateway_type": "razorpay",
            "api_key": "rzp_test_1234567890",
            "api_secret": "secret_test_1234567890",
            "webhook_secret": "whsec_test_123",
            "is_active": True,
            "for_operator_id": None  # Platform gateway for SaaS payments
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/payment-gateways", json=gateway_data, headers=headers)
        assert response.status_code == 200, f"Create gateway failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        print(f"PASS: Created payment gateway config: {data['message']}")
    
    def test_delete_payment_gateway(self, admin_token):
        """DELETE /api/admin/payment-gateways/{id}"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get gateways
        gateways_resp = requests.get(f"{BASE_URL}/api/admin/payment-gateways", headers=headers)
        gateways = gateways_resp.json()
        
        if not gateways:
            # Create one first
            create_data = {
                "gateway_type": "cashfree",
                "api_key": "cf_test_key_delete",
                "api_secret": "cf_test_secret_delete",
                "is_active": True
            }
            create_resp = requests.post(f"{BASE_URL}/api/admin/payment-gateways", json=create_data, headers=headers)
            assert create_resp.status_code == 200
            
            # Get gateways again
            gateways_resp = requests.get(f"{BASE_URL}/api/admin/payment-gateways", headers=headers)
            gateways = gateways_resp.json()
        
        if not gateways:
            pytest.skip("No payment gateways to delete")
        
        gateway_id = gateways[0]["id"]
        
        response = requests.delete(f"{BASE_URL}/api/admin/payment-gateways/{gateway_id}", headers=headers)
        assert response.status_code == 200, f"Delete gateway failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        print(f"PASS: Deleted payment gateway {gateway_id}")


class TestCreateOperatorManual:
    """Feature 1: Admin manually create operator with all fields"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_create_operator_with_all_fields(self, admin_token):
        """POST /api/admin/operators/create - Create operator with all registration fields"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get a plan first
        plans_resp = requests.get(f"{BASE_URL}/api/admin/saas-plans", headers=headers)
        plans = plans_resp.json()
        if not plans:
            pytest.skip("No SaaS plans available")
        
        unique_id = datetime.now().strftime("%H%M%S")
        
        # This matches the field order in Create Operator dialog:
        # Company Name, Owner Name, Email, Phone, Password, GST section, Bank section, Plan section
        operator_data = {
            "company_name": f"TEST_FullFields_{unique_id}",
            "owner_name": f"Test Owner {unique_id}",
            "email": f"full_fields_{unique_id}@test.com",
            "phone": "9876543210",
            "password": "securepass123",
            "gst_number": "22AAAAA0000A1Z5",
            "charge_gst": True,
            "bank_account_name": "Test Account Holder",
            "bank_account_number": "1234567890123456",
            "bank_ifsc": "SBIN0001234",
            "bank_name": "State Bank of India",
            "saas_plan_id": plans[0]["id"],
            "status": "active",
            "subscription_months": 3
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/operators/create", json=operator_data, headers=headers)
        assert response.status_code == 200, f"Create operator failed: {response.text}"
        
        operator = response.json()
        assert operator["company_name"] == operator_data["company_name"]
        assert operator["owner_name"] == operator_data["owner_name"]
        assert operator["email"] == operator_data["email"]
        assert operator["phone"] == operator_data["phone"]
        assert operator["gst_number"] == operator_data["gst_number"]
        assert operator["charge_gst"] == True
        assert operator["status"] == "active"
        
        print(f"PASS: Created operator with all fields: {operator['company_name']}")
        print(f"  - Owner: {operator['owner_name']}")
        print(f"  - Email: {operator['email']}")
        print(f"  - GST: {operator['gst_number']}")
        print(f"  - Plan: {operator.get('saas_plan_name', 'N/A')}")
        
        # Clean up - delete the test operator
        requests.delete(f"{BASE_URL}/api/admin/operators/{operator['id']}", headers=headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
