# E-Bill Platform - CHANGELOG

## 2026-04-02

### V8.4: Decommission WhatsApp & Automation Enhancements
- **WhatsApp WebJS Decommissioned:** Completely removed the WhatsApp Web UI from operator settings and invoice actions. Purged the `whatsapp-webjs` Docker service from deployment definitions.
- **Automated Operator Wallets:** When admins manually create operators, their wallet is now automatically initialized and funded with the SaaS plan's `monthly_price`. 
- **Consolidated Payment Gateways:** Unified `custom_payment_gateway` and `payment_gateway` addon configurations. Public invoice payments now strictly enforce the use of operator-assigned keys, eliminating the platform gateway fallback.

### V8.3: Production Deployment Hardening
- **Fixed Container Name Conflicts** - Removed rigid `container_name` properties from all services in `docker-compose.prod.yml` to prevent "container name already in use" errors during CI/CD redeployment.
- **Added Clean Deployment Step** - Added explicit `docker-compose down --remove-orphans` before starting services to ensure a clean state.
- **Fixed WhatsApp Image Tag** - Aligned the CI/CD workflow image tag (`ebill-whatsapp-webjs`) with the service definition in `docker-compose.prod.yml`.
- **Added V8.3 CI/CD Trigger** - Updated `docker-build-push.yml` to trigger on pushes to the `V8.3` branch.


### V7.16.6: WhatsApp Service CI/CD & Deployment Fix
- **Fixed WhatsApp Deployment** - Added missing `whatsapp-service` build and push steps to the GitHub Actions workflow.
- **Automated CI/CD Pipeline** - Implemented GitHub Actions for automated building and deployment.
- **Docker Hub Integration** - Configured automated image builds and storage on Docker Hub for backend, frontend, and whatsapp services.
- **Production Deployment Workflow** - Verified and finalized the deployment path to production servers for all services.
- **Documentation Updates** - Simplified and updated CI/CD and Docker setup guides.


## 2026-03-25

### V7.15-10: Docker Infrastructure Optimization & Production-Ready Setup

#### Docker & Environment Refactor
- **Optimized .env Configuration** - Reduced from 40+ variables to only 8-10 core essentials
  - Only loads: DOMAIN, MONGO_URI, JWT_SECRET, BACKUP_PASSWORD, DB_NAME, CORS_ORIGINS, REACT_APP_BACKEND_URL
  - All optional settings (Email, WhatsApp, Payment) managed via Admin Settings UI
  - Significantly reduces deployment complexity and credential exposure

- **Fixed Critical MongoDB Authentication** - Resolved "command find requires authentication" errors
  - Updated MONGO_URI to use authenticated connection strings: `mongodb://user:pass@mongodb:27017/db?authSource=admin`
  - Properly handles credentials passed through docker-compose environment variables
  - Tested and verified both dev and prod authentication flows

- **Dual Environment Docker Compose Files**
  - `docker-compose.yml` (Development): Exposes ports locally, includes all debugging tools, lower resource limits
  - `docker-compose.prod.yml` (Production): Internal networking, optimized resources, structured logging, auto-restart policies
  - Both tested and working with full container health checks

- **Enhanced Backend Dockerfile** - Multi-stage intelligent build system
  - Added `BUILD_ENV` build argument to conditionally select requirements files
  - Development mode: Includes `requirements_local.txt` with dev/debug dependencies
  - Production mode: Uses `requirements.txt` only (minimal image size)
  - Maintains multi-stage build pattern for optimized final image

- **Environment-Aware Python Configuration** (`backend/config.py`)
  - New `LOG_LEVEL` configuration based on environment (DEBUG in dev, INFO in prod)
  - Feature flags disabled/enabled based on integration availability
  - JWT_SECRET and BACKUP_PASSWORD validation (required in production)
  - Structured `FEATURES` dictionary for feature availability detection
  - `IS_PRODUCTION` and `IS_DEVELOPMENT` boolean flags for environment-specific behavior

- **Improved MongoDB Connection Handling** (`backend/database.py`)
  - Cleaner priority-based MONGO_URI resolution
  - Better error messages and documentation
  - Supports both authenticated and fallback connection methods
  - URL encoding for special characters in credentials

- **Cleaned Up Server Initialization** (`backend/server.py`)
  - Removed redundant `.env` file generation (now handled by `docker/init-env.sh`)
  - Updated logging to use config-based LOG_LEVEL
  - Improved CORS configuration from centralized `config.py`
  - All environment setup now consolidated in init phase

- **Optimized Container Initialization** (`docker/init-env.sh`)
  - Reduced from ~45 lines to ~30 lines with focused content
  - Only generates critical core 7-8 environment variables
  - Clear documentation about what's managed in Admin Settings vs .env
  - Better suited for containerized environments

#### Documentation & References
- Created `DOCKER_QUICK_REFERENCE.md` - Daily development commands and quick troubleshooting
- Created `DOCKER_OPTIMIZATION_V7_15_10.md` - Comprehensive optimization guide with deployment instructions
- Updated `.env.example` with detailed inline documentation, dev/prod examples, and environment-specific settings

#### Files Modified
- [docker-compose.yml](/d:/eBill/docker-compose.yml) - Development environment optimized
- [docker-compose.prod.yml](/d:/eBill/docker-compose.prod.yml) - Production environment optimized
- [backend/Dockerfile](/d:/eBill/backend/Dockerfile) - Conditional dev/prod builds
- [backend/config.py](/d:/eBill/backend/config.py) - Environment-aware configuration
- [backend/database.py](/d:/eBill/backend/database.py) - Improved MongoDB URI handling
- [backend/server.py](/d:/eBill/backend/server.py) - Removed redundant env generation
- [docker/init-env.sh](/d:/eBill/docker/init-env.sh) - Optimized to core variables only
- [.env.example](/d:/eBill/.env.example) - Comprehensive documentation and examples
- [DOCKER_QUICK_REFERENCE.md](/d:/eBill/DOCKER_QUICK_REFERENCE.md) [NEW]
- [DOCKER_OPTIMIZATION_V7_15_10.md](/d:/eBill/DOCKER_OPTIMIZATION_V7_15_10.md) [NEW]

#### Testing & Validation
✅ Docker build successful (both backend and frontend images)
✅ docker-compose up -d starts all services successfully
✅ Backend service health check passes - returns `{"status":"healthy"...}`
✅ Frontend service healthy - HTTP 200 response
✅ MongoDB authentication verified - no credential errors
✅ CORS configuration working properly
✅ All containers reach healthy state within startup period

#### Benefits
- ✅ Simplified deployment with minimal environment variables
- ✅ Production-ready Docker configuration with proper logging and resource limits
- ✅ Fixed critical MongoDB authentication issues
- ✅ Clear separation between dev and prod configurations
- ✅ Better security posture with centralized credential management
- ✅ Comprehensive documentation for deployment and daily operations
- ✅ Faster image builds with conditional dependencies
- ✅ Environment-aware feature flagging

#### Known Issues Resolved
- ❌ Previous: Backend couldn't connect to MongoDB (auth error) → ✅ Fixed with authenticated MONGO_URI
- ❌ Previous: Bloated .env with 40+ variables → ✅ Reduced to 8-10 core variables
- ❌ Previous: No clear dev vs prod configuration → ✅ Separate docker-compose files with clear intent

---

### V7.15-9: Settings Consolidation & Caddy Optimization

#### Admin Settings UI Refactor
- **Removed Orphaned "Env Tab"** - Consolidated duplicate settings configuration screens
- **Enhanced Security Tab** - Added new "Cryptography Keys" card with JWT Secret and Backup Encryption Password
- Settings now have proper segregation:
  - **General Tab**: Platform configuration, GST, session timeout, cron schedules
  - **Security Tab**: JWT & Backup credentials, Admin profile, Password change
  - **Payment Gateways Tab**: Razorpay, Cashfree, PhonePe configuration
  - **Email API Tab**: Resend API key and SMTP fallback configuration
  - **WhatsApp Tab**: Phone Number ID, Business Account, Access Token, Templates
  - **Reminders Tab**: Global reminder scheduling and templates
  - **Backup & Restore Tab**: Manual backups and restore operations

#### Backend Routes & Models
- Added dedicated `/admin/security-settings` GET/PUT endpoints for JWT and backup credentials
- Added `SecuritySettingsUpdate` and `SecuritySettingsResponse` Pydantic models
- Maintained backward compatibility with existing `/admin/env-settings` routes
- Both routes share same database (global_settings.type=env_settings)

#### Environment File Generator
- Created `backend/services/env_generator.py` utility for automated .env file generation
- Smart configuration source priority: Database → Environment Variables → Defaults
- Supports async and sync initialization patterns
- Pulls email, WhatsApp, and payment configurations from database
- Used during deployment and application startup

#### Caddy Proxy Optimization
- Added comprehensive security headers (X-Frame-Options, X-XSS-Protection, X-Content-Type-Options, Referrer-Policy)
- Implemented HTTPS-specific headers (Strict-Transport-Security for production)
- Added request header propagation (X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Host)
- Added explicit file uploads routing (@uploads path /uploads/*)
- Separated HTTP (localhost) and HTTPS (SERVER_IP) configurations
- Foundation for request/response logging support

#### Files Modified
- [frontend/src/pages/admin/Settings.jsx](/d:/eBill/frontend/src/pages/admin/Settings.jsx)
- [backend/routers/admin.py](/d:/eBill/backend/routers/admin.py)
- [backend/models.py](/d:/eBill/backend/models.py)
- [backend/services/env_generator.py](/d:/eBill/backend/services/env_generator.py) [NEW]
- [Caddyfile](/d:/eBill/Caddyfile)

#### Benefits
- ✅ Eliminated settings duplication and user confusion
- ✅ Centralized credential management in database
- ✅ Reduced administrative burden with dedicated security tab
- ✅ Production-ready proxy with proper header handling
- ✅ Simplified deployment with auto-generated .env files

### V7.15-8: Admin Env Settings & Service Refactor

#### Environment Management
- Migrated sensitive environment variables (JWT, Razorpay, Resend, WhatsApp) from `.env` file to a secure, database-backed "Env" tab in the Admin Settings panel.
- Implemented `backend/services/env_service.py` to centralize setting retrieval with a database-first priority and automatic fallback to environment variables.
- Sensitive values are masked in the Admin UI with toggleable visibility for secure management.
- FIXED: Resolved a `ReferenceError: fetchEmailConfig is not defined` on the Admin Settings page that caused the UI to crash.

#### Service Layer Architecture
- Refactored `WhatsAppService` and `RazorpayService` with async factory functions (`get_whatsapp_service_async`, `get_razorpay_service_async`) to dynamically load credentials from the database.
- Refactored `email_service.py` to prioritize database-stored Resend configuration.
- Updated `cron_service.py` (WhatsApp reminders) and `cron_backup_job` to use the new async service initialization pattern.

#### Files Modified
- [backend/services/env_service.py](/d:/eBill/backend/services/env_service.py) [NEW]
- [backend/services/whatsapp_service.py](/d:/eBill/backend/services/whatsapp_service.py)
- [backend/services/razorpay_service.py](/d:/eBill/backend/services/razorpay_service.py)
- [backend/services/email_service.py](/d:/eBill/backend/services/email_service.py)
- [backend/services/cron_service.py](/d:/eBill/backend/services/cron_service.py)
- [backend/routers/admin.py](/d:/eBill/backend/routers/admin.py)
- [backend/models.py](/d:/eBill/backend/models.py)
- [frontend/src/pages/admin/Settings.jsx](/d:/eBill/frontend/src/pages/admin/Settings.jsx)

### V7.15-7: index.html Script Cleanup

### V7.15-6: Operator Plans List View Redesign

#### Plans Layout Improvements
- Migrated the Operator Plans page from a heavy card-based grid layout to a clean and efficient data table list format.
- Added explicit columns for `Plan Name`, `Price`, `Validity`, `Tax`, `Status`, and `Description`.
- Reorganized plan action buttons (Edit, Delete) into a dedicated `Actions` column with streamlined icon-only ghost buttons.

#### Files Modified
- [frontend/src/pages/operator/Plans.jsx](/d:/eBill/frontend/src/pages/operator/Plans.jsx)

#### Bug Fixes & Optimizations
- **Razorpay Script Loading**: Removed the global Razorpay checkout script from `index.html` to eliminate aggressive browser preload warnings.
- Created a shared dynamic loader utility `lib/razorpay.js` and integrated it across `PublicInvoice.jsx`, `operator/Wallet.jsx`, `operator/Subscription.jsx`, and `operator/Addons.jsx` so the script is only fetched precisely when needed.

### V7.15-5: Staff Edit Endpoints, Status Toggle, and Announcement History View

#### Staff Management Enhancements
- Added backend `PUT /operator/staff/{staff_id}` endpoint to support full staff editing capabilities.
- Added `StaffUpdate` Pydantic model for secured validation.
- Added "Account Status" dropdown to the operator frontend Staff Edit form, enabling operators to seamlessly toggle staff members between `Active` and `Suspended` states.

#### Announcement Enhancements
- Added a "View Announcement" feature (Eye icon) to the Announcement History table.
- Added a detailed dialog displaying announcement title, message, date of issuance, total recipients, and delivery channels (WhatsApp / Email).

#### Files Modified
- [backend/models.py](/d:/eBill/backend/models.py)
- [backend/routers/operator.py](/d:/eBill/backend/routers/operator.py)
- [frontend/src/pages/operator/Staff.jsx](/d:/eBill/frontend/src/pages/operator/Staff.jsx)
- [frontend/src/pages/operator/Announcements.jsx](/d:/eBill/frontend/src/pages/operator/Announcements.jsx)

### V7.15-2: Invoice Settings Restrictions

#### Invoice Settings - Image Upload Disabled
- Image upload button in invoice settings is now permanently disabled.
- Users can only provide logo URLs manually, not upload image files.
- Button styling reflects disabled state for clear user feedback.

#### Invoice Settings - Show Logo Toggle Disabled
- "Show Logo" switch in invoice settings is now always toggled OFF.
- Users cannot change this setting; it remains disabled permanently.
- Logo visibility is fully controlled by the system, not operator choices.

#### Files Modified
- [frontend/src/pages/operator/Settings.jsx](/d:/eBill/frontend/src/pages/operator/Settings.jsx)

#### Validation
- Image upload button should appear disabled and non-functional in operator invoice settings.
- Show Logo switch should always be OFF and disabled.

### V7.14-15: Operator Referral Code Auto-Generation, Logo Upload Reorganization, Subscription Renewal Window, and Announcements Enhancements

#### Operator Referral Code Fix
- Operators created by admin now automatically receive a unique referral code if missing.
- Referral code is generated on-demand when accessing wallet if not already assigned.
- Ensures all operators, including legacy ones, have valid referral codes for the referral program.

#### Logo Upload Path Reorganization
- Operator logo uploads now save to project root `/uploads` folder instead of `backend/uploads`.
- Updated file path configuration in `operator.py` and `pdf_service.py`.
- Public URL changed from `/api/uploads/` to `/uploads/` for consistency.
- Both admin and operator logo uploads now use the same centralized upload directory.

#### Subscription Renewal Window
- Added 3-day renewal window restriction: operators can renew subscription from 3 days before expiry until the expiry date.
- Early renewal attempts show clear error message indicating when renewal becomes available.
- Implemented backend validation in `renew-subscription` endpoint.
- Frontend now shows disabled renewal button with tooltip when outside the renewal window.

#### Subscription Renewal UI Improvements
- Added **Wallet Topup button** next to renewal buttons on subscription page.
- Topup button navigates directly to the wallet page for easy credit management.
- Available in both urgent renewal (within 3 days/expired) and normal renewal sections.
- Improves user experience for operators who may need wallet credits before renewal.

#### Wallet Transaction Display
- Transaction history properly displays meaningful `description` field instead of operator ID.
- Each transaction shows context-specific details (e.g., "Invoice generation charge", "Wallet Topup", etc.).
- Admin wallet transaction view provides clear transaction details for audit purposes.

#### Announcements Enhancements
- Changed announcement frequency limit from **3 per day** to **6 per week**.
- Weekly limit calculation uses ISO week start (Monday).
- Added **email notification checkbox** to announcement creation form.
- Announcements can now be sent via **WhatsApp, Email, or both**.
- Uses Resend API for email delivery with fallback support.
- Announcement list now displays **Email status badge** (Sent/No) alongside WhatsApp status.
- Get announcements endpoint returns **weekly statistics** showing:
  - Total limit (6)
  - Announcements sent this week
  - Remaining announcements available this week
- Frontend displays weekly limit indicator on announcement page showing progress and remaining quota.

#### Validation
- Operator referral code generation should be verified during wallet access.
- Admin-created operators should receive referral codes automatically.
- Logo uploads should be stored in root `/uploads` folder and served via `/uploads/` URLs.
- Subscription renewal should be blocked outside the 3-day window with appropriate error messages.
- Renewal/Topup buttons should display correctly on subscription page.
- Announcements should enforce 6-per-week limit with clear feedback.
- Email announcements should send via Resend API when enabled.
- Weekly statistics should display correctly in announcements UI.

### V7.14-14: Operator Dashboard Stats, SMTP Stability, and Referral Automation

#### Dashboard Stats
- Operator dashboard now shows monthly invoice value, received value this month, pending value this month, and total pending value.

#### SMTP Hardening
- SMTP sending/testing is now more tolerant.
- SMTP now supports port `465` implicit SSL.
- Timeout and disconnect errors now surface more clearly.

#### Referral Automation
- Admin-created operators now receive referral codes automatically.
- Admin general settings now manage referral benefits:
  - discount percent/max
  - reward percent
  - reward validity days
- Referral discount/reward logic now uses those settings.

#### Validation
- Operator dashboard totals and month-to-date values should be verified against live invoices/payments.
- SMTP test mail and implicit SSL behavior should be verified against supported mail servers.
- Admin-created operator referral-code generation should be verified during operator creation.
- Referral benefits/settings should be verified in admin settings and downstream calculations.

### V7.14-13: Invoice Bulk Upload, Address Fallback, and Logo Rendering

#### Invoice Import
- Added bulk upload support for operator invoices.
- Bulk invoice upload now includes sample CSV/XLSX flow similar to the subscriber bulk upload experience.

#### Invoice Settings
- Invoice settings now fall back to the operator registration/profile address when the invoice company address is empty.

#### Invoice Branding
- Uploaded invoice logos now persist immediately.
- Uploaded logos now preview correctly in operator settings.
- Uploaded logos now render correctly on the public invoice page.
- Backend now serves uploaded assets through `/api/uploads` URLs.

#### Validation
- Bulk invoice upload sample-file flow should be verified against the operator import path.
- Invoice address fallback should be verified on blank-address invoices.
- Logo preview/rendering should be verified in operator settings and public invoice views.
- Uploaded asset URLs should be verified over `/api/uploads`.

### V7.14-12: Cache Clearing, Admin Profile, and Email Test Actions

#### Cache Management
- Added cache-clear tools in admin and operator settings for clearing stale dashboard data.
- Login/session switching now automatically clears browser/app cache.
- Service worker caching no longer stores `/api` responses.

#### Admin Profile
- Admin settings now allow changing the admin display name.

#### Email Testing and SMTP Compatibility
- Email settings now support Resend test mail actions.
- Email settings now support SMTP test mail actions.
- SMTP fallback now skips login when the server does not advertise `AUTH`.

#### Validation
- Browser refresh/login cache behavior verified in the UI flow.
- Resend and SMTP test-email flows now have validation coverage.
- SMTP servers without AUTH support are tracked for fallback verification.

### Pre-Task Documentation Sync
- Refreshed docs on `V7.14-11` before starting the next cache/admin-profile/email task batch.
- Captured the next requested scope:
  - clear browser/app cache from the UI to address stale dashboard data after login
  - allow changing the admin name
  - add test mail actions for Resend and fallback email settings

### Pre-Task Documentation Sync
- Refreshed docs on `V7.14-11` before starting the next gateway-management feature batch.
- Captured the next requested scope:
  - admin can assign payment gateway keys directly to an operator from the admin dialog
  - operator-side payment gateway settings should be removed

### V7.14-11 Follow-Up: Admin Payment Gateway Assignment

#### Admin Gateway Management
- Extended the admin payment gateway dialog so the same form can save:
  - platform / SaaS payment keys
  - operator-specific payment gateway keys
- Added operator selection in the admin dialog.
- Enriched the admin gateway list so assigned operator names are visible.
- Tightened admin upsert behavior so operator-targeted keys update by operator id.

#### Operator Experience
- Removed payment gateway configuration from the operator settings panel.
- Updated custom-gateway messaging so operators are directed to contact admin for key assignment.
- Blocked the old operator payment-gateway write endpoint so gateway keys are admin-managed.

#### Validation
- `python -m py_compile backend\\routers\\admin.py backend\\routers\\operator.py` passed.
- `npm run build` passed in `frontend/`.
- Existing frontend `react-hooks/exhaustive-deps` warnings remain, but build output succeeded.

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
