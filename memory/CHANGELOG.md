# E-Bill Platform - CHANGELOG

## 2026-03-23

### Branches
- Created and pushed `V7.14-6` from `V7.14-5`
- Created, implemented, and pushed `V7.14-7`
- Documentation alignment prepared on `V7.14-8`

### V7.14-7: Single Session, Recovery, and Invoice Control

#### Auth / Session Management
- Added single-session enforcement at the backend level using a per-user active session id.
- New login replaces the user's previous active session, which forces the old device/session to expire.
- Password change and password reset now rotate the active session id and invalidate older logins.
- Frontend auth bootstrap now re-checks session validity on window focus and periodic interval so old sessions close automatically in the UI.
- Admin return-from-impersonation now issues a fresh admin session id.

#### Password Recovery
- Removed WhatsApp OTP as a password recovery delivery method.
- Forgot-password flow is now email-only in both API and frontend UI.
- Recovery resend flow now always sends by email.

#### Invoices
- Added backend support to edit invoices while they are still in `pending` status.
- Added frontend edit flow for pending invoices.
- Operators can no longer cancel paid invoices.
- Admin can still cancel a paid invoice through the invoice status API.
- Manual mark-as-paid flow now requires payment mode and payment date.
- Stored payment modes now include:
  - `cash`
  - `own_upi`
  - `bank_transfer`
  - `cheque`
- Public online payment verification now stores `payment_mode = online`.

#### Validation
- `python -m py_compile` passed for touched backend modules.
- `npm run build` passed in `frontend/`.
- Existing frontend ESLint hook-dependency warnings remain, but they are pre-existing and non-blocking for build output.

## 2026-03-21

### Sprint 1 Progress: Wallet + Auth Hardening in Code

#### Task 1: Wallet Accounting and Billing Integrity
- Wallet top-up now treats the entered amount as wallet credit before GST.
- Top-up checkout orders now store GST breakup fields: `base_amount`, `gst_rate`, `gst_amount`, `exact_total`, `rounding_diff`, `total_amount`.
- Wallet verification credits only the pre-GST wallet amount, not the total amount paid.
- Referral reward on wallet top-up now uses the credited amount basis.
- Removed stale subscription wallet-credit logic from SaaS checkout verification to align with simplified flat subscription pricing.
- Updated operator wallet/top-up UI copy to explain pre-GST crediting and paid-vs-credited totals.

#### Task 2: Auth and OTP Production Hardening
- Removed hardcoded registration and password-recovery OTP bypasses.
- Added Resend-backed email OTP delivery via `backend/services/email_service.py`.
- Registration OTP flow now sends via email.
- Forgot-password recovery email flow now uses real provider-backed delivery.
- Added resend cooldown and resend-count limits for registration and recovery OTP flows.
- Removed login demo-credentials panel and forgot-password test OTP hints from the frontend.

#### Task 3: Platform Maintenance Mode
- Added `maintenance_mode` and `maintenance_message` to platform global settings.
- Added shared maintenance/access-state helpers in backend dependencies.
- Added `/auth/app-state` for layout-level maintenance/read-only state loading.
- Operator dashboard, wallet, and subscription responses now expose maintenance fields.
- Wallet top-up and subscription checkout/renew flows now block during maintenance.
- Cron automation and daily wallet checks now short-circuit with a maintenance skip reason.
- Admin settings UI now includes a maintenance toggle and custom message field.
- Admin and operator layouts now show maintenance banners, and operator action buttons are disabled while maintenance is active.

#### Task 4: Invoice Branding and Public Invoice Consistency
- Public invoice endpoints now resolve by `invoice_number` first with legacy internal-id fallback.
- Operator-created public invoice links now use `/invoice/{invoice_number}`.
- Added shared invoice-view helpers so public invoice payloads and PDF payloads come from the same merged invoice settings object.
- Invoice settings now support field-visibility toggles and operator logo upload.
- Public invoice page now shows operator logo/address and respects selected visibility rules.
- PDF generation now uses the same branding data and includes logo rendering when available.

#### Task 5: Multi-Plan Subscribers and Multi-Line Invoices
- Subscriber model updated to support multiple active plans via a plans list.
- Invoice model updated to support multiple `line_items` per invoice.
- Subscriber API now handles multiple plan objects with individual billing dates and discounts.
- Invoice API accepts multiple line items and calculates aggregate totals.
- Cron billing logic groups plans with identical billing dates into single combined multi-line invoices.

#### Task 8: Admin Wallet Operations
- Added admin wallet credit, debit, and suspend endpoints.
- Added wallet adjustment UI in admin wallet management.
- Debits below threshold auto-suspend; restorative credits can auto-unsuspend.

## 2026-03-22

### V7.14-4 / V7.14-5 Fixes
- Fixed invoice add-row crash and create-invoice calendar popovers.
- Fixed invoice logo visibility in PDF and logo path resolution.
- Updated SaaS plan GST text to exclusive-of-GST wording.
- Removed Landing Page link from admin sidebar.
- Added global email API settings in admin panel.
- Removed Wallet Top-up tab from operator Subscription page.
- Improved public invoice printing and paid-invoice receipt display.
- Fixed public invoice loading for newer multi-line invoices.
