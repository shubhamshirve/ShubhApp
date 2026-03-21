import pytest
from httpx import AsyncClient, ASGITransport
import os
import sys

# Change dir to backend so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app
from database import db
from utils import create_token, hash_password
from datetime import datetime, timezone

# Test users
TEST_OPERATOR_EMAIL = "operator_task6@test.com"
TEST_STAFF_EMAIL = "staff_task6@test.com"
PASSWORD = "TestPassword@123"

@pytest.fixture(scope="module")
async def setup_users():
    """Setup a test operator and staff user for RBAC validation."""
    operator = {
        "id": "operator_task6",
        "email": TEST_OPERATOR_EMAIL,
        "password": hash_password(PASSWORD),
        "role": "operator",
        "operator_id": "operator_task6",
        "status": "active",
        "deleted_at": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    staff = {
        "id": "staff_task6",
        "email": TEST_STAFF_EMAIL,
        "password": hash_password(PASSWORD),
        "role": "staff",
        "operator_id": "operator_task6",
        "status": "active",
        "deleted_at": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_many([operator, staff])
    yield
    await db.users.delete_many({"id": {"$in": ["operator_task6", "staff_task6"]}})

@pytest.mark.asyncio
async def test_expired_token(setup_users):
    """Test that a JWT configured with a negative expiry acts as an expired token."""
    expired_token = create_token({
        "id": "operator_task6", 
        "email": TEST_OPERATOR_EMAIL, 
        "role": "operator", 
        "operator_id": "operator_task6"
    }, expiration_hours=-1)  # expired 1 hour ago
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/operator/profile",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        assert "Signature has expired" in response.json()["detail"] or "validate credentials" in response.text.lower()

@pytest.mark.asyncio
async def test_staff_cannot_delete(setup_users):
    """Test that staff user is blocked by require_operator_no_staff from calling DELETE routes."""
    staff_token = create_token({
        "id": "staff_task6", 
        "email": TEST_STAFF_EMAIL, 
        "role": "staff", 
        "operator_id": "operator_task6"
    })
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            "/api/operator/staff/some_staff_id",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403
        assert "Staff users cannot perform delete operations" in response.json()["detail"]

@pytest.mark.asyncio
async def test_operator_can_delete_staff(setup_users):
    """Test that operator successfully bypasses the no-staff guard for DELETE routes."""
    operator_token = create_token({
        "id": "operator_task6", 
        "email": TEST_OPERATOR_EMAIL, 
        "role": "operator", 
        "operator_id": "operator_task6"
    })
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Operator trying to delete staff
        # Given "some_staff_id" doesn't exist, it should pass the guard and return 404
        response = await client.delete(
            "/api/operator/staff/some_staff_id",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 404
