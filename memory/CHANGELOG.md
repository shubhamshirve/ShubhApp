# E-Bill Platform - CHANGELOG

## 2026-03-24

### V7.14-11 Follow-Up: Settings Refresh and Backup List Sync

#### Fixes
- Cron timing settings now persist visually after save and show the stored value on refresh.
- Email API settings now reload correctly after save and page refresh.
- Auto-backup entries now show up in the backup list after cron completion.

#### Validation
- Manual settings refresh confirmed for cron and email pages.
- Backup list refresh now reflects the latest scheduled backup run.

### V7.14-11: SEO Metadata, Link Previews, and PWA Installability

#### Release Workflow
- Synced documentation on `V7.14-10`, pushed that branch, then created `V7.14-11` for the metadata and installability update.

#### Frontend Metadata
- Enriched `frontend/public/index.html` with:
  - canonical URL
  - improved description and keyword metadata
  - Open Graph tags
  - Twitter card tags
  - Apple/mobile web app capability tags
  - theme and tile color metadata
- Added JSON-LD schema for:
  - `Organization`
  - `SoftwareApplication`

#### PWA / Install Support
- Added `frontend/public/manifest.json`.
- Added install icons:
  - `frontend/public/icon-192.png`
  - `frontend/public/icon-512.png`
  - `frontend/public/apple-touch-icon.png`
- Added `frontend/public/sw.js` for lightweight caching and installability support.
- Registered the service worker in production from `frontend/src/index.js`.
- This enables supported browsers/devices to show add-to-home-screen or install UI when deployed over HTTPS.

#### Validation
- `npm run build` passed in `frontend/`.
- Existing frontend `react-hooks/exhaustive-deps` warnings remain, but build output succeeded.

### V7.14-10: App Title, Email Fallback, and Configurable Cron Timings

#### Release Workflow
- Synced all memory/readme files on `V7.14-9` before starting feature work, then created `V7.14-10` for this delivery batch.

#### Frontend
- Updated the browser/app title to `E-Bill | Invoice Automation Software`.
- Expanded admin settings UI with editable cron timing controls for:
  - auto backup
  - expiry checks
  - invoice generation
  - wallet checks
  - reminder processing
- Updated backup settings UI copy to reflect configured IST timing instead of stale fixed UTC wording.
- Expanded admin email settings UI to support SMTP fallback fields and TLS toggle.

#### Email Delivery
- Added `FallbackEmailService` that tries Resend first and automatically falls back to SMTP on failure.
- Added SMTP transport support using Python `smtplib`.
- Added DB-backed SMTP configuration support in admin email settings.
- Allowed email delivery to be configured via Resend, SMTP, or both.
- Added SMTP environment keys to generated/default env templates.

#### Scheduler / Cron Controls
- Added reusable cron schedule normalization helpers.
- Backend scheduler startup now reads cron times from platform settings, falling back to defaults when unset.
- Saving admin platform settings now reschedules APScheduler jobs immediately without restart.
- Daily and manual invoice-generation flows now respect the configured `auto_invoice_days_before` setting instead of a hardcoded value.

#### Validation
- `python -m py_compile backend\\models.py backend\\routers\\admin.py backend\\services\\cron_service.py backend\\services\\email_service.py backend\\services\\scheduler_settings.py backend\\server.py` passed.
- `npm run build` passed in `frontend/`.
- Existing frontend `react-hooks/exhaustive-deps` warnings remain, but build output succeeded.

## 2026-03-23

### V7.14-9: VPS Cron Scheduler Reliability Fix

#### Scheduler / VPS Fix
- Fixed backend APScheduler registration in `backend/server.py`.
- Replaced lambda-based manual `asyncio.create_task(...)` wrappers with direct async job registration.
- Added scheduler event listeners for job success/failure logging.
- Added startup logging for each registered job and next run time.
- Added `coalesce=True` and `misfire_grace_time=3600` to the scheduled jobs to make delayed VPS/container starts more resilient.

#### Why this matters
- The old scheduler setup could fail silently on VPS/container environments because the lambda wrapper might run outside the expected event-loop context.
- The new setup is safer for `AsyncIOScheduler` and gives clearer backend logs when jobs are registered or fail.

#### Validation
- `python -m py_compile backend/server.py backend/services/cron_service.py` passed.

### Branches
- Created and pushed `V7.14-6` from `V7.14-5`
- Created, implemented, and pushed `V7.14-7`
- Documentation alignment prepared on `V7.14-8`
- Created and pushed `V7.14-9` for the VPS cron fix
- Created and pushed `V7.14-10` for title, email fallback, and configurable cron timings
- Created and pushed `V7.14-11` for SEO metadata and installable web app support

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
