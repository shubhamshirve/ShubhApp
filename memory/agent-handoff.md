# Agent Handoff - E-Bill Platform

**Last Updated:** 2026-03-21  
**Active Branch:** `7.13-2`  
**Status:** Task 1 and Task 2 implemented in code; live verification and Task 3 pending

---

## Current Snapshot

The branch now includes working code changes for the first two Sprint 1 items:

- Task 1: Wallet accounting and billing integrity
- Task 2: Auth and OTP production hardening

Supporting env/bootstrap files were also aligned so the new auth provider keys exist consistently in:
- [.env](/d:/eBill/.env)
- [.env.example](/d:/eBill/.env.example)
- [setup.bat](/d:/eBill/setup.bat)
- [init-env.sh](/d:/eBill/docker/init-env.sh)
- [server.py](/d:/eBill/backend/server.py)

Task 3, maintenance mode, has not started yet.

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

---

## Pending Tests

### Completed local verification
- `python -m py_compile backend/routers/wallet.py backend/routers/operator.py`
- `python -m py_compile backend/routers/auth.py backend/services/email_service.py backend/server.py`

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

### Task 3: Platform Maintenance Mode

Why this should come next:
- Tasks 1 and 2 are already patched through the codebase.
- Maintenance mode is the next Sprint 1 blocker and affects cron, write-guards, and frontend state.
- It should land before bigger schema/reporting work.

Likely starting files:
- [admin.py](/d:/eBill/backend/routers/admin.py)
- [dependencies.py](/d:/eBill/backend/dependencies.py)
- [server.py](/d:/eBill/backend/server.py)
- [cron_service.py](/d:/eBill/backend/services/cron_service.py)
- frontend layout/app shell files for global read-only popup/banner

Expected implementation shape:
- add admin-controlled maintenance flag in platform settings
- stop scheduled automation while enabled
- force non-admin write paths into read-only mode
- surface a global maintenance message in the frontend

---

## Risks To Keep In Mind

- Task 1 still needs real payment-provider verification before being treated as production-complete.
- Task 2 now depends on correct Resend env configuration; auth testing will fail without those keys.
- There are still older historical docs/tests in the repo that reference legacy plan-credit behavior and may need cleanup later.
- Maintenance mode will touch both API write guards and cron startup/runtime behavior, so avoid partial rollout.

---

## Branch / Git State At Handoff

- Current working branch for delivery: `7.13-2`
- Source implementation branch before delivery branch creation: `V7.14`
- Latest code in progress includes:
  - wallet/top-up accounting changes
  - auth/OTP hardening
  - env/bootstrap alignment
  - pending memory/changelog sync

If continuing from here, start Task 3 after the requested git push is complete.
