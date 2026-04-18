# E-Bill Platform — CHANGELOG

## 2026-04-18

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
