# Invoice / Auto-Invoice / Expiry — Deep Analysis & Pending Tasks

> Created: Feb 2026
> Status: **PENDING USER REVIEW & APPROVAL** — no code changes have been made.
> Scope: Reviewed `/app/backend/services/cron_service.py`, `/app/backend/services/invoice_helpers.py`, and `/app/backend/routers/operator.py` (invoice + subscriber sections).
> Purpose: Capture every observed bug, logic inconsistency, and enhancement so the user can compare them against the originally intended business logic before the next agent picks up implementation.

---

## 0. How the system is *supposed* to work (per PRD V9.12)

| Aspect | PRD rule |
|---|---|
| Expiry sync source | From invoice **creation/update** (not payment) |
| Expiry hybrid rule | `new_expiry = MAX(old_plan_expiry_date, line_item.service_end_date)` — only move forward |
| New plans on an invoice | Auto-added to `subscriber.plans[]` |
| Custom line items | Skipped from sync |
| Cron schedule | Expiry check 00:05 IST, Invoice gen 08:00 IST, Reminders 10:00 IST, Wallet check 09:00 IST |
| Paid invoices | Operator cannot cancel; admin can |
| Wallet | ≥ ₹50 required to generate invoices; < ₹50 = wallet_suspended + read_only |
| Subscriber plans | Embedded array, up to 5 |

---

## 1. Critical Bugs (P0)

### B1. Duplicate auto-invoices possible on expiry-based path
**File:** `cron_service.py` L91-167
**Current behaviour:**
```python
# ── Expiry-date approach: find subscribers whose plan expires within days_before ──
# ...
# ── Expiry-date plans: no duplicate check needed ──────
# The expiry date IS the deduplication — a plan only appears
# in the query when it is actually expiring soon.
```
The code skips per-plan duplicate detection on the modern expiry-based branch (only legacy `billing_date` plans get `_check_plan_recently_billed`).

**Why this breaks:**
1. If `run_daily_invoice_generation` is triggered twice in the same day (manual scheduler trigger + APScheduler), the same plan is billed twice — the first generation only updates `subscriber.plans[].plan_expiry_date` *after* the new invoice is inserted, but a concurrent second call already queried the old expiry.
2. If a subscriber's plan expiry is *manually* edited backwards, the next cron run will re-bill a plan that already has a pending invoice for the same period.
3. Manual `create_invoice` for the same plan in the 3-day window does NOT prevent the cron from generating a parallel auto-invoice (sync moves expiry forward, so it usually saves us, but only if the manual invoice's `service_end_date > target window`).

**Proposed fix:**
- Add `_check_plan_recently_billed` check on the expiry-based branch as well, with the window equal to the current plan's validity (use `relativedelta` not 28-day approximation).
- Better: query existing `invoices` for `(operator_id, subscriber_id, line_items.plan_id, status != cancelled, service_end_date == plan_expiry_date_of_this_renewal)` and skip if found.

---

### B2. Past-expired plans are silently skipped
**File:** `cron_service.py` L93-101
**Current query:**
```python
"plan_expiry_date": {"$gte": today_str, "$lte": target_str}
```
Plans whose `plan_expiry_date < today` (already lapsed, unrenewed) are **never picked up**. They become stale forever unless an operator manually creates an invoice.

**Real-world impact:** Subscriber lapses on Day 1 → cron doesn't run that day for whatever reason → on Day 2 the plan is already past `today_str` → cron permanently ignores it.

**Proposed fix:** Extend lower bound — e.g. `{"$gte": (today - 60d), "$lte": target}`. Plans expired > 60 days ago should be flagged separately for manual review (auto-suspend candidate).

---

### B3. Pending → Overdue transition is never automatic
**Files:**
- `cron_service.py` `process_scheduled_reminders` (L868-1127) reads invoices with `status: {"$in": ["pending", "overdue"]}` — but never transitions them.
- `cron_service.py` `send_overdue_reminders` (L194-273) DOES transition pending → overdue, but is **NOT wired to any scheduler** (only `run_daily_reminder_processing` is registered, which calls `process_scheduled_reminders`).
- `run_daily_expiry_check` (L1281) only flips *operator* status, not invoice status.

**Result:** Once due_date passes, invoice stays `status="pending"` in the DB even though the UI shows it as overdue. Filtering, reporting, and the `overdue_count` in `run_daily_operator_report` all break.

**Proposed fix:** Add an automatic status transition step at the start of `process_scheduled_reminders` (or as its own micro-job): update all `pending` invoices where `due_date < now` → `status="overdue"`.

---

### B4. Three different definitions of "monthly" service length
| Function | Monthly length | Quarterly | Half-yearly | Yearly |
|---|---|---|---|---|
| `operator.py::_calc_plan_expiry` (subscriber create) | `relativedelta(months=1) - 1d` | months=3-1d | months=6-1d | months=12-1d |
| `cron_service.py::_create_first_invoice` (when fallback path hits) | **30 days** | 90 days | 180 days | 365 days |
| `cron_service.py::_create_auto_invoice` | `relativedelta(months=1) - 1d` | months=3-1d | months=6-1d | months=12-1d |
| `cron_service.py::_check_existing_invoice` / `_check_plan_recently_billed` (dedup window) | **28 days** | 80 | 170 | 355 |

**Consequence:** A Feb-starting monthly plan computes:
- Subscriber expiry: 2026-02-28 (calendar)
- First invoice fallback: 2026-03-03 (30 days)
- Dedup window: 28 days — could allow a duplicate on day 29-30

**Proposed fix:** Centralize one helper `service_period(start, validity) -> (start, end)` using `relativedelta(months=N) - 1d`. Use it everywhere. Dedup window = same `(months=N) - 1d`.

---

### B5. PRD violation: `update_invoice` uses `force=True`, can shorten expiry
**File:** `operator.py` L2204
```python
await _sync_subscriber_plans_from_invoice(data.subscriber_id, payload["line_items"], force=True)
```
PRD rule: `new_expiry = MAX(old, line_item.service_end_date)` — only move forward.
**`force=True` bypasses the MAX rule** and overwrites with whatever the user typed.

**Two valid resolutions** — needs user decision:
- (i) **Code fix**: drop `force=True`, keep MAX semantics on edit too.
- (ii) **PRD fix**: declare "invoice edit is a power-user action that overrides expiry forward or backward" and document it.

---

### B6. Renewal service period overlaps old expiry day by 1 day
**File:** `cron_service.py::_create_auto_invoice` L419-438
```python
expiry_date_str = p_info.get("plan_expiry_date")  # e.g. "2026-02-28"
service_start = datetime.strptime(expiry_date_str, "%Y-%m-%d")  # 2026-02-28
service_end = service_start + relativedelta(months=svc_months) - timedelta(days=1)  # 2026-03-27
```
But the **old invoice's** `service_end_date` was already `2026-02-28`. So the new invoice's `service_start_date == previous invoice's service_end_date`. Customer is double-billed for that one day.

**Proposed fix:** `service_start = (old_expiry + 1 day)`. Adjust `_calc_plan_expiry` and `_create_first_invoice` consistently — pick a convention ("inclusive end" vs "exclusive end") and apply globally.

---

### B7. `due_date = service_start - 1 day` cuts off pre-due reminders
**File:** `cron_service.py::_create_auto_invoice` L480-482
```python
due_date = first_service_start - timedelta(days=1)
```
Auto-invoices are generated `days_before=3` days before expiry → `due_date` ends up being 2-4 days *after* invoice creation. With `remind_before_due = [7, 5, 3, 2, 1]`, the **7d/5d slots can never fire**, because the invoice didn't exist yet on those days.

**Proposed fix:**
- Either bump `auto_invoice_days_before` default to 7+ days so all reminder slots can fire, OR
- Make due-date offset configurable (operator setting: "Due X days after invoice issued").

---

### B8. Race-condition: invoice inserted before wallet deducted
**Files:** `operator.py` L2023-2036 and `cron_service.py` L536, 572
```python
await db.invoices.insert_one(invoice)
# ...
await deduct_wallet_for_invoice(operator_id, invoice["id"])  # may fail/raise
```
If wallet deduction fails (DB blip, edge case), the invoice persists without being billed against wallet → operator gets free invoice.

**Proposed fix:** Reverse the order — deduct first (with idempotency key = invoice.id), then insert invoice. Or wrap both in a Mongo transaction.

---

### B9. Auto-invoices skip audit log
**File:** `cron_service.py::_create_auto_invoice` L487-536
Manual `create_invoice` writes an audit log (well, on update it does — actually create_invoice in operator.py also doesn't audit-log on creation!). Cron-created invoices also produce no `audit_logs` entry, only the high-level `cron_executed` log.

**Proposed fix:** Add `log_audit` call inside `_create_auto_invoice`, `_create_first_invoice`, and manual `create_invoice` (currently only `update_invoice` and `update_invoice_status` audit).

---

### B10. Two parallel reminder code paths
- `send_overdue_reminders` (L194) — orphaned, not scheduled, transitions pending→overdue + sends WA.
- `process_scheduled_reminders` (L868) — active, scheduled, doesn't transition status but handles 3 templates (invoice / on-due / overdue).

**Proposed fix:** Delete `send_overdue_reminders` entirely; move its pending→overdue transition into `process_scheduled_reminders`. (Tied to B3.)

---

## 2. Logic Enhancements (P1)

### E1. Idempotency key for invoice generation
Composite key: `(operator_id, subscriber_id, plan_id, billing_period_start)`. Unique index on `invoices` collection prevents duplicates at DB level regardless of race conditions.

### E2. Configurable invoice-generation lead time (`auto_invoice_days_before`)
Already in `platform_settings` (L1133) but defaulted to 3. Expose this per-operator and document the interplay with `reminder_before_due`.

### E3. Configurable due-date offset
Currently `service_start - 1d` hardcoded. Operator UX expectation: "Net 7" or "Due on receipt". Add `operator.invoice_due_offset_days` (default 0 = due on service start).

### E4. Atomic invoice + wallet + sync
Wrap `insert invoice → deduct wallet → sync subscriber.plans → send WA` in a try/except with explicit rollback (or use Mongo session). Today each is a fire-and-forget try/except with warnings, leaving inconsistent state.

### E5. Add audit logs everywhere invoices mutate
Specifically:
- `create_invoice` (manual) — currently NO audit log
- `_create_auto_invoice` (cron) — no audit log
- `_create_first_invoice` (on subscriber creation) — no audit log

### E6. Per-plan billing date tracking (not per-subscriber)
Today, the legacy `billing_date` lives on `subscriber.plans[i].billing_date`. The expiry-date approach stored `plan_expiry_date` per plan. Some old plans still have `billing_date` set without `plan_expiry_date`. Provide a migration check / nightly job: any plan with `billing_date` AND missing `plan_expiry_date` → compute and backfill.

### E7. Reminders should NOT mark invoice "overdue" mid-job
B3 fix should run *before* iterating invoices, so the per-invoice loop sees consistent statuses.

### E8. Plan-suspension auto-rule
Today, expiry check only flips operator status. **Subscriber** plans that have been expired > N days (operator-configurable) should auto-transition to `status="suspended"`. Currently no such logic exists — manual cleanup required.

---

## 3. Code-Quality / Refactor (P2)

### R1. Split `cron_service.py` (1530 lines)
```
backend/services/cron/
├── __init__.py
├── invoices.py     # generate_upcoming_invoices, _create_auto_invoice, _create_first_invoice
├── reminders.py    # process_scheduled_reminders (+ helper for whatsapp send pattern)
├── expiry.py       # run_daily_expiry_check, check_subscription_expiry
├── wallet.py       # run_daily_wallet_check
├── reports.py      # run_daily_operator_report
└── common.py       # get_maintenance_state, log_cron_execution, _resolve_operator_variables
```

### R2. DRY line-item builder
`_create_auto_invoice`, `_create_first_invoice`, and `invoice_helpers.build_invoice_payload` each repeat ~150 lines of:
- plan lookup
- validity → months scaling
- tax exclusive/inclusive calculation
- line_item dict assembly

Extract to `invoice_helpers.build_line_item(plan, p_info, can_charge_gst, service_start, service_end) -> dict`. Call from all three places.

### R3. DRY WhatsApp send pattern
The "template_doc fetch → build_wa_send_params → if body_vars send_template_message else send_fallback → log_whatsapp_message" block is duplicated ≥ 6 times. Move to `whatsapp_service.send_for_event(event_type, invoice, subscriber, ...)`.

### R4. Pydantic models for cron results
The dicts `{"total_checked": ..., "invoices_generated": ..., "errors": []}` are unstructured. Define `CronInvoiceResult`, `CronReminderResult`, etc. — easier to consume in admin dashboards.

### R5. Tests
Currently `/app/backend/tests` directory exists per architecture but has no invoice/cron coverage. Add:
- `test_cron_invoices.py` — dedup, past-expired, service-period correctness
- `test_invoice_sync.py` — MAX rule, force mode, custom item skip
- `test_invoice_helpers.py` — price scaling, tax calc

---

## 4. Subtle "logic difference" observations (FYI — may not be bugs)

| Observation | Where | Note |
|---|---|---|
| Subscriber `billing_date` set to `start.day` on create, but only used by legacy cron path | `operator.py:1415` | Kept for "legacy display only" per comment. Confirm UI doesn't use it. |
| Expiry check at 00:05 doesn't email/notify operator subscribers | `cron_service.py:1281` | Only WhatsApps the operator owners themselves about *their* SaaS expiry, not the end-customers. |
| Wallet `< 50` blocks invoice creation; `< 100` warns. Cron skips operator entirely if `< 50` | `cron_service.py:84-86`, `operator.py:2000` | Consistent, but if wallet sits at 49.99 → all auto-invoices for that operator silently skipped. User may not realise. Should produce a visible warning. |
| `_check_existing_invoice` uses `service_start_date >= cutoff`; `_check_plan_recently_billed` does the same but elem-matches `plan_id` | `cron_service.py:341, 373` | Former is now dead-code on modern path (only legacy uses it). Candidate for deletion. |
| Force-mode sync on update overwrites `selected_validity` from line item | `operator.py:152-153` | Means changing the validity on an invoice edit also retroactively changes subscriber's plan. Intentional? |
| `_create_first_invoice` uses `(now + 7d)` for fallback due_date in WhatsApp message, but actual `due_date` field is `service_start - 1d` | `cron_service.py:835` | Cosmetic — WhatsApp shows wrong date if fallback path taken. |
| Plan addition via invoice line item: `new_sp` does NOT inherit `op_plan.billing_date` | `operator.py:161-170` | New plan added to subscriber via invoice has `billing_date: None` always. Fine for new system, but legacy cron won't pick it up. |
| `_to_ymd` uses string comparison `new_expiry_str > old_expiry_str` for MAX | `operator.py:143` | Works because ISO YYYY-MM-DD is lexically ordered — but fragile. Use `date` objects. |

---

## 5. Suggested execution phases (for approval)

### Phase 1 — P0 bug fixes (safest, highest ROI)
1. B4 — unify service-period helper (foundation)
2. B6 — renewal start = old_expiry + 1d
3. B1 — dedup on expiry path
4. B2 — include past-expired window
5. B3 + B10 — auto pending→overdue transition; delete orphan `send_overdue_reminders`
6. B5 — code OR PRD fix (needs decision)
7. B7 — bump `auto_invoice_days_before` default
8. B8 — wallet deduction order
9. B9 — audit logs on auto/manual create
10. Backend tests + testing_agent_v3_fork

### Phase 2 — P1 enhancements
- E1 idempotency unique index
- E3 configurable due-offset
- E4 atomic flow w/ rollback
- E6 plan migration nightly job
- E8 subscriber auto-suspend rule

### Phase 3 — P2 refactor
- R1 split cron_service.py
- R2 + R3 DRY helpers
- R4 typed cron results
- R5 unit tests

---

## 6. Open questions for the user (answer before Phase 1)

| # | Question |
|---|---|
| Q1 | **B5**: On invoice edit, should expiry follow MAX rule (PRD) or always overwrite (current code)? |
| Q2 | **B6**: Renewal `service_start` = `old_expiry + 1d` is the safest fix. Confirm this is the intended behaviour. (Alternative: service_start = old_expiry, and reduce expiry by 1 day so periods are exclusive.) |
| Q3 | **B2**: Lookback window for past-expired plans — 30 days, 60 days, or configurable? |
| Q4 | **B7**: Should `auto_invoice_days_before` default change from 3 → 7 (or higher)? |
| Q5 | **E3**: Should due-date offset be a global platform setting, per-operator, or per-plan? |
| Q6 | **E8**: After how many days of plan expiry should subscriber be auto-suspended? Or never (operator handles manually)? |
| Q7 | Phase ordering — do all 3 phases, only P0, or only P0+P1? |
