"""Tests for impersonation using httpOnly cookie auth."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"


def _login(session):
    return session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )


@pytest.fixture
def admin_session():
    s = requests.Session()
    r = _login(s)
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    return s


@pytest.fixture
def operator_id(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/operators")
    assert r.status_code == 200
    ops = r.json()
    if not ops:
        # seed an operator via admin endpoint
        payload = {
            "company_name": "TEST_ImpOp",
            "owner_name": "Test Owner",
            "email": "TEST_imp_op@test.com",
            "phone": "9999999999",
            "password": "test123",
        }
        cr = admin_session.post(f"{BASE_URL}/api/admin/operators", json=payload)
        assert cr.status_code in (200, 201), f"Failed to seed operator: {cr.text}"
        r = admin_session.get(f"{BASE_URL}/api/admin/operators")
        ops = r.json()
    assert ops, "No operator available"
    return ops[0]["id"]


class TestImpersonationCookie:
    def test_impersonate_sets_httponly_cookie(self, admin_session, operator_id):
        admin_cookie = admin_session.cookies.get("access_token")
        assert admin_cookie, "Admin cookie must be present"

        r = admin_session.post(
            f"{BASE_URL}/api/admin/operators/{operator_id}/impersonate"
        )
        assert r.status_code == 200, f"Impersonate failed: {r.text}"
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "operator" in data

        sc = r.headers.get("set-cookie", "").lower()
        assert "access_token=" in sc
        assert "httponly" in sc, "Cookie missing HttpOnly"
        assert "samesite=lax" in sc, "Cookie missing SameSite=Lax"
        assert "secure" in sc, "Cookie missing Secure"

        # Cookie in session jar should now be impersonation token
        new_cookie = admin_session.cookies.get("access_token")
        assert new_cookie and new_cookie != admin_cookie, "Cookie should be updated"

    def test_me_via_cookie_shows_operator_and_impersonated_by(
        self, admin_session, operator_id
    ):
        r = admin_session.post(
            f"{BASE_URL}/api/admin/operators/{operator_id}/impersonate"
        )
        assert r.status_code == 200
        # rely solely on cookie (no Authorization header)
        me = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert me.status_code == 200, me.text
        mdata = me.json()
        assert mdata["role"] == "operator"
        assert mdata.get("impersonated_by"), "impersonated_by must be set"

    def test_return_from_impersonate_cookie(self, admin_session, operator_id):
        # Impersonate
        r = admin_session.post(
            f"{BASE_URL}/api/admin/operators/{operator_id}/impersonate"
        )
        assert r.status_code == 200
        imp_cookie = admin_session.cookies.get("access_token")

        # Return (using cookie)
        rr = admin_session.post(f"{BASE_URL}/api/admin/return-from-impersonate")
        assert rr.status_code == 200, f"Return failed: {rr.text}"
        rdata = rr.json()
        assert "access_token" in rdata
        assert rdata["token_type"] == "bearer"

        sc = rr.headers.get("set-cookie", "").lower()
        assert "access_token=" in sc
        assert "httponly" in sc
        assert "samesite=lax" in sc
        assert "secure" in sc

        new_cookie = admin_session.cookies.get("access_token")
        assert new_cookie and new_cookie != imp_cookie, "Cookie should switch back"

        # Now /me should be admin again with no impersonated_by
        me = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert me.status_code == 200
        mdata = me.json()
        assert mdata["role"] == "admin"
        assert mdata.get("impersonated_by") in (None, ""), (
            f"impersonated_by should be null for admin, got {mdata.get('impersonated_by')}"
        )

    def test_return_without_impersonation_returns_400(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/return-from-impersonate")
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_session_persistence_during_impersonation(
        self, admin_session, operator_id
    ):
        assert admin_session.post(
            f"{BASE_URL}/api/admin/operators/{operator_id}/impersonate"
        ).status_code == 200
        for _ in range(3):
            me = admin_session.get(f"{BASE_URL}/api/auth/me")
            assert me.status_code == 200
            assert me.json()["role"] == "operator"
