"""
Backend tests for Task 5: Multi-Plan Subscribers and Multi-Line Invoices.
"""
import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL') or 'http://localhost:8000'
BASE_URL = BASE_URL.rstrip('/')

# Test credentials
OPERATOR_EMAIL = "operator1@test.com"
OPERATOR_PASSWORD = "Test@123"

@pytest.fixture(scope="module")
def auth_headers():
    """Get operator authentication headers"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def test_plans(auth_headers):
    """Get available operator plans"""
    response = requests.get(
        f"{BASE_URL}/api/operator/plans",
        headers=auth_headers
    )
    assert response.status_code == 200
    plans = response.json()
    assert len(plans) >= 2, "Need at least 2 plans for testing"
    return plans

class TestMultiPlanSubscribers:
    def test_create_subscriber_multi_plan(self, auth_headers, test_plans):
        """Create a subscriber with 2 active plans"""
        payload = {
            "name": "Multi Plan Test User",
            "whatsapp_number": "919876543210",
            "email": "multi@test.com",
            "address": "123 Multi St",
            "plans": [
                {
                    "plan_id": test_plans[0]["id"],
                    "billing_date": 1,
                    "discount": 50
                },
                {
                    "plan_id": test_plans[1]["id"],
                    "billing_date": 15,
                    "discount": 0
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/operator/subscribers",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["plans"]) == 2
        assert data["plans"][0]["plan_name"] == test_plans[0]["name"]
        assert data["plans"][1]["plan_name"] == test_plans[1]["name"]
        return data["id"]

    def test_update_subscriber_plans(self, auth_headers, test_plans):
        """Update plans for an existing subscriber"""
        # First create a subscriber
        sub_id = self.test_create_subscriber_multi_plan(auth_headers, test_plans)
        
        # Update to have only 1 plan
        payload = {
            "name": "Multi Plan Test User UPDATED",
            "whatsapp_number": "919876543210",
            "plans": [
                {
                    "plan_id": test_plans[1]["id"],
                    "billing_date": 10,
                    "discount": 100
                }
            ]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/operator/subscribers/{sub_id}",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["plans"]) == 1
        assert data["plans"][0]["billing_date"] == 10
        assert data["plans"][0]["discount"] == 100

class TestMultiLineInvoices:
    def test_create_manual_multi_line_invoice(self, auth_headers, test_plans):
        """Manually create an invoice with 2 line items"""
        # Create a subscriber first
        sub_payload = {
            "name": "Invoice Test User",
            "whatsapp_number": "919000000001",
            "plans": [{"plan_id": test_plans[0]["id"], "billing_date": 1}]
        }
        sub_res = requests.post(f"{BASE_URL}/api/operator/subscribers", headers=auth_headers, json=sub_payload)
        subscriber_id = sub_res.json()["id"]
        
        now = datetime.now(timezone.utc)
        due_date = now + timedelta(days=5)
        
        payload = {
            "subscriber_id": subscriber_id,
            "due_date": due_date.isoformat(),
            "line_items": [
                {
                    "plan_id": test_plans[0]["id"],
                    "base_amount": 500,
                    "discount": 50,
                    "service_start_date": now.isoformat(),
                    "service_end_date": (now + timedelta(days=30)).isoformat()
                },
                {
                    "plan_id": test_plans[1]["id"],
                    "base_amount": 1000,
                    "discount": 0,
                    "service_start_date": now.isoformat(),
                    "service_end_date": (now + timedelta(days=30)).isoformat()
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/operator/invoices",
            headers=auth_headers,
            json=payload
        )
        if response.status_code != 200:
            print(f"FAILED Response: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["line_items"]) == 2
        
        # Verify totals: (500-50) + (1000-0) = 1450 (assuming no tax for these test plans)
        # Note: If tax is applied, final_amount will be higher. 
        # But base_amount - discount should be at least 1450.
        assert data["base_amount"] == 1500
        assert data["discount"] == 50
        assert data["final_amount"] >= 1450
        print(f"Manual Multi-line Invoice Created: {data['invoice_number']}, Final: ₹{data['final_amount']}")

    def test_auto_invoice_logic_check(self, auth_headers, test_plans):
        """
        Since we can't easily trigger the cron job and wait for it in a simple API test,
        we'll verify the subscriber search query logic by checking the endpoint filter.
        """
        # Create a subscriber with 2 plans on the same billing date (today)
        today_day = datetime.now(timezone.utc).day
        if today_day > 28: today_day = 28
        
        sub_payload = {
            "name": "Cron Test User",
            "whatsapp_number": "919000000002",
            "plans": [
                {"plan_id": test_plans[0]["id"], "billing_date": today_day, "discount": 10},
                {"plan_id": test_plans[1]["id"], "billing_date": today_day, "discount": 20}
            ]
        }
        requests.post(f"{BASE_URL}/api/operator/subscribers", headers=auth_headers, json=sub_payload)
        
        # Verify we can find this subscriber by plan_id (new query logic)
        response = requests.get(
            f"{BASE_URL}/api/operator/subscribers?plan_id={test_plans[0]['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        subs = response.json()
        assert any(s["name"] == "Cron Test User" for s in subs)
        print("Subscriber filtering by nested plan_id verified")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
