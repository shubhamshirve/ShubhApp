# Agent Handoff - E-Bill Platform

**Last Updated:** 2026-03-24  
**Active Branch:** `V7.14-10`
**Latest Feature Branch:** `V7.14-10`

---

## Current Snapshot

The codebase now includes:

- wallet accounting corrections
- email-backed OTP hardening
- maintenance mode
- invoice branding and invoice-number public links
- multi-plan subscribers and multi-line invoices
- global reminder controls with IST scheduling
- admin wallet actions
- single active session enforcement
- email-only password recovery OTP
- pending invoice edit support
- payment mode and payment date confirmation when operators manually mark invoices paid
- VPS cron scheduler reliability fix with direct async job registration and startup/job logging
- app title update to `E-Bill | Invoice Automation Software`
- Resend email delivery with SMTP fallback
- admin-configurable cron timings with live scheduler reschedule

---

## Most Recent Delivery

### Branch Flow
- `V7.14-6` was created and pushed from `V7.14-5`
- `V7.14-7` was created and pushed from `V7.14-6`
- `V7.14-8` is the documentation update branch based on `V7.14-7`
- `V7.14-9` is the scheduler reliability fix branch based on `V7.14-8`
- `V7.14-10` is the title, email fallback, and cron-settings branch based on `V7.14-9`

### V7.14-10 Changes

Primary files:
- [frontend/public/index.html](/d:/eBill/frontend/public/index.html)
- [frontend/src/pages/admin/Settings.jsx](/d:/eBill/frontend/src/pages/admin/Settings.jsx)
- [backend/services/email_service.py](/d:/eBill/backend/services/email_service.py)
- [backend/services/scheduler_settings.py](/d:/eBill/backend/services/scheduler_settings.py)
- [backend/routers/admin.py](/d:/eBill/backend/routers/admin.py)
- [backend/server.py](/d:/eBill/backend/server.py)
- [backend/server.py](/d:/eBill/backend/server.py)

Implemented behavior:
- Updated the browser title to the requested product name.
- Added Resend-first email delivery with SMTP fallback support.
- Added SMTP credentials to admin settings and env templates.
- Added admin-configurable cron timing fields and live job rescheduling on save.
- Updated invoice-generation cron/manual triggers to use the configured advance-day value.

---

## Validation Completed Locally

- `python -m py_compile backend\models.py backend\routers\admin.py backend\services\cron_service.py backend\services\email_service.py backend\services\scheduler_settings.py backend\server.py`
- `npm run build` in `frontend/`

Build result:
- backend compile check succeeded

---

## Outstanding Validation

See [PENDING_TESTS.md](/d:/eBill/memory/PENDING_TESTS.md) for the live list.

Highest-value remaining checks:
- deploy `V7.14-10` to VPS and verify scheduler registration logs on startup
- verify cron-setting changes update next-run times cleanly on the running VPS
- verify Resend failure falls back to SMTP with real credentials
- verify cron jobs actually fire on VPS

---

## Current Documentation State

The following files were refreshed on `V7.14-10`:
- [README.md](/d:/eBill/README.md)
- [memory/CHANGELOG.md](/d:/eBill/memory/CHANGELOG.md)
- [memory/ROADMAP.md](/d:/eBill/memory/ROADMAP.md)
- [memory/PRD.md](/d:/eBill/memory/PRD.md)
- [memory/PENDING_TESTS.md](/d:/eBill/memory/PENDING_TESTS.md)
- [memory/agent-handoff.md](/d:/eBill/memory/agent-handoff.md)
- [frontend/README.md](/d:/eBill/frontend/README.md)

---

## Recommended Next Work

1. Deploy and verify `V7.14-10` on VPS.
2. Build payment receipt generation and delivery.
3. Expand payment confirmations through email/WhatsApp.
4. Continue messaging and reporting polish.

---

## Git State At Handoff

- Current branch: `V7.14-10`
- Feature baseline under docs branch: `V7.14-10`
