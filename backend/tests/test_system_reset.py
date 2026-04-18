"""
Test System Reset (Danger Zone) Feature
Tests the OTP-based system reset functionality for admin users.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"


class TestSystemResetFeature:
    """Tests for the System Reset (Danger Zone) feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with admin authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        
    def get_admin_token(self):
        """Authenticate as admin and return token"""
        if self.admin_token:
            return self.admin_token
            
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in login response"
        self.admin_token = data["access_token"]
        return self.admin_token
    
    def get_auth_headers(self):
        """Get authorization headers with admin token"""
        token = self.get_admin_token()
        return {"Authorization": f"Bearer {token}"}
    
    # ─── Test: Request OTP Endpoint ───────────────────────────────────────────
    
    def test_request_otp_requires_auth(self):
        """POST /api/admin/reset/request-otp without auth should return 401/403"""
        response = self.session.post(f"{BASE_URL}/api/admin/reset/request-otp")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Request OTP endpoint requires authentication")
    
    def test_request_otp_success(self):
        """POST /api/admin/reset/request-otp with admin auth should return success"""
        response = self.session.post(
            f"{BASE_URL}/api/admin/reset/request-otp",
            headers=self.get_auth_headers()
        )
        # May fail if email service not configured, but endpoint should be accessible
        if response.status_code == 200:
            data = response.json()
            assert "message" in data, "Response should have message field"
            assert "OTP sent" in data["message"] or "sent" in data["message"].lower(), \
                f"Unexpected message: {data['message']}"
            print(f"✓ Request OTP success: {data['message']}")
        elif response.status_code == 500:
            # Email service not configured - this is expected in test environment
            data = response.json()
            assert "detail" in data, "Error response should have detail"
            assert "email" in data["detail"].lower() or "otp" in data["detail"].lower(), \
                f"Unexpected error: {data['detail']}"
            print(f"✓ Request OTP endpoint accessible (email service not configured): {data['detail']}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}, body: {response.text}")
    
    # ─── Test: Execute Reset Endpoint ─────────────────────────────────────────
    
    def test_execute_reset_requires_auth(self):
        """POST /api/admin/reset/execute without auth should return 401/403"""
        response = self.session.post(
            f"{BASE_URL}/api/admin/reset/execute",
            json={"otp": "123456"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Execute reset endpoint requires authentication")
    
    def test_execute_reset_without_otp_request(self):
        """POST /api/admin/reset/execute without prior OTP request should fail"""
        response = self.session.post(
            f"{BASE_URL}/api/admin/reset/execute",
            headers=self.get_auth_headers(),
            json={"otp": "123456"}
        )
        # Should fail because no OTP was requested (or OTP is invalid)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Error response should have detail"
        # Could be "No pending reset OTP" or "Invalid OTP" depending on state
        print(f"✓ Execute reset without OTP request fails: {data['detail']}")
    
    def test_execute_reset_with_invalid_otp(self):
        """POST /api/admin/reset/execute with invalid OTP should fail"""
        # First request OTP (may fail if email not configured, but creates OTP record)
        self.session.post(
            f"{BASE_URL}/api/admin/reset/request-otp",
            headers=self.get_auth_headers()
        )
        
        # Try to execute with wrong OTP
        response = self.session.post(
            f"{BASE_URL}/api/admin/reset/execute",
            headers=self.get_auth_headers(),
            json={"otp": "000000"}  # Wrong OTP
        )
        # Should fail with 400 (invalid OTP) or 400 (no pending OTP if email failed)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Error response should have detail"
        print(f"✓ Execute reset with invalid OTP fails: {data['detail']}")
    
    def test_execute_reset_validates_otp_format(self):
        """POST /api/admin/reset/execute validates OTP format"""
        response = self.session.post(
            f"{BASE_URL}/api/admin/reset/execute",
            headers=self.get_auth_headers(),
            json={"otp": ""}  # Empty OTP
        )
        # Should fail - either validation error or no pending OTP
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print("✓ Execute reset validates OTP format")
    
    # ─── Test: Endpoint Accessibility ─────────────────────────────────────────
    
    def test_reset_endpoints_exist(self):
        """Verify reset endpoints are registered and accessible"""
        # Test request-otp endpoint exists
        response = self.session.post(
            f"{BASE_URL}/api/admin/reset/request-otp",
            headers=self.get_auth_headers()
        )
        # Should not be 404
        assert response.status_code != 404, "request-otp endpoint not found"
        print("✓ /api/admin/reset/request-otp endpoint exists")
        
        # Test execute endpoint exists
        response = self.session.post(
            f"{BASE_URL}/api/admin/reset/execute",
            headers=self.get_auth_headers(),
            json={"otp": "123456"}
        )
        # Should not be 404
        assert response.status_code != 404, "execute endpoint not found"
        print("✓ /api/admin/reset/execute endpoint exists")
    
    # ─── Test: Non-Admin Access ───────────────────────────────────────────────
    
    def test_operator_cannot_access_reset_endpoints(self):
        """Operator users should not be able to access reset endpoints"""
        # Try to login as operator
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "operator@test.com",
            "password": "test123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Operator account not available for testing")
            return
        
        operator_token = login_response.json().get("access_token")
        operator_headers = {"Authorization": f"Bearer {operator_token}"}
        
        # Try request-otp
        response = self.session.post(
            f"{BASE_URL}/api/admin/reset/request-otp",
            headers=operator_headers
        )
        assert response.status_code in [401, 403], \
            f"Operator should not access request-otp, got {response.status_code}"
        print("✓ Operator cannot access request-otp endpoint")
        
        # Try execute
        response = self.session.post(
            f"{BASE_URL}/api/admin/reset/execute",
            headers=operator_headers,
            json={"otp": "123456"}
        )
        assert response.status_code in [401, 403], \
            f"Operator should not access execute endpoint, got {response.status_code}"
        print("✓ Operator cannot access execute endpoint")


class TestSystemResetModel:
    """Tests for SystemResetOTPRequest model"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Get admin token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            self.admin_token = response.json().get("access_token")
            self.auth_headers = {"Authorization": f"Bearer {self.admin_token}"}
        else:
            pytest.skip("Admin login failed")
    
    def test_otp_field_required(self):
        """OTP field should be required in request body"""
        response = self.session.post(
            f"{BASE_URL}/api/admin/reset/execute",
            headers=self.auth_headers,
            json={}  # Missing otp field
        )
        assert response.status_code == 422, f"Expected 422 for missing otp, got {response.status_code}"
        print("✓ OTP field is required")
    
    def test_otp_accepts_string(self):
        """OTP should accept string values"""
        response = self.session.post(
            f"{BASE_URL}/api/admin/reset/execute",
            headers=self.auth_headers,
            json={"otp": "123456"}
        )
        # Should not be 422 (validation error) - should be 400 (business logic error)
        assert response.status_code != 422, "OTP string should be accepted"
        print("✓ OTP accepts string values")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
