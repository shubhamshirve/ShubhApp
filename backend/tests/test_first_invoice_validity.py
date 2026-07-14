"""
Test suite for first invoice generation with selected_validity (multi-tenure pricing).

Bug fixes verified:
1. routers/operator.py: validity_groups now keyed on ep.selected_validity or op_plan.validity.
2. services/cron_service.py: _create_first_invoice scales price by VALIDITY_MONTHS based on
   effective_validity (selected_validity > plan.validity).

Scenarios:
- monthly-priced plan + selected_validity=yearly  -> base_amount = price * 12
- monthly-priced plan + selected_validity=quarterly  -> base_amount = price * 3
- monthly-priced plan + selected_validity=half_yearly -> base_amount = price * 6
- monthly-priced plan + selected_validity=monthly (default) -> base_amount = price
- Mixed validities on a single subscriber -> separate invoices per effective tenure
"""
import os
import time
import uuid
import pytest
import requests
from pathlib import Path


def _load_frontend_env():
    env_path = Path("/app/frontend/.env")
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


_load_frontend_env()
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
OP_EMAIL = "operator@test.com"
OP_PASSWORD = "test123"

PLAN_PRICE = 500.0
EXPECTED = {
    "monthly": PLAN_PRICE * 1,
    "quarterly": PLAN_PRICE * 3,
    "half_yearly": PLAN_PRICE * 6,
    "yearly": PLAN_PRICE * 12,
}


# ────────────────────────── fixtures ──────────────────────────

@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth_token(api_client):
    r = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OP_EMAIL, "password": OP_PASSWORD},
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"Operator login failed: {r.status_code} {r.text}")
    data = r.json()
    return data["access_token"]


@pytest.fixture(scope="module")
def auth_client(api_client, auth_token):
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


@pytest.fixture(scope="module")
def test_plan(auth_client):
    """Create a plan price=500 monthly, supports all validities."""
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "name": f"TEST_MultiTenure_Plan_{suffix}",
        "price": PLAN_PRICE,
        "validity": "monthly",
        "available_validities": ["monthly", "quarterly", "half_yearly", "yearly"],
        "tax_percentage": 0,
        "tax_type": "none",
        "description": "Test plan for multi-tenure invoice tests",
    }
    r = auth_client.post(f"{BASE_URL}/api/operator/plans", json=payload, timeout=15)
    assert r.status_code == 200, f"Plan create failed: {r.status_code} {r.text}"
    plan = r.json()
    assert plan["price"] == PLAN_PRICE
    assert plan["validity"] == "monthly"
    yield plan
    # teardown
    try:
        auth_client.delete(f"{BASE_URL}/api/operator/plans/{plan['id']}", timeout=10)
    except Exception:
        pass


# helper to create subscriber & fetch their invoices
def _create_subscriber_with_validity(client, plan_id, selected_validity, marker):
    payload = {
        "name": f"TEST_FirstInv_{selected_validity}_{marker}",
        "whatsapp_number": f"+91{int(time.time()*1000) % 10000000000:010d}",
        "email": f"test_{selected_validity}_{marker}@example.com",
        "address": "Test address",
        "plans": [
            {
                "plan_id": plan_id,
                "selected_validity": selected_validity,
                "plan_start_date": "2026-01-01",
                "discount": 0,
                "status": "active",
            }
        ],
        "generate_first_invoice": True,
    }
    r = client.post(f"{BASE_URL}/api/operator/subscribers", json=payload, timeout=20)
    assert r.status_code == 200, f"Subscriber create failed [{selected_validity}]: {r.status_code} {r.text}"
    return r.json()


def _get_invoices_for_subscriber(client, subscriber_id):
    r = client.get(f"{BASE_URL}/api/operator/invoices?subscriber_id={subscriber_id}", timeout=15)
    assert r.status_code == 200, f"Invoice list failed: {r.status_code} {r.text}"
    return r.json()


def _cleanup_subscriber(client, subscriber_id):
    """Operator users can only suspend; for full test cleanup we delete directly
    from MongoDB (test data only, prefixed TEST_)."""
    try:
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        # Use DB_NAME env var (defaults to saas_db)
        db_name = os.environ.get("DB_NAME", "saas_db")
        mc = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
        mc[db_name].invoices.delete_many({"subscriber_id": subscriber_id})
        mc[db_name].subscribers.delete_one({"id": subscriber_id})
        mc.close()
    except Exception:
        # fall back to API suspend
        try:
            client.post(f"{BASE_URL}/api/operator/subscribers/{subscriber_id}/suspend", timeout=10)
        except Exception:
            pass


# ────────────────────────── tests ──────────────────────────

class TestFirstInvoiceValidity:
    """First invoice is scaled according to selected_validity."""

    @pytest.mark.parametrize("validity", ["monthly", "quarterly", "half_yearly", "yearly"])
    def test_first_invoice_base_amount_per_validity(self, auth_client, test_plan, validity):
        marker = uuid.uuid4().hex[:6]
        subscriber = _create_subscriber_with_validity(
            auth_client, test_plan["id"], validity, marker
        )
        sub_id = subscriber["id"]
        try:
            # small wait in case invoice insert is async-ish
            time.sleep(1.0)
            invoices = _get_invoices_for_subscriber(auth_client, sub_id)
            assert len(invoices) >= 1, f"No invoice generated for {validity}"

            # find the first invoice — InvoiceResponse model strips is_first_invoice
            # (extra='ignore'), so just take the most recent invoice (only 1 for new subscriber)
            assert len(invoices) >= 1, f"No invoice generated for {validity}"
            inv = invoices[0]

            assert inv["line_items"], "Invoice has no line items"
            line = inv["line_items"][0]

            expected_base = EXPECTED[validity]
            assert line.get("selected_validity") == validity, (
                f"line.selected_validity expected '{validity}' got '{line.get('selected_validity')}'"
            )
            assert float(line["base_amount"]) == pytest.approx(expected_base), (
                f"line.base_amount expected {expected_base} got {line['base_amount']} "
                f"for validity={validity}"
            )

            # Aggregates must match the line item (single-line invoice, no discount/tax)
            assert float(inv["base_amount"]) == pytest.approx(expected_base), (
                f"invoice.base_amount expected {expected_base} got {inv['base_amount']}"
            )
            assert float(inv["final_amount"]) == pytest.approx(expected_base), (
                f"invoice.final_amount expected {expected_base} got {inv['final_amount']}"
            )

            # Service window: start = plan_start_date (2026-01-01),
            # end = plan_expiry_date computed by calendar months (no strict equality enforced
            # because the operator route computes plan_expiry_date for us; but ensure it's a
            # valid future date string from the same start)
            assert line["service_start_date"].startswith("2026-01-01"), (
                f"service_start_date should equal plan_start_date 2026-01-01, got {line['service_start_date']}"
            )
            assert line["service_end_date"] > line["service_start_date"], (
                "service_end_date must be after service_start_date"
            )
        finally:
            _cleanup_subscriber(auth_client, sub_id)

    def test_mixed_validities_produce_separate_invoices(self, auth_client, test_plan):
        """A subscriber with two plan-rows of different effective validity should
        get one invoice per tenure group."""
        marker = uuid.uuid4().hex[:6]
        payload = {
            "name": f"TEST_FirstInv_Mixed_{marker}",
            "whatsapp_number": f"+91{int(time.time()*1000) % 10000000000:010d}",
            "email": f"test_mixed_{marker}@example.com",
            "plans": [
                {
                    "plan_id": test_plan["id"],
                    "selected_validity": "monthly",
                    "plan_start_date": "2026-01-01",
                    "discount": 0,
                    "status": "active",
                },
                {
                    "plan_id": test_plan["id"],
                    "selected_validity": "yearly",
                    "plan_start_date": "2026-01-01",
                    "discount": 0,
                    "status": "active",
                },
            ],
            "generate_first_invoice": True,
        }
        r = auth_client.post(f"{BASE_URL}/api/operator/subscribers", json=payload, timeout=20)
        assert r.status_code == 200, f"Mixed-validity subscriber create failed: {r.status_code} {r.text}"
        sub = r.json()
        sub_id = sub["id"]
        try:
            time.sleep(1.0)
            invoices = _get_invoices_for_subscriber(auth_client, sub_id)

            # Note: InvoiceResponse model strips is_first_invoice (extra='ignore').
            # All invoices for a freshly-created subscriber are first invoices,
            # so we use the full list.
            first_invs = invoices
            assert len(first_invs) == 2, (
                f"Expected 2 first invoices (one per tenure group), got {len(first_invs)}: "
                f"{[(i.get('invoice_number'), i.get('base_amount')) for i in first_invs]}"
            )

            tenure_to_amount = {}
            for inv in first_invs:
                line = inv["line_items"][0]
                tenure_to_amount[line["selected_validity"]] = float(inv["base_amount"])

            assert tenure_to_amount.get("monthly") == pytest.approx(EXPECTED["monthly"]), (
                f"monthly invoice amount mismatch: {tenure_to_amount}"
            )
            assert tenure_to_amount.get("yearly") == pytest.approx(EXPECTED["yearly"]), (
                f"yearly invoice amount mismatch: {tenure_to_amount}"
            )
        finally:
            _cleanup_subscriber(auth_client, sub_id)
