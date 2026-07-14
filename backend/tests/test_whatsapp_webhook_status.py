"""WhatsApp Cloud API webhook status events — tests for delivery_status pipeline.

Covers:
 (a) GET /api/webhooks/whatsapp verify handshake (correct + wrong token)
 (b) Save webhook_verify_token via PUT /api/admin/whatsapp-config
 (c) GET /api/admin/whatsapp-config returns masked preview & no leak
 (d) POST status events: sent → delivered → read pipeline updates a seeded log row
 (e) failed event with errors[].code / title / error_data.details
 (f) Orphan event → creates row with trigger='webhook_orphan'
 (g) Idempotency / no-downgrade (read should not be overwritten by delivered)
 (h) GET /api/admin/whatsapp-message-logs?delivery_status=<...> filter
"""
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient


# ─── Resolve BASE_URL from frontend/.env (REACT_APP_BACKEND_URL) ────────────
def _load_base_url() -> str:
    env_path = Path("/app/frontend/.env")
    for line in env_path.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not found in /app/frontend/.env")


BASE_URL = _load_base_url()
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "saas_db")
ADMIN_EMAIL = "admin@saas.com"
ADMIN_PASSWORD = "admin123"

VERIFY_TOKEN = "TEST_verify_token_abc123"
SEED_MSG_ID = "wamid.TEST_SEED_MSG_001"
ORPHAN_MSG_ID = "wamid.TEST_ORPHAN_MSG_999"


# ─── Shared fixtures ────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module", autouse=True)
def _set_verify_token_and_cleanup(admin_headers, mongo_db):
    """Save verify token once for the module, snapshot/restore prior config, clean test rows."""
    # snapshot existing wa config (so we don't permanently overwrite real creds)
    prior = mongo_db.global_settings.find_one({"type": "platform_whatsapp"}) or {}
    payload = {
        "phone_number_id": prior.get("phone_number_id") or "1234567890",
        "access_token": prior.get("access_token") or "TEST_dummy_access_token",
        "business_account_id": prior.get("business_account_id") or "",
        "webhook_verify_token": VERIFY_TOKEN,
    }
    r = requests.put(f"{BASE_URL}/api/admin/whatsapp-config", json=payload, headers=admin_headers, timeout=15)
    assert r.status_code == 200, f"PUT whatsapp-config failed: {r.status_code} {r.text}"

    # Pre-clean any leftover test rows
    mongo_db.whatsapp_message_logs.delete_many(
        {"message_id": {"$in": [SEED_MSG_ID, ORPHAN_MSG_ID]}}
    )
    yield
    # Teardown: remove test rows + restore config
    mongo_db.whatsapp_message_logs.delete_many(
        {"message_id": {"$in": [SEED_MSG_ID, ORPHAN_MSG_ID]}}
    )
    if prior:
        prior.pop("_id", None)
        mongo_db.global_settings.update_one(
            {"type": "platform_whatsapp"}, {"$set": prior}, upsert=True
        )


# ─── (a) Webhook GET verify ─────────────────────────────────────────────────
class TestWebhookVerify:
    def test_verify_wrong_token_returns_403(self):
        r = requests.get(
            f"{BASE_URL}/api/webhooks/whatsapp",
            params={"hub.mode": "subscribe", "hub.challenge": "XYZ", "hub.verify_token": "WRONG_TOKEN"},
            timeout=10,
        )
        assert r.status_code == 403, f"expected 403, got {r.status_code} body={r.text}"

    def test_verify_correct_token_echoes_challenge(self):
        r = requests.get(
            f"{BASE_URL}/api/webhooks/whatsapp",
            params={"hub.mode": "subscribe", "hub.challenge": "XYZ", "hub.verify_token": VERIFY_TOKEN},
            timeout=10,
        )
        assert r.status_code == 200, f"expected 200, got {r.status_code} body={r.text}"
        assert r.text == "XYZ", f"expected body 'XYZ', got '{r.text}'"
        assert "text/plain" in r.headers.get("content-type", "").lower()


# ─── (c) Admin config preview/masking ───────────────────────────────────────
class TestAdminConfigPreview:
    def test_get_returns_masked_verify_token_preview(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/whatsapp-config", headers=admin_headers, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "webhook_verify_token_preview" in data, "preview field missing"
        preview = data["webhook_verify_token_preview"]
        # Must NOT leak full token
        assert VERIFY_TOKEN not in preview, f"Full verify token leaked in preview: {preview}"
        # Should contain a mask marker
        assert "*" in preview, f"preview '{preview}' missing mask"
        # Must not return the raw access_token field
        assert "access_token" not in data or data.get("access_token") in (None, "", "****"), \
            f"raw access_token leaked: {data.get('access_token')}"
        assert "webhook_verify_token" not in data, "raw webhook_verify_token must not be returned"


# ─── (d)(e)(g) Status pipeline against a seeded log row ─────────────────────
def _seed_log(mongo_db, status="sent", delivery_status="sent"):
    now_iso = datetime.now(timezone.utc).isoformat()
    mongo_db.whatsapp_message_logs.delete_many({"message_id": SEED_MSG_ID})
    doc = {
        "id": "TEST_seedlog_id_001",
        "operator_id": None,
        "template_name": "TEST_template",
        "template_category": "test",
        "recipient_phone": "919999999999",
        "status": status,
        "delivery_status": delivery_status,
        "message_id": SEED_MSG_ID,
        "wa_id": "919999999999",
        "error_message": "",
        "error_code": None,
        "error_title": None,
        "delivered_at": None,
        "read_at": None,
        "failed_at": None,
        "events": [{"status": status, "timestamp": now_iso, "source": "send_api"}],
        "invoice_id": None,
        "invoice_number": "",
        "trigger": "manual_test",
        "created_at": now_iso,
    }
    mongo_db.whatsapp_message_logs.insert_one(doc)


def _post_status_event(msg_id: str, status: str, errors=None, recipient="919999999999"):
    st = {
        "id": msg_id,
        "status": status,
        "timestamp": str(int(time.time())),
        "recipient_id": recipient,
    }
    if errors:
        st["errors"] = errors
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "TEST_WABA", "changes": [{"field": "messages", "value": {"statuses": [st]}}]}],
    }
    return requests.post(f"{BASE_URL}/api/webhooks/whatsapp", json=payload, timeout=10)


class TestStatusPipeline:
    def test_delivered_event_updates_existing_row(self, mongo_db):
        _seed_log(mongo_db)
        r = _post_status_event(SEED_MSG_ID, "delivered")
        assert r.status_code == 200, r.text

        time.sleep(0.3)
        row = mongo_db.whatsapp_message_logs.find_one({"message_id": SEED_MSG_ID})
        assert row is not None
        assert row["delivery_status"] == "delivered"
        assert row["delivered_at"] is not None
        assert row["status"] == "sent"  # send-time status preserved
        assert any(e.get("source") == "webhook" and e.get("status") == "delivered" for e in row["events"])

    def test_read_event_after_delivered(self, mongo_db):
        # Continue from delivered row (don't reseed)
        r = _post_status_event(SEED_MSG_ID, "read")
        assert r.status_code == 200
        time.sleep(0.3)
        row = mongo_db.whatsapp_message_logs.find_one({"message_id": SEED_MSG_ID})
        assert row["delivery_status"] == "read"
        assert row["read_at"] is not None
        assert row["delivered_at"] is not None

    def test_no_downgrade_read_to_delivered(self, mongo_db):
        """A subsequent 'delivered' event after 'read' must NOT overwrite delivery_status."""
        # Row already at 'read' from previous test
        before = mongo_db.whatsapp_message_logs.find_one({"message_id": SEED_MSG_ID})
        assert before["delivery_status"] == "read"

        r = _post_status_event(SEED_MSG_ID, "delivered")
        assert r.status_code == 200
        time.sleep(0.3)
        after = mongo_db.whatsapp_message_logs.find_one({"message_id": SEED_MSG_ID})
        assert after["delivery_status"] == "read", \
            f"delivery_status downgraded! got {after['delivery_status']}"

    def test_failed_event_with_error_codes(self, mongo_db):
        # Reseed clean row
        _seed_log(mongo_db)
        errors = [{
            "code": 131026,
            "title": "Message undeliverable",
            "error_data": {"details": "Recipient phone number not in allowed list"},
        }]
        r = _post_status_event(SEED_MSG_ID, "failed", errors=errors)
        assert r.status_code == 200
        time.sleep(0.3)
        row = mongo_db.whatsapp_message_logs.find_one({"message_id": SEED_MSG_ID})
        assert row["delivery_status"] == "failed"
        assert row["failed_at"] is not None
        assert row["error_code"] == 131026
        assert row["error_title"] == "Message undeliverable"
        assert "Recipient phone number not in allowed list" in (row.get("error_message") or "")


# ─── (f) Orphan event ───────────────────────────────────────────────────────
class TestOrphanEvent:
    def test_orphan_creates_placeholder_row(self, mongo_db):
        mongo_db.whatsapp_message_logs.delete_many({"message_id": ORPHAN_MSG_ID})
        r = _post_status_event(ORPHAN_MSG_ID, "delivered", recipient="918888888888")
        assert r.status_code == 200, r.text
        time.sleep(0.3)
        row = mongo_db.whatsapp_message_logs.find_one({"message_id": ORPHAN_MSG_ID})
        assert row is not None, "Orphan placeholder row was not created"
        assert row.get("trigger") == "webhook_orphan"
        assert row.get("delivery_status") == "delivered"
        assert row.get("recipient_phone") == "918888888888"
        assert row.get("delivered_at") is not None


# ─── (h) delivery_status query filter ────────────────────────────────────────
class TestDeliveryStatusFilter:
    def test_filter_delivered_only(self, mongo_db, admin_headers):
        # Ensure we have at least one 'delivered' row (orphan from previous test)
        # And one non-delivered 'failed' row from seed test
        if not mongo_db.whatsapp_message_logs.find_one({"message_id": ORPHAN_MSG_ID, "delivery_status": "delivered"}):
            # re-create if previous test class deleted it
            _post_status_event(ORPHAN_MSG_ID, "delivered", recipient="918888888888")
            time.sleep(0.3)

        r = requests.get(
            f"{BASE_URL}/api/admin/whatsapp-message-logs",
            params={"delivery_status": "delivered"},
            headers=admin_headers,
            timeout=15,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        data = r.json()
        # Endpoint may return list or {"logs": [...]} — handle both
        rows = data if isinstance(data, list) else (data.get("logs") or data.get("items") or [])
        assert isinstance(rows, list), f"Unexpected response shape: {type(data)} {str(data)[:200]}"
        # Every row must have delivery_status == 'delivered'
        for row in rows:
            assert row.get("delivery_status") == "delivered", \
                f"Filter leak: row {row.get('message_id')} has delivery_status={row.get('delivery_status')}"
        # Our orphan row must be present
        assert any(r.get("message_id") == ORPHAN_MSG_ID for r in rows), \
            "Seeded orphan row (delivered) not returned by filter"

    def test_filter_read(self, mongo_db, admin_headers):
        # Seed a 'read' row directly
        msg_id = "wamid.TEST_FILTER_READ_001"
        mongo_db.whatsapp_message_logs.delete_many({"message_id": msg_id})
        try:
            _seed_log(mongo_db)  # creates SEED_MSG_ID
            # Hijack: seed an additional row with delivery_status='read'
            now_iso = datetime.now(timezone.utc).isoformat()
            mongo_db.whatsapp_message_logs.insert_one({
                "id": "TEST_filter_read_id",
                "operator_id": None, "template_name": "TEST",
                "recipient_phone": "917777777777", "status": "sent",
                "delivery_status": "read", "message_id": msg_id,
                "wa_id": "917777777777", "error_message": "",
                "error_code": None, "error_title": None,
                "delivered_at": now_iso, "read_at": now_iso, "failed_at": None,
                "events": [], "invoice_id": None, "invoice_number": "",
                "trigger": "manual_test", "created_at": now_iso,
            })

            r = requests.get(
                f"{BASE_URL}/api/admin/whatsapp-message-logs",
                params={"delivery_status": "read"},
                headers=admin_headers, timeout=15,
            )
            assert r.status_code == 200, r.text
            data = r.json()
            rows = data if isinstance(data, list) else (data.get("logs") or data.get("items") or [])
            for row in rows:
                assert row.get("delivery_status") == "read"
            assert any(r.get("message_id") == msg_id for r in rows), \
                "Seeded read row not returned by delivery_status=read filter"
        finally:
            mongo_db.whatsapp_message_logs.delete_many({"message_id": msg_id})
