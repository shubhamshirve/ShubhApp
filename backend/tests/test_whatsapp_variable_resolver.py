import pytest
from datetime import datetime, timezone
from services.whatsapp_service import resolve_template_variables

def _make_invoice(**kwargs):
    base = {
        "invoice_number": "EBILL-ABC123",
        "final_amount": 599.0,
        "due_date": "2026-04-25T00:00:00+00:00",
        "payment_link": "https://rzp.io/pay/abc",
        "line_items": [
            {
                "plan_name": "Fiber 50Mbps",
                "service_start_date": "2026-04-01T00:00:00+00:00",
                "service_end_date": "2026-04-30T00:00:00+00:00",
            }
        ],
    }
    base.update(kwargs)
    return base

def _make_subscriber(**kwargs):
    base = {"name": "Ramesh Kumar"}
    base.update(kwargs)
    return base


def test_customer_name():
    result = resolve_template_variables(["customer_name"], _make_invoice(), _make_subscriber())
    assert result == ["Ramesh Kumar"]


def test_invoice_number():
    result = resolve_template_variables(["invoice_number"], _make_invoice(), _make_subscriber())
    assert result == ["EBILL-ABC123"]


def test_amount():
    result = resolve_template_variables(["amount"], _make_invoice(), _make_subscriber())
    assert result == ["₹599.00"]


def test_due_date():
    result = resolve_template_variables(["due_date"], _make_invoice(), _make_subscriber())
    assert result == ["25 Apr 2026"]


def test_plan_name_single():
    result = resolve_template_variables(["plan_name"], _make_invoice(), _make_subscriber())
    assert result == ["Fiber 50Mbps"]


def test_plan_name_multi():
    inv = _make_invoice(line_items=[
        {"plan_name": "Fiber 50Mbps", "service_start_date": "2026-04-01T00:00:00+00:00", "service_end_date": "2026-04-30T00:00:00+00:00"},
        {"plan_name": "OTT Bundle", "service_start_date": "2026-04-01T00:00:00+00:00", "service_end_date": "2026-04-30T00:00:00+00:00"},
    ])
    result = resolve_template_variables(["plan_name"], inv, _make_subscriber())
    assert result == ["Fiber 50Mbps, OTT Bundle"]


def test_tenure_single():
    result = resolve_template_variables(["tenure"], _make_invoice(), _make_subscriber())
    assert result == ["01 Apr 2026 – 30 Apr 2026"]


def test_tenure_multi_different_ranges():
    inv = _make_invoice(line_items=[
        {"plan_name": "Fiber", "service_start_date": "2026-04-01T00:00:00+00:00", "service_end_date": "2026-04-30T00:00:00+00:00"},
        {"plan_name": "OTT", "service_start_date": "2026-05-01T00:00:00+00:00", "service_end_date": "2026-05-31T00:00:00+00:00"},
    ])
    result = resolve_template_variables(["tenure"], inv, _make_subscriber())
    assert result == ["01 Apr 2026 – 30 Apr 2026, 01 May 2026 – 31 May 2026"]


def test_payment_link():
    result = resolve_template_variables(["payment_link"], _make_invoice(), _make_subscriber())
    assert result == ["https://rzp.io/pay/abc"]


def test_unknown_key_passthrough():
    result = resolve_template_variables(["my_custom_text"], _make_invoice(), _make_subscriber())
    assert result == ["my_custom_text"]


def test_empty_body_variables():
    result = resolve_template_variables([], _make_invoice(), _make_subscriber())
    assert result == []


def test_full_invoice_template_order():
    """Matches the example template: Dear {{1}}, plan {{2}}, tenure {{3}}, due {{4}}"""
    result = resolve_template_variables(
        ["customer_name", "plan_name", "tenure", "due_date"],
        _make_invoice(),
        _make_subscriber(),
    )
    assert result == [
        "Ramesh Kumar",
        "Fiber 50Mbps",
        "01 Apr 2026 – 30 Apr 2026",
        "25 Apr 2026",
    ]


def test_missing_due_date_returns_empty():
    inv = _make_invoice(due_date=None)
    result = resolve_template_variables(["due_date"], inv, _make_subscriber())
    assert result == [""]


def test_empty_line_items_plan_name():
    inv = _make_invoice(line_items=[])
    result = resolve_template_variables(["plan_name"], inv, _make_subscriber())
    assert result == [""]


def test_empty_line_items_tenure():
    inv = _make_invoice(line_items=[])
    result = resolve_template_variables(["tenure"], inv, _make_subscriber())
    assert result == [""]
