# E-Bill Platform — CHANGELOG

## 2026-04-19

### V8.23: GST Control Settings for SAAS Plans & Wallet Topups

#### New Feature: Configurable GST Charges
- **Admin Settings:** Added toggle controls to enable/disable GST charges independently for:
  - SAAS Plan subscriptions (purchases and renewals)
  - Wallet topups
- **Default Behavior:** Both GST toggles enabled by default (maintains existing behavior)
- **Backend Logic:** Checkout and topup endpoints now check GST enablement settings before calculating GST
- **Flexibility:** Admin can disable GST for specific transaction types while keeping it enabled for others

**Changes:**
- `frontend/src/pages/admin/Settings.jsx`: Added two Switch controls under Platform Settings
  - "Apply GST on SAAS Plans" toggle
  - "Apply GST on Wallet Topups" toggle
- `backend/routers/wallet.py`: Wallet topup endpoint checks `gst_enabled_on_wallet_topup` setting
- `backend/routers/operator.py`: Checkout endpoint checks `gst_enabled_on_saas_plans` setting
- Both settings stored in `global_settings.platform` document

**Use Cases:**
- Disable GST for international operators
- Promotional periods without GST
- Regional tax compliance variations
- Testing without tax calculations

---

### V8.22: Critical Security Enhancement - HttpOnly Cookie Authentication

#### 🔒 Security Fix: localStorage to HttpOnly Cookies Migration
- **CRITICAL SECURITY UPGRADE:** Migrated authentication from localStorage to secure httpOnly cookies
- **XSS Protection:** Auth tokens no longer accessible via JavaScript, preventing XSS token theft
- **CSRF Protection:** Implemented SameSite=lax cookie policy
- **Secure Transport:** Cookies marked as secure (HTTPS-only)

**Backend Changes:**
- `backend/routers/auth.py`:
  - `/auth/login` endpoint now sets httpOnly cookie instead of returning token in body
  - `/auth/verify-otp` (registration) endpoint sets httpOnly cookie
  - Added `/auth/logout` endpoint to properly clear cookies
  - Cookie settings: httpOnly, secure, samesite=lax, 24-hour expiry
- `backend/dependencies.py`:
  - `get_current_user()` now reads from cookie first, fallback to Authorization header
  - Maintains backward compatibility during migration period

**Frontend Changes:**
- `frontend/src/App.js`:
  - Removed all `localStorage.getItem("token")` and `localStorage.setItem("token")` calls
  - Removed token state management
  - All axios requests now use `withCredentials: true` to send cookies
  - Login/register flows updated to work with cookies
  - Logout now calls `/auth/logout` endpoint to clear server-side session

**Security Improvements:**
- ✅ Tokens no longer stored in localStorage (XSS-proof)
- ✅ HttpOnly flag prevents JavaScript access to auth tokens
- ✅ Secure flag ensures cookies only sent over HTTPS
- ✅ SameSite=lax provides CSRF protection
- ✅ Server-side session invalidation on logout

**Migration Notes:**
- Existing users will be logged out once (cookies replace localStorage)
- No action required from end users
- Backend maintains compatibility with Authorization header for API clients

---

### V8.21: Wallet Suspension Threshold Adjustment

#### UI Standardization: Date Pickers
- **Standardized date pickers** across the entire application
- Replaced custom PopoverDatePicker (calendar popup) with standard HTML5 `<Input type="date">`
- **Affected locations:**
  - Operator Invoices page: Due date, service start/end dates, payment confirmation date
  - Operator Reports page: Start date and end date filters
  - Now matches the date picker style used in Admin Payment Reports page
- **Benefits:** Consistent UX, better mobile support, native browser date picker
- **Files:** `frontend/src/pages/operator/Invoices.jsx`, `frontend/src/pages/operator/Reports.jsx`

#### Enhancement: Search Bar on Plans Page
- **Added search functionality** to Plans page
- Search by plan name, description, or price
- Real-time filtering as you type
- Shows appropriate empty state for no results
- **File:** `frontend/src/pages/operator/Plans.jsx`

#### Enhancement: Audit Logs Pagination
- **Reduced pagination limit** from 50 to 20 items per page
- Better performance and faster load times
- **File:** `frontend/src/pages/admin/AuditLogs.jsx`

#### Enhancement: Payment Mode on Invoice Receipt
- **Added payment mode** display to public invoice receipts
- Shows in "Payment Details" section for paid invoices
- **Display format:** Capitalizes and formats payment mode (e.g., "Bank Transfer", "Cash", "Own Upi")
- **Visible only when:** Invoice status is "paid" and payment_mode exists
- **File:** `frontend/src/pages/PublicInvoice.jsx`

#### Bug Fix: System Reset Email Service
- **Issue:** System reset OTP emails failed with "No email delivery provider is configured" even when email settings were configured in Admin UI
- **Root Cause:** `request_system_reset_otp` endpoint was using `get_email_service()` (sync) which only reads from environment variables, ignoring database configuration
- **Fix:** Changed to `get_email_service_async()` which properly loads email settings from database (Admin Settings UI)
- **Impact:** System reset OTP, password reset, and all transactional emails now work with database-configured email settings
- **File:** `backend/routers/admin.py` (Line 1738)
- **Note:** Users must configure email settings in Admin → Settings → Email Settings (SMTP or Resend)

#### UI Enhancement: Login Page Logo
- **Desktop view:** Logo now has a white rounded square background (10% larger than logo size)
- Improves visibility of logo against blue gradient background
- Mobile view unchanged
- File: `frontend/src/pages/Login.jsx`

#### Wallet Balance Thresholds Updated
- **Suspension threshold reduced:** ₹100 → ₹50
  - Operators now suspended when wallet balance drops below ₹50 (was ₹100)
  - Auto-unsuspend when balance reaches ₹50 or above
- **Low balance warning threshold reduced:** ₹500 → ₹100
  - Daily cron now sends WhatsApp low-balance warnings when balance < ₹100 (was < ₹500)
- **Files modified:** 
  - `backend/routers/wallet.py` — suspension/unsuspension logic in `deduct_wallet()`, topup handlers, admin credit endpoints
  - `backend/services/cron_service.py` — daily wallet check cron job, warning message text updated

**New Threshold Summary:**
```
₹50   → Suspension threshold (account read-only mode)
₹100  → Low balance warning (WhatsApp notification sent)
```

### V8.20: Welcome Modal, Operator WA Notifications, Invoice Limit Removal

#### 1. Welcome Modal (Admin → Settings → General)
- **Admin-configurable announcement popup** shown to users on first login (or when version is incremented)
- Settings: `welcome_modal_enabled`, `welcome_modal_title`, `welcome_modal_content`, `welcome_modal_show_for` (all/operators/admins), `welcome_modal_version`
- New endpoint: `GET /admin/welcome-modal` — accessible to all authenticated roles
- Frontend: `WelcomeModal.jsx` component added to Admin and Operator dashboards
- Version-tracked per user in localStorage — increment version to force re-show to all users

#### 2. Cron & WhatsApp Analysis — Fixes
- **Removed dead code:** `send_overdue_reminders` + `run_hourly_reminder_check` were defined but never scheduled; removed to avoid confusion
- **Wallet check WA upgraded to template-based**: Previously used `send_text_message` (only works within 24h conversation window); now uses `operator_low_balance_template` if configured, falls back to text only if no template assigned
- **Expiry check WA added**: `run_daily_expiry_check` now sends WA to operator when trial ends or subscription expires using `operator_account_expiry_template`
- **Renewal reminders added**: 7, 3, 1 day before subscription expiry sends WA using `operator_renewal_template`

#### 3. Remove Invoice Generation Wallet Limit
- Removed the ₹50 minimum wallet balance requirement from manual invoice creation (`POST /operator/invoices`)
- Removed the ₹50 minimum wallet balance check from auto-invoice cron (`generate_upcoming_invoices`)
- Wallet deduction (₹10 per invoice) still happens; only the blocking minimum check is removed

#### 4. Operator WhatsApp Notifications (New Template Categories)
- **4 new WA template types** in `WhatsAppTemplates.jsx`: `operator_low_balance`, `operator_account_expiry`, `operator_renewal`, `operator_daily_report`
- **Operator-specific variable options** in template editor: `operator_name`, `balance`, `expiry_date`, `days_to_expiry`, `report_date`, `total_invoices`, `collected_today`, `pending_count`, `overdue_count`
- **4 new template assignment fields** in Admin Settings → WhatsApp tab (under "Operator Notifications" section)
- **New cron job**: `daily_operator_report` (default 09:30 IST) — sends daily billing summary WA to each operator
- **New cron time setting**: `cron_daily_report_time` (configurable in Admin Settings → General → Cron Schedule Times)
- **`_resolve_operator_variables()`** helper function in cron_service.py maps template variable names to operator context data

## 2026-04-17

### V8.19: Code Review & Cleanup
- **Unused files removed:** Deleted `cron_service_restored.py`, `cron_service_utf8.py` (orphaned duplicates), `test_out.txt`, `diff.txt`, `backend_test.py`, three `feature*_summary.md` files, `announcement_whatsapp_template_guide.md` (duplicate), `CLAUDE.md`, `GEMINI.md`
- **server.py:** Removed duplicate `import logging`; updated module docstring to reflect current architecture
- **README, CHANGELOG, agent-handoff:** Updated to V8.19 with all recent features

### V8.18: WhatsApp Template Testing
- **Test button per template:** Flask icon button on every row in the Templates table opens a "Test Template" dialog
- **Test dialog:** Shows template metadata, per-variable editable fields (pre-filled with sensible defaults), optional header image URL and button URL fields, and a result banner (success/failure with WhatsApp message ID)
- **Backend endpoint:** `POST /admin/whatsapp-test-template` — fetches template from DB, auto-fills missing variable slots, calls WhatsApp Cloud API, logs errors, returns human-readable error messages for common failure cases (phone not in allowed list, template name mismatch, etc.)

### V8.17: Invoice & Wallet Rule Hardening
- **Wallet minimum Rs 50:** Invoice creation (manual and cron auto-generate) now blocked when operator wallet balance < ₹50 (was ₹100). Error message updated. Cron service skips operators with insufficient balance before attempting auto-invoice creation.
- **Generate Payment Link visibility:** Button now requires ALL of: `status === "pending"`, payment_gateway add-on active, operator has payment gateway keys configured (`/operator/payment-gateway → configured: true`), AND `accept_payment_gateway === true` in invoice settings. Previously showed for any non-paid invoice with the add-on.

### V8.16: WhatsApp Stats & Message Logging
- **whatsapp_message_logs collection:** Every WhatsApp send (cron reminders, auto-invoice, manual operator sends) is logged with operator_id, template_name, template_category, recipient_phone, status, message_id, wa_id, invoice reference, and trigger type
- **Stats page `/admin/whatsapp-stats`:** Overview cards (Total, Today, This Month, Success Rate), 7-day bar chart, breakdown by category and trigger, paginated message logs table with filters (status, category, date range, search), and WhatsApp error logs section
- **API endpoints:** `GET /admin/whatsapp-stats`, `GET /admin/whatsapp-message-logs` (paginated + filterable), `DELETE /admin/whatsapp-message-logs`
- **"WA Stats" sidebar link** added to admin navigation

### V8.15: Payment Due Reminders Template Category
- **New template category `payment_due_reminder`:** Separate from `payment_reminder` (before/on due date) — intended for overdue invoices only; shown in red badge
- **Cron logic:** `days_diff < 0` → `payment_due_reminder_template`; `days_diff == 0` → `reminder_template`; `days_diff > 0` → `invoice_template` (previously `days_diff <= 0` used the same template)
- **Template assignment UI:** New "Payment Due Reminders (Overdue)" field in admin Settings → Template Assignment
- **Quick Setup preset** added for payment_due_reminder type

### V8.14: Operator Dashboard & UX Fixes
- **Cancelled invoices card:** Added 5th stat card (Cancelled) to operator dashboard alongside Total, Pending, Overdue, Paid
- **Invoice action menu:** "Send via WhatsApp API" relabelled to "Send via WhatsApp API (Rs 0.5)"; added "Send via WhatsApp Web" button (opens wa.me link, no feature flag required)
- **OperatorResponse model:** Made `owner_name` and `status` Optional with safe defaults to prevent `KeyError` / Pydantic validation errors on older operator documents missing these fields

## 2026-04-15

### V8.13: WhatsApp Template Header Support & Media Handling
- **Dynamic Headers:** Added support for Text and Image headers in WhatsApp templates.
- **Media Parameter Support:** The WhatsApp service now correctly handles header parameters for Image-type templates, preventing the "Format mismatch" error.
- **Variable-to-Header Mapping:** Operators can now map variables like `Company Logo` directly to the template header.
- **Absolute Media URLs:** Implemented automatic resolution of relative file paths (e.g., logos) to absolute URLs required by the WhatsApp API.

### V8.12: WhatsApp Template Variable Resolver
- **Dynamic Variable Mapping:** Implemented `resolve_template_variables` to automatically map placeholders like `{{1}}`, `{{2}}` to database fields (Customer Name, Invoice No, etc.).
- **Admin Variable Selection:** Updated the WhatsApp Template management UI to allow selection of variables for body text.

### V8.11: UPI Payment Message Prefill & Invoice Enhancements
- **UPI Transaction Note (`tn`):** Plan name and service tenure (start–end date) are now automatically prefilled as the payment note when a subscriber pays via any UPI app, giving the operator clear transaction context.
- **Plan Description on Invoice:** The public invoice now shows the plan's description as an italicised sub-line below the service tenure in the line items table.
- **Payment Method Selector:** Replaced individual payment-type toggles with an explicit dropdown in Invoice Customization — options are Both, Gateway Only, UPI Only, or None.
- **UPI App Chooser Modal:** Tapping "Pay with UPI" now opens a modal letting the subscriber choose Google Pay, PhonePe, Paytm, BHIM, or any other app, preventing automatic OS hijacking.
- **Gateway Key Enforcement:** Payment gateway is now only enabled when the operator has their own dedicated keys configured; no platform gateway fallback for subscriber payments.

## 2026-04-14

### V8.10: Direct UPI Payments Integration
- **Direct UPI App Payments (Intent Link):** Added the ability for operators to accept direct peer-to-peer UPI payments without a payment gateway.
- **Business Profile Settings:** Added a new field for `UPI ID` in the operator's business profile.
- **Invoice Preferences:** Operators can now independently toggle "Accept Payment via Gateway" and "Accept Payment via UPI Apps".
- **Dynamic Invoice UI:** The public invoice page dynamically displays "Pay Online" and/or "Pay via UPI App" buttons based on operator settings.

### V8.9: Payment Link Generation & UI Enhancements
- **Manual Payment Links:** Operators can now generate manual payment links for individual invoices via the Invoices page.
- **Dynamic Payment Routing:** Integrated operator-specific gateway credentials for manual payment links to ensure correct fund routing.
- **Invoice UI Update:** Added "Generate Payment Link" action button to the Invoices table for faster operator access.

## 2026-04-03

### V8.8: Bulk Subscriber Upload — Multi-Plan Support
- **Multi-Plan CSV Format:** Bulk subscriber upload now supports up to 5 plans per subscriber via `plan_name_1..5`, `billing_date_1..5`, `discount_1..5` columns (one row per subscriber)
- **Route Ordering Fix:** Moved `sample-csv` and `bulk-upload` routes before `{subscriber_id}` parameterized routes to prevent FastAPI matching `sample-csv` as a subscriber ID (was causing 404)
- **CSV Download Fix:** Fixed silent download failure across Subscribers, Plans, Invoices, and Reports pages — anchor element must be appended to DOM before `.click()`

### V8.7: CSV Download Fix
- Fixed bulk upload sample file download (404) — static routes must precede parameterized routes in FastAPI
- Fixed programmatic CSV/file downloads across all pages (anchor not appended to DOM)

### V8.6: Remove WhatsApp Web Service
- **WhatsApp WebJS Removed:** Removed `whatsapp-service` Docker container from `docker-compose.prod.yml` and GitHub Actions build pipeline
- **Deployment Log Capture:** Added backend and MongoDB log dump to CI/CD script on deployment failure for easier debugging
- Deleted `whatsapp-service/` source directory

## 2026-04-02

### V8.4: Decommission WhatsApp & Automation Enhancements
- **WhatsApp WebJS Decommissioned:** Removed WhatsApp Web UI from operator settings and invoice actions
- **Automated Operator Wallets:** Wallet auto-initialized with SaaS plan `monthly_price` when admin creates an operator
- **Consolidated Payment Gateways:** Unified gateway configs; public invoice payments enforce operator-assigned keys exclusively

### V8.3: Production Deployment Hardening
- Removed `container_name` from `docker-compose.prod.yml` to prevent name conflicts during redeployment
- Added `docker-compose down --remove-orphans` before `up` for clean deploys
- Fixed WhatsApp image tag alignment in CI/CD workflow

## 2026-03-25

### V7.15-10: Docker Infrastructure Optimization
- Reduced `.env` from 40+ to 8-10 core variables
- Fixed MongoDB authentication (`authSource=admin` in URI)
- Dual compose files: `docker-compose.yml` (dev) + `docker-compose.prod.yml` (prod)
- Multi-stage backend Dockerfile with `BUILD_ENV` arg (dev vs prod requirements)
- Environment-aware config (`IS_PRODUCTION`, `LOG_LEVEL`, feature flags)

### V7.15-9: Settings Consolidation
- Removed orphaned "Env Tab"; added Security Tab with JWT + backup password fields
- Added `env_generator.py` for `.env` auto-generation from database
- Caddy proxy with security headers

### V7.15-8: Service Refactor
- Migrated JWT, Razorpay, Resend credentials to database-backed storage
- `env_service.py` with database-first priority
- Async factory functions for all services

### Earlier Versions (V7.14–V7.15-7)
- Single-session JWT enforcement
- Invoice bulk upload with sample CSV/XLSX
- Invoice branding, public links, and public payment verification
- Multi-plan subscribers and multi-line invoices
- Global IST cron scheduling (configurable from admin UI)
- Admin impersonation and return flow
- Email OTP registration + SMTP fallback
- Wallet accounting, referral codes, discount codes
- Support tickets, audit logs, automated backups
- SEO metadata, PWA support (manifest + service worker)
- Staff management with account status toggle
- Operator payment gateway delegation
- Dashboard monthly value statistics
- SMTP fallback tolerates servers without AUTH support


### V8.13: WhatsApp Template Header Support & Media Handling
- **Dynamic Headers:** Added support for Text and Image headers in WhatsApp templates.
- **Media Parameter Support:** The WhatsApp service now correctly handles header parameters for Image-type templates, preventing the "Format mismatch" error.
- **Variable-to-Header Mapping:** Operators can now map variables like `Company Logo` directly to the template header.
- **Absolute Media URLs:** Implemented automatic resolution of relative file paths (e.g., logos) to absolute URLs required by the WhatsApp API.

### V8.12: WhatsApp Template Variable Resolver
- **Dynamic Variable Mapping:** Implemented `resolve_template_variables` to automatically map placeholders like `{{1}}`, `{{2}}` to database fields (Customer Name, Invoice No, etc.).
- **Admin Variable Selection:** Updated the WhatsApp Template management UI to allow selection of variables for body text.

### V8.11: UPI Payment Message Prefill & Invoice Enhancements
- **UPI Transaction Note (`tn`):** Plan name and service tenure (start–end date) are now automatically prefilled as the payment note when a subscriber pays via any UPI app, giving the operator clear transaction context.
- **Plan Description on Invoice:** The public invoice now shows the plan's description as an italicised sub-line below the service tenure in the line items table.
- **Payment Method Selector:** Replaced individual payment-type toggles with an explicit dropdown in Invoice Customization — options are Both, Gateway Only, UPI Only, or None.
- **UPI App Chooser Modal:** Tapping "Pay with UPI" now opens a modal letting the subscriber choose Google Pay, PhonePe, Paytm, BHIM, or any other app, preventing automatic OS hijacking.
- **Gateway Key Enforcement:** Payment gateway is now only enabled when the operator has their own dedicated keys configured; no platform gateway fallback for subscriber payments.

## 2026-04-14

### V8.10: Direct UPI Payments Integration
- **Direct UPI App Payments (Intent Link):** Added the ability for operators to accept direct peer-to-peer UPI payments without a payment gateway. 
- **Business Profile Settings:** Added a new field for `UPI ID` in the operator's business profile.
- **Invoice Preferences:** Operators can now independently toggle "Accept Payment via Gateway" and "Accept Payment via UPI Apps".
- **Dynamic Invoice UI:** The public invoice page dynamically displays "Pay Online" and/or "Pay via UPI App" buttons based on operator settings.

### V8.9: Payment Link Generation & UI Enhancements
- **Manual Payment Links:** Operators can now generate manual payment links for individual invoices via the Invoices page.
- **Dynamic Payment Routing:** Integrated operator-specific gateway credentials for manual payment links to ensure correct fund routing.
- **Invoice UI Update:** Added "Generate Payment Link" action button to the Invoices table for faster operator access.

## 2026-04-03

### V8.8: Bulk Subscriber Upload — Multi-Plan Support
- **Multi-Plan CSV Format:** Bulk subscriber upload now supports up to 5 plans per subscriber via `plan_name_1..5`, `billing_date_1..5`, `discount_1..5` columns (one row per subscriber)
- **Route Ordering Fix:** Moved `sample-csv` and `bulk-upload` routes before `{subscriber_id}` parameterized routes to prevent FastAPI matching `sample-csv` as a subscriber ID (was causing 404)
- **CSV Download Fix:** Fixed silent download failure across Subscribers, Plans, Invoices, and Reports pages — anchor element must be appended to DOM before `.click()`

### V8.7: CSV Download Fix
- Fixed bulk upload sample file download (404) — static routes must precede parameterized routes in FastAPI
- Fixed programmatic CSV/file downloads across all pages (anchor not appended to DOM)

### V8.6: Remove WhatsApp Web Service
- **WhatsApp WebJS Removed:** Removed `whatsapp-service` Docker container from `docker-compose.prod.yml` and GitHub Actions build pipeline
- **Deployment Log Capture:** Added backend and MongoDB log dump to CI/CD script on deployment failure for easier debugging
- Deleted `whatsapp-service/` source directory

## 2026-04-02

### V8.4: Decommission WhatsApp & Automation Enhancements
- **WhatsApp WebJS Decommissioned:** Removed WhatsApp Web UI from operator settings and invoice actions
- **Automated Operator Wallets:** Wallet auto-initialized with SaaS plan `monthly_price` when admin creates an operator
- **Consolidated Payment Gateways:** Unified gateway configs; public invoice payments enforce operator-assigned keys exclusively

### V8.3: Production Deployment Hardening
- Removed `container_name` from `docker-compose.prod.yml` to prevent name conflicts during redeployment
- Added `docker-compose down --remove-orphans` before `up` for clean deploys
- Fixed WhatsApp image tag alignment in CI/CD workflow

## 2026-03-25

### V7.15-10: Docker Infrastructure Optimization
- Reduced `.env` from 40+ to 8-10 core variables
- Fixed MongoDB authentication (`authSource=admin` in URI)
- Dual compose files: `docker-compose.yml` (dev) + `docker-compose.prod.yml` (prod)
- Multi-stage backend Dockerfile with `BUILD_ENV` arg (dev vs prod requirements)
- Environment-aware config (`IS_PRODUCTION`, `LOG_LEVEL`, feature flags)

### V7.15-9: Settings Consolidation
- Removed orphaned "Env Tab"; added Security Tab with JWT + backup password fields
- Added `env_generator.py` for `.env` auto-generation from database
- Caddy proxy with security headers

### V7.15-8: Service Refactor
- Migrated JWT, Razorpay, Resend credentials to database-backed storage
- `env_service.py` with database-first priority
- Async factory functions for all services

### Earlier Versions (V7.14–V7.15-7)
- Single-session JWT enforcement
- Invoice bulk upload with sample CSV/XLSX
- Invoice branding, public links, and public payment verification
- Multi-plan subscribers and multi-line invoices
- Global IST cron scheduling (configurable from admin UI)
- Admin impersonation and return flow
- Email OTP registration + SMTP fallback
- Wallet accounting, referral codes, discount codes
- Support tickets, audit logs, automated backups
- SEO metadata, PWA support (manifest + service worker)
- Staff management with account status toggle
- Operator payment gateway delegation
- Dashboard monthly value statistics
- SMTP fallback tolerates servers without AUTH support
