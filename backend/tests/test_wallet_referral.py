"""
Test suite for Wallet & Referral System
Tests: wallet endpoints, referral code generation, admin wallet view
"""
import pytest
import requests
import os
import re

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
OPERATOR1_EMAIL = "operator1@test.com"
OPERATOR1_PASSWORD = "Test@123"
OPERATOR1_REFERRAL_CODE = "REF-8HVOO1"

OPERATOR2_EMAIL = "operator2@test.com"
OPERATOR2_PASSWORD = "Test@123"

ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "Admin@123"


@pytest.fixture(scope="module")
def operator1_token():
    """Get operator1 access token."""
    res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OPERATOR1_EMAIL,
        "password": OPERATOR1_PASSWORD,
    })
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def operator2_token():
    """Get operator2 access token."""
    res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": OPERATOR2_EMAIL,
        "password": OPERATOR2_PASSWORD,
    })
    if res.status_code != 200:
        pytest.skip("operator2 login failed - skipping operator2 tests")
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    """Get admin access token."""
    res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    return res.json()["access_token"]


# ─── Operator Wallet Tests ────────────────────────────────────────────────────

class TestOperatorWallet:
    """GET /api/operator/wallet tests"""

    def test_get_wallet_success(self, operator1_token):
        """Wallet returns 200 with correct fields."""
        res = requests.get(
            f"{BASE_URL}/api/operator/wallet",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        print(f"Wallet data: {data}")
        assert "balance" in data, "Missing 'balance' field"
        assert "referral_code" in data, "Missing 'referral_code' field"
        assert "wallet_suspended" in data, "Missing 'wallet_suspended' field"
        assert isinstance(data["balance"], (int, float)), "balance should be numeric"
        assert isinstance(data["wallet_suspended"], bool), "wallet_suspended should be bool"

    def test_wallet_has_referral_code_format(self, operator1_token):
        """Referral code matches REF-XXXXXX format."""
        res = requests.get(
            f"{BASE_URL}/api/operator/wallet",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        referral_code = data.get("referral_code", "")
        print(f"Referral code: {referral_code}")
        assert referral_code, "Referral code should not be empty"
        # REF- followed by 6 uppercase alphanumeric chars
        assert re.match(r"^REF-[A-Z0-9]{6,8}$", referral_code), \
            f"Referral code '{referral_code}' does not match REF-XXXXXX format"

    def test_wallet_operator1_referral_code(self, operator1_token):
        """Operator1 referral code matches known value REF-8HVOO1."""
        res = requests.get(
            f"{BASE_URL}/api/operator/wallet",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        print(f"Operator1 referral code: {data.get('referral_code')}")
        assert data.get("referral_code") == OPERATOR1_REFERRAL_CODE, \
            f"Expected {OPERATOR1_REFERRAL_CODE}, got {data.get('referral_code')}"

    def test_wallet_operator2_referred_by_code(self, operator2_token):
        """Operator2 (registered with referral code) has referred_by_code in wallet."""
        res = requests.get(
            f"{BASE_URL}/api/operator/wallet",
            headers={"Authorization": f"Bearer {operator2_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        print(f"Operator2 wallet: {data}")
        assert "referred_by_code" in data, "Missing 'referred_by_code' field"
        referred_by = data.get("referred_by_code")
        print(f"referred_by_code: {referred_by}")
        # operator2 registered with REF-8HVOO1
        assert referred_by == OPERATOR1_REFERRAL_CODE, \
            f"Expected referred_by_code={OPERATOR1_REFERRAL_CODE}, got {referred_by}"

    def test_wallet_unauthenticated(self):
        """Wallet endpoint returns 401/403 without token."""
        res = requests.get(f"{BASE_URL}/api/operator/wallet")
        assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}"

    def test_wallet_admin_access_denied(self, admin_token):
        """Admin cannot access operator wallet (should get 400)."""
        res = requests.get(
            f"{BASE_URL}/api/operator/wallet",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code in [400, 403], f"Expected 400/403 for admin, got {res.status_code}"


# ─── Wallet Transactions Tests ────────────────────────────────────────────────

class TestWalletTransactions:
    """GET /api/operator/wallet/transactions tests"""

    def test_get_transactions_success(self, operator1_token):
        """Transactions endpoint returns 200 with correct structure."""
        res = requests.get(
            f"{BASE_URL}/api/operator/wallet/transactions",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        print(f"Transactions response: total={data.get('total')}, count={len(data.get('transactions', []))}")
        assert "transactions" in data, "Missing 'transactions' field"
        assert "total" in data, "Missing 'total' field"
        assert isinstance(data["transactions"], list), "transactions should be list"
        assert isinstance(data["total"], int), "total should be int"

    def test_transactions_pagination(self, operator1_token):
        """Pagination params are accepted."""
        res = requests.get(
            f"{BASE_URL}/api/operator/wallet/transactions?skip=0&limit=5",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["transactions"]) <= 5, "Should respect limit=5"

    def test_transactions_unauthenticated(self):
        """Transactions endpoint returns 401/403 without token."""
        res = requests.get(f"{BASE_URL}/api/operator/wallet/transactions")
        assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}"

    def test_transaction_fields(self, operator1_token):
        """Each transaction has expected fields if any transactions exist."""
        res = requests.get(
            f"{BASE_URL}/api/operator/wallet/transactions",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        txs = data.get("transactions", [])
        if txs:
            tx = txs[0]
            print(f"Sample transaction: {tx}")
            assert "id" in tx, "Transaction missing 'id'"
            assert "type" in tx, "Transaction missing 'type'"
            assert "amount" in tx, "Transaction missing 'amount'"
            assert "description" in tx, "Transaction missing 'description'"
            assert "created_at" in tx, "Transaction missing 'created_at'"


# ─── Topup Create Order Tests ─────────────────────────────────────────────────

class TestTopupOrder:
    """POST /api/operator/wallet/topup/create-order tests"""

    def test_topup_below_minimum(self, operator1_token):
        """Amount below Rs.100 returns 400."""
        res = requests.post(
            f"{BASE_URL}/api/operator/wallet/topup/create-order?amount=50",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        assert res.status_code == 400, f"Expected 400, got {res.status_code}"
        print(f"Below minimum: {res.json()}")

    def test_topup_above_maximum(self, operator1_token):
        """Amount above Rs.50000 returns 400."""
        res = requests.post(
            f"{BASE_URL}/api/operator/wallet/topup/create-order?amount=60000",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        assert res.status_code == 400, f"Expected 400, got {res.status_code}"
        print(f"Above maximum: {res.json()}")

    def test_topup_no_gateway_configured(self, operator1_token):
        """Topup fails with 500 if no Razorpay key configured (expected behavior)."""
        res = requests.post(
            f"{BASE_URL}/api/operator/wallet/topup/create-order?amount=500",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        # Expected to fail since no Razorpay key is configured
        print(f"Topup create order status: {res.status_code}, response: {res.text}")
        assert res.status_code in [500, 400], \
            f"Expected 500/400 (no gateway configured), got {res.status_code}"


# ─── Admin Wallets Tests ───────────────────────────────────────────────────────

class TestAdminWallets:
    """GET /api/admin/wallets tests"""

    def test_admin_get_all_wallets(self, admin_token):
        """Admin can see all wallets with correct structure."""
        res = requests.get(
            f"{BASE_URL}/api/admin/wallets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        print(f"Admin wallets: total={data.get('total')}, count={len(data.get('wallets', []))}")
        assert "wallets" in data, "Missing 'wallets' field"
        assert "total" in data, "Missing 'total' field"
        assert isinstance(data["wallets"], list), "wallets should be list"

    def test_admin_wallets_sorted_by_balance(self, admin_token):
        """Admin wallets are sorted by lowest balance first."""
        res = requests.get(
            f"{BASE_URL}/api/admin/wallets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        wallets = data.get("wallets", [])
        if len(wallets) >= 2:
            balances = [w.get("balance", 0) for w in wallets]
            assert balances == sorted(balances), \
                f"Wallets not sorted by balance: {balances}"

    def test_admin_wallets_enriched_fields(self, admin_token):
        """Each wallet has enriched fields: company_name, operator_status, wallet_suspended."""
        res = requests.get(
            f"{BASE_URL}/api/admin/wallets",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        wallets = data.get("wallets", [])
        if wallets:
            w = wallets[0]
            print(f"Sample wallet: {w}")
            assert "company_name" in w, "Missing 'company_name'"
            assert "operator_status" in w, "Missing 'operator_status'"
            assert "wallet_suspended" in w, "Missing 'wallet_suspended'"
            assert "balance" in w, "Missing 'balance'"
            assert "operator_id" in w, "Missing 'operator_id'"

    def test_admin_wallets_unauthenticated(self):
        """Admin wallets endpoint returns 401/403 without token."""
        res = requests.get(f"{BASE_URL}/api/admin/wallets")
        assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}"

    def test_admin_wallets_operator_access_denied(self, operator1_token):
        """Operator cannot access admin wallets."""
        res = requests.get(
            f"{BASE_URL}/api/admin/wallets",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        assert res.status_code in [400, 403], \
            f"Expected 400/403 for operator on admin endpoint, got {res.status_code}"

    def test_admin_wallet_transactions(self, admin_token, operator1_token):
        """Admin can view transactions for a specific operator."""
        # First get operator1 wallet to get operator_id
        res_wallet = requests.get(
            f"{BASE_URL}/api/operator/wallet",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        assert res_wallet.status_code == 200
        operator_id = res_wallet.json().get("operator_id")
        print(f"Testing transactions for operator_id: {operator_id}")

        res = requests.get(
            f"{BASE_URL}/api/admin/wallets/{operator_id}/transactions",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert isinstance(data, list), "Should return a list of transactions"
        print(f"Admin view transactions count: {len(data)}")


# ─── Referral Code Generation ──────────────────────────────────────────────────

class TestReferralCodeGeneration:
    """Verify referral codes are generated correctly on registration."""

    def test_operator1_has_referral_code(self, operator1_token):
        """Operator1 has a referral code."""
        res = requests.get(
            f"{BASE_URL}/api/operator/wallet",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        assert res.status_code == 200
        code = res.json().get("referral_code", "")
        assert code, "Operator should have a referral code"
        print(f"Operator1 referral code: {code}")

    def test_referral_code_format_regex(self, operator1_token):
        """Referral code format is REF-XXXXXX (6 alphanumeric chars)."""
        res = requests.get(
            f"{BASE_URL}/api/operator/wallet",
            headers={"Authorization": f"Bearer {operator1_token}"}
        )
        code = res.json().get("referral_code", "")
        # Matches REF-<6-8 uppercase alphanumeric>
        assert re.match(r"^REF-[A-Z0-9]{6,8}$", code), \
            f"Referral code '{code}' format invalid"

    def test_operator2_has_referred_by(self, operator2_token):
        """Operator2 (registered with code) has referred_by_code set."""
        res = requests.get(
            f"{BASE_URL}/api/operator/wallet",
            headers={"Authorization": f"Bearer {operator2_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data.get("referred_by_code"), \
            "Operator2 should have referred_by_code since registered with a code"

    def test_referral_reward_active_field(self, operator2_token):
        """Wallet response includes referral_reward_active field."""
        res = requests.get(
            f"{BASE_URL}/api/operator/wallet",
            headers={"Authorization": f"Bearer {operator2_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "referral_reward_active" in data, "Missing 'referral_reward_active' field"
        print(f"referral_reward_active: {data.get('referral_reward_active')}")
