# WhatsApp Template Variable Resolver — Design Spec

**Date:** 2026-04-16  
**Status:** Approved

---

## Problem

WhatsApp templates store `body_variables` as an ordered list of descriptive labels (e.g. `["customer_name", "plan_name", "tenure", "due_date"]`). These labels are currently **documentation only** — they have no effect on what values are actually sent to the WhatsApp API.

Every send call uses a hardcoded helper (`send_invoice_notification`) that always passes `[customer_name, invoice_number, amount, due_date]` regardless of the template's configured variables. If a template's `{{2}}` is meant to be `plan_name`, it will incorrectly receive `invoice_number` instead.

---

## Goal

Make `body_variables` drive the actual values sent for `{{1}}`, `{{2}}`, etc. by:

1. Adding a central variable resolver in the backend
2. Updating all call sites to use the resolver
3. Updating the frontend to guide users to recognized field keys (for invoice-type templates)

---

## Architecture

### Approach

**Central resolver function in `whatsapp_service.py`** (single source of truth). All call sites fetch the template's `body_variables` and pass them to the resolver along with invoice + subscriber data.

---

## Backend Design

### 1. Variable Resolver (`backend/services/whatsapp_service.py`)

Add a `KNOWN_INVOICE_VARIABLES` dict and two helper functions:

```python
KNOWN_INVOICE_VARIABLES = {
    "customer_name":  lambda inv, sub: sub.get("name", ""),
    "invoice_number": lambda inv, sub: inv.get("invoice_number", ""),
    "amount":         lambda inv, sub: f"₹{inv.get('final_amount', 0):,.2f}",
    "due_date":       lambda inv, sub: _fmt_date(inv.get("due_date")),
    "plan_name":      lambda inv, sub: ", ".join(
                          li["plan_name"] for li in inv.get("line_items", [])
                          if li.get("plan_name")
                      ) or inv.get("plan_name", ""),
    "tenure":         lambda inv, sub: _fmt_tenure(inv.get("line_items", [])),
    "payment_link":   lambda inv, sub: inv.get("payment_link", ""),
}

def resolve_template_variables(
    body_variables: List[str],
    invoice: dict,
    subscriber: dict
) -> List[str]:
    """Return ordered list of resolved values for {{1}}, {{2}}, ..."""
    return [
        KNOWN_INVOICE_VARIABLES.get(key, lambda i, s: key)(invoice, subscriber)
        for key in body_variables
    ]
```

**Helper functions:**

- `_fmt_date(value)` — accepts a `datetime`, ISO string, or `None`; returns `"DD Mon YYYY"` or `""`.
- `_fmt_tenure(line_items)` — for each line item, formats `service_start_date – service_end_date` as `"DD Mon YYYY – DD Mon YYYY"`. If all items share the same range, returns one string. If multiple different ranges, returns them comma-joined.

**Unrecognized keys** (e.g. free-text keys used in announcement/custom templates) are passed through as the literal key string. This is intentional — it acts as a visible placeholder so the operator knows resolution failed, rather than silently sending empty strings.

### 2. Call Sites

All five call sites are updated to:
1. Fetch `body_variables` from the already-retrieved template DB record
2. Call `resolve_template_variables(body_variables, invoice, subscriber)`
3. Pass the result to `send_template_message()` directly

**Affected locations:**
- `backend/routers/operator.py:1589` — manual invoice send
- `backend/routers/operator.py:2147` — bulk invoice send
- `backend/services/cron_service.py:381` — auto-generated invoice notify
- `backend/services/cron_service.py:518` — cron payment reminder
- `backend/services/job_queue_service.py:567` — job queue send

**Fallback:** If `body_variables` is empty or the template record is not found, fall back to the existing `send_invoice_notification()` / `send_payment_reminder()` wrappers with their hardcoded 4-variable order. This ensures zero breakage for existing configured templates.

### 3. CTA Button & Header Image

- **Header image:** Static in Meta Business Suite — no code changes needed.
- **CTA button (payment link):** Continues to be passed via `invoice.get("payment_link")` as `button_params` when `template.has_payment_button` is `True`. No changes to this flow.

---

## Frontend Design

### `frontend/src/pages/admin/WhatsAppTemplates.jsx`

The "Body Variables" input section switches based on `form.template_type`:

**Invoice-type templates** (`invoice_notification`, `payment_reminder`, `payment_confirmation`):  
Replace the free-text `<Input>` with a `<Select>` dropdown showing recognized field keys:

| Label shown | Key stored in `body_variables` |
|---|---|
| Customer Name | `customer_name` |
| Plan Name | `plan_name` |
| Tenure (Date Range) | `tenure` |
| Invoice Number | `invoice_number` |
| Amount | `amount` |
| Due Date | `due_date` |
| Payment Link | `payment_link` |

The Add button, ordered badge list (`{{1}} customer_name`), and remove (×) buttons remain unchanged.

**Announcement / Custom templates:**  
Keep the existing free-text `<Input>` unchanged.

The switch is driven by a constant:
```js
const INVOICE_TYPE_TEMPLATES = ["invoice_notification", "payment_reminder", "payment_confirmation"];
```

---

## Data Flow

```
Template DB record
  └── body_variables: ["customer_name", "plan_name", "tenure", "due_date"]

Call site fetches template + invoice + subscriber
  └── resolve_template_variables(body_variables, invoice, subscriber)
        └── Returns: ["Ramesh Kumar", "Fiber 50Mbps", "01 Apr 2026 – 30 Apr 2026", "25 Apr 2026"]

send_template_message(
  template_name="invoice_v2",
  variables=["Ramesh Kumar", "Fiber 50Mbps", "01 Apr 2026 – 30 Apr 2026", "25 Apr 2026"],
  button_params=[{...payment_link...}]   # if has_payment_button
)
```

---

## Error Handling

- Missing invoice field → empty string `""` (WhatsApp API will reject if required, surfaces error in logs)
- `due_date` parse failure → `""` with a warning log
- `line_items` empty for `plan_name` / `tenure` → `""` gracefully

---

## Files Changed

| File | Change |
|---|---|
| `backend/services/whatsapp_service.py` | Add `KNOWN_INVOICE_VARIABLES`, `_fmt_date`, `_fmt_tenure`, `resolve_template_variables` |
| `backend/routers/operator.py` | 2 call sites: fetch `body_variables`, use resolver |
| `backend/services/cron_service.py` | 2 call sites: fetch `body_variables`, use resolver |
| `backend/services/job_queue_service.py` | 1 call site: fetch `body_variables`, use resolver |
| `frontend/src/pages/admin/WhatsAppTemplates.jsx` | Conditional dropdown vs free-text for body variables |

---

## Out of Scope

- `cron_service_utf8.py` and `cron_service_restored.py` are legacy/backup files — not modified
- No changes to the WhatsApp template DB schema
- No changes to the Meta template approval process
