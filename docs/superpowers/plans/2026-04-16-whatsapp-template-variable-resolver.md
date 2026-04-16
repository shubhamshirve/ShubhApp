# WhatsApp Template Variable Resolver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make WhatsApp template `body_variables` drive the actual values sent for `{{1}}`, `{{2}}`, etc. instead of always using a hardcoded 4-variable order.

**Architecture:** A central `resolve_template_variables()` function in `whatsapp_service.py` maps ordered key names (e.g. `"plan_name"`, `"tenure"`) to actual invoice/subscriber data. All five call sites fetch the full template DB record by name, call the resolver, and pass dynamic variables to `send_template_message()`. Invoice-type templates fall back to the old hardcoded helper if `body_variables` is empty, ensuring zero breakage for existing setups. The frontend switches from a free-text input to a dropdown for invoice-type templates.

**Tech Stack:** Python 3.11, FastAPI, Motor (async MongoDB), React 18, shadcn/ui Select component

---

## File Map

| File | Change |
|---|---|
| `backend/services/whatsapp_service.py` | Add `_fmt_date`, `_fmt_tenure`, `KNOWN_INVOICE_VARIABLES`, `resolve_template_variables` |
| `backend/tests/test_whatsapp_variable_resolver.py` | New — unit tests for resolver |
| `backend/routers/operator.py` | Update 2 call sites (lines ~1585 and ~2132) |
| `backend/services/cron_service.py` | Update 2 call sites (lines ~376 and ~504) |
| `backend/services/job_queue_service.py` | Update 1 call site (lines ~547) |
| `frontend/src/pages/admin/WhatsAppTemplates.jsx` | Conditional dropdown vs free-text for body variables |

---

## Task 1: Add resolver to whatsapp_service.py

**Files:**
- Modify: `backend/services/whatsapp_service.py`
- Create: `backend/tests/test_whatsapp_variable_resolver.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_whatsapp_variable_resolver.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest tests/test_whatsapp_variable_resolver.py -v 2>&1 | head -30
```

Expected: `ImportError` or `AttributeError` — `resolve_template_variables` does not exist yet.

- [ ] **Step 3: Add resolver to whatsapp_service.py**

Open `backend/services/whatsapp_service.py`. After the existing imports (line 8), add:

```python
from datetime import datetime
```

(It's already imported — skip if present.)

Then, **before the `WhatsAppService` class definition** (before line 13), insert the following block:

```python
# ─── Template Variable Resolver ───────────────────────────────────────────────

def _fmt_date(value) -> str:
    """Parse datetime, ISO string, or None → 'DD Mon YYYY'."""
    if value is None:
        return ""
    try:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except (ValueError, TypeError):
        logger.warning(f"_fmt_date: could not parse '{value}'")
        return ""


def _fmt_tenure(line_items: list) -> str:
    """Format line_items service date ranges → 'DD Mon YYYY – DD Mon YYYY' (comma-joined if multiple)."""
    if not line_items:
        return ""
    ranges = []
    for item in line_items:
        start = _fmt_date(item.get("service_start_date"))
        end = _fmt_date(item.get("service_end_date"))
        if start and end:
            ranges.append(f"{start} \u2013 {end}")
    return ", ".join(ranges)


KNOWN_INVOICE_VARIABLES = {
    "customer_name":  lambda inv, sub: sub.get("name", ""),
    "invoice_number": lambda inv, sub: inv.get("invoice_number", ""),
    "amount":         lambda inv, sub: f"\u20b9{inv.get('final_amount', 0):,.2f}",
    "due_date":       lambda inv, sub: _fmt_date(inv.get("due_date")),
    "plan_name":      lambda inv, sub: ", ".join(
        li["plan_name"] for li in inv.get("line_items", []) if li.get("plan_name")
    ) or inv.get("plan_name", ""),
    "tenure":         lambda inv, sub: _fmt_tenure(inv.get("line_items", [])),
    "payment_link":   lambda inv, sub: inv.get("payment_link", "") or "",
}


def resolve_template_variables(
    body_variables: list,
    invoice: dict,
    subscriber: dict,
) -> list:
    """
    Resolve an ordered list of variable keys to actual values.

    Recognized keys are mapped via KNOWN_INVOICE_VARIABLES.
    Unrecognized keys are passed through as-is (literal string).
    Returns values for {{1}}, {{2}}, ... in order.
    """
    return [
        KNOWN_INVOICE_VARIABLES.get(key, lambda i, s, k=key: k)(invoice, subscriber)
        for key in body_variables
    ]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend && python -m pytest tests/test_whatsapp_variable_resolver.py -v
```

Expected output: all 14 tests PASSED.

- [ ] **Step 5: Commit**

```bash
cd backend && git add services/whatsapp_service.py tests/test_whatsapp_variable_resolver.py
git commit -m "feat(V8.12): add WhatsApp template variable resolver"
```

---

## Task 2: Update operator.py — auto-send on invoice create (line ~1585)

**Files:**
- Modify: `backend/routers/operator.py` (lines 1585–1597)

- [ ] **Step 1: Replace the hardcoded send with dynamic resolver**

Find the block starting at line 1585 that reads:

```python
                template_settings = await _get_whatsapp_template_settings()
                template_name = template_settings.get("invoice_template") or "invoice_notification"
                from services.whatsapp_service import WhatsAppService
                wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
                await wa_service.send_invoice_notification(
                    recipient_phone=subscriber["whatsapp_number"],
                    customer_name=subscriber["name"],
                    invoice_number=invoice["invoice_number"],
                    amount=f"₹{invoice['final_amount']:,.2f}",
                    due_date=data.due_date.strftime("%d %b %Y"),
                    payment_link=public_invoice_url,
                    template_name_override=template_name
                )
```

Replace with:

```python
                template_settings = await _get_whatsapp_template_settings()
                template_name = template_settings.get("invoice_template") or "invoice_notification"
                from services.whatsapp_service import WhatsAppService, resolve_template_variables
                wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
                tmpl_doc = await db.whatsapp_templates.find_one(
                    {"template_name": template_name, "deleted_at": None}, {"_id": 0}
                )
                body_vars = (tmpl_doc or {}).get("body_variables") or []
                if body_vars:
                    variables = resolve_template_variables(body_vars, invoice, subscriber)
                    btn_params = None
                    if (tmpl_doc or {}).get("has_payment_button") and public_invoice_url:
                        btn_params = [{"sub_type": "url", "parameters": [{"type": "text", "text": public_invoice_url}]}]
                    await wa_service.send_template_message(
                        recipient_phone=subscriber["whatsapp_number"],
                        template_name=template_name,
                        language_code=(tmpl_doc or {}).get("language_code", "en"),
                        variables=variables,
                        button_params=btn_params,
                    )
                else:
                    await wa_service.send_invoice_notification(
                        recipient_phone=subscriber["whatsapp_number"],
                        customer_name=subscriber["name"],
                        invoice_number=invoice["invoice_number"],
                        amount=f"₹{invoice['final_amount']:,.2f}",
                        due_date=data.due_date.strftime("%d %b %Y"),
                        payment_link=public_invoice_url,
                        template_name_override=template_name,
                    )
```

- [ ] **Step 2: Verify the server imports cleanly**

```bash
cd backend && python -c "from routers.operator import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/routers/operator.py
git commit -m "feat(V8.12): use variable resolver for auto-send invoice notification"
```

---

## Task 3: Update operator.py — manual send-notification endpoint (line ~2132)

**Files:**
- Modify: `backend/routers/operator.py` (lines 2132–2154)

- [ ] **Step 1: Replace both branches of the send-notification endpoint**

Find the block starting at line 2132:

```python
        template_settings = await _get_whatsapp_template_settings()
        wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
        if data.notification_type == "reminder":
            template_name = template_settings.get("reminder_template") or "payment_reminder"
            due_date = datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00'))
            days_overdue = max(0, (datetime.now(timezone.utc) - due_date).days)
            result = await wa_service.send_payment_reminder(
                recipient_phone=subscriber["whatsapp_number"], customer_name=subscriber["name"],
                invoice_number=invoice["invoice_number"],
                amount_due=f"₹{invoice['final_amount']:,.2f}", days_overdue=str(days_overdue),
                payment_link=invoice.get("payment_link"),
                template_name_override=template_name
            )
        else:
            template_name = template_settings.get("invoice_template") or "invoice_notification"
            result = await wa_service.send_invoice_notification(
                recipient_phone=subscriber["whatsapp_number"], customer_name=subscriber["name"],
                invoice_number=invoice["invoice_number"],
                amount=f"₹{invoice['final_amount']:,.2f}",
                due_date=datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00')).strftime("%d %b %Y"),
                payment_link=invoice.get("payment_link"),
                template_name_override=template_name
            )
```

Replace with:

```python
        from services.whatsapp_service import resolve_template_variables
        template_settings = await _get_whatsapp_template_settings()
        wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])
        if data.notification_type == "reminder":
            template_name = template_settings.get("reminder_template") or "payment_reminder"
            tmpl_doc = await db.whatsapp_templates.find_one(
                {"template_name": template_name, "deleted_at": None}, {"_id": 0}
            )
            body_vars = (tmpl_doc or {}).get("body_variables") or []
            if body_vars:
                variables = resolve_template_variables(body_vars, invoice, subscriber)
                btn_params = None
                if (tmpl_doc or {}).get("has_payment_button") and invoice.get("payment_link"):
                    btn_params = [{"sub_type": "url", "parameters": [{"type": "text", "text": invoice["payment_link"]}]}]
                result = await wa_service.send_template_message(
                    recipient_phone=subscriber["whatsapp_number"],
                    template_name=template_name,
                    language_code=(tmpl_doc or {}).get("language_code", "en"),
                    variables=variables,
                    button_params=btn_params,
                )
            else:
                due_date = datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00'))
                days_overdue = max(0, (datetime.now(timezone.utc) - due_date).days)
                result = await wa_service.send_payment_reminder(
                    recipient_phone=subscriber["whatsapp_number"], customer_name=subscriber["name"],
                    invoice_number=invoice["invoice_number"],
                    amount_due=f"₹{invoice['final_amount']:,.2f}", days_overdue=str(days_overdue),
                    payment_link=invoice.get("payment_link"),
                    template_name_override=template_name,
                )
        else:
            template_name = template_settings.get("invoice_template") or "invoice_notification"
            tmpl_doc = await db.whatsapp_templates.find_one(
                {"template_name": template_name, "deleted_at": None}, {"_id": 0}
            )
            body_vars = (tmpl_doc or {}).get("body_variables") or []
            if body_vars:
                variables = resolve_template_variables(body_vars, invoice, subscriber)
                btn_params = None
                if (tmpl_doc or {}).get("has_payment_button") and invoice.get("payment_link"):
                    btn_params = [{"sub_type": "url", "parameters": [{"type": "text", "text": invoice["payment_link"]}]}]
                result = await wa_service.send_template_message(
                    recipient_phone=subscriber["whatsapp_number"],
                    template_name=template_name,
                    language_code=(tmpl_doc or {}).get("language_code", "en"),
                    variables=variables,
                    button_params=btn_params,
                )
            else:
                result = await wa_service.send_invoice_notification(
                    recipient_phone=subscriber["whatsapp_number"], customer_name=subscriber["name"],
                    invoice_number=invoice["invoice_number"],
                    amount=f"₹{invoice['final_amount']:,.2f}",
                    due_date=datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00')).strftime("%d %b %Y"),
                    payment_link=invoice.get("payment_link"),
                    template_name_override=template_name,
                )
```

- [ ] **Step 2: Verify imports**

```bash
cd backend && python -c "from routers.operator import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/routers/operator.py
git commit -m "feat(V8.12): use variable resolver for manual send-notification endpoint"
```

---

## Task 4: Update cron_service.py — auto-invoice notification (line ~376)

**Files:**
- Modify: `backend/services/cron_service.py` (lines ~376–390)

- [ ] **Step 1: Replace auto-invoice notification call**

Find the block starting at approximately line 376:

```python
        # Send notification if WhatsApp is available
        from services.whatsapp_service import get_whatsapp_service_async
        wa_service = await get_whatsapp_service_async()
        if wa_service:
            try:
                await wa_service.send_invoice_notification(
                    recipient_phone=subscriber["whatsapp_number"],
                    customer_name=subscriber["name"],
                    invoice_number=invoice_number,
                    amount=f"INR {invoice['final_amount']:,.2f}",
                    due_date=due_date.strftime("%d %b %Y"),
                    payment_link=invoice.get("payment_link")
                )
            except Exception as e:
                logger.error(f"Failed to send invoice notification: {str(e)}")
```

Replace with:

```python
        # Send notification if WhatsApp is available
        from services.whatsapp_service import get_whatsapp_service_async, resolve_template_variables
        wa_service = await get_whatsapp_service_async()
        if wa_service:
            try:
                cron_template_settings = await self.db.global_settings.find_one(
                    {"type": "whatsapp_template_settings"}, {"_id": 0}
                ) or {}
                invoice_tpl_name = cron_template_settings.get("invoice_template") or "invoice_notification"
                tmpl_doc = await self.db.whatsapp_templates.find_one(
                    {"template_name": invoice_tpl_name, "deleted_at": None}, {"_id": 0}
                )
                body_vars = (tmpl_doc or {}).get("body_variables") or []
                if body_vars:
                    variables = resolve_template_variables(body_vars, invoice, subscriber)
                    btn_params = None
                    if (tmpl_doc or {}).get("has_payment_button") and invoice.get("payment_link"):
                        btn_params = [{"sub_type": "url", "parameters": [{"type": "text", "text": invoice["payment_link"]}]}]
                    await wa_service.send_template_message(
                        recipient_phone=subscriber["whatsapp_number"],
                        template_name=invoice_tpl_name,
                        language_code=(tmpl_doc or {}).get("language_code", "en"),
                        variables=variables,
                        button_params=btn_params,
                    )
                else:
                    await wa_service.send_invoice_notification(
                        recipient_phone=subscriber["whatsapp_number"],
                        customer_name=subscriber["name"],
                        invoice_number=invoice_number,
                        amount=f"INR {invoice['final_amount']:,.2f}",
                        due_date=due_date.strftime("%d %b %Y"),
                        payment_link=invoice.get("payment_link"),
                    )
            except Exception as e:
                logger.error(f"Failed to send invoice notification: {str(e)}")
```

- [ ] **Step 2: Verify imports**

```bash
cd backend && python -c "from services.cron_service import CronService; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/services/cron_service.py
git commit -m "feat(V8.12): use variable resolver in cron auto-invoice notification"
```

---

## Task 5: Update cron_service.py — scheduled reminders (line ~504)

**Files:**
- Modify: `backend/services/cron_service.py` (lines ~504–526)

- [ ] **Step 1: Replace both branches of the reminder send**

Find the block starting at approximately line 504:

```python
                        if days_diff <= 0:
                            reminder_tpl = template_settings.get("reminder_template") or "payment_reminder"
                            days_overdue = max(0, abs(days_diff))
                            await wa_service.send_payment_reminder(
                                recipient_phone=subscriber["whatsapp_number"],
                                customer_name=subscriber["name"],
                                invoice_number=invoice["invoice_number"],
                                amount_due=f"INR {invoice['final_amount']:,.2f}",
                                days_overdue=str(days_overdue),
                                payment_link=invoice.get("payment_link"),
                                template_name_override=reminder_tpl,
                            )
                        else:
                            invoice_tpl = template_settings.get("invoice_template") or "invoice_notification"
                            await wa_service.send_invoice_notification(
                                recipient_phone=subscriber["whatsapp_number"],
                                customer_name=subscriber["name"],
                                invoice_number=invoice["invoice_number"],
                                amount=f"INR {invoice['final_amount']:,.2f}",
                                due_date=due_date.strftime("%d %b %Y"),
                                payment_link=invoice.get("payment_link"),
                                template_name_override=invoice_tpl,
                            )
```

Replace with:

```python
                        from services.whatsapp_service import resolve_template_variables
                        if days_diff <= 0:
                            reminder_tpl = template_settings.get("reminder_template") or "payment_reminder"
                            days_overdue = max(0, abs(days_diff))
                            tmpl_doc = await self.db.whatsapp_templates.find_one(
                                {"template_name": reminder_tpl, "deleted_at": None}, {"_id": 0}
                            )
                            body_vars = (tmpl_doc or {}).get("body_variables") or []
                            if body_vars:
                                variables = resolve_template_variables(body_vars, invoice, subscriber)
                                btn_params = None
                                if (tmpl_doc or {}).get("has_payment_button") and invoice.get("payment_link"):
                                    btn_params = [{"sub_type": "url", "parameters": [{"type": "text", "text": invoice["payment_link"]}]}]
                                await wa_service.send_template_message(
                                    recipient_phone=subscriber["whatsapp_number"],
                                    template_name=reminder_tpl,
                                    language_code=(tmpl_doc or {}).get("language_code", "en"),
                                    variables=variables,
                                    button_params=btn_params,
                                )
                            else:
                                await wa_service.send_payment_reminder(
                                    recipient_phone=subscriber["whatsapp_number"],
                                    customer_name=subscriber["name"],
                                    invoice_number=invoice["invoice_number"],
                                    amount_due=f"INR {invoice['final_amount']:,.2f}",
                                    days_overdue=str(days_overdue),
                                    payment_link=invoice.get("payment_link"),
                                    template_name_override=reminder_tpl,
                                )
                        else:
                            invoice_tpl = template_settings.get("invoice_template") or "invoice_notification"
                            tmpl_doc = await self.db.whatsapp_templates.find_one(
                                {"template_name": invoice_tpl, "deleted_at": None}, {"_id": 0}
                            )
                            body_vars = (tmpl_doc or {}).get("body_variables") or []
                            if body_vars:
                                variables = resolve_template_variables(body_vars, invoice, subscriber)
                                btn_params = None
                                if (tmpl_doc or {}).get("has_payment_button") and invoice.get("payment_link"):
                                    btn_params = [{"sub_type": "url", "parameters": [{"type": "text", "text": invoice["payment_link"]}]}]
                                await wa_service.send_template_message(
                                    recipient_phone=subscriber["whatsapp_number"],
                                    template_name=invoice_tpl,
                                    language_code=(tmpl_doc or {}).get("language_code", "en"),
                                    variables=variables,
                                    button_params=btn_params,
                                )
                            else:
                                await wa_service.send_invoice_notification(
                                    recipient_phone=subscriber["whatsapp_number"],
                                    customer_name=subscriber["name"],
                                    invoice_number=invoice["invoice_number"],
                                    amount=f"INR {invoice['final_amount']:,.2f}",
                                    due_date=due_date.strftime("%d %b %Y"),
                                    payment_link=invoice.get("payment_link"),
                                    template_name_override=invoice_tpl,
                                )
```

- [ ] **Step 2: Verify imports**

```bash
cd backend && python -c "from services.cron_service import CronService; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/services/cron_service.py
git commit -m "feat(V8.12): use variable resolver in cron reminder scheduler"
```

---

## Task 6: Update job_queue_service.py — bulk notification (line ~547)

**Files:**
- Modify: `backend/services/job_queue_service.py` (lines ~547–577)

- [ ] **Step 1: Replace the bulk notification send call**

Find the block starting at approximately line 547:

```python
        template_settings = await _get_whatsapp_template_settings()
        invoice_template = template_settings.get("invoice_template") or "invoice_notification"

        results = {"sent": 0, "failed": 0, "errors": []}
        wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])

        for subscriber_id in subscriber_ids:
            try:
                subscriber = await db.subscribers.find_one(
                    {"id": subscriber_id, "operator_id": operator_id, "deleted_at": None},
                    {"_id": 0},
                )
                if not subscriber:
                    continue

                invoice = await db.invoices.find_one(
                    {"subscriber_id": subscriber_id, "status": {"$in": ["pending", "overdue"]}, "deleted_at": None},
                    {"_id": 0},
                )
                if invoice:
                    await wa_service.send_invoice_notification(
                        recipient_phone=subscriber["whatsapp_number"],
                        customer_name=subscriber["name"],
                        invoice_number=invoice["invoice_number"],
                        amount=f"₹{invoice['final_amount']:,.2f}",
                        due_date=datetime.fromisoformat(
                            invoice["due_date"].replace("Z", "+00:00")
                        ).strftime("%d %b %Y"),
                        payment_link=invoice.get("payment_link"),
                        template_name_override=invoice_template,
                    )
                    results["sent"] += 1
```

Replace with:

```python
        from services.whatsapp_service import resolve_template_variables
        template_settings = await _get_whatsapp_template_settings()
        invoice_template = template_settings.get("invoice_template") or "invoice_notification"
        tmpl_doc = await db.whatsapp_templates.find_one(
            {"template_name": invoice_template, "deleted_at": None}, {"_id": 0}
        )
        body_vars = (tmpl_doc or {}).get("body_variables") or []

        results = {"sent": 0, "failed": 0, "errors": []}
        wa_service = WhatsAppService(wa_config["phone_number_id"], wa_config["access_token"])

        for subscriber_id in subscriber_ids:
            try:
                subscriber = await db.subscribers.find_one(
                    {"id": subscriber_id, "operator_id": operator_id, "deleted_at": None},
                    {"_id": 0},
                )
                if not subscriber:
                    continue

                invoice = await db.invoices.find_one(
                    {"subscriber_id": subscriber_id, "status": {"$in": ["pending", "overdue"]}, "deleted_at": None},
                    {"_id": 0},
                )
                if invoice:
                    if body_vars:
                        variables = resolve_template_variables(body_vars, invoice, subscriber)
                        btn_params = None
                        if (tmpl_doc or {}).get("has_payment_button") and invoice.get("payment_link"):
                            btn_params = [{"sub_type": "url", "parameters": [{"type": "text", "text": invoice["payment_link"]}]}]
                        await wa_service.send_template_message(
                            recipient_phone=subscriber["whatsapp_number"],
                            template_name=invoice_template,
                            language_code=(tmpl_doc or {}).get("language_code", "en"),
                            variables=variables,
                            button_params=btn_params,
                        )
                    else:
                        await wa_service.send_invoice_notification(
                            recipient_phone=subscriber["whatsapp_number"],
                            customer_name=subscriber["name"],
                            invoice_number=invoice["invoice_number"],
                            amount=f"₹{invoice['final_amount']:,.2f}",
                            due_date=datetime.fromisoformat(
                                invoice["due_date"].replace("Z", "+00:00")
                            ).strftime("%d %b %Y"),
                            payment_link=invoice.get("payment_link"),
                            template_name_override=invoice_template,
                        )
                    results["sent"] += 1
```

- [ ] **Step 2: Verify imports**

```bash
cd backend && python -c "from services.job_queue_service import JobQueueService; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/services/job_queue_service.py
git commit -m "feat(V8.12): use variable resolver in bulk notification job"
```

---

## Task 7: Update WhatsAppTemplates.jsx — conditional variable input

**Files:**
- Modify: `frontend/src/pages/admin/WhatsAppTemplates.jsx`

- [ ] **Step 1: Add the constant and state for the dropdown**

After the `TYPE_COLORS` constant (around line 48), add:

```js
const INVOICE_TYPE_TEMPLATES = ["invoice_notification", "payment_reminder", "payment_confirmation"];

const INVOICE_VARIABLE_OPTIONS = [
  { value: "customer_name",  label: "Customer Name" },
  { value: "plan_name",      label: "Plan Name" },
  { value: "tenure",         label: "Tenure (Date Range)" },
  { value: "invoice_number", label: "Invoice Number" },
  { value: "amount",         label: "Amount" },
  { value: "due_date",       label: "Due Date" },
  { value: "payment_link",   label: "Payment Link" },
];
```

- [ ] **Step 2: Add a selectedVariable state**

In the component, after the `variableInput` state declaration (currently line 69):

```js
const [variableInput, setVariableInput] = useState("");
const [selectedVariable, setSelectedVariable] = useState("");
```

Replace the existing line with those two lines.

- [ ] **Step 3: Update openCreate and openEdit to reset selectedVariable**

In `openCreate` (around line 89), add `setSelectedVariable("");` alongside `setVariableInput("");`:

```js
  const openCreate = () => {
    setEditTemplate(null);
    setForm(defaultForm);
    setVariableInput("");
    setSelectedVariable("");
    setShowDialog(true);
  };
```

In `openEdit` (around line 96), add `setSelectedVariable("");` alongside `setVariableInput("");`:

```js
  const openEdit = (tmpl) => {
    setEditTemplate(tmpl);
    setForm({
      template_name: tmpl.template_name,
      display_name: tmpl.display_name,
      template_type: tmpl.template_type,
      language_code: tmpl.language_code || "en",
      description: tmpl.description || "",
      body_variables: tmpl.body_variables || [],
      has_payment_button: tmpl.has_payment_button || false,
      is_active: tmpl.is_active !== false,
    });
    setVariableInput("");
    setSelectedVariable("");
    setShowDialog(true);
  };
```

- [ ] **Step 4: Add a handler for the dropdown add action**

After the existing `addVariable` function (around line 165), add:

```js
  const addSelectedVariable = () => {
    if (!selectedVariable) return;
    if (form.body_variables.includes(selectedVariable)) {
      toast.error("Variable already added");
      return;
    }
    setForm({ ...form, body_variables: [...form.body_variables, selectedVariable] });
    setSelectedVariable("");
  };
```

- [ ] **Step 5: Replace the Body Variables input section in the dialog**

Find the "Body Variables" section in the form (around line 426):

```jsx
            {/* Body Variables */}
            <div className="space-y-2">
              <Label>Body Variables</Label>
              <p className="text-xs text-slate-500">
                Add variable descriptions in order — these become <code className="bg-slate-100 px-1 rounded">{`{{1}}`}</code>, <code className="bg-slate-100 px-1 rounded">{`{{2}}`}</code>, etc. in the template.
              </p>
              <div className="flex gap-2">
                <Input
                  placeholder="e.g. customer_name"
                  value={variableInput}
                  onChange={(e) => setVariableInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addVariable(); } }}
                />
                <Button type="button" variant="outline" onClick={addVariable} className="shrink-0">
                  Add
                </Button>
              </div>
```

Replace with:

```jsx
            {/* Body Variables */}
            <div className="space-y-2">
              <Label>Body Variables</Label>
              <p className="text-xs text-slate-500">
                Add variables in order — these become <code className="bg-slate-100 px-1 rounded">{`{{1}}`}</code>, <code className="bg-slate-100 px-1 rounded">{`{{2}}`}</code>, etc. in the template.
              </p>
              {INVOICE_TYPE_TEMPLATES.includes(form.template_type) ? (
                <div className="flex gap-2">
                  <Select value={selectedVariable} onValueChange={setSelectedVariable}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a variable..." />
                    </SelectTrigger>
                    <SelectContent>
                      {INVOICE_VARIABLE_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button type="button" variant="outline" onClick={addSelectedVariable} className="shrink-0">
                    Add
                  </Button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <Input
                    placeholder="e.g. promo_text"
                    value={variableInput}
                    onChange={(e) => setVariableInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addVariable(); } }}
                  />
                  <Button type="button" variant="outline" onClick={addVariable} className="shrink-0">
                    Add
                  </Button>
                </div>
              )}
```

- [ ] **Step 6: Verify the frontend builds**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: build completes with no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/admin/WhatsAppTemplates.jsx
git commit -m "feat(V8.12): show variable dropdown for invoice-type WhatsApp templates"
```

---

## Task 8: Run full test suite and final check

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && python -m pytest tests/test_whatsapp_variable_resolver.py -v
```

Expected: 14 tests PASSED, 0 failed.

- [ ] **Step 2: Verify all five backend modules import cleanly**

```bash
cd backend && python -c "
from services.whatsapp_service import resolve_template_variables
from routers.operator import router
from services.cron_service import CronService
from services.job_queue_service import JobQueueService
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 3: Manual smoke test checklist**

In the admin UI:
1. Go to WhatsApp Templates → New Template
2. Set type to "Invoice Notification" → confirm variable input shows a dropdown with 7 options
3. Add `customer_name`, `plan_name`, `tenure`, `due_date` in order → confirm badges show `{{1}} customer_name`, `{{2}} plan_name`, etc.
4. Set type to "Announcement" → confirm variable input reverts to free-text
5. Save the template

- [ ] **Step 4: Final commit (if any loose files)**

```bash
cd d:/eBill && git status
```

If clean, no action needed. Otherwise stage and commit remaining changes.
