"""
Test iteration 7 features:
1. Admin impersonation: POST /api/admin/operators/{id}/impersonate returns token with impersonated_by
2. GET /api/auth/me with impersonated token returns impersonated_by field
3. POST /api/admin/return-from-impersonate returns admin token successfully
4. Admin audit logs: GET /api/admin/audit-logs returns array of audit log entries
5. WhatsApp Business API .env keys present
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestImpersonationFlow:
    """Test admin impersonation flow"""
    
    admin_token = None
    operator_id = None
    impersonated_token = None
    
    @pytest.fixture(autouse=True)
    def setup_admin_login(self):
        """Login as admin first"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@saas.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        TestImpersonationFlow.admin_token = response.json()["access_token"]
    
    def test_01_get_operators_list(self):
        """Get list of operators to find one to impersonate"""
        headers = {"Authorization": f"Bearer {TestImpersonationFlow.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/operators", headers=headers)
        assert response.status_code == 200, f"Failed to get operators: {response.text}"
        operators = response.json()
        assert isinstance(operators, list), "Operators should be a list"
        # Find an operator to impersonate
        if operators:
            TestImpersonationFlow.operator_id = operators[0]["id"]
            print(f"Found operator to impersonate: {operators[0]['company_name']}")
        else:
            pytest.skip("No operators found to impersonate")
    
    def test_02_impersonate_operator(self):
        """POST /api/admin/operators/{id}/impersonate returns token with impersonated_by"""
        if not TestImpersonationFlow.operator_id:
            pytest.skip("No operator ID available")
        
        headers = {"Authorization": f"Bearer {TestImpersonationFlow.admin_token}"}
        response = requests.post(
            f"{BASE_URL}/api/admin/operators/{TestImpersonationFlow.operator_id}/impersonate",
            headers=headers
        )
        assert response.status_code == 200, f"Impersonation failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data, "Response should contain access_token"
        assert "token_type" in data, "Response should contain token_type"
        assert data["token_type"] == "bearer", "Token type should be bearer"
        
        TestImpersonationFlow.impersonated_token = data["access_token"]
        print(f"Impersonation successful, got token")
    
    def test_03_auth_me_returns_impersonated_by(self):
        """GET /api/auth/me with impersonated token returns impersonated_by field (not null)"""
        if not TestImpersonationFlow.impersonated_token:
            pytest.skip("No impersonated token available")
        
        headers = {"Authorization": f"Bearer {TestImpersonationFlow.impersonated_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Get me failed: {response.text}"
        data = response.json()
        
        # Key assertion: impersonated_by should be present and not null
        assert "impersonated_by" in data, "Response should contain impersonated_by field"
        assert data["impersonated_by"] is not None, "impersonated_by should NOT be null when impersonating"
        print(f"impersonated_by field: {data['impersonated_by']}")
        
        # Verify role is operator (impersonating as operator)
        assert data["role"] == "operator", f"Role should be 'operator', got {data['role']}"
    
    def test_04_return_from_impersonate(self):
        """POST /api/admin/return-from-impersonate returns admin token successfully"""
        if not TestImpersonationFlow.impersonated_token:
            pytest.skip("No impersonated token available")
        
        headers = {"Authorization": f"Bearer {TestImpersonationFlow.impersonated_token}"}
        response = requests.post(f"{BASE_URL}/api/admin/return-from-impersonate", headers=headers)
        assert response.status_code == 200, f"Return from impersonate failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data, "Response should contain access_token"
        assert "token_type" in data, "Response should contain token_type"
        
        # Verify the returned token is for admin
        admin_token = data["access_token"]
        verify_headers = {"Authorization": f"Bearer {admin_token}"}
        verify_response = requests.get(f"{BASE_URL}/api/auth/me", headers=verify_headers)
        assert verify_response.status_code == 200, "Should be able to use returned token"
        verify_data = verify_response.json()
        assert verify_data["role"] == "admin", f"Returned token should be for admin, got role: {verify_data['role']}"
        # impersonated_by should be null for the admin token
        assert verify_data.get("impersonated_by") is None, "Admin token should have impersonated_by as null"
        print("Return to admin successful")
    
    def test_05_return_from_impersonate_fails_without_impersonation(self):
        """POST /api/admin/return-from-impersonate fails when not impersonating"""
        # Use regular admin token (not impersonating)
        headers = {"Authorization": f"Bearer {TestImpersonationFlow.admin_token}"}
        response = requests.post(f"{BASE_URL}/api/admin/return-from-impersonate", headers=headers)
        assert response.status_code == 400, f"Should fail with 400 when not impersonating: {response.text}"
        data = response.json()
        assert "detail" in data, "Response should have error detail"
        print(f"Correctly rejected non-impersonating request: {data['detail']}")


class TestAuditLogs:
    """Test admin audit logs endpoint"""
    
    admin_token = None
    
    @pytest.fixture(autouse=True)
    def setup_admin_login(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@saas.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        TestAuditLogs.admin_token = response.json()["access_token"]
    
    def test_01_get_audit_logs(self):
        """GET /api/admin/audit-logs returns array of audit log entries without errors"""
        headers = {"Authorization": f"Bearer {TestAuditLogs.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/audit-logs?limit=50", headers=headers)
        assert response.status_code == 200, f"Audit logs request failed: {response.text}"
        data = response.json()
        
        # Verify response is an array
        assert isinstance(data, list), f"Audit logs should be an array, got {type(data)}"
        print(f"Found {len(data)} audit log entries")
        
        # If there are entries, verify structure
        if data:
            entry = data[0]
            required_fields = ["id", "user_id", "user_name", "role", "action", "module", "created_at"]
            for field in required_fields:
                assert field in entry, f"Audit log entry should have '{field}' field"
            print(f"Sample audit log: user={entry['user_name']}, action={entry['action']}, module={entry['module']}")
    
    def test_02_audit_logs_pagination(self):
        """GET /api/admin/audit-logs supports skip and limit"""
        headers = {"Authorization": f"Bearer {TestAuditLogs.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/audit-logs?skip=0&limit=10", headers=headers)
        assert response.status_code == 200, f"Audit logs with pagination failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Should return a list"
        assert len(data) <= 10, "Should respect limit parameter"


class TestWhatsAppEnvKeys:
    """Test WhatsApp Business API .env keys"""
    
    def test_env_keys_present(self):
        """Root .env has WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_BUSINESS_ACCOUNT_ID keys"""
        with open('/app/.env', 'r') as f:
            env_content = f.read()
        
        # Check for presence of keys (they may be empty but should exist)
        assert "WHATSAPP_PHONE_NUMBER_ID" in env_content, "WHATSAPP_PHONE_NUMBER_ID key should be in .env"
        assert "WHATSAPP_ACCESS_TOKEN" in env_content, "WHATSAPP_ACCESS_TOKEN key should be in .env"
        assert "WHATSAPP_BUSINESS_ACCOUNT_ID" in env_content, "WHATSAPP_BUSINESS_ACCOUNT_ID key should be in .env"
        print("All WhatsApp API keys present in .env (note: values may be empty - MOCKED)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
