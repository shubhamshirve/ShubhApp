"""Test subscriber search endpoint for searchable dropdown feature."""
import pytest
from httpx import AsyncClient
from server import app
import os

BASE_URL = os.getenv("REACT_APP_BACKEND_URL", "http://localhost:8001")

@pytest.mark.asyncio
async def test_subscriber_search_empty_query():
    """Test subscriber search with empty query returns results."""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        # Login first
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "operator@test.com", "password": "test123"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Test empty search
        response = await client.get(
            "/api/operator/subscribers/search?q=&limit=50",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify response structure
        if len(data) > 0:
            subscriber = data[0]
            assert "id" in subscriber
            assert "name" in subscriber
            assert "whatsapp_number" in subscriber
            assert "email" in subscriber

@pytest.mark.asyncio
async def test_subscriber_search_by_name():
    """Test subscriber search by name."""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        # Login
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "operator@test.com", "password": "test123"}
        )
        token = login_response.json()["access_token"]
        
        # Search for 'Raj' - should find Rajesh Kumar
        response = await client.get(
            "/api/operator/subscribers/search?q=Raj&limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        
        # Verify at least one result contains 'Raj'
        names = [s["name"] for s in data]
        assert any("Raj" in name for name in names)

@pytest.mark.asyncio
async def test_subscriber_search_by_phone():
    """Test subscriber search by phone number."""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        # Login
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "operator@test.com", "password": "test123"}
        )
        token = login_response.json()["access_token"]
        
        # Search by phone pattern
        response = await client.get(
            "/api/operator/subscribers/search?q=987&limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify all results contain '987' in phone
        for subscriber in data:
            assert "987" in subscriber["whatsapp_number"]

@pytest.mark.asyncio
async def test_subscriber_search_limit():
    """Test subscriber search respects limit parameter."""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        # Login
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "operator@test.com", "password": "test123"}
        )
        token = login_response.json()["access_token"]
        
        # Request only 3 results
        response = await client.get(
            "/api/operator/subscribers/search?q=&limit=3",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_subscriber_search_empty_query())
    asyncio.run(test_subscriber_search_by_name())
    asyncio.run(test_subscriber_search_by_phone())
    asyncio.run(test_subscriber_search_limit())
    print("✅ All subscriber search tests passed!")
