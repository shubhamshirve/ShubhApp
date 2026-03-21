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

### Sprint 1 Progress: Maintenance Mode in Code

#### Task 3: Platform Maintenance Mode (implemented, pending live verification)
- Added `maintenance_mode` and `maintenance_message` to platform global settings.
- Added shared maintenance/access-state helpers in backend dependencies so effective read-only now includes platform maintenance.
- Added `/auth/app-state` for layout-level maintenance/read-only state loading.
- Operator dashboard, wallet, and subscription responses now expose maintenance fields.
- Wallet top-up and subscription checkout/renew flows now block during maintenance.
- Cron automation and daily wallet checks now short-circuit with a maintenance skip reason.
- Admin settings UI now includes a maintenance toggle and custom message field.
- Admin and operator layouts now show maintenance banners, and operator action buttons are disabled while maintenance is active.

#### Task 3 tests still pending
- Manual admin maintenance toggle and persistence verification
- Manual operator/staff read-only behavior verification
- Manual admin layout banner verification
- Manual cron skip verification while maintenance is enabled
- Frontend runtime smoke test for `/auth/app-state` and disabled-action states

### Invoice Branding and Public Invoice Consistency in Code

#### Task 4: Invoice Branding and Public Invoice Consistency (implemented, pending live verification)
- Public invoice endpoints now resolve by `invoice_number` first with legacy internal-id fallback.
- Operator-created public invoice links now use `/invoice/{invoice_number}`.
- Added shared invoice-view helpers so public invoice payloads and PDF payloads come from the same merged invoice settings object.
- Invoice settings now support field-visibility toggles and operator logo upload.
- Public invoice page now shows operator logo/address and respects selected visibility rules.
- PDF generation now uses the same branding data and includes logo rendering when available.
- Added a dedicated pending-test tracker in [PENDING_TESTS.md](/d:/eBill/memory/PENDING_TESTS.md).

#### Task 4 tests still pending
- Manual invoice-number URL verification with legacy link fallback
- Manual operator logo upload and visibility-toggle persistence verification
- Manual public invoice verification for branding, hidden fields, and payment status
- Manual PDF verification for branding parity and invoice-number filename
- Public payment route regression check after invoice-number routing change

### Multi-Plan Subscribers and Multi-Line Invoices in Code

#### Task 5: Multi-Plan Subscribers and Multi-Line Invoices (implemented and verified)
- Subscriber model updated to support multiple active plans via `plans` list.
- Invoice model updated to support multiple `line_items` per invoice.
- Subscriber API (POST/PUT) now handles multiple plan objects with individual billing dates and discounts.
- Invoice API (POST) now accepts multiple line items and calculates aggregate totals (base, discount, tax, final).
- Cron billing logic (`generate_upcoming_invoices`) now groups plans with identical billing dates for a subscriber into single combined multi-line invoices.
- Updated `OperatorSubscribers` UI to allow adding/editing multiple plan rows.
- Updated `OperatorInvoices` UI to allow selecting multiple plans when creating invoices manually.
- Updated `PublicInvoice` and `PDF Service` to render multi-line tables and aggregated totals.
- Created data migration script `backend/migrations/task5_multi_plan.py` for legacy schema conversion.
- Verified with automated API tests in `backend/tests/test_task5_multi_plan.py`.

### Admin Wallet Operations in Code

#### Task 8: Admin Wallet Operations (implemented, pending live verification)
- Backend: Added `WalletAdjustmentRequest` and `WalletSuspendRequest` models. Added three endpoints: `POST /admin/wallets/{operator_id}/credit`, `debit`, and `suspend`.
- Frontend: Upgraded `Wallets.jsx` with Credit/Debit/Suspend buttons, a shared adjustment modal, a suspend confirmation dialog, and full list/transaction refreshing after actions.
- Behavior: Debits > balance fail. Debits that drop balance < 100 auto-suspend. Credits that restore balance >= 100 auto-unsuspend.
- Validation: All actions capture reasons and write full audit logs.
- Tests: Added test suite in `backend/tests/test_task8_admin_wallet.py`.

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

## 2026-03-22

### Bug Fixes & Feature Additions (Branch V7.14-4)

#### Fix 1: Invoice Add-Row Crash & Calendar Popover
- Missing `Trash2` lucide icon import in `Invoices.jsx` was crashing React when a second line item was added.
- Added `modal={true}` to all three `<Popover>` date pickers (due date, service start, service end) inside the invoice Dialog so they no longer close immediately.
- Fixed `Select` value to use `undefined` instead of `""` for empty plan_id so the placeholder renders.

#### Fix 2 & 3: PDF Invoice Logo Visibility
- `pdf_service.py` `_build_logo()` now has a dedicated `/uploads/` path branch.
- Resolves logo filename against both the local dev path (`../../frontend/public/uploads/`) and the Docker path (`/app/frontend/public/uploads/`) with clear fallback.

#### Fix 4: SaaS Plans GST Text (Admin Panel)
- `SaaSPlans.jsx` header subtitle changed from "GST inclusive" → "exclusive of GST — 18% GST will be added at checkout".
- Per-plan card badge changed from "GST Inclusive" → "Excl. GST".
- Form helper text updated to reflect exclusive pricing.

#### Fix 5: Remove Landing Page from Admin Navbar
- Removed `Landing Page` link entry from `AdminSidebar` in `Layout.jsx`.
- Removed unused `Layout` icon import.

#### Feature: Global Email API Keys in Admin Panel
- Added `GET /admin/email-settings` — returns configured Resend from-email and masked API key preview.
- Added `PUT /admin/email-settings` — stores `resend_api_key` + `resend_from_email` in `global_settings` collection in MongoDB.
- Added `get_email_service_async()` to `email_service.py` — checks DB first, falls back to OS env vars.
- Added `Email API` tab to Admin → Settings with:
  - Masked Resend API Key field with show/hide toggle.
  - From Email input.
  - Green "configured" badge when a key exists.
  - Link to resend.com/api-keys.

#### Subscription GST & Wallet Credit (Previous Session)
- SaaS subscription checkout now adds 18% GST to the plan price (exclusive, not inclusive).
- On successful payment verification, the pre-GST plan amount is credited to the operator wallet.
- Operator Settings page crash bug fixed — removed leftover Reminders tab state/JSX that caused crashes during admin impersonation.

#### Fix 6: Subscription Wallet Top-up Removal
- Removed the "Wallet Top-up" tab and UI block from the `Subscription.jsx` operator screen to streamline flows.

#### Fix 7: PDF Invoice Download (Client-Side Print Replacement)
- Replaced backend ReportLab PDF generation with a `window.print()` implementation via the `PublicInvoice.jsx` layout.
- This ensures downloaded PDFs exactly match the beautiful Tailwind CSS layout of the modern public invoice.
- Added `@media print:hidden` CSS utility classes to hide navigation/header bars and "Pay Now" actions on the printed PDF.
- Added `payment_id` and `paid_at` data to `public.py` so the "Payment Received" confirmation block reliably displays the Date Paid and Transaction Ref on the printed receipt acting as proof of payment.

