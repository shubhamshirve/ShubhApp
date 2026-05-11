"""
Backend tests for Task 2: Basic/Pro Plan Revamp
Tests: SaaS plan creation with plan_type, per_customer pricing, checkout order pricing
"""
import pytest
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment from frontend .env
load_dotenv(Path("/app/frontend/.env"))
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://whatsapp-stats-view.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "Admin@123"
OPERATOR1_EMAIL = "operator1@test.com"
OPERATOR1_PASSWORD = "Test@123"

# Known IDs from DB (seeded)
BASIC_PLAN_ID = "66149629-0db4-46f7-ae89-7556580b1654"
PRO_PLAN_ID = "de250946-df4b-46e7-97e4-78cf398a8006"
OPERATOR1_ID = "044f8fde-f6b7-44fd-8b9e-6ef1345732d6"

# Created during test (cleaned up after)
_created_plan_ids = []


@pytest.fixture(scope="module")
def admin_token():
    """Get admin JWT token."""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
    })
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def operator1_token():
    """Get operator1 JWT token."""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OPERATOR1_EMAIL, "password": OPERATOR1_PASSWORD
    })
    assert resp.status_code == 200, f"Operator1 login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def op1_headers(operator1_token):
    return {"Authorization": f"Bearer {operator1_token}"}


# ── GET /api/admin/saas-plans ──────────────────────────────────────────────

class TestGetSaaSPlans:
    """Tests for GET /api/admin/saas-plans"""

    def test_get_plans_returns_200(self, admin_headers):
        resp = requests.get(f"{BASE_URL}/api/admin/saas-plans", headers=admin_headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_get_plans_returns_list(self, admin_headers):
        resp = requests.get(f"{BASE_URL}/api/admin/saas-plans", headers=admin_headers)
        data = resp.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 2, f"Should have at least 2 plans, got {len(data)}"

    def test_get_plans_have_plan_type_field(self, admin_headers):
        resp = requests.get(f"{BASE_URL}/api/admin/saas-plans", headers=admin_headers)
        plans = resp.json()
        for plan in plans:
            assert "plan_type" in plan, f"Plan {plan['name']} missing plan_type field"

    def test_get_plans_have_per_customer_rate_field(self, admin_headers):
        resp = requests.get(f"{BASE_URL}/api/admin/saas-plans", headers=admin_headers)
        plans = resp.json()
        for plan in plans:
            assert "per_customer_rate" in plan, f"Plan {plan['name']} missing per_customer_rate field"

    def test_get_plans_have_monthly_base_fee_field(self, admin_headers):
        resp = requests.get(f"{BASE_URL}/api/admin/saas-plans", headers=admin_headers)
        plans = resp.json()
        for plan in plans:
            assert "monthly_base_fee" in plan, f"Plan {plan['name']} missing monthly_base_fee field"

    def test_basic_plan_has_correct_rate(self, admin_headers):
        resp = requests.get(f"{BASE_URL}/api/admin/saas-plans", headers=admin_headers)
        plans = resp.json()
        basic = next((p for p in plans if p.get("plan_type") == "basic"), None)
        assert basic is not None, "Basic plan not found"
        assert basic["per_customer_rate"] == 12.0, f"Basic plan per_customer_rate should be 12, got {basic['per_customer_rate']}"
        assert basic["monthly_base_fee"] == 0.0, f"Basic plan monthly_base_fee should be 0, got {basic['monthly_base_fee']}"
        assert basic["platform_fee_percentage"] == 0.0, f"Basic plan platform_fee should be 0, got {basic['platform_fee_percentage']}"
        assert basic["included_addons"] == [], f"Basic plan included_addons should be [], got {basic['included_addons']}"

    def test_pro_plan_has_correct_rate(self, admin_headers):
        resp = requests.get(f"{BASE_URL}/api/admin/saas-plans", headers=admin_headers)
        plans = resp.json()
        pro = next((p for p in plans if p.get("plan_type") == "pro"), None)
        assert pro is not None, "Pro plan not found"
        assert pro["per_customer_rate"] == 22.0, f"Pro plan per_customer_rate should be 22, got {pro['per_customer_rate']}"
        assert pro["monthly_base_fee"] == 1000.0, f"Pro plan monthly_base_fee should be 1000, got {pro['monthly_base_fee']}"
        assert pro["platform_fee_percentage"] == 0.0, f"Pro plan platform_fee should be 0, got {pro['platform_fee_percentage']}"

    def test_get_plans_returns_401_without_auth(self):
        resp = requests.get(f"{BASE_URL}/api/admin/saas-plans")
        assert resp.status_code in (401, 403), f"Expected 401/403 without auth, got {resp.status_code}"


# ── POST /api/admin/saas-plans (basic) ────────────────────────────────────

class TestCreateBasicPlan:
    """Tests for creating a Basic plan via POST /api/admin/saas-plans"""

    def test_create_basic_plan_returns_201_or_200(self, admin_headers):
        payload = {"name": "TEST_Basic_Plan_v2", "plan_type": "basic"}
        resp = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=payload, headers=admin_headers)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}: {resp.text}"
        _created_plan_ids.append(resp.json()["id"])

    def test_create_basic_plan_auto_sets_per_customer_rate_12(self, admin_headers):
        payload = {"name": "TEST_Basic_Plan_rate_check", "plan_type": "basic"}
        resp = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=payload, headers=admin_headers)
        assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
        data = resp.json()
        _created_plan_ids.append(data["id"])
        assert data["per_customer_rate"] == 12.0, f"Expected per_customer_rate=12, got {data['per_customer_rate']}"

    def test_create_basic_plan_auto_sets_monthly_base_fee_0(self, admin_headers):
        payload = {"name": "TEST_Basic_base_fee_check", "plan_type": "basic"}
        resp = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=payload, headers=admin_headers)
        assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
        data = resp.json()
        _created_plan_ids.append(data["id"])
        assert data["monthly_base_fee"] == 0.0, f"Expected monthly_base_fee=0, got {data['monthly_base_fee']}"

    def test_create_basic_plan_auto_sets_platform_fee_0(self, admin_headers):
        payload = {"name": "TEST_Basic_fee_check", "plan_type": "basic"}
        resp = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=payload, headers=admin_headers)
        assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
        data = resp.json()
        _created_plan_ids.append(data["id"])
        assert data["platform_fee_percentage"] == 0.0, f"Expected platform_fee=0, got {data['platform_fee_percentage']}"

    def test_create_basic_plan_auto_sets_included_addons_empty(self, admin_headers):
        payload = {"name": "TEST_Basic_addons_check", "plan_type": "basic"}
        resp = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=payload, headers=admin_headers)
        assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
        data = resp.json()
        _created_plan_ids.append(data["id"])
        assert data["included_addons"] == [], f"Expected included_addons=[], got {data['included_addons']}"

    def test_create_basic_plan_persists_in_get(self, admin_headers):
        # Create plan
        payload = {"name": "TEST_Basic_Plan_persist", "plan_type": "basic"}
        create_resp = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=payload, headers=admin_headers)
        assert create_resp.status_code in (200, 201), f"Create failed: {create_resp.text}"
        plan_id = create_resp.json()["id"]
        _created_plan_ids.append(plan_id)

        # GET to verify persistence
        get_resp = requests.get(f"{BASE_URL}/api/admin/saas-plans", headers=admin_headers)
        plans = get_resp.json()
        found = next((p for p in plans if p["id"] == plan_id), None)
        assert found is not None, f"Created plan {plan_id} not found in GET response"
        assert found["plan_type"] == "basic"
        assert found["per_customer_rate"] == 12.0


# ── POST /api/admin/saas-plans (pro) ──────────────────────────────────────

class TestCreateProPlan:
    """Tests for creating a Pro plan via POST /api/admin/saas-plans"""

    def test_create_pro_plan_returns_200_or_201(self, admin_headers):
        payload = {"name": "TEST_Pro_Plan_v2", "plan_type": "pro"}
        resp = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=payload, headers=admin_headers)
        assert resp.status_code in (200, 201), f"Expected 200/201, got {resp.status_code}: {resp.text}"
        _created_plan_ids.append(resp.json()["id"])

    def test_create_pro_plan_auto_sets_per_customer_rate_22(self, admin_headers):
        payload = {"name": "TEST_Pro_rate_check", "plan_type": "pro"}
        resp = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=payload, headers=admin_headers)
        assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
        data = resp.json()
        _created_plan_ids.append(data["id"])
        assert data["per_customer_rate"] == 22.0, f"Expected per_customer_rate=22, got {data['per_customer_rate']}"

    def test_create_pro_plan_auto_sets_monthly_base_fee_1000(self, admin_headers):
        payload = {"name": "TEST_Pro_base_fee_check", "plan_type": "pro"}
        resp = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=payload, headers=admin_headers)
        assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
        data = resp.json()
        _created_plan_ids.append(data["id"])
        assert data["monthly_base_fee"] == 1000.0, f"Expected monthly_base_fee=1000, got {data['monthly_base_fee']}"

    def test_create_pro_plan_auto_sets_platform_fee_0(self, admin_headers):
        payload = {"name": "TEST_Pro_fee_check", "plan_type": "pro"}
        resp = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=payload, headers=admin_headers)
        assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
        data = resp.json()
        _created_plan_ids.append(data["id"])
        assert data["platform_fee_percentage"] == 0.0, f"Expected platform_fee=0, got {data['platform_fee_percentage']}"

    def test_create_pro_plan_auto_includes_all_addons(self, admin_headers):
        """Pro plan should include all addons when created via API (after addons exist)"""
        # First get all existing addon codes
        addons_resp = requests.get(f"{BASE_URL}/api/admin/addons", headers=admin_headers)
        assert addons_resp.status_code == 200
        all_addon_codes = [a["code"] for a in addons_resp.json()]

        payload = {"name": "TEST_Pro_addons_check", "plan_type": "pro"}
        resp = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=payload, headers=admin_headers)
        assert resp.status_code in (200, 201), f"Create failed: {resp.text}"
        data = resp.json()
        _created_plan_ids.append(data["id"])

        # Pro plan should have all addon codes
        for code in all_addon_codes:
            assert code in data["included_addons"], f"Pro plan missing addon '{code}' in included_addons"

    def test_create_pro_plan_persists_in_get(self, admin_headers):
        payload = {"name": "TEST_Pro_Plan_persist", "plan_type": "pro"}
        create_resp = requests.post(f"{BASE_URL}/api/admin/saas-plans", json=payload, headers=admin_headers)
        assert create_resp.status_code in (200, 201), f"Create failed: {create_resp.text}"
        plan_id = create_resp.json()["id"]
        _created_plan_ids.append(plan_id)

        get_resp = requests.get(f"{BASE_URL}/api/admin/saas-plans", headers=admin_headers)
        plans = get_resp.json()
        found = next((p for p in plans if p["id"] == plan_id), None)
        assert found is not None, f"Created plan {plan_id} not found in GET"
        assert found["plan_type"] == "pro"
        assert found["per_customer_rate"] == 22.0
        assert found["monthly_base_fee"] == 1000.0


# ── Checkout Order Pricing Tests ───────────────────────────────────────────

class TestCheckoutOrderPricing:
    """
    Tests for POST /api/operator/checkout/create-order
    operator1 has 5 active subscribers
    Basic: 5 * 12 = 60, Pro: 5 * 22 + 1000 = 1110
    """

    def test_basic_plan_checkout_returns_200(self, op1_headers):
        resp = requests.post(
            f"{BASE_URL}/api/operator/checkout/create-order"
            f"?item_type=subscription&plan_id={BASIC_PLAN_ID}&months=1",
            headers=op1_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_basic_plan_checkout_calculates_correct_base_amount(self, op1_headers):
        """Basic plan: 5 subscribers * Rs.12 = Rs.60"""
        resp = requests.post(
            f"{BASE_URL}/api/operator/checkout/create-order"
            f"?item_type=subscription&plan_id={BASIC_PLAN_ID}&months=1",
            headers=op1_headers
        )
        assert resp.status_code == 200, f"Create order failed: {resp.text}"
        data = resp.json()
        assert data["base_amount"] == 60.0, f"Expected base_amount=60, got {data['base_amount']}"

    def test_basic_plan_checkout_description_mentions_per_customer(self, op1_headers):
        """Basic plan description should mention subscribers and per-customer rate"""
        resp = requests.post(
            f"{BASE_URL}/api/operator/checkout/create-order"
            f"?item_type=subscription&plan_id={BASIC_PLAN_ID}&months=1",
            headers=op1_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        desc = data.get("description", "")
        assert "subscriber" in desc.lower() or "₹12" in desc or "customer" in desc.lower(), \
            f"Description should mention per-customer pricing, got: {desc}"

    def test_pro_plan_checkout_returns_200(self, op1_headers):
        resp = requests.post(
            f"{BASE_URL}/api/operator/checkout/create-order"
            f"?item_type=subscription&plan_id={PRO_PLAN_ID}&months=1",
            headers=op1_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_pro_plan_checkout_calculates_correct_base_amount(self, op1_headers):
        """Pro plan: 5 subscribers * Rs.22 + Rs.1000 base = Rs.1110"""
        resp = requests.post(
            f"{BASE_URL}/api/operator/checkout/create-order"
            f"?item_type=subscription&plan_id={PRO_PLAN_ID}&months=1",
            headers=op1_headers
        )
        assert resp.status_code == 200, f"Create order failed: {resp.text}"
        data = resp.json()
        assert data["base_amount"] == 1110.0, f"Expected base_amount=1110, got {data['base_amount']}"

    def test_pro_plan_checkout_description_mentions_base_fee(self, op1_headers):
        """Pro plan description should mention base fee"""
        resp = requests.post(
            f"{BASE_URL}/api/operator/checkout/create-order"
            f"?item_type=subscription&plan_id={PRO_PLAN_ID}&months=1",
            headers=op1_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        desc = data.get("description", "")
        assert "1000" in desc or "base" in desc.lower(), \
            f"Description should mention base fee, got: {desc}"

    def test_basic_plan_checkout_3_months_multiplied(self, op1_headers):
        """3 months: 5 * 12 * 3 = 180"""
        resp = requests.post(
            f"{BASE_URL}/api/operator/checkout/create-order"
            f"?item_type=subscription&plan_id={BASIC_PLAN_ID}&months=3",
            headers=op1_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["base_amount"] == 180.0, f"Expected base_amount=180 for 3 months, got {data['base_amount']}"

    def test_pro_plan_checkout_3_months_multiplied(self, op1_headers):
        """3 months: (5 * 22 + 1000) * 3 = 3330"""
        resp = requests.post(
            f"{BASE_URL}/api/operator/checkout/create-order"
            f"?item_type=subscription&plan_id={PRO_PLAN_ID}&months=3",
            headers=op1_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["base_amount"] == 3330.0, f"Expected base_amount=3330 for 3 months, got {data['base_amount']}"


# ── DB Wallet Credit Amount Tests ──────────────────────────────────────────

class TestCheckoutOrderWalletCredit:
    """
    Tests that checkout_orders in DB have correct wallet_credit_amount
    Basic: wallet_credit_amount=0
    Pro: wallet_credit_amount=1000
    """

    def test_db_has_checkout_orders(self):
        """Verify that checkout_orders exist in DB from previous API calls."""
        import asyncio
        import motor.motor_asyncio
        from pathlib import Path
        from dotenv import load_dotenv

        load_dotenv(Path("/app/.env"))
        MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        DB_NAME = os.environ.get("DB_NAME", "saas_db")

        async def check():
            client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
            db_client = client[DB_NAME]
            orders = await db_client.checkout_orders.find(
                {"deleted_at": None}, {"_id": 0}
            ).sort("created_at", -1).to_list(20)
            client.close()
            return orders

        orders = asyncio.run(check())
        assert len(orders) > 0, "No checkout orders found in DB"

    def test_basic_plan_checkout_order_has_wallet_credit_0(self):
        """Basic plan checkout order should have wallet_credit_amount=0"""
        import asyncio
        import motor.motor_asyncio
        from pathlib import Path
        from dotenv import load_dotenv

        load_dotenv(Path("/app/.env"))
        MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        DB_NAME = os.environ.get("DB_NAME", "saas_db")

        async def check():
            client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
            db_client = client[DB_NAME]
            # Get the most recent basic plan order
            orders = await db_client.checkout_orders.find(
                {"plan_id": BASIC_PLAN_ID, "deleted_at": None}, {"_id": 0}
            ).sort("created_at", -1).to_list(5)
            client.close()
            return orders

        orders = asyncio.run(check())
        assert len(orders) > 0, f"No checkout orders for basic plan ({BASIC_PLAN_ID}) found in DB"
        latest = orders[0]
        assert latest["wallet_credit_amount"] == 0, \
            f"Expected wallet_credit_amount=0 for basic plan, got {latest['wallet_credit_amount']}"

    def test_pro_plan_checkout_order_has_wallet_credit_proportional(self):
        """Pro plan checkout order wallet_credit_amount = monthly_base_fee * months (1000 per month)"""
        import asyncio
        import motor.motor_asyncio
        from pathlib import Path
        from dotenv import load_dotenv

        load_dotenv(Path("/app/.env"))
        MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        DB_NAME = os.environ.get("DB_NAME", "saas_db")

        async def check():
            client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
            db_client = client[DB_NAME]
            orders = await db_client.checkout_orders.find(
                {"plan_id": PRO_PLAN_ID, "deleted_at": None}, {"_id": 0}
            ).sort("created_at", -1).to_list(10)
            client.close()
            return orders

        orders = asyncio.run(check())
        assert len(orders) > 0, f"No checkout orders for pro plan ({PRO_PLAN_ID}) found in DB"
        # Find a 1-month order to check wallet_credit = 1000
        one_month_order = next((o for o in orders if o.get("months") == 1), None)
        assert one_month_order is not None, "No 1-month pro plan order found"
        assert one_month_order["wallet_credit_amount"] == 1000.0, \
            f"Expected wallet_credit_amount=1000 for 1-month pro plan, got {one_month_order['wallet_credit_amount']}"

    def test_basic_plan_checkout_order_base_amount_60(self):
        """DB: Basic 1-month plan order base_amount should be 60 (5 * 12)"""
        import asyncio
        import motor.motor_asyncio
        from pathlib import Path
        from dotenv import load_dotenv

        load_dotenv(Path("/app/.env"))
        MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        DB_NAME = os.environ.get("DB_NAME", "saas_db")

        async def check():
            client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
            db_client = client[DB_NAME]
            orders = await db_client.checkout_orders.find(
                {"plan_id": BASIC_PLAN_ID, "deleted_at": None}, {"_id": 0}
            ).sort("created_at", -1).to_list(10)
            client.close()
            return orders

        orders = asyncio.run(check())
        assert len(orders) > 0, "No basic plan orders in DB"
        one_month_order = next((o for o in orders if o.get("months") == 1), None)
        assert one_month_order is not None, "No 1-month basic plan order found"
        assert one_month_order["base_amount"] == 60.0, \
            f"Expected base_amount=60 in DB for 1-month basic plan, got {one_month_order['base_amount']}"

    def test_pro_plan_checkout_order_base_amount_1110(self):
        """DB: Pro 1-month plan order base_amount should be 1110 (5 * 22 + 1000)"""
        import asyncio
        import motor.motor_asyncio
        from pathlib import Path
        from dotenv import load_dotenv

        load_dotenv(Path("/app/.env"))
        MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        DB_NAME = os.environ.get("DB_NAME", "saas_db")

        async def check():
            client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
            db_client = client[DB_NAME]
            orders = await db_client.checkout_orders.find(
                {"plan_id": PRO_PLAN_ID, "deleted_at": None}, {"_id": 0}
            ).sort("created_at", -1).to_list(10)
            client.close()
            return orders

        orders = asyncio.run(check())
        assert len(orders) > 0, "No pro plan orders in DB"
        one_month_order = next((o for o in orders if o.get("months") == 1), None)
        assert one_month_order is not None, "No 1-month pro plan order found"
        assert one_month_order["base_amount"] == 1110.0, \
            f"Expected base_amount=1110 in DB for 1-month pro plan, got {one_month_order['base_amount']}"


# ── Cleanup ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_plans():
    """Delete TEST_ prefixed plans created during tests."""
    yield
    if not _created_plan_ids:
        return
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        if resp.status_code != 200:
            return
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        for plan_id in _created_plan_ids:
            requests.delete(f"{BASE_URL}/api/admin/saas-plans/{plan_id}", headers=headers)
        print(f"Cleanup: deleted {len(_created_plan_ids)} test plans")
    except Exception as e:
        print(f"Cleanup error: {e}")
