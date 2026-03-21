import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL') or 'http://localhost:8000'
BASE_URL = BASE_URL.rstrip('/')

OPERATOR_EMAIL = "operator1@test.com"
OPERATOR_PASSWORD = "Test@123"

@pytest.fixture(scope="module")
def operator_token():
    """Login and return operator token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD}
    )
    assert response.status_code == 200, f"Operator login failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def staff_token(operator_token):
    """Use operator token to create a staff member and log in."""
    staff_pwd = "StaffPassword123"
    staff_email = f"test_staff_{uuid.uuid4().hex[:8]}@test.com"
    payload = {
        "name": "Test Staff",
        "email": staff_email,
        "password": staff_pwd,
        "permissions": ["view_dashboard"]
    }
    
    # Create Staff
    create_resp = requests.post(
        f"{BASE_URL}/api/operator/staff",
        json=payload,
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert create_resp.status_code == 200, f"Staff creation failed: {create_resp.text}"
    
    # Login as Staff
    login_resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": staff_email, "password": staff_pwd}
    )
    assert login_resp.status_code == 200, f"Staff login failed: {login_resp.text}"
    return login_resp.json()["access_token"]


def test_invalid_token_rejected(operator_token):
    """Test that an invalid or expired token is rejected with 401 Unauthorized."""
    # Append random string to invalidate signature
    invalid_token = operator_token[:-5] + "XXXXX"
    
    response = requests.get(
        f"{BASE_URL}/api/operator/profile",
        headers={"Authorization": f"Bearer {invalid_token}"}
    )
    assert response.status_code == 401
    assert "validate credentials" in response.json().get("detail", "").lower() or "signature has expired" in response.text.lower()


def test_staff_blocked_from_deletes(staff_token):
    """Test that staff user is blocked by require_operator_no_staff from calling DELETE routes."""
    response = requests.delete(
        f"{BASE_URL}/api/operator/staff/some_fake_id",
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert response.status_code == 403
    assert "Staff users cannot perform delete operations" in response.json().get("detail", "")


def test_operator_allowed_deletes(operator_token):
    """Test that operator successfully bypasses the no-staff guard for DELETE routes."""
    response = requests.delete(
        f"{BASE_URL}/api/operator/staff/some_fake_id",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    # Target doesn't exist, but it passed auth
    assert response.status_code == 404
