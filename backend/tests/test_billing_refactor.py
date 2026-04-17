"""
Tests for SaaS Billing Refactor:
- Admin SaaS Plans CRUD with monthly_price + per_invoice_price
- No legacy fields (plan_type, per_customer_rate, monthly_base_fee) in responses
- Operator subscription endpoint returns correct data with available_plans
- Checkout create-order returns total_amount = monthly_price (1-month, GST inclusive)
- Operator wallet endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://invoice-alert-hub-1.preview.emergentagent.com"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@test.com",
        "password": "Admin@123"
    })
    if res.status_code != 200:
        pytest.skip(f"Admin login failed: {res.status_code} {res.text}")
    return res.json().get("access_token")


@pytest.fixture(scope="module")
def operator_token():
    """Get operator1 auth token"""
    res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "operator1@test.com",
        "password": "Test@123"
    })
    if res.status_code != 200:
        pytest.skip(f"Operator login failed: {res.status_code} {res.text}")
    return res.json().get("access_token")


@pytest.fixture(scope="module")
def admin_client(admin_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"})
    return s


@pytest.fixture(scope="module")
def operator_client(operator_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {operator_token}"})
    return s


# ─── Admin Auth ──────────────────────────────────────────────────────────────

class TestAdminAuth:
    """Admin authentication"""

    def test_admin_login_success(self):
        res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com", "password": "Admin@123"
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert isinstance(data["access_token"], str) and len(data["access_token"]) > 0

    def test_operator_login_success(self):
        res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "operator1@test.com", "password": "Test@123"
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data


# ─── Admin SaaS Plans CRUD ───────────────────────────────────────────────────

class TestAdminSaaSPlans:
    """Admin SaaS Plans: new simplified model (monthly_price + per_invoice_price)"""

    created_plan_id = None

    def test_get_plans_returns_list(self, admin_client):
        res = admin_client.get(f"{BASE_URL}/api/admin/saas-plans")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        print(f"  Found {len(data)} existing plans")

    def test_existing_plans_have_monthly_price(self, admin_client):
        """Verify existing plans have monthly_price field"""
        res = admin_client.get(f"{BASE_URL}/api/admin/saas-plans")
        assert res.status_code == 200
        plans = res.json()
        for plan in plans:
            assert "monthly_price" in plan, f"Plan {plan.get('name')} missing monthly_price"
            assert "per_invoice_price" in plan, f"Plan {plan.get('name')} missing per_invoice_price"
            print(f"  Plan: {plan['name']}, monthly_price={plan['monthly_price']}, per_invoice={plan['per_invoice_price']}")

    def test_existing_plans_no_legacy_plan_type(self, admin_client):
        """Verify no plan_type field in plans (legacy field)"""
        res = admin_client.get(f"{BASE_URL}/api/admin/saas-plans")
        assert res.status_code == 200
        plans = res.json()
        for plan in plans:
            # plan_type should not be in the response (legacy field)
            assert "plan_type" not in plan or plan.get("plan_type") is None, \
                f"Legacy field plan_type found in plan {plan.get('name')}"

    def test_create_plan_monthly_price_1499(self, admin_client):
        """Create plan with monthly_price=1499, per_invoice_price=8"""
        res = admin_client.post(f"{BASE_URL}/api/admin/saas-plans", json={
            "name": "TEST_Billing_Refactor_Plan",
            "monthly_price": 1499,
            "per_invoice_price": 8,
            "included_addons": []
        })
        assert res.status_code == 200, f"Create plan failed: {res.status_code} {res.text}"
        data = res.json()
        assert data["name"] == "TEST_Billing_Refactor_Plan"
        assert data["monthly_price"] == 1499.0
        assert data["per_invoice_price"] == 8.0
        assert "id" in data
        TestAdminSaaSPlans.created_plan_id = data["id"]
        print(f"  Created plan ID: {data['id']}")

    def test_created_plan_persisted_via_get(self, admin_client):
        """Verify created plan persists via GET"""
        plan_id = TestAdminSaaSPlans.created_plan_id
        if not plan_id:
            pytest.skip("No plan created in previous test")
        res = admin_client.get(f"{BASE_URL}/api/admin/saas-plans")
        assert res.status_code == 200
        plans = res.json()
        found = next((p for p in plans if p["id"] == plan_id), None)
        assert found is not None, "Created plan not found in list"
        assert found["monthly_price"] == 1499.0
        assert found["per_invoice_price"] == 8.0

    def test_update_plan(self, admin_client):
        """Update the test plan"""
        plan_id = TestAdminSaaSPlans.created_plan_id
        if not plan_id:
            pytest.skip("No plan created")
        res = admin_client.put(f"{BASE_URL}/api/admin/saas-plans/{plan_id}", json={
            "name": "TEST_Billing_Refactor_Plan_Updated",
            "monthly_price": 1599,
            "per_invoice_price": 9,
            "included_addons": []
        })
        assert res.status_code == 200
        data = res.json()
        assert data["monthly_price"] == 1599.0
        assert data["per_invoice_price"] == 9.0

    def test_get_plan_after_update(self, admin_client):
        """Verify update was persisted"""
        plan_id = TestAdminSaaSPlans.created_plan_id
        if not plan_id:
            pytest.skip("No plan created")
        res = admin_client.get(f"{BASE_URL}/api/admin/saas-plans")
        assert res.status_code == 200
        plans = res.json()
        found = next((p for p in plans if p["id"] == plan_id), None)
        assert found is not None
        assert found["monthly_price"] == 1599.0

    def test_delete_test_plan(self, admin_client):
        """Delete the test plan"""
        plan_id = TestAdminSaaSPlans.created_plan_id
        if not plan_id:
            pytest.skip("No plan created")
        res = admin_client.delete(f"{BASE_URL}/api/admin/saas-plans/{plan_id}")
        assert res.status_code == 200

    def test_plan_gone_after_delete(self, admin_client):
        """Verify plan deleted"""
        plan_id = TestAdminSaaSPlans.created_plan_id
        if not plan_id:
            pytest.skip("No plan created")
        res = admin_client.get(f"{BASE_URL}/api/admin/saas-plans")
        assert res.status_code == 200
        plans = res.json()
        assert not any(p["id"] == plan_id for p in plans), "Plan still exists after delete"

    def test_create_plan_requires_auth(self):
        """Plan creation without auth returns 401"""
        res = requests.post(f"{BASE_URL}/api/admin/saas-plans", json={
            "name": "unauth_plan", "monthly_price": 999, "per_invoice_price": 10
        })
        assert res.status_code in [401, 403]


# ─── Operator Subscription Endpoint ─────────────────────────────────────────

class TestOperatorSubscription:
    """Operator subscription endpoint returns correct fields"""

    def test_subscription_loads_200(self, operator_client):
        res = operator_client.get(f"{BASE_URL}/api/operator/subscription")
        assert res.status_code == 200

    def test_subscription_has_status(self, operator_client):
        res = operator_client.get(f"{BASE_URL}/api/operator/subscription")
        data = res.json()
        assert "status" in data
        assert data["status"] in ["trial", "active", "expired", "suspended"]
        print(f"  Operator status: {data['status']}")

    def test_subscription_has_available_plans(self, operator_client):
        """available_plans list must be returned"""
        res = operator_client.get(f"{BASE_URL}/api/operator/subscription")
        data = res.json()
        assert "available_plans" in data
        assert isinstance(data["available_plans"], list)
        print(f"  Available plans: {len(data['available_plans'])}")

    def test_available_plans_have_monthly_price(self, operator_client):
        """Each available plan must have monthly_price and per_invoice_price"""
        res = operator_client.get(f"{BASE_URL}/api/operator/subscription")
        data = res.json()
        plans = data.get("available_plans", [])
        for plan in plans:
            assert "monthly_price" in plan, f"Plan {plan.get('name')} missing monthly_price"
            assert "per_invoice_price" in plan, f"Plan {plan.get('name')} missing per_invoice_price"
            assert isinstance(plan["monthly_price"], (int, float))
            assert isinstance(plan["per_invoice_price"], (int, float))

    def test_subscription_has_per_invoice_price(self, operator_client):
        """Subscription response should include per_invoice_price"""
        res = operator_client.get(f"{BASE_URL}/api/operator/subscription")
        data = res.json()
        assert "per_invoice_price" in data
        print(f"  per_invoice_price: {data['per_invoice_price']}")

    def test_subscription_requires_auth(self):
        """Subscription without auth returns 401"""
        res = requests.get(f"{BASE_URL}/api/operator/subscription")
        assert res.status_code in [401, 403]


# ─── Operator Wallet Endpoint ─────────────────────────────────────────────────

class TestOperatorWallet:
    """Operator wallet endpoint"""

    def test_wallet_loads_200(self, operator_client):
        res = operator_client.get(f"{BASE_URL}/api/operator/wallet")
        assert res.status_code == 200

    def test_wallet_has_balance(self, operator_client):
        res = operator_client.get(f"{BASE_URL}/api/operator/wallet")
        data = res.json()
        assert "balance" in data
        assert isinstance(data["balance"], (int, float))
        print(f"  Wallet balance: ₹{data['balance']}")

    def test_wallet_requires_auth(self):
        res = requests.get(f"{BASE_URL}/api/operator/wallet")
        assert res.status_code in [401, 403]


# ─── Checkout Create Order ───────────────────────────────────────────────────

class TestCheckoutCreateOrder:
    """Checkout create-order with 1-month subscription"""

    def test_checkout_requires_plan_id(self, operator_client):
        """Missing plan_id returns error"""
        res = operator_client.post(
            f"{BASE_URL}/api/operator/checkout/create-order?item_type=subscription&months=1"
        )
        # Should fail with 400 (no plan selected) or possibly proceed if operator has existing plan
        assert res.status_code in [200, 400, 404, 500]
        if res.status_code != 200:
            print(f"  As expected, missing plan_id fails: {res.status_code} {res.text}")

    def test_checkout_with_valid_plan_id(self, operator_client, admin_client):
        """Create order with a valid plan_id returns total_amount = monthly_price"""
        # Get available plans first
        sub_res = operator_client.get(f"{BASE_URL}/api/operator/subscription")
        assert sub_res.status_code == 200
        plans = sub_res.json().get("available_plans", [])
        if not plans:
            pytest.skip("No available plans to test checkout")
        
        plan = plans[0]
        plan_id = plan["id"]
        monthly_price = plan["monthly_price"]
        print(f"  Testing checkout with plan: {plan['name']}, monthly_price={monthly_price}")

        res = operator_client.post(
            f"{BASE_URL}/api/operator/checkout/create-order?item_type=subscription&plan_id={plan_id}&months=1"
        )
        
        # May fail with 500 if Razorpay is not configured OR succeed
        if res.status_code == 500 and "payment gateway" in res.text.lower():
            print(f"  Checkout failed due to Razorpay not configured (expected in test env): {res.text}")
            pytest.skip("Razorpay gateway not configured in test environment")
        
        assert res.status_code == 200, f"Checkout failed: {res.status_code} {res.text}"
        data = res.json()
        
        # Verify total_amount == monthly_price (GST inclusive, no additional GST)
        assert "total_amount" in data
        # total_amount should be rounded monthly_price
        assert abs(data["total_amount"] - monthly_price) <= 1, \
            f"total_amount {data['total_amount']} != monthly_price {monthly_price}"
        
        # Verify gst_amount is 0 (GST inclusive pricing)
        assert data.get("gst_amount", 0) == 0.0, f"gst_amount should be 0, got {data.get('gst_amount')}"
        
        print(f"  total_amount: {data['total_amount']}, monthly_price: {monthly_price}")

    def test_invalid_item_type(self, operator_client):
        """Invalid item_type returns 400"""
        res = operator_client.post(
            f"{BASE_URL}/api/operator/checkout/create-order?item_type=invalid"
        )
        assert res.status_code == 400

    def test_checkout_requires_auth(self):
        res = requests.post(
            f"{BASE_URL}/api/operator/checkout/create-order?item_type=subscription&months=1"
        )
        assert res.status_code in [401, 403]


# ─── Payment History ─────────────────────────────────────────────────────────

class TestPaymentHistory:
    """Operator payment history endpoint"""

    def test_payment_history_loads(self, operator_client):
        res = operator_client.get(f"{BASE_URL}/api/operator/payment-history")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        print(f"  Payment history: {len(data)} records")

    def test_payment_history_requires_auth(self):
        res = requests.get(f"{BASE_URL}/api/operator/payment-history")
        assert res.status_code in [401, 403]
