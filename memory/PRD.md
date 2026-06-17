# E-Bill — Product Requirements Document
<!-- Current Version: V9.12 -->

## Product Summary

Multi-tenant SaaS billing platform for ISP, broadband, and cable operators. Supports platform admins, business operators, and staff with role-based access.

## Roles

| Role | Key Capabilities |
|------|----------------|
| **Admin** | Manage operators, SaaS plans, addons, wallets, payment gateways, reports, impersonation, platform settings |
| **Operator** | Manage subscribers, plans, invoices, staff, settings, subscription, reports |
| **Staff** | Operator-side access with no destructive delete permissions |

## Tech Stack

- **Frontend:** React, React Router, Axios, Tailwind, shadcn/ui (Radix)
- **Backend:** FastAPI, Motor/PyMongo, APScheduler
- **Auth:** JWT (single active session per user), admin impersonation
- **Infra:** Docker Compose, Caddy, MongoDB 4.4

## Core Business Rules

- One active session per user — new login invalidates previous token
- Pending invoices are editable; paid invoices protected from operator cancellation
- Password recovery via email OTP only (WhatsApp discontinued)
- Public online payments store mode as `"online"`
- Subscriber plans stored as embedded array (up to 5 per subscriber)
- Subscriber `plan_expiry_date` syncs from invoice **creation/update** (not payment); hybrid rule: only move forward — `new_expiry = max(old_plan_expiry_date, line_item.service_end_date)`. New plans on an invoice are auto-added to `subscriber.plans[]`. Custom line items are skipped.
- Bulk subscriber CSV: one row per subscriber, plan columns suffixed `_1` through `_5`
- Wallet crediting is GST-exclusive
- Operator payment gateway keys enforced on public payments (no platform fallback)
- Staff cannot perform destructive deletes

## Key Workflows

1. **Subscriber lifecycle:** Create (with 1–5 plans) → Invoice auto-generated → Reminder sent → Expiry check → Renewal
2. **Payment flow:** Invoice generated → Payment link shared → Payment via Razorpay → Status updated → Receipt (planned)
3. **Bulk upload:** Download sample CSV → Fill data → Upload → Background job → Poll for result
4. **Admin impersonation:** Admin selects operator → Assumes operator session → Return to admin

## Scheduled Automation (IST, admin-configurable)

| Job | Default Time |
|-----|-------------|
| Auto Backup | 03:00 |
| Expiry Check | 00:05 |
| Invoice Generation | 08:00 |
| Reminder Processing | 10:00 |
| Wallet Balance Check | 09:00 |

## Current Gaps

- Payment receipt generation and delivery
- Email announcement broadcasts
- GST reconciliation reporting
- WhatsApp Business API notifications (infrastructure ready, not wired to UI)

---

## Pending: Invoice / Auto-Invoice / Expiry Logic Review (Feb 2026)

**Full analysis lives in `/app/memory/INVOICE_LOGIC_ANALYSIS.md`** — that document contains code references, current behaviour, proposed fixes, and open questions for the user. The next agent MUST read it before touching invoice/cron/expiry code.

### P0 — Critical bugs identified (awaiting user approval)
- **B1**: Duplicate auto-invoices possible on expiry-based path (no dedup) → `cron_service.py:91-167`
- **B2**: Past-expired plans (expiry < today) are silently skipped by cron → `cron_service.py:93-101`
- **B3**: Pending → Overdue invoice status transition is never automatic → `cron_service.py:868`
- **B4**: Three inconsistent definitions of "monthly" length (calendar / 30d / 28d) across `operator.py::_calc_plan_expiry`, `cron_service.py::_create_first_invoice`, `cron_service.py::_check_*`
- **B5**: `update_invoice` violates PRD MAX-rule (uses `force=True`) → `operator.py:2204`
- **B6**: Renewal `service_start = old_expiry` overlaps 1 day → `cron_service.py:419-438`
- **B7**: `due_date = service_start - 1d` makes pre-due reminders (7d/5d slots) impossible to fire
- **B8**: Invoice inserted before wallet deducted — race-condition leaves invoice without billing
- **B9**: Auto-invoices (cron + first invoice + manual create) skip audit logs
- **B10**: Orphan `send_overdue_reminders` not wired to scheduler — dead code

### P1 — Enhancements queued
- **E1**: Unique index for invoice idempotency `(operator_id, subscriber_id, plan_id, period_start)`
- **E2**: Expose `auto_invoice_days_before` per operator
- **E3**: Configurable due-date offset (global / per-operator / per-plan — needs decision)
- **E4**: Atomic invoice+wallet+sync with explicit rollback (or Mongo transaction)
- **E5**: Audit logs on every invoice mutation (create included)
- **E6**: Nightly migration job for plans with `billing_date` but no `plan_expiry_date`
- **E7**: Mark pending→overdue *before* iterating in reminder cron
- **E8**: Auto-suspend subscriber plan after N days of expiry (N TBD)

### P2 — Refactor queued
- **R1**: Split `cron_service.py` (1530 lines) → `services/cron/{invoices,reminders,expiry,wallet,reports,common}.py`
- **R2**: DRY line-item builder — single `invoice_helpers.build_line_item()` used by all 3 invoice paths
- **R3**: DRY WhatsApp send pattern (currently duplicated 6+ times)
- **R4**: Pydantic models for cron results
- **R5**: Add `/app/backend/tests/test_cron_invoices.py`, `test_invoice_sync.py`, `test_invoice_helpers.py`

### Open questions for user (must answer before Phase 1)
1. **B5 resolution** — fix code to MAX rule, or update PRD to say "edit overrides"?
2. **B6 convention** — renewal `service_start = old_expiry + 1d` (inclusive end) vs `service_start = old_expiry` with end reduced (exclusive end)?
3. **B2 lookback window** — 30d / 60d / configurable?
4. **B7** — bump `auto_invoice_days_before` default from 3 → 7+?
5. **E3 scope** — due-offset global, per-operator, or per-plan?
6. **E8** — auto-suspend after N days of expiry (N=?), or leave manual?
7. **Phase scope** — all 3 phases, only P0, or P0+P1?
