# Agent Handoff - E-Bill Platform

**Last Updated:** 2026-03-21  
**Active Branch:** `V7.14-2`  
**Status:** Tasks 1-6 implemented in code; live verification still pending

---

## Current Snapshot

The branch now includes working code changes for the first six prioritized tasks:

- Task 1: Wallet accounting and billing integrity
- Task 2: Auth and OTP production hardening
- Task 3: Platform maintenance mode
- Task 4: Invoice branding and public invoice consistency
- Task 5: Multi-plan subscribers and multi-line invoices
- Task 6: Session timeout and strong role validation

Supporting env/bootstrap files were also aligned so the new auth provider keys exist consistently in:
- [.env](/d:/eBill/.env)
- [.env.example](/d:/eBill/.env.example)
- [setup.bat](/d:/eBill/setup.bat)
- [init-env.sh](/d:/eBill/docker/init-env.sh)
- [server.py](/d:/eBill/backend/server.py)

---

## What Was Implemented

### Task 1: Wallet Accounting and Billing Integrity

Primary files:
- [wallet.py](/d:/eBill/backend/routers/wallet.py)
- [operator.py](/d:/eBill/backend/routers/operator.py)
- [Wallet.jsx](/d:/eBill/frontend/src/pages/operator/Wallet.jsx)
- [Subscription.jsx](/d:/eBill/frontend/src/pages/operator/Subscription.jsx)
- [test_wallet_referral.py](/d:/eBill/backend/tests/test_wallet_referral.py)

Implemented behavior:
- Wallet top-up amount is now treated as wallet credit before GST.
- GST rate is read from platform settings and stored in the checkout order.
- Wallet verification credits only `base_amount`, not the GST-inclusive paid amount.
- Referral reward on wallet top-up now uses the credited amount.
- Stale subscription wallet-credit branch was removed from checkout verification.
- Operator UI copy now explains that GST is added at checkout and only the pre-GST amount is credited.

Important outcome:
- Subscription renewals no longer carry dead `wallet_credit_amount` logic under the simplified SaaS plan model.

### Task 2: Auth and OTP Production Hardening

Primary files:
- [auth.py](/d:/eBill/backend/routers/auth.py)
- [email_service.py](/d:/eBill/backend/services/email_service.py)
- [Login.jsx](/d:/eBill/frontend/src/pages/Login.jsx)
- [ForgotPassword.jsx](/d:/eBill/frontend/src/pages/ForgotPassword.jsx)
- [Register.jsx](/d:/eBill/frontend/src/pages/Register.jsx)
- [server.py](/d:/eBill/backend/server.py)

Implemented behavior:
- Removed hardcoded registration and recovery OTP bypass values.
- Added Resend-backed email OTP delivery service.
- Registration OTP flow now sends by email.
- Forgot-password email mode now sends real provider-backed OTP instead of fake success logging.
- Added resend cooldown and resend-count limits.
- Removed frontend demo credentials and test OTP hints.
- Registration and recovery UI copy now reflects real delivery behavior.

Security note:
- Forgot-password keeps a generic response for unknown emails and stores a non-usable recovery session to reduce account-enumeration leakage.

### Task 3: Platform Maintenance Mode

Primary files:
- [models.py](/d:/eBill/backend/models.py)
- [dependencies.py](/d:/eBill/backend/dependencies.py)
- [admin.py](/d:/eBill/backend/routers/admin.py)
- [auth.py](/d:/eBill/backend/routers/auth.py)
- [operator.py](/d:/eBill/backend/routers/operator.py)
- [wallet.py](/d:/eBill/backend/routers/wallet.py)
- [cron_service.py](/d:/eBill/backend/services/cron_service.py)
- [Layout.jsx](/d:/eBill/frontend/src/components/Layout.jsx)
- [Settings.jsx](/d:/eBill/frontend/src/pages/admin/Settings.jsx)

Implemented behavior:
- Admin can enable maintenance mode and set a platform-wide message from settings.
- Platform maintenance state now feeds a shared access-state helper used alongside operator read-only status.
- Operator dashboard, wallet, and subscription responses expose `maintenance_mode`, `maintenance_message`, and effective `is_read_only`.
- Wallet top-up and subscription checkout/renew flows are blocked during maintenance.
- Cron jobs and daily wallet automation now short-circuit while maintenance mode is enabled.
- Admin and operator layouts fetch `/auth/app-state` and show a visible maintenance banner.
- Wallet and subscription UI actions now disable during maintenance.

### Task 4: Invoice Branding and Public Invoice Consistency

Primary files:
- [invoice_view_service.py](/d:/eBill/backend/services/invoice_view_service.py)
- [public.py](/d:/eBill/backend/routers/public.py)
- [operator.py](/d:/eBill/backend/routers/operator.py)
- [pdf_service.py](/d:/eBill/backend/services/pdf_service.py)
- [PublicInvoice.jsx](/d:/eBill/frontend/src/pages/PublicInvoice.jsx)
- [Settings.jsx](/d:/eBill/frontend/src/pages/operator/Settings.jsx)
- [Invoices.jsx](/d:/eBill/frontend/src/pages/operator/Invoices.jsx)
- [PENDING_TESTS.md](/d:/eBill/memory/PENDING_TESTS.md)

Implemented behavior:
- Public invoice APIs now resolve invoices by `invoice_number` first and fall back to internal invoice id for backwards compatibility.
- Operator-created public invoice links now use `/invoice/{invoice_number}` instead of internal ids.
- Added shared invoice-view helpers so public invoice data and PDF data are built from the same merged invoice settings object.
- Invoice settings now include field-visibility controls and an operator logo upload endpoint.
- Public invoice page now shows operator branding/address and respects field visibility rules.
- PDF generation now pulls from the same branding data and supports logo rendering for uploaded or direct logo URLs.

---

## Pending Tests

### Completed local verification
- `python -m py_compile backend/routers/wallet.py backend/routers/operator.py`
- `python -m py_compile backend/routers/auth.py backend/services/email_service.py backend/server.py`
- `python -m py_compile backend/models.py backend/dependencies.py backend/routers/admin.py backend/routers/auth.py backend/routers/operator.py backend/routers/wallet.py backend/services/cron_service.py`
- `python -m py_compile backend/models.py backend/services/invoice_view_service.py backend/routers/public.py backend/routers/operator.py backend/services/pdf_service.py`
- `cmd /c npm run build` in [frontend](/d:/eBill/frontend) completed successfully with existing hook-dependency lint warnings only

### Still pending for Task 1
- Manual wallet top-up with Razorpay test/live keys:
  - confirm entered amount is treated as pre-GST credit
  - confirm paid amount includes GST
  - confirm wallet balance increases only by base amount
- Manual operator wallet transaction/history check after top-up
- Manual subscription renewal regression:
  - confirm no `subscription_credit` wallet transaction is created
- Optional targeted API verification:
  - `/api/operator/wallet/topup/create-order`
  - `/api/operator/wallet/topup/verify`

### Still pending for Task 2
- Live registration OTP send/verify with valid `RESEND_API_KEY` and `RESEND_FROM_EMAIL`
- Live forgot-password email OTP send/verify/reset flow
- WhatsApp recovery OTP regression check
- Automated tests for:
  - OTP expiry
  - resend cooldown/limit handling
  - invalid OTP attempt limit
  - provider failure handling

### Still pending for Task 3
- Manual admin maintenance toggle test:
  - enable maintenance mode
  - save custom message
  - confirm values persist on reload
- Manual operator verification:
  - wallet top-up is blocked
  - subscription renew is blocked
  - read-only pages still load
- Manual admin verification:
  - admin still has settings access while maintenance is on
  - maintenance banner appears in layout
- Manual cron verification:
  - scheduled jobs skip work and return maintenance reason
- Frontend smoke test:
  - `/auth/app-state` banner loads correctly without request loops
  - wallet/subscription buttons disable correctly during maintenance

### Still pending for Task 4
- Public invoice route verification:
  - open `/invoice/{invoice_number}`
  - confirm old `/invoice/{invoice_id}` links still resolve
- Invoice settings verification:
  - upload logo
  - save visibility toggles
  - reload settings and confirm persistence
- Public invoice verification:
  - operator address/logo display
  - payment status display
  - hidden fields actually disappear
- PDF verification:
  - branding and visibility settings match the public invoice data
  - downloaded filename uses invoice number
- Payment regression:
  - create-payment-order and verify-payment still work through invoice-number route

---

## Current Working Plan

The active source of truth remains [ROADMAP.md](/d:/eBill/memory/ROADMAP.md).

### Sprint 1
1. Wallet accounting and billing integrity
2. Auth and OTP production hardening
3. Platform maintenance mode

### Sprint 2
4. Invoice branding and public invoice consistency
5. Multi-plan subscribers and multi-line invoices
6. Session timeout and strong role validation

### Sprint 3
7. Global reminder control and IST scheduling
8. Admin wallet operations

### Sprint 4
9. Messaging and reporting polish
10. Payment receipts and confirmation delivery
11. Import/export enhancements

---

## Immediate Next Task

### Task 7: Global Reminder Control and IST Scheduling

Why this should come next:
- The backend cron-job logic was stabilized during Maintenance Mode integration.
- Moving to automated scheduling (IST offsets, reminders) establishes the automation core.
- The platform needs to reliably execute reminder delivery before scaling up messaging.

Likely starting files:
- `backend/services/cron_service.py`
- `backend/models.py`
- `frontend/src/pages/admin/Settings.jsx`

Expected implementation shape:
- Move reminder scheduling controls from the operator level to the global admin settings.
- Adjust all system timing from UTC behavior to India Standard Time (IST).
- Revise the cron workers to respect the global toggle.

---

## Risks To Keep In Mind

- Task 1 still needs real payment-provider verification before being treated as production-complete.
- Task 2 now depends on correct Resend env configuration; auth testing will fail without those keys.
- Task 3 needs browser and cron validation before being treated as rollout-ready.
- Task 4 needs real route/PDF/payment verification before being treated as customer-ready.
- There are still older historical docs/tests in the repo that reference legacy plan-credit behavior and may need cleanup later.
- Task 5 will likely require schema migration work, so avoid starting it without a migration/testing plan.

---

## Branch / Git State At Handoff

- Current working branch for delivery: `7.13-4`
- Source implementation branch before delivery branch creation: `V7.14`
- Latest code in progress includes:
  - wallet/top-up accounting changes
  - auth/OTP hardening
  - env/bootstrap alignment
  - maintenance mode across admin settings, API access state, cron guards, and layout banners
  - invoice-number public routing, invoice branding/visibility controls, and operator logo upload

If continuing from here, start Task 5 after this branch is committed, pushed, and the pending Task 4 checks are reviewed.
