"""Tests for _sync_subscriber_plans_from_invoice (operator router).

Run as plain script to avoid pytest-asyncio dependency:
    python tests/test_invoice_plan_sync.py
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from routers.operator import _sync_subscriber_plans_from_invoice, _to_ymd  # noqa: E402
from database import db  # noqa: E402


async def _cleanup():
    await db.subscribers.delete_many({"id": {"$regex": "^test-sync-"}})
    await db.operator_plans.delete_many({"id": {"$regex": "^test-sync-"}})


def _line_item(plan_id, start, end, plan_name="Plan A", is_custom=False, selected_validity="monthly"):
    return {
        "plan_id": plan_id,
        "plan_name": plan_name,
        "selected_validity": selected_validity,
        "service_start_date": start,
        "service_end_date": end,
        "is_custom": is_custom,
        "base_amount": 100,
        "discount": 0,
        "tax_amount": 0,
        "final_amount": 100,
    }


async def test_new_plan_added_to_subscriber():
    await _cleanup()
    sub_id = "test-sync-sub-1"
    plan_id = "test-sync-plan-1"
    await db.operator_plans.insert_one({
        "id": plan_id, "name": "New Plan", "validity": "monthly",
        "deleted_at": None, "operator_id": "op-1",
    })
    await db.subscribers.insert_one({
        "id": sub_id, "operator_id": "op-1", "plans": [], "deleted_at": None,
        "name": "Test Sub", "whatsapp_number": "+919876543210",
    })

    line_items = [_line_item(plan_id, datetime(2026, 5, 1), datetime(2026, 5, 31), plan_name="New Plan")]
    await _sync_subscriber_plans_from_invoice(sub_id, line_items)

    sub = await db.subscribers.find_one({"id": sub_id}, {"_id": 0})
    assert len(sub["plans"]) == 1, f"expected 1 plan, got {len(sub['plans'])}"
    assert sub["plans"][0]["plan_id"] == plan_id
    assert sub["plans"][0]["plan_expiry_date"] == "2026-05-31"
    assert sub["plans"][0]["plan_start_date"] == "2026-05-01"
    assert sub["plans"][0]["status"] == "active"
    print("✓ test_new_plan_added_to_subscriber")


async def test_existing_plan_expiry_extended_forward():
    await _cleanup()
    sub_id = "test-sync-sub-2"
    plan_id = "test-sync-plan-2"
    await db.subscribers.insert_one({
        "id": sub_id, "operator_id": "op-1", "deleted_at": None,
        "name": "Test", "whatsapp_number": "+919876543210",
        "plans": [{
            "plan_id": plan_id, "plan_name": "X", "selected_validity": "monthly",
            "plan_start_date": "2026-04-25", "plan_expiry_date": "2026-05-25",
            "status": "active", "discount": 0,
        }],
    })

    line_items = [_line_item(plan_id, datetime(2026, 5, 26), datetime(2026, 5, 28))]
    await _sync_subscriber_plans_from_invoice(sub_id, line_items)

    sub = await db.subscribers.find_one({"id": sub_id}, {"_id": 0})
    assert len(sub["plans"]) == 1
    assert sub["plans"][0]["plan_expiry_date"] == "2026-05-28", sub["plans"][0]
    assert sub["plans"][0]["plan_start_date"] == "2026-05-26"
    print("✓ test_existing_plan_expiry_extended_forward")


async def test_existing_plan_unchanged_when_invoice_earlier():
    await _cleanup()
    sub_id = "test-sync-sub-3"
    plan_id = "test-sync-plan-3"
    await db.subscribers.insert_one({
        "id": sub_id, "operator_id": "op-1", "deleted_at": None,
        "name": "Test", "whatsapp_number": "+919876543210",
        "plans": [{
            "plan_id": plan_id, "plan_name": "X", "selected_validity": "monthly",
            "plan_start_date": "2026-06-01", "plan_expiry_date": "2026-06-30",
            "status": "active", "discount": 0,
        }],
    })

    line_items = [_line_item(plan_id, datetime(2026, 5, 1), datetime(2026, 5, 31))]
    await _sync_subscriber_plans_from_invoice(sub_id, line_items)

    sub = await db.subscribers.find_one({"id": sub_id}, {"_id": 0})
    assert sub["plans"][0]["plan_expiry_date"] == "2026-06-30", sub["plans"][0]
    assert sub["plans"][0]["plan_start_date"] == "2026-06-01"
    print("✓ test_existing_plan_unchanged_when_invoice_earlier")


async def test_custom_line_items_skipped():
    await _cleanup()
    sub_id = "test-sync-sub-4"
    await db.subscribers.insert_one({
        "id": sub_id, "operator_id": "op-1", "deleted_at": None,
        "name": "Test", "whatsapp_number": "+919876543210", "plans": [],
    })

    line_items = [_line_item(None, datetime(2026, 5, 1), datetime(2026, 5, 31), is_custom=True)]
    await _sync_subscriber_plans_from_invoice(sub_id, line_items)

    sub = await db.subscribers.find_one({"id": sub_id}, {"_id": 0})
    assert sub["plans"] == [], sub["plans"]
    print("✓ test_custom_line_items_skipped")


async def test_multiple_line_items_mixed():
    await _cleanup()
    sub_id = "test-sync-sub-5"
    plan_a = "test-sync-plan-5a"
    plan_b = "test-sync-plan-5b"
    await db.operator_plans.insert_many([
        {"id": plan_a, "name": "A", "validity": "monthly", "deleted_at": None, "operator_id": "op-1"},
        {"id": plan_b, "name": "B", "validity": "quarterly", "deleted_at": None, "operator_id": "op-1"},
    ])
    await db.subscribers.insert_one({
        "id": sub_id, "operator_id": "op-1", "deleted_at": None,
        "name": "Test", "whatsapp_number": "+919876543210",
        "plans": [{
            "plan_id": plan_a, "plan_name": "A", "selected_validity": "monthly",
            "plan_start_date": "2026-04-01", "plan_expiry_date": "2026-04-30",
            "status": "active", "discount": 0,
        }],
    })

    line_items = [
        _line_item(plan_a, datetime(2026, 5, 1), datetime(2026, 5, 31), plan_name="A"),
        _line_item(plan_b, datetime(2026, 5, 1), datetime(2026, 7, 31), plan_name="B"),
    ]
    await _sync_subscriber_plans_from_invoice(sub_id, line_items)

    sub = await db.subscribers.find_one({"id": sub_id}, {"_id": 0})
    plans_by_id = {p["plan_id"]: p for p in sub["plans"]}
    assert len(plans_by_id) == 2, plans_by_id
    assert plans_by_id[plan_a]["plan_expiry_date"] == "2026-05-31"
    assert plans_by_id[plan_b]["plan_expiry_date"] == "2026-07-31"
    print("✓ test_multiple_line_items_mixed")


def test_to_ymd_handles_various_inputs():
    assert _to_ymd(datetime(2026, 5, 28, tzinfo=timezone.utc)) == "2026-05-28"
    assert _to_ymd("2026-05-28") == "2026-05-28"
    assert _to_ymd("2026-05-28T10:30:00+00:00") == "2026-05-28"
    assert _to_ymd(None) is None
    print("✓ test_to_ymd_handles_various_inputs")


async def main():
    test_to_ymd_handles_various_inputs()
    await test_new_plan_added_to_subscriber()
    await test_existing_plan_expiry_extended_forward()
    await test_existing_plan_unchanged_when_invoice_earlier()
    await test_custom_line_items_skipped()
    await test_multiple_line_items_mixed()
    await _cleanup()
    print("\nAll tests passed ✓")


if __name__ == "__main__":
    asyncio.run(main())
