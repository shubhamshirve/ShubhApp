"""
E2E HTTP-level tests for invoice -> subscriber.plans sync (Bug #1) and
bulk-notification WhatsApp logging (Bug #2).

Backend under test: REACT_APP_BACKEND_URL (runtime DB = saas_db via DB_NAME env var).
Seeds a TEST_ operator + user + wallet + subscriber + plans directly in mongo,
executes HTTP calls as the TEST operator, and verifies DB state.

Covers:
  * Bug 1a: POST invoice extends existing plan's plan_expiry_date FORWARD.
  * Bug 1b: POST invoice with earlier service_end_date does NOT move expiry back.
  * Bug 1c: POST invoice with NEW plan_id adds entry to subscriber.plans[].
  * Bug 1d: PUT invoice resyncs subscriber.plans (same hybrid rule).
  * Bug 1e: Custom line items (is_custom=true, plan_id=null) — NOT supported
            by current server-side validation (blocked at _build_invoice_payload);
            verified via direct helper call only.
  * Regression: mark-paid via PUT /invoices/{id}/status still works, does NOT
            re-sync (no double-sync).
  * Bug 2:  /api/operator/bulk-notification endpoint enqueues a job;
            _run_bulk_notification (invoked directly with monkey-patched
            WhatsAppService) captures message_id and calls log_whatsapp_message
            with trigger='bulk_notification'.
"""
import os
import sys
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

# Runtime DB is set via DB_NAME env var (defaults to saas_db).  Override before importing
# backend modules so direct DB access (via motor) targets the same DB.
os.environ.setdefault("DB_NAME", "saas_db")

# Make /app/backend importable so we can reuse password hashing + the helper.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")  # MONGO_URL
# Reassert default after dotenv loaded (env var takes priority if already set)
os.environ.setdefault("DB_NAME", "saas_db")

from utils import hash_password  # noqa: E402
from database import db  # noqa: E402
from routers.operator import _sync_subscriber_plans_from_invoice  # noqa: E402

FRONTEND_ENV = Path("/app/frontend/.env")
BASE_URL = None
for line in FRONTEND_ENV.read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL="):
        BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not found"

# ----- Unique identifiers for this run -----
RUN = uuid.uuid4().hex[:8]
OP_ID = f"TEST_op_{RUN}"
USER_ID = f"TEST_user_{RUN}"
SUB_ID = f"TEST_sub_{RUN}"
PLAN_A = f"TEST_plan_A_{RUN}"
PLAN_B = f"TEST_plan_B_{RUN}"
EMAIL = f"test_{RUN}@example.com"
PASSWORD = "TestPass123!"


# ----- Test seeding / cleanup -----
async def _seed():
    now = datetime.now(timezone.utc).isoformat()

    # Operator (no WhatsApp addon to avoid auto-send path)
    await db.operators.insert_one({
        "id": OP_ID,
        "business_name": "TEST Sync Co",
        "business_whatsapp_number": "+911111111111",
        "owner_email": EMAIL,
        "status": "active",
        "active_addons": [],  # no whatsapp_notifications
        "saas_plan_id": None,
        "created_at": now,
        "deleted_at": None,
    })

    # User (role=operator)
    await db.users.insert_one({
        "id": USER_ID,
        "email": EMAIL,
        "password": hash_password(PASSWORD),
        "name": "TEST Sync Owner",
        "phone": "9111111111",
        "role": "operator",
        "operator_id": OP_ID,
        "status": "active",
        "created_at": now,
        "deleted_at": None,
    })

    # Wallet with Rs. 10000 (more than enough for ≥Rs.50 gate + per-invoice deductions)
    await db.operator_wallets.insert_one({
        "operator_id": OP_ID,
        "balance": 10000.0,
        "created_at": now,
        "updated_at": now,
    })

    # Plans
    await db.operator_plans.insert_many([
        {"id": PLAN_A, "operator_id": OP_ID, "name": "TEST Plan A",
         "validity": "monthly", "price": 100.0, "deleted_at": None,
         "created_at": now},
        {"id": PLAN_B, "operator_id": OP_ID, "name": "TEST Plan B",
         "validity": "monthly", "price": 200.0, "deleted_at": None,
         "created_at": now},
    ])

    # Subscriber with PLAN_A already attached, expiry = 2026-05-25
    await db.subscribers.insert_one({
        "id": SUB_ID, "operator_id": OP_ID,
        "name": "TEST Subscriber", "whatsapp_number": "+919999999999",
        "email": f"sub_{RUN}@example.com",
        "address": "TEST address",
        "plans": [{
            "plan_id": PLAN_A, "plan_name": "TEST Plan A",
            "selected_validity": "monthly",
            "plan_start_date": "2026-04-25",
            "plan_expiry_date": "2026-05-25",
            "status": "active", "discount": 0,
        }],
        "created_at": now, "deleted_at": None,
    })


async def _cleanup():
    await db.operators.delete_many({"id": OP_ID})
    await db.users.delete_many({"id": USER_ID})
    await db.operator_wallets.delete_many({"operator_id": OP_ID})
    await db.operator_plans.delete_many({"operator_id": OP_ID})
    await db.subscribers.delete_many({"operator_id": OP_ID})
    await db.invoices.delete_many({"operator_id": OP_ID})
    await db.whatsapp_message_logs.delete_many({"operator_id": OP_ID})
    await db.background_jobs.delete_many({"operator_id": OP_ID})


# Single persistent event loop for all async DB ops so motor client stays bound.
_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)


def _run(coro):
    return _LOOP.run_until_complete(coro)


@pytest.fixture(scope="module", autouse=True)
def seed_data():
    _run(_cleanup())
    _run(_seed())
    yield
    _run(_cleanup())


@pytest.fixture(scope="module")
def token():
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=15,
    )
    assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def client(token):
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    return s


# ----- Helpers -----
def _iso(d: datetime) -> str:
    return d.replace(tzinfo=timezone.utc).isoformat() if d.tzinfo is None else d.isoformat()


def _line_item(plan_id, start: datetime, end: datetime, is_custom=False):
    return {
        "plan_id": plan_id,
        "plan_name": "",          # server refetches for plan-based items
        "selected_validity": "monthly",
        "is_custom": is_custom,
        "base_amount": 100.0,
        "discount": 0,
        "tax_amount": 0,
        "final_amount": 100.0,
        "service_start_date": _iso(start),
        "service_end_date": _iso(end),
        "description": "TEST custom" if is_custom else None,
    }


async def _get_sub_plans():
    sub = await db.subscribers.find_one({"id": SUB_ID}, {"_id": 0})
    return {p["plan_id"]: p for p in (sub.get("plans") or [])}


# =====================================================================
# Bug 1a – POST invoice EXTENDS existing plan expiry forward.
# =====================================================================
def test_1a_post_invoice_extends_expiry_forward(client):
    # Pre-state: PLAN_A expiry = 2026-05-25
    new_end = datetime(2026, 6, 5)  # 10 days later
    payload = {
        "subscriber_id": SUB_ID,
        "line_items": [_line_item(PLAN_A, datetime(2026, 5, 26), new_end)],
        "due_date": _iso(datetime(2026, 6, 10)),
    }
    r = client.post(f"{BASE_URL}/api/operator/invoices", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["subscriber_id"] == SUB_ID

    plans = _run(_get_sub_plans())
    assert PLAN_A in plans, plans
    assert plans[PLAN_A]["plan_expiry_date"] == "2026-06-05", plans[PLAN_A]
    # start should have advanced too since line item start (2026-05-26) > old (2026-04-25)
    assert plans[PLAN_A]["plan_start_date"] == "2026-05-26"


# =====================================================================
# Bug 1b – POST invoice with EARLIER service_end_date does NOT move expiry back.
# =====================================================================
def test_1b_post_invoice_earlier_does_not_rewind(client):
    # Current expiry after 1a = 2026-06-05
    payload = {
        "subscriber_id": SUB_ID,
        "line_items": [_line_item(PLAN_A, datetime(2026, 3, 1), datetime(2026, 3, 31))],
        "due_date": _iso(datetime(2026, 4, 10)),
    }
    r = client.post(f"{BASE_URL}/api/operator/invoices", json=payload, timeout=20)
    assert r.status_code == 200, r.text

    plans = _run(_get_sub_plans())
    # Unchanged: expiry stays at 2026-06-05
    assert plans[PLAN_A]["plan_expiry_date"] == "2026-06-05", plans[PLAN_A]
    # And start stays at 2026-05-26 (we do NOT rewind)
    assert plans[PLAN_A]["plan_start_date"] == "2026-05-26"


# =====================================================================
# Bug 1c – POST invoice with a NEW plan_id adds a new entry to subscriber.plans[].
# =====================================================================
def test_1c_post_invoice_new_plan_added(client):
    payload = {
        "subscriber_id": SUB_ID,
        "line_items": [_line_item(PLAN_B, datetime(2026, 7, 1), datetime(2026, 7, 31))],
        "due_date": _iso(datetime(2026, 8, 5)),
    }
    r = client.post(f"{BASE_URL}/api/operator/invoices", json=payload, timeout=20)
    assert r.status_code == 200, r.text

    plans = _run(_get_sub_plans())
    assert PLAN_B in plans, plans
    assert plans[PLAN_B]["plan_expiry_date"] == "2026-07-31"
    assert plans[PLAN_B]["plan_start_date"] == "2026-07-01"
    assert plans[PLAN_B]["status"] == "active"
    # A still exists untouched
    assert plans[PLAN_A]["plan_expiry_date"] == "2026-06-05"


# =====================================================================
# Bug 1d – PUT /invoices/{id} re-syncs subscriber.plans.
# =====================================================================
def test_1d_put_invoice_resyncs_plans(client):
    # Create a pending invoice first, then edit it to push PLAN_A expiry further.
    create_payload = {
        "subscriber_id": SUB_ID,
        "line_items": [_line_item(PLAN_A, datetime(2026, 6, 6), datetime(2026, 6, 10))],
        "due_date": _iso(datetime(2026, 6, 20)),
    }
    c = client.post(f"{BASE_URL}/api/operator/invoices", json=create_payload, timeout=20)
    assert c.status_code == 200, c.text
    inv_id = c.json()["id"]

    # After create: expiry should now be 2026-06-10 (forward from 06-05)
    plans = _run(_get_sub_plans())
    assert plans[PLAN_A]["plan_expiry_date"] == "2026-06-10"

    # Update: push expiry to 2026-06-25
    update_payload = {
        "subscriber_id": SUB_ID,
        "line_items": [_line_item(PLAN_A, datetime(2026, 6, 6), datetime(2026, 6, 25))],
        "due_date": _iso(datetime(2026, 6, 30)),
    }
    u = client.put(f"{BASE_URL}/api/operator/invoices/{inv_id}", json=update_payload, timeout=20)
    assert u.status_code == 200, u.text

    plans = _run(_get_sub_plans())
    assert plans[PLAN_A]["plan_expiry_date"] == "2026-06-25", plans[PLAN_A]


# =====================================================================
# Bug 1e – Custom line items skipped (direct helper check; POST path is gated by
# server-side validation that requires plan_id for all line items).
# =====================================================================
def test_1e_custom_line_items_skipped_via_helper():
    # Snapshot plans
    plans_before = _run(_get_sub_plans())

    custom_item = {
        "plan_id": None,
        "is_custom": True,
        "service_start_date": datetime(2026, 9, 1),
        "service_end_date": datetime(2026, 9, 30),
        "description": "TEST custom",
        "selected_validity": None,
        "base_amount": 50, "discount": 0, "tax_amount": 0, "final_amount": 50,
    }
    _run(
        _sync_subscriber_plans_from_invoice(SUB_ID, [custom_item])
    )
    plans_after = _run(_get_sub_plans())
    assert plans_before == plans_after, (plans_before, plans_after)


# =====================================================================
# Regression – mark-paid still works and does NOT re-sync plans.
# =====================================================================
def test_regression_mark_paid_no_double_sync(client):
    # Create fresh invoice with end_date 2026-06-26 (forward by 1 day)
    payload = {
        "subscriber_id": SUB_ID,
        "line_items": [_line_item(PLAN_A, datetime(2026, 6, 6), datetime(2026, 6, 26))],
        "due_date": _iso(datetime(2026, 7, 1)),
    }
    c = client.post(f"{BASE_URL}/api/operator/invoices", json=payload, timeout=20)
    assert c.status_code == 200, c.text
    inv_id = c.json()["id"]

    plans_before_paid = _run(_get_sub_plans())
    assert plans_before_paid[PLAN_A]["plan_expiry_date"] == "2026-06-26"

    # Mark as paid
    r = client.put(
        f"{BASE_URL}/api/operator/invoices/{inv_id}/status",
        json={"status": "paid", "payment_mode": "cash",
              "payment_date": _iso(datetime(2026, 6, 27))},
        timeout=20,
    )
    assert r.status_code == 200, r.text

    plans_after_paid = _run(_get_sub_plans())
    # Expiry must not change from the paid flow itself
    assert plans_after_paid[PLAN_A]["plan_expiry_date"] == "2026-06-26", plans_after_paid[PLAN_A]


# =====================================================================
# Bug 2 – Bulk notification enqueue + run_bulk_notification logs message_id.
# =====================================================================
def test_bug2_bulk_notification_http_enqueues(client):
    # There is at least one pending invoice for SUB_ID from earlier create calls
    # (several were created and most are still pending).
    payload = {"subscriber_ids": [SUB_ID], "message_template": "invoice_notification"}
    r = client.post(f"{BASE_URL}/api/operator/bulk-notification", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "job_id" in body and body["job_id"]


def test_bug2_run_bulk_notification_logs_message_id(monkeypatch):
    """Directly invoke _run_bulk_notification with monkey-patched WhatsAppService to
    verify the new code path (wa_result capture + log_whatsapp_message call)."""
    from services import job_queue_service as jqs
    from services import whatsapp_service as wsvc

    FAKE_MSG_ID = f"wamid.TEST_BULK_{RUN}"
    FAKE_WA_ID = "919999999999"

    # Pre-seed a platform_whatsapp config so _run_bulk_notification doesn't raise.
    async def _setup_cfg():
        await db.global_settings.update_one(
            {"type": "platform_whatsapp"},
            {"$set": {
                "type": "platform_whatsapp",
                "phone_number_id": "TEST_pnid",
                "access_token": "TEST_token",
                "business_account_id": "TEST_baid",
                "webhook_verify_token": "TEST_vt",
            }},
            upsert=True,
        )
        # Also ensure there's at least one pending invoice for SUB_ID
        inv = await db.invoices.find_one(
            {"operator_id": OP_ID, "subscriber_id": SUB_ID, "status": "pending"}
        )
        return inv is not None

    had_pending = _run(_setup_cfg())
    assert had_pending, "expected at least one pending invoice from prior tests"

    # Monkey-patch WhatsAppService.send_template_message + send_invoice_notification
    async def _fake_send_template_message(self, **kwargs):
        return {
            "messages": [{"id": FAKE_MSG_ID}],
            "contacts": [{"wa_id": FAKE_WA_ID}],
        }

    async def _fake_send_invoice_notification(self, **kwargs):
        return {
            "messages": [{"id": FAKE_MSG_ID}],
            "contacts": [{"wa_id": FAKE_WA_ID}],
        }

    monkeypatch.setattr(wsvc.WhatsAppService, "send_template_message",
                        _fake_send_template_message, raising=True)
    monkeypatch.setattr(wsvc.WhatsAppService, "send_invoice_notification",
                        _fake_send_invoice_notification, raising=True)

    async def _invoke_job():
        job = {
            "operator_id": OP_ID,
            "payload": {"subscriber_ids": [SUB_ID],
                        "message_template": "invoice_notification"},
        }
        return await jqs.JobQueueService._run_bulk_notification(job)

    result = _run(_invoke_job())
    assert result.get("sent", 0) >= 1, result

    # Verify whatsapp_message_logs got a row with trigger='bulk_notification'
    async def _find_logs():
        return await db.whatsapp_message_logs.find(
            {"operator_id": OP_ID, "trigger": "bulk_notification"},
            {"_id": 0},
        ).to_list(10)

    logs = _run(_find_logs())
    assert logs, "expected at least 1 bulk_notification log"
    assert any(lg.get("message_id") == FAKE_MSG_ID for lg in logs), \
        f"message_id {FAKE_MSG_ID} not found in logs={logs}"

    # Cleanup: remove the seeded platform_whatsapp config so other tests/envs stay clean
    async def _teardown_cfg():
        await db.global_settings.delete_one({"type": "platform_whatsapp",
                                             "access_token": "TEST_token"})
    _run(_teardown_cfg())
