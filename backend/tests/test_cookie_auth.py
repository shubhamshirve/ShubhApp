"""Tests for httpOnly cookie-based authentication migration."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture
def fresh_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(session):
    return session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )


class TestCookieLogin:
    def test_login_sets_httponly_cookie(self, fresh_session):
        r = _login(fresh_session)
        assert r.status_code == 200, f"login failed: {r.text}"
        data = r.json()
        assert "access_token" in data
        assert data["user"]["email"] == ADMIN_EMAIL

        # Check Set-Cookie header
        set_cookie = r.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie.lower(), f"No access_token cookie: {set_cookie}"
        low = set_cookie.lower()
        assert "httponly" in low, "Cookie missing HttpOnly attribute"
        assert "samesite=lax" in low, "Cookie missing SameSite=Lax"
        assert "secure" in low, "Cookie missing Secure attribute"
        # Session jar should have the cookie
        assert "access_token" in fresh_session.cookies.get_dict()

    def test_invalid_credentials_no_cookie(self, fresh_session):
        r = fresh_session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": "wrong"},
        )
        assert r.status_code == 401
        assert "access_token" not in fresh_session.cookies.get_dict()


class TestCookieAuthenticatedRequests:
    def test_me_via_cookie_only(self, fresh_session):
        assert _login(fresh_session).status_code == 200
        # Do NOT pass Authorization header, rely solely on cookie jar
        r = fresh_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200, f"/me via cookie failed: {r.text}"
        assert r.json()["email"] == ADMIN_EMAIL

    def test_me_via_bearer_header_still_works(self, fresh_session):
        r = _login(fresh_session)
        assert r.status_code == 200
        token = r.json()["access_token"]
        # Clear cookies; use only Authorization header for backward-compat
        bare = requests.Session()
        bare.headers.update({"Authorization": f"Bearer {token}"})
        r2 = bare.get(f"{BASE_URL}/api/auth/me")
        assert r2.status_code == 200, f"bearer fallback failed: {r2.text}"
        assert r2.json()["email"] == ADMIN_EMAIL

    def test_no_cookie_no_header_returns_401(self, fresh_session):
        r = fresh_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401

    def test_protected_endpoint_with_cookie(self, fresh_session):
        assert _login(fresh_session).status_code == 200
        r = fresh_session.get(f"{BASE_URL}/api/auth/app-state")
        assert r.status_code == 200, f"app-state failed: {r.text}"
        body = r.json()
        assert "maintenance_mode" in body
        assert body.get("role") == "admin"


class TestLogoutClearsCookie:
    def test_logout_clears_cookie_and_invalidates_session(self, fresh_session):
        assert _login(fresh_session).status_code == 200
        assert "access_token" in fresh_session.cookies.get_dict()

        r = fresh_session.post(f"{BASE_URL}/api/auth/logout")
        assert r.status_code == 200, f"logout failed: {r.text}"

        set_cookie = r.headers.get("set-cookie", "").lower()
        # FastAPI delete_cookie sets empty value with Max-Age=0 or expires in past
        assert "access_token=" in set_cookie
        assert ("max-age=0" in set_cookie) or ("expires=" in set_cookie)

        # After logout cookies should be cleared from session
        assert fresh_session.cookies.get("access_token", "") in ("", None)

        # Reusing the old cookie (session invalidated server-side) should fail
        # Try /me again - since cookie is cleared, expect 401
        r2 = fresh_session.get(f"{BASE_URL}/api/auth/me")
        assert r2.status_code == 401

    def test_logout_without_auth_returns_401(self, fresh_session):
        r = fresh_session.post(f"{BASE_URL}/api/auth/logout")
        assert r.status_code == 401


class TestSessionPersistence:
    def test_multiple_requests_reuse_cookie(self, fresh_session):
        assert _login(fresh_session).status_code == 200
        for _ in range(3):
            r = fresh_session.get(f"{BASE_URL}/api/auth/me")
            assert r.status_code == 200

    def test_new_login_invalidates_old_session(self, fresh_session):
        # First login
        s1 = requests.Session()
        assert _login(s1).status_code == 200
        token1 = s1.cookies.get("access_token")

        # Second login from another session
        s2 = requests.Session()
        assert _login(s2).status_code == 200

        # First session's token should now be invalid (session_id mismatch)
        bare = requests.Session()
        bare.cookies.set("access_token", token1)
        r = bare.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401, "Old session should be invalidated"
