# E-Bill Platform - CHANGELOG

## 2026-03-21

### Sprint 1 Progress: Wallet + Auth Hardening in Code

#### Task 1: Wallet Accounting and Billing Integrity (implemented, pending live verification)
- Wallet top-up now treats the entered amount as wallet credit before GST.
- Top-up checkout orders now store GST breakup fields: `base_amount`, `gst_rate`, `gst_amount`, `exact_total`, `rounding_diff`, `total_amount`.
- Wallet verification credits only the pre-GST wallet amount, not the total amount paid.
- Referral reward on wallet top-up now uses the credited amount basis.
- Removed stale subscription wallet-credit logic from SaaS checkout verification to align with simplified flat subscription pricing.
- Updated operator wallet/top-up UI copy to explain pre-GST crediting and paid-vs-credited totals.

#### Task 2: Auth and OTP Production Hardening (implemented, pending provider verification)
- Removed hardcoded registration and password-recovery OTP bypasses.
- Added Resend-backed email OTP delivery via new `backend/services/email_service.py`.
- Registration OTP flow now sends via email.
- Forgot-password email flow now uses real provider-backed email delivery instead of fake success logging.
- Added resend cooldown and resend-count limits for registration and recovery OTP flows.
- Removed login demo-credentials panel and forgot-password test OTP hints from the frontend.
- Updated registration OTP messaging to reflect email delivery.

#### Env / Bootstrap Sync
- Added `RESEND_API_KEY` and `RESEND_FROM_EMAIL` to:
  - root `.env`
  - `.env.example`
  - `setup.bat`
  - `docker/init-env.sh`
  - backend `.env` auto-bootstrap in `server.py`

#### Tests still pending
- Manual Razorpay top-up verification for credited amount vs paid amount
- Manual subscription renewal regression check for wallet transactions
- Live Resend registration OTP test
- Live Resend forgot-password OTP test
- Additional automated OTP edge-case tests: expiry, resend throttling, invalid attempts, provider failure handling

## 2025-07-18

### Batch 8: Codebase Cleanup & Removal
- Settlement system removed from frontend, backend, and cron.
- Platform fee logic removed from plan models and related endpoints.
- Dead files deleted, including legacy landing and KYC test files.
- Dead constants and landing-page route cleanup completed.

## 2026-03-18

### Task 1: Referral + Wallet System
- Added `operator_wallets` and `wallet_transactions` collections.
- Operators receive unique referral codes on registration.
- Referral discounts and rewards were added to initial wallet flow.
- Wallet deduction, reminder, suspension, top-up, and admin wallet views were introduced.

### Task 2: Basic/Pro Plan Revamp
- Added Basic/Pro plan revamp with legacy plan-type pricing model at that time.
- Checkout and admin plan creation were updated around that older pricing structure.

### Task 5: Support Ticket System
- Added threaded support ticket flows for operator/staff/admin.
- Added `/operator/support` and `/admin/support`.

### Task 7: Remove Landing Page
- Root `/` now redirects to `/login`.
- Admin landing-page builder remains available for future use.
