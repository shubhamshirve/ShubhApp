"""
Tests for Billing Expiry Refactor (billing_date -> plan_expiry_date)

Coverage:
- Create subscriber with generate_first_invoice=true (invoice inserted immediately)
- Create subscriber with generate_first_invoice=false (no invoice)
- Default plan_start_date = today; plan_expiry_date = start + validity days
- mark-paid extends plan_expiry_date by validity days (base = max(old_expiry, paid_date))
- /subscribers/migrate-to-expiry-dates backfills legacy subscribers
- /subscribers/sample-csv includes plan_start_date_1..5 columns
- Admin cron /cron/generate-invoices only picks subscribers whose plan_expiry_date
  is within notice window
"""
import os
import csv
import io
import pytest
import requests
from datetime import datetime, timedelta, date

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    pytest.skip("REACT_APP_BACKEND_URL missing", allow_module_level=True)

OPERATOR_EMAIL = "operator@test.com"
OPERATOR_PASSWORD = "test123"
ADMIN_EMAIL = "admin@saas.com"  # admin@test.com not present; admin@saas.com is seeded admin
ADMIN_PASSWORD = "admin123"

VALIDITY_DAYS = {"monthly": 30, "quarterly": 90, "half_yearly": 180, "yearly": 365}


# ───── Fixtures ─────────────────────────────────────────────────────────────

def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Login failed for {email}: {r.status_code} {r.text[:200]}")
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def op_client():
    token = _login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json",
                      "Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def admin_client():
    token = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json",
                      "Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def funded_operator(admin_client, op_client):
    """Ensure the test operator has wallet balance >= ₹100 before cron tests."""
    # Get operator_id via /api/operator/profile (current user)
    r = op_client.get(f"{BASE_URL}/api/operator/profile")
    if r.status_code != 200:
        # Try alternative endpoint
        r = op_client.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200, f"Failed to fetch operator profile: {r.text}"
    me = r.json()
    operator_id = me.get("operator_id") or me.get("id")
    assert operator_id, f"Could not find operator_id in {me}"

    # Check wallet balance via admin endpoint
    wres = admin_client.get(f"{BASE_URL}/api/admin/wallets?limit=500")
    current = 0
    if wres.status_code == 200:
        body = wres.json()
        wallets = body.get("wallets", body) if isinstance(body, dict) else body
        target = next((w for w in wallets if isinstance(w, dict) and w.get("operator_id") == operator_id), None)
        current = (target or {}).get("balance", 0)
    if current < 100:
        cr = admin_client.post(
            f"{BASE_URL}/api/admin/wallets/{operator_id}/credit",
            json={"amount": 500, "reason": "TEST_fund_for_cron_invoice_generation"}
        )
        assert cr.status_code in (200, 201), f"Credit failed: {cr.status_code} {cr.text}"
    return operator_id


@pytest.fixture(scope="module")
def monthly_plan_id(op_client):
    """Ensure an operator monthly plan exists; return its id."""
    # Reuse existing or create
    r = op_client.get(f"{BASE_URL}/api/operator/plans")
    assert r.status_code == 200
    for p in r.json():
        if p.get("validity") == "monthly" and p.get("status") == "active":
            return p["id"]
    payload = {"name": "TEST_Expiry_Monthly", "price": 500,
               "validity": "monthly", "tax_percentage": 0,
               "tax_type": "exclusive", "description": "Test plan"}
    r = op_client.post(f"{BASE_URL}/api/operator/plans", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]


# Track created entities for cleanup
_created_subscribers = []


def _cleanup(op_client):
    for sid in _created_subscribers:
        try:
            op_client.delete(f"{BASE_URL}/api/operator/subscribers/{sid}")
        except Exception:
            pass


@pytest.fixture(scope="module", autouse=True)
def cleanup_after(op_client):
    yield
    _cleanup(op_client)


# ───── Helpers ───────────────────────────────────────────────────────────────

def _create_subscriber(op_client, plan_id, *, generate_first_invoice=False,
                       plan_start_date=None, discount=0, name_suffix=""):
    plan_obj = {"plan_id": plan_id, "discount": discount}
    if plan_start_date:
        plan_obj["plan_start_date"] = plan_start_date
    payload = {
        "name": f"TEST_Exp_{name_suffix}_{datetime.utcnow().timestamp():.0f}",
        "whatsapp_number": "9" + str(int(datetime.utcnow().timestamp()))[-9:],
        "email": "",
        "address": "Test Addr",
        "plans": [plan_obj],
        "generate_first_invoice": generate_first_invoice,
    }
    r = op_client.post(f"{BASE_URL}/api/operator/subscribers", json=payload)
    assert r.status_code == 200, f"Create subscriber failed: {r.status_code} {r.text}"
    data = r.json()
    _created_subscribers.append(data["id"])
    return data


# ───── Tests ────────────────────────────────────────────────────────────────

class TestSubscriberCreateExpiry:
    """POST /api/operator/subscribers with new expiry-date model"""

    def test_defaults_start_today_expiry_plus_validity(self, op_client, monthly_plan_id):
        sub = _create_subscriber(op_client, monthly_plan_id, name_suffix="defaults")
        assert sub["plans"] and len(sub["plans"]) == 1
        plan = sub["plans"][0]
        assert plan.get("plan_start_date"), "plan_start_date not set"
        assert plan.get("plan_expiry_date"), "plan_expiry_date not set"
        start = datetime.strptime(plan["plan_start_date"], "%Y-%m-%d").date()
        expiry = datetime.strptime(plan["plan_expiry_date"], "%Y-%m-%d").date()
        # start should equal today (UTC) +-1 day
        today = datetime.utcnow().date()
        assert abs((start - today).days) <= 1, f"start {start} not today {today}"
        assert (expiry - start).days == 30, "monthly validity should be 30 days"

    def test_explicit_start_date_computes_expiry(self, op_client, monthly_plan_id):
        explicit_start = "2026-02-15"
        sub = _create_subscriber(op_client, monthly_plan_id,
                                 plan_start_date=explicit_start,
                                 name_suffix="explicit")
        plan = sub["plans"][0]
        assert plan["plan_start_date"] == explicit_start
        assert plan["plan_expiry_date"] == "2026-03-17"  # 15 Feb + 30d

    def test_generate_first_invoice_true_creates_invoice(self, op_client, monthly_plan_id):
        sub = _create_subscriber(op_client, monthly_plan_id,
                                 generate_first_invoice=True,
                                 name_suffix="genfirst_true")
        # Poll invoices for this subscriber
        r = op_client.get(f"{BASE_URL}/api/operator/invoices?subscriber_id={sub['id']}")
        assert r.status_code == 200
        invoices = r.json()
        assert len(invoices) >= 1, "Expected at least 1 invoice generated"
        inv = invoices[0]
        plan = sub["plans"][0]
        # service_start/end may be on top-level or inside line_items
        service_start = inv.get("service_start_date") or (inv.get("line_items", [{}])[0].get("service_start_date", ""))
        service_end = inv.get("service_end_date") or (inv.get("line_items", [{}])[0].get("service_end_date", ""))
        assert service_start.startswith(plan["plan_start_date"]), \
            f"service_start {service_start} != {plan['plan_start_date']}"
        assert service_end.startswith(plan["plan_expiry_date"]), \
            f"service_end {service_end} != {plan['plan_expiry_date']}"
        # is_first_invoice flag if present
        if "is_first_invoice" in inv:
            assert inv["is_first_invoice"] is True

    def test_generate_first_invoice_false_creates_no_invoice(self, op_client, monthly_plan_id):
        sub = _create_subscriber(op_client, monthly_plan_id,
                                 generate_first_invoice=False,
                                 name_suffix="genfirst_false")
        r = op_client.get(f"{BASE_URL}/api/operator/invoices?subscriber_id={sub['id']}")
        assert r.status_code == 200
        invoices = r.json()
        assert len(invoices) == 0, f"Expected 0 invoices, got {len(invoices)}"


class TestMarkPaidExtendsExpiry:
    """POST /api/operator/invoices/{id}/mark-paid extends plan expiry"""

    def test_mark_paid_extends_expiry_by_validity(self, op_client, monthly_plan_id):
        # Create subscriber with first invoice
        sub = _create_subscriber(op_client, monthly_plan_id,
                                 generate_first_invoice=True,
                                 name_suffix="markpaid")
        invoices = op_client.get(
            f"{BASE_URL}/api/operator/invoices?subscriber_id={sub['id']}"
        ).json()
        assert invoices, "No invoice to mark paid"
        invoice_id = invoices[0]["id"]

        old_expiry_str = sub["plans"][0]["plan_expiry_date"]
        old_expiry = datetime.strptime(old_expiry_str, "%Y-%m-%d").date()

        # Mark paid via PUT /invoices/{id}/status
        r = op_client.put(
            f"{BASE_URL}/api/operator/invoices/{invoice_id}/status",
            json={"status": "paid", "payment_mode": "cash"}
        )
        assert r.status_code == 200, f"mark-paid failed: {r.status_code} {r.text}"

        # Re-fetch subscriber
        r2 = op_client.get(f"{BASE_URL}/api/operator/subscribers")
        assert r2.status_code == 200
        fetched = next((s for s in r2.json() if s["id"] == sub["id"]), None)
        assert fetched is not None
        new_expiry_str = fetched["plans"][0]["plan_expiry_date"]
        new_expiry = datetime.strptime(new_expiry_str, "%Y-%m-%d").date()

        paid_date = datetime.utcnow().date()
        base_date = old_expiry if old_expiry >= paid_date else paid_date
        expected = base_date + timedelta(days=30)
        assert new_expiry == expected, \
            f"Expected new expiry {expected}, got {new_expiry} (old {old_expiry}, paid {paid_date})"


class TestMigrationEndpoint:
    """POST /api/operator/subscribers/migrate-to-expiry-dates"""

    def test_migrate_endpoint_returns_counts(self, op_client):
        r = op_client.post(f"{BASE_URL}/api/operator/subscribers/migrate-to-expiry-dates")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "plans_migrated" in data
        assert "plans_skipped_already_migrated" in data
        assert "message" in data
        assert isinstance(data["plans_migrated"], int)
        assert isinstance(data["plans_skipped_already_migrated"], int)

    def test_migrate_idempotent_second_call_migrates_zero(self, op_client):
        # After first call, a second call should migrate 0 and skip all
        r1 = op_client.post(f"{BASE_URL}/api/operator/subscribers/migrate-to-expiry-dates")
        assert r1.status_code == 200
        r2 = op_client.post(f"{BASE_URL}/api/operator/subscribers/migrate-to-expiry-dates")
        assert r2.status_code == 200
        assert r2.json()["plans_migrated"] == 0, \
            "Second migration call should migrate 0 plans (all already migrated)"


class TestSampleCSV:
    """GET /api/operator/subscribers/sample-csv"""

    def test_sample_csv_has_plan_start_date_headers(self, op_client):
        r = op_client.get(f"{BASE_URL}/api/operator/subscribers/sample-csv")
        assert r.status_code == 200
        content = r.text
        reader = csv.reader(io.StringIO(content))
        headers = next(reader)
        # Must include plan_start_date_1..5, must NOT include billing_date_1..5
        for i in range(1, 6):
            assert f"plan_start_date_{i}" in headers, \
                f"Missing plan_start_date_{i} in headers: {headers}"
            assert f"billing_date_{i}" not in headers, \
                f"Legacy billing_date_{i} still present in headers: {headers}"


class TestCronGenerateUpcomingInvoices:
    """Admin cron generate-invoices uses plan_expiry_date window, not hardcoded 28d"""

    def test_cron_runs_without_error(self, admin_client, funded_operator):
        r = admin_client.post(f"{BASE_URL}/api/admin/cron/generate-invoices")
        assert r.status_code == 200, r.text
        data = r.json()
        # Result shape should contain some counts
        assert isinstance(data, dict)

    def test_cron_skips_far_future_expiry(self, op_client, admin_client, monthly_plan_id, funded_operator):
        # Create subscriber with plan_start 90 days in future => expiry 120d future => far out of notice window
        future_start = (datetime.utcnow().date() + timedelta(days=90)).strftime("%Y-%m-%d")
        sub = _create_subscriber(op_client, monthly_plan_id,
                                 plan_start_date=future_start,
                                 name_suffix="farfuture")
        # Trigger cron
        r = admin_client.post(f"{BASE_URL}/api/admin/cron/generate-invoices")
        assert r.status_code == 200
        # Verify no invoice was created for this subscriber
        inv_resp = op_client.get(
            f"{BASE_URL}/api/operator/invoices?subscriber_id={sub['id']}"
        )
        assert inv_resp.status_code == 200
        assert len(inv_resp.json()) == 0, \
            "Far-future subscriber should NOT have invoice generated by cron"

    def test_cron_creates_invoice_when_in_notice_window(self, op_client, admin_client, monthly_plan_id, funded_operator):
        # Create subscriber whose plan expires within next 3 days (notice window default).
        # Start = today - 28 days => expiry = today + 2 days (within default 3 day window)
        start = (datetime.utcnow().date() - timedelta(days=28)).strftime("%Y-%m-%d")
        sub = _create_subscriber(op_client, monthly_plan_id,
                                 plan_start_date=start,
                                 name_suffix="in_window")
        # Trigger cron
        r = admin_client.post(f"{BASE_URL}/api/admin/cron/generate-invoices")
        assert r.status_code == 200
        cron_data = r.json()
        print(f"CRON RESPONSE: {cron_data}")

        inv_resp = op_client.get(
            f"{BASE_URL}/api/operator/invoices?subscriber_id={sub['id']}"
        )
        assert inv_resp.status_code == 200
        invoices = inv_resp.json()
        print(f"Subscriber plan_expiry_date={sub['plans'][0]['plan_expiry_date']}, invoices={len(invoices)}")
        assert len(invoices) >= 1, (
            f"Cron did NOT create invoice for subscriber with expiry in 2 days. "
            f"Cron response: {cron_data}, subscriber_id={sub['id']}"
        )
        plan = sub["plans"][0]
        old_expiry = plan["plan_expiry_date"]
        inv = invoices[0]
        service_start = inv.get("service_start_date") or (inv.get("line_items", [{}])[0].get("service_start_date", ""))
        service_end = inv.get("service_end_date") or (inv.get("line_items", [{}])[0].get("service_end_date", ""))
        assert service_start.startswith(old_expiry), \
            f"service_start {service_start} != old_expiry {old_expiry}"
        expected_end = (datetime.strptime(old_expiry, "%Y-%m-%d").date()
                        + timedelta(days=30)).strftime("%Y-%m-%d")
        assert service_end.startswith(expected_end), \
            f"service_end {service_end} != expected {expected_end}"
