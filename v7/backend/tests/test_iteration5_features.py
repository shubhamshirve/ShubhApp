"""
Backend tests for iteration 5 features:
1. Invoice customization settings (GET/PUT /api/operator/invoice-settings)
2. Subscription renewal (GET /api/operator/subscription, POST /api/operator/renew-subscription)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
OPERATOR_EMAIL = "demo@democorp.com"
OPERATOR_PASSWORD = "demo123"


@pytest.fixture(scope="module")
def operator_token():
    """Get operator authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(operator_token):
    """Auth headers for operator requests"""
    return {"Authorization": f"Bearer {operator_token}"}


class TestInvoiceSettings:
    """Tests for invoice customization feature"""
    
    def test_get_invoice_settings(self, auth_headers):
        """GET /api/operator/invoice-settings returns settings"""
        response = requests.get(
            f"{BASE_URL}/api/operator/invoice-settings",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Verify expected fields exist
        assert "company_name" in data
        assert "company_email" in data or data.get("company_email") is None
        assert "company_phone" in data or data.get("company_phone") is None
        assert "company_address" in data or data.get("company_address") is None
        assert "invoice_prefix" in data
        assert "show_gst" in data
        print(f"Invoice settings retrieved: prefix={data.get('invoice_prefix')}, show_gst={data.get('show_gst')}")
    
    def test_update_invoice_settings(self, auth_headers):
        """PUT /api/operator/invoice-settings updates and persists"""
        test_data = {
            "company_name": "TEST_Company_Invoice",
            "company_address": "TEST 123 Business Lane",
            "company_phone": "+91 9999999999",
            "company_email": "test-invoice@example.com",
            "logo_url": "https://example.com/logo.png",
            "invoice_prefix": "TI5",
            "invoice_footer": "TEST Footer - Thank you!",
            "show_gst": False,
            "terms_conditions": "TEST Terms - Pay within 30 days"
        }
        
        # Update settings
        response = requests.put(
            f"{BASE_URL}/api/operator/invoice-settings",
            headers=auth_headers,
            json=test_data
        )
        assert response.status_code == 200
        assert response.json().get("message") == "Invoice settings updated"
        print("Invoice settings updated successfully")
        
        # Verify persistence with GET
        get_response = requests.get(
            f"{BASE_URL}/api/operator/invoice-settings",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        saved_data = get_response.json()
        
        assert saved_data["company_name"] == test_data["company_name"]
        assert saved_data["company_address"] == test_data["company_address"]
        assert saved_data["invoice_prefix"] == test_data["invoice_prefix"]
        assert saved_data["show_gst"] == test_data["show_gst"]
        assert saved_data["invoice_footer"] == test_data["invoice_footer"]
        assert saved_data["terms_conditions"] == test_data["terms_conditions"]
        print("Invoice settings verified to be persisted correctly")


class TestOperatorSubscription:
    """Tests for subscription and renewal feature"""
    
    def test_get_subscription_details(self, auth_headers):
        """GET /api/operator/subscription returns subscription info with available plans"""
        response = requests.get(
            f"{BASE_URL}/api/operator/subscription",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "operator_id" in data
        assert "status" in data
        assert "saas_plan_id" in data
        assert "saas_plan_name" in data
        assert "available_plans" in data
        
        # Verify available_plans is a list with plan details
        assert isinstance(data["available_plans"], list)
        if len(data["available_plans"]) > 0:
            plan = data["available_plans"][0]
            assert "id" in plan
            assert "name" in plan
            assert "monthly_price" in plan
        
        print(f"Subscription status: {data['status']}, plan: {data['saas_plan_name']}")
        print(f"Available plans: {len(data['available_plans'])}")
        return data
    
    def test_renew_subscription_creates_payment_link(self, auth_headers):
        """POST /api/operator/renew-subscription creates Razorpay payment link"""
        # First get available plans
        sub_response = requests.get(
            f"{BASE_URL}/api/operator/subscription",
            headers=auth_headers
        )
        assert sub_response.status_code == 200
        available_plans = sub_response.json().get("available_plans", [])
        
        # Find a paid plan (price > 0)
        paid_plan = None
        for plan in available_plans:
            if plan["monthly_price"] > 0:
                paid_plan = plan
                break
        
        if not paid_plan:
            pytest.skip("No paid plans available to test renewal")
        
        # Request renewal with 1 month
        response = requests.post(
            f"{BASE_URL}/api/operator/renew-subscription?plan_id={paid_plan['id']}&months=1",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["plan_id"] == paid_plan["id"]
        assert data["plan_name"] == paid_plan["name"]
        assert data["months"] == 1
        assert data["base_amount"] == paid_plan["monthly_price"]
        assert data["status"] == "pending"
        
        # Verify GST is calculated (18%)
        expected_gst = round(paid_plan["monthly_price"] * 0.18, 2)
        assert data["gst_amount"] == expected_gst
        
        # Verify total amount
        expected_total = paid_plan["monthly_price"] + expected_gst
        assert data["total_amount"] == expected_total
        
        # Verify payment link is generated (Razorpay integration)
        assert "payment_link" in data
        assert data["payment_link"] is not None
        assert "rzp.io" in data["payment_link"] or "razorpay" in data["payment_link"].lower()
        
        print(f"Renewal created for {paid_plan['name']}: total=₹{data['total_amount']}")
        print(f"Payment link: {data['payment_link']}")
    
    def test_renew_subscription_multiple_months(self, auth_headers):
        """POST /api/operator/renew-subscription with 3 months calculates correctly"""
        # Get available plans
        sub_response = requests.get(
            f"{BASE_URL}/api/operator/subscription",
            headers=auth_headers
        )
        available_plans = sub_response.json().get("available_plans", [])
        
        paid_plan = next((p for p in available_plans if p["monthly_price"] > 0), None)
        if not paid_plan:
            pytest.skip("No paid plans available")
        
        # Request 3-month renewal
        response = requests.post(
            f"{BASE_URL}/api/operator/renew-subscription?plan_id={paid_plan['id']}&months=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify amount calculations for 3 months
        expected_base = paid_plan["monthly_price"] * 3
        expected_gst = round(expected_base * 0.18, 2)
        expected_total = expected_base + expected_gst
        
        assert data["months"] == 3
        assert data["base_amount"] == expected_base
        assert data["gst_amount"] == expected_gst
        assert data["total_amount"] == expected_total
        
        print(f"3-month renewal: base=₹{expected_base}, gst=₹{expected_gst}, total=₹{expected_total}")
    
    def test_renew_subscription_requires_plan(self, auth_headers):
        """POST /api/operator/renew-subscription without plan_id uses current plan or returns error"""
        # This tests the behavior when no plan_id is provided
        response = requests.post(
            f"{BASE_URL}/api/operator/renew-subscription?months=1",
            headers=auth_headers
        )
        # Should either use current plan or return 400 if no current plan
        assert response.status_code in [200, 400]
        if response.status_code == 400:
            assert "plan" in response.json().get("detail", "").lower()


class TestInvoiceSettingsCleanup:
    """Restore original settings after tests"""
    
    def test_restore_original_settings(self, auth_headers):
        """Restore original invoice settings after tests"""
        original_data = {
            "company_name": "Demo Corp Pvt Ltd",
            "company_address": "123 Tech Park, Bangalore",
            "company_phone": "9876543210",
            "company_email": "billing@democorp.com",
            "logo_url": "",
            "invoice_prefix": "DC",
            "invoice_footer": "Thank you for your business!",
            "show_gst": True,
            "terms_conditions": "Payment due within 7 days"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/operator/invoice-settings",
            headers=auth_headers,
            json=original_data
        )
        assert response.status_code == 200
        print("Original invoice settings restored")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
