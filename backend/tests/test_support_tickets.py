"""Support Ticket System backend tests - Task 5."""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASS = "Admin@123"
OPERATOR_EMAIL = "operator1@test.com"
OPERATOR_PASS = "Test@123"

# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def operator_token(api):
    r = api.post(f"{BASE_URL}/api/auth/login", json={"email": OPERATOR_EMAIL, "password": OPERATOR_PASS})
    assert r.status_code == 200, f"Operator login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def operator_headers(operator_token):
    return {"Authorization": f"Bearer {operator_token}"}


# ─── Ticket IDs to share across tests ─────────────────────────────────────────
_created_ticket_id = None


# ─── Operator: Create Ticket ──────────────────────────────────────────────────

class TestCreateTicket:
    """POST /api/operator/support/tickets"""

    def test_create_ticket_success(self, api, operator_headers):
        global _created_ticket_id
        payload = {
            "title": "TEST_Internet Outage Issue",
            "description": "Our subscribers are facing intermittent connectivity issues since this morning.",
            "priority": "high"
        }
        r = api.post(f"{BASE_URL}/api/operator/support/tickets", json=payload, headers=operator_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["title"] == payload["title"]
        assert data["description"] == payload["description"]
        assert data["priority"] == "high"
        assert data["status"] == "open"
        assert "id" in data
        assert data["reply_count"] == 0
        _created_ticket_id = data["id"]
        print(f"Created ticket id: {_created_ticket_id}")

    def test_create_ticket_missing_title(self, api, operator_headers):
        r = api.post(f"{BASE_URL}/api/operator/support/tickets", json={
            "description": "Some issue", "priority": "low"
        }, headers=operator_headers)
        assert r.status_code == 400

    def test_create_ticket_missing_description(self, api, operator_headers):
        r = api.post(f"{BASE_URL}/api/operator/support/tickets", json={
            "title": "TEST_Title only", "priority": "medium"
        }, headers=operator_headers)
        assert r.status_code == 400

    def test_create_ticket_invalid_priority(self, api, operator_headers):
        r = api.post(f"{BASE_URL}/api/operator/support/tickets", json={
            "title": "TEST_Bad priority",
            "description": "desc",
            "priority": "critical"
        }, headers=operator_headers)
        assert r.status_code == 400

    def test_create_urgent_ticket(self, api, operator_headers):
        r = api.post(f"{BASE_URL}/api/operator/support/tickets", json={
            "title": "TEST_Urgent billing issue",
            "description": "Payments are failing for all subscribers.",
            "priority": "urgent"
        }, headers=operator_headers)
        assert r.status_code == 200
        assert r.json()["priority"] == "urgent"

    def test_create_ticket_requires_auth(self, api):
        r = api.post(f"{BASE_URL}/api/operator/support/tickets", json={
            "title": "TEST_No auth", "description": "Test", "priority": "low"
        })
        assert r.status_code == 401


# ─── Operator: List Tickets ───────────────────────────────────────────────────

class TestListOperatorTickets:
    """GET /api/operator/support/tickets"""

    def test_list_tickets_returns_own(self, api, operator_headers):
        r = api.get(f"{BASE_URL}/api/operator/support/tickets", headers=operator_headers)
        assert r.status_code == 200
        data = r.json()
        assert "tickets" in data
        assert "total" in data
        assert data["total"] >= 1  # At least the ticket we created

    def test_list_tickets_status_filter_open(self, api, operator_headers):
        r = api.get(f"{BASE_URL}/api/operator/support/tickets?status=open", headers=operator_headers)
        assert r.status_code == 200
        data = r.json()
        for t in data["tickets"]:
            assert t["status"] == "open"

    def test_list_tickets_status_filter_resolved(self, api, operator_headers):
        r = api.get(f"{BASE_URL}/api/operator/support/tickets?status=resolved", headers=operator_headers)
        assert r.status_code == 200
        data = r.json()
        for t in data["tickets"]:
            assert t["status"] == "resolved"

    def test_list_tickets_requires_auth(self, api):
        r = api.get(f"{BASE_URL}/api/operator/support/tickets")
        assert r.status_code == 401


# ─── Operator: Get Ticket Detail ─────────────────────────────────────────────

class TestGetTicketDetail:
    """GET /api/operator/support/tickets/{ticket_id}"""

    def test_get_ticket_detail(self, api, operator_headers):
        assert _created_ticket_id, "No ticket id from create test"
        r = api.get(f"{BASE_URL}/api/operator/support/tickets/{_created_ticket_id}", headers=operator_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == _created_ticket_id
        assert "replies" in data
        assert isinstance(data["replies"], list)

    def test_get_ticket_detail_not_found(self, api, operator_headers):
        r = api.get(f"{BASE_URL}/api/operator/support/tickets/nonexistent-id", headers=operator_headers)
        assert r.status_code == 404

    def test_get_ticket_detail_requires_auth(self, api):
        r = api.get(f"{BASE_URL}/api/operator/support/tickets/some-id")
        assert r.status_code == 401


# ─── Operator: Reply to Ticket ────────────────────────────────────────────────

class TestOperatorReply:
    """POST /api/operator/support/tickets/{ticket_id}/reply"""

    def test_operator_reply_success(self, api, operator_headers):
        assert _created_ticket_id, "No ticket id from create test"
        r = api.post(f"{BASE_URL}/api/operator/support/tickets/{_created_ticket_id}/reply",
                     json={"message": "Can you please look into this? It's affecting our business."},
                     headers=operator_headers)
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["ticket_id"] == _created_ticket_id
        assert data["message"] == "Can you please look into this? It's affecting our business."
        assert data["author_role"] in ["operator", "staff"]

    def test_operator_reply_empty_message(self, api, operator_headers):
        assert _created_ticket_id
        r = api.post(f"{BASE_URL}/api/operator/support/tickets/{_created_ticket_id}/reply",
                     json={"message": ""}, headers=operator_headers)
        assert r.status_code == 400

    def test_operator_reply_requires_auth(self, api):
        r = api.post(f"{BASE_URL}/api/operator/support/tickets/some-id/reply",
                     json={"message": "test"})
        assert r.status_code == 401

    def test_reply_count_incremented(self, api, operator_headers):
        """Verify reply count is updated after reply"""
        assert _created_ticket_id
        r = api.get(f"{BASE_URL}/api/operator/support/tickets/{_created_ticket_id}", headers=operator_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["reply_count"] >= 1


# ─── Admin: List All Tickets ──────────────────────────────────────────────────

class TestAdminListTickets:
    """GET /api/admin/support/tickets"""

    def test_admin_list_tickets(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "tickets" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_admin_tickets_have_company_name(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets", headers=admin_headers)
        assert r.status_code == 200
        tickets = r.json()["tickets"]
        # All tickets should have company_name field
        for t in tickets:
            assert "company_name" in t

    def test_admin_filter_by_status_open(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets?status=open", headers=admin_headers)
        assert r.status_code == 200
        for t in r.json()["tickets"]:
            assert t["status"] == "open"

    def test_admin_filter_by_priority_high(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets?priority=high", headers=admin_headers)
        assert r.status_code == 200
        for t in r.json()["tickets"]:
            assert t["priority"] == "high"

    def test_admin_filter_by_priority_urgent(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets?priority=urgent", headers=admin_headers)
        assert r.status_code == 200
        for t in r.json()["tickets"]:
            assert t["priority"] == "urgent"

    def test_admin_search_tickets(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets?search=TEST_Internet", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert any("Internet" in t["title"] for t in data["tickets"])

    def test_admin_list_requires_auth(self, api):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets")
        assert r.status_code == 401

    def test_operator_cannot_access_admin_endpoint(self, api, operator_headers):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets", headers=operator_headers)
        assert r.status_code in [401, 403]


# ─── Admin: Stats ─────────────────────────────────────────────────────────────

class TestAdminStats:
    """GET /api/admin/support/tickets/stats"""

    def test_stats_returns_correct_fields(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets/stats", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "open" in data
        assert "in_progress" in data
        assert "resolved" in data
        assert "urgent" in data

    def test_stats_are_non_negative(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets/stats", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["open"] >= 0
        assert data["in_progress"] >= 0
        assert data["resolved"] >= 0
        assert data["urgent"] >= 0

    def test_stats_open_count_reflects_created_ticket(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets/stats", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        # We created test tickets with status=open
        assert data["open"] >= 1

    def test_stats_requires_auth(self, api):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets/stats")
        assert r.status_code == 401


# ─── Admin: Get Ticket Detail ─────────────────────────────────────────────────

class TestAdminGetTicket:
    """GET /api/admin/support/tickets/{ticket_id}"""

    def test_admin_get_ticket_detail(self, api, admin_headers):
        assert _created_ticket_id
        r = api.get(f"{BASE_URL}/api/admin/support/tickets/{_created_ticket_id}", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == _created_ticket_id
        assert "replies" in data
        assert isinstance(data["replies"], list)
        assert "operator_info" in data

    def test_admin_ticket_has_operator_info(self, api, admin_headers):
        assert _created_ticket_id
        r = api.get(f"{BASE_URL}/api/admin/support/tickets/{_created_ticket_id}", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        op_info = data.get("operator_info", {})
        assert isinstance(op_info, dict)

    def test_admin_ticket_replies_include_operator_reply(self, api, admin_headers):
        assert _created_ticket_id
        r = api.get(f"{BASE_URL}/api/admin/support/tickets/{_created_ticket_id}", headers=admin_headers)
        assert r.status_code == 200
        replies = r.json()["replies"]
        assert len(replies) >= 1  # Operator added reply earlier

    def test_admin_get_ticket_not_found(self, api, admin_headers):
        r = api.get(f"{BASE_URL}/api/admin/support/tickets/nonexistent", headers=admin_headers)
        assert r.status_code == 404


# ─── Admin: Reply to Ticket ───────────────────────────────────────────────────

class TestAdminReply:
    """POST /api/admin/support/tickets/{ticket_id}/reply"""

    def test_admin_reply_auto_sets_in_progress(self, api, admin_headers):
        """Admin reply on open ticket should auto-set status to in_progress"""
        assert _created_ticket_id
        r = api.post(f"{BASE_URL}/api/admin/support/tickets/{_created_ticket_id}/reply",
                     json={"message": "We are investigating this issue. Please hold."},
                     headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["author_role"] == "admin"
        assert data["ticket_status"] == "in_progress"

    def test_admin_reply_status_persisted(self, api, admin_headers):
        """Verify status is actually updated to in_progress in DB"""
        assert _created_ticket_id
        r = api.get(f"{BASE_URL}/api/admin/support/tickets/{_created_ticket_id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_admin_reply_empty_message(self, api, admin_headers):
        assert _created_ticket_id
        r = api.post(f"{BASE_URL}/api/admin/support/tickets/{_created_ticket_id}/reply",
                     json={"message": ""}, headers=admin_headers)
        assert r.status_code == 400

    def test_admin_reply_requires_auth(self, api):
        r = api.post(f"{BASE_URL}/api/admin/support/tickets/some-id/reply",
                     json={"message": "test"})
        assert r.status_code == 401


# ─── Admin: Update Ticket Status ─────────────────────────────────────────────

class TestAdminUpdateStatus:
    """PUT /api/admin/support/tickets/{ticket_id}/status"""

    def test_update_status_to_resolved(self, api, admin_headers):
        assert _created_ticket_id
        r = api.put(f"{BASE_URL}/api/admin/support/tickets/{_created_ticket_id}/status",
                    json={"status": "resolved"}, headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == _created_ticket_id
        assert data["status"] == "resolved"

    def test_status_update_persisted(self, api, admin_headers):
        assert _created_ticket_id
        r = api.get(f"{BASE_URL}/api/admin/support/tickets/{_created_ticket_id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "resolved"

    def test_update_status_invalid(self, api, admin_headers):
        assert _created_ticket_id
        r = api.put(f"{BASE_URL}/api/admin/support/tickets/{_created_ticket_id}/status",
                    json={"status": "invalid_status"}, headers=admin_headers)
        assert r.status_code == 400

    def test_update_status_to_closed(self, api, admin_headers):
        assert _created_ticket_id
        r = api.put(f"{BASE_URL}/api/admin/support/tickets/{_created_ticket_id}/status",
                    json={"status": "closed"}, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "closed"

    def test_cannot_reply_to_closed_ticket_operator(self, api, operator_headers):
        """Operator should not be able to reply to a closed ticket"""
        assert _created_ticket_id
        r = api.post(f"{BASE_URL}/api/operator/support/tickets/{_created_ticket_id}/reply",
                     json={"message": "Follow-up on closed ticket."}, headers=operator_headers)
        assert r.status_code == 400

    def test_cannot_reply_to_closed_ticket_admin(self, api, admin_headers):
        """Admin should not be able to reply to a closed ticket"""
        assert _created_ticket_id
        r = api.post(f"{BASE_URL}/api/admin/support/tickets/{_created_ticket_id}/reply",
                     json={"message": "Admin reply on closed ticket."}, headers=admin_headers)
        assert r.status_code == 400

    def test_update_status_requires_auth(self, api):
        r = api.put(f"{BASE_URL}/api/admin/support/tickets/some-id/status",
                    json={"status": "resolved"})
        assert r.status_code == 401

    def test_update_status_not_found(self, api, admin_headers):
        r = api.put(f"{BASE_URL}/api/admin/support/tickets/nonexistent/status",
                    json={"status": "resolved"}, headers=admin_headers)
        assert r.status_code == 404
