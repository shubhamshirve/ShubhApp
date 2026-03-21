"""
Task 8 Tests: Admin Wallet Operations (credit / debit / suspend)
Run with:  pytest backend/tests/test_task8_admin_wallet.py -v
Requires a running server at http://localhost:8000 with:
  - A seeded admin account (admin@ebill.com / admin123)
  - At least one operator with a wallet
"""
import requests
import pytest

BASE_URL = "http://localhost:8000/api"
ADMIN_EMAIL = "admin@ebill.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_token():
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def first_operator_id(admin_token):
    """Return the operator_id of the first wallet in the admin wallet list."""
    res = requests.get(f"{BASE_URL}/admin/wallets", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    wallets = res.json().get("wallets", [])
    assert len(wallets) > 0, "No wallets found; ensure at least one operator exists."
    return wallets[0]["operator_id"]


class TestAdminWalletList:
    def test_wallet_list_returns_200(self, admin_token):
        res = requests.get(f"{BASE_URL}/admin/wallets", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        assert "wallets" in res.json()

    def test_wallet_fields_present(self, admin_token):
        res = requests.get(f"{BASE_URL}/admin/wallets", headers={"Authorization": f"Bearer {admin_token}"})
        for w in res.json().get("wallets", []):
            assert "balance" in w, "Missing 'balance'"
            assert "wallet_suspended" in w, "Missing 'wallet_suspended'"
            assert "company_name" in w, "Missing 'company_name'"

    def test_unauth_returns_401(self):
        res = requests.get(f"{BASE_URL}/admin/wallets")
        assert res.status_code == 401


class TestAdminWalletCredit:
    def test_credit_wallet_success(self, admin_token, first_operator_id):
        payload = {"amount": 100.0, "reason": "Test credit from automated test suite"}
        res = requests.post(
            f"{BASE_URL}/admin/wallets/{first_operator_id}/credit",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert "new_balance" in data
        assert data["new_balance"] > 0

    def test_credit_zero_amount_fails(self, admin_token, first_operator_id):
        res = requests.post(
            f"{BASE_URL}/admin/wallets/{first_operator_id}/credit",
            json={"amount": 0, "reason": "Should fail"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 422

    def test_credit_short_reason_fails(self, admin_token, first_operator_id):
        res = requests.post(
            f"{BASE_URL}/admin/wallets/{first_operator_id}/credit",
            json={"amount": 50, "reason": "bad"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 422

    def test_credit_nonexistent_operator_returns_404(self, admin_token):
        res = requests.post(
            f"{BASE_URL}/admin/wallets/nonexistent-id/credit",
            json={"amount": 50, "reason": "Test reason ok"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 404


class TestAdminWalletDebit:
    def test_debit_wallet_success(self, admin_token, first_operator_id):
        # First credit to ensure sufficient balance
        requests.post(
            f"{BASE_URL}/admin/wallets/{first_operator_id}/credit",
            json={"amount": 200, "reason": "Setup credit for debit test"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        payload = {"amount": 50.0, "reason": "Test debit from automated test suite"}
        res = requests.post(
            f"{BASE_URL}/admin/wallets/{first_operator_id}/debit",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert "new_balance" in data

    def test_debit_over_balance_fails(self, admin_token, first_operator_id):
        res = requests.post(
            f"{BASE_URL}/admin/wallets/{first_operator_id}/debit",
            json={"amount": 999999, "reason": "Should fail as over balance"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 400


class TestAdminWalletSuspend:
    def test_suspend_wallet(self, admin_token, first_operator_id):
        res = requests.post(
            f"{BASE_URL}/admin/wallets/{first_operator_id}/suspend",
            json={"suspend": True, "reason": "Automated suspension test"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        assert res.json()["wallet_suspended"] is True

    def test_unsuspend_wallet(self, admin_token, first_operator_id):
        res = requests.post(
            f"{BASE_URL}/admin/wallets/{first_operator_id}/suspend",
            json={"suspend": False, "reason": "Automated unsuspend test"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        assert res.json()["wallet_suspended"] is False

    def test_suspend_short_reason_fails(self, admin_token, first_operator_id):
        res = requests.post(
            f"{BASE_URL}/admin/wallets/{first_operator_id}/suspend",
            json={"suspend": True, "reason": "bad"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 422
