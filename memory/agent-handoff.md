# Agent Handoff - E-Bill Platform

**Last Updated:** 2026-04-02  
**Active Branch:** `V8.3`
**Latest Feature Branch:** `V8.3` (Production Deployment Hardening)

---

## Current Snapshot

The codebase now includes:

- Docker infrastructure fully optimized for dev and production environments
- Minimal .env configuration (only 8-10 core variables)
- Fixed MongoDB authentication with proper credential handling
- Dual docker-compose files: docker-compose.yml (dev) and docker-compose.prod.yml (prod)
- Conditional Dockerfile builds with BUILD_ENV argument for dev vs production
- Environment-aware Python configuration with feature flags and validation
- Comprehensive Docker documentation (quick reference and optimization guides)
- settings consolidation with dedicated security tab
- JWT and backup password management in admin security settings
- .env file auto-generation from database
- optimized Caddy proxy with security headers and request logging setup
- separated HTTP/HTTPS caddy configurations
- previous features from V7.15-8 and earlier:
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
  - richer SEO/Open Graph/Twitter/schema metadata
  - installable web app support with manifest, icons, and service worker
  - cron settings persistence now refreshes correctly in the UI
  - auto-backup entries now appear in the backup list after cron completion
  - email settings now reload the latest saved values after save/refresh
  - admin can assign payment gateway keys directly to operators
  - operator settings no longer expose payment gateway configuration
  - browser cache clear tools now exist in admin/operator settings
  - login/session switching now clears stale cache automatically
  - admin display-name changes are supported from settings
  - Resend and SMTP test mail actions are available
  - SMTP fallback now tolerates servers without AUTH support
  - operator invoice bulk upload with sample CSV/XLSX flow is now available
  - invoice settings fall back to the registration/profile address when the company address is empty
  - invoice logos persist immediately and render correctly via `/api/uploads`
  - operator dashboard monthly value stats are now shown
  - SMTP sending/testing is more tolerant, including implicit SSL on port 465
  - admin-created operators now receive referral codes automatically
  - referral benefits/settings now live in admin general settings
  - invoice image upload button is permanently disabled
  - invoice show logo toggle is always OFF and disabled
  - backend `PUT /operator/staff/{staff_id}` endpoint implemented alongside `StaffUpdate` model
  - operator UI "Account Status" toggle added to Staff Edit dialogue
- detailed view dialog added to the announcement history page via "Eye" icon
- operator plans layout upgraded to an organized data table list view
- optimized Razorpay by converting to a dynamic script loader (`lib/razorpay.js`) to eliminate global preload console warnings
- removed unnecessary legacy scripts (PostHog and error handler) from `index.html` to improve performance and code cleanliness
- migrated sensitive environment variables (JWT, Razorpay, Resend, WhatsApp) to a secure, database-backed "Env" tab in Admin Settings
- implemented centralized `env_service.py` for prioritized setting retrieval with fallbacks
- refactored WhatsApp and Razorpay services with async factory functions for dynamic configuration
- updated email and cron services to utilize database-backed environment settings
- FIXED: Resolved a `ReferenceError: fetchEmailConfig is not defined` in `Settings.jsx` that caused the Admin Settings page to crash


---

## Most Recent Delivery

### Branch Flow
- `V7.14-6` was created and pushed from `V7.14-5`
- `V7.14-7` was created and pushed from `V7.14-6`
- `V7.14-8` is the documentation update branch based on `V7.14-7`
- `V7.14-9` is the scheduler reliability fix branch based on `V7.14-8`
- `V7.14-10` is the title, email fallback, and cron-settings branch based on `V7.14-9`
- `V7.14-11` is the metadata and installable web app branch based on `V7.14-10`
- `V7.14-12` is the cache clearing, admin profile, and email test branch based on `V7.14-11`
- `V7.14-13` is the invoice bulk upload, address fallback, and logo rendering branch based on `V7.14-12`
- `V7.14-14` is the dashboard stats, SMTP stability, and referral automation branch based on `V7.14-13`
- `V7.14-15` is the operator referral codes, logo reorganization, renewal window, and announcements branch based on `V7.14-14`
- `V7.15-2` is the invoice settings restrictions and print preview optimization branch based on `V7.14-15`
- `V7.15-3` is the initial backend implementation of the staff edit endpoints branch
- `V7.15-4` is the announcement history viewing branch
- `V7.15-5` is the active branch representing combined Staff management and Announcement history additions
- `V7.15-6` is the operator plans list view layout redesign branch
- `V7.15-7` is the index.html unnecessary script cleanup branch
- `V7.15-8` is the Admin Env Settings and Service Refactor branch
- `V7.15-9` is the Settings Consolidation and Caddy Optimization branch
- `V7.15.10` is the Docker Infrastructure Optimization branch (current)

### V7.16.6 Changes (Current)

**Primary Focus:** WhatsApp Service CI/CD & Deployment Fix

**GitHub Actions:**
- Added missing `whatsapp-service` build and push automated steps to `docker-build-push.yml`.
- Configured automated image builds and storage on Docker Hub for backend, frontend, and whatsapp services.
- Automated deployment from `live` branch with internal code pull and container restart on migration servers.

**Bug Fixes:**
- Fixed `pull access denied` error for `ebill-whatsapp` image by ensuring it is built and pushed to Docker Hub by CI/CD.

---

### V7.15.10 Changes

**Primary Focus:** Docker & Environment Infrastructure Optimization

**Docker Architecture:**
- Dual compose files: `docker-compose.yml` (development) and `docker-compose.prod.yml` (production)
- Development compose includes exposed ports, all services, minimal resource limits, Caddy for local routing
- Production compose uses internal networking, optimized resource limits, structured logging, auto-restart policies
- Both tested and verified with full container health checks passing

**Environment Configuration:**
- Reduced .env from 40+ variables to only 8-10 core essentials (DOMAIN, MONGO_URI, JWT_SECRET, BACKUP_PASSWORD, DB_NAME, CORS_ORIGINS, REACT_APP_BACKEND_URL)
- Most optional settings (Email, WhatsApp, Payment) now managed exclusively via Admin Settings UI
- Clear separation of deployment configuration and business logic

**Docker Image Improvements:**
- Multi-stage backend Dockerfile with conditional build dependencies based on BUILD_ENV argument
- Development mode builds include requirements_local.txt (with dev tooling)
- Production mode builds with requirements.txt only (minimal footprint)
- Health checks on all container services for reliable startup detection

**MongoDB Authentication Fix:**
- Resolved critical "command find requires authentication" error
- Updated docker-compose files to use authenticated MONGO_URI: `mongodb://user:pass@mongodb:27017/db?authSource=admin`
- Proper handling of credentials via environment variable interpolation
- Tested authentication flow in both dev and prod setups

**Python Configuration Enhancements:**
- `backend/config.py` now environment-aware with IS_PRODUCTION and IS_DEVELOPMENT flags
- Feature flags dictionary (email, whatsapp, razorpay, scheduler, api_docs, etc.) based on available integrations
- Validation: JWT_SECRET and BACKUP_PASSWORD required in production, optional in development
- LOG_LEVEL configuration drives debug vs info level logging based on environment
- CORS_ORIGINS properly parsed and validated from configuration

**Database Connection Improvements:**
- `backend/database.py` cleaner priority-based MONGO_URI resolution
- Support for both authenticated and fallback connection methods
- Proper URL encoding for special characters in credentials
- Better error messages and documentation

**Server Initialization Cleanup:**
- `backend/server.py` removes redundant `.env` generation (now via docker/init-env.sh)
- CORS middleware reads from centralized config
- Logging uses environment-aware LOG_LEVEL from configuration
- All env setup consolidated in initialization phase

**Container Initialization Optimization:**
- `docker/init-env.sh` reduced to ~30 lines (was ~45), focused on core variables only
- Clear documentation distinguishing between .env variables and Admin Settings configuration
- Better suited for containerized orchestration and cloud deployments

**Documentation:**
- `DOCKER_QUICK_REFERENCE.md`: Daily development commands, testing procedures, troubleshooting
- `DOCKER_OPTIMIZATION_V7_15_10.md`: Comprehensive guide with deployment instructions, dev vs prod comparison
- Updated `.env.example` with detailed inline documentation, dev/prod examples, environment-specific guidance

**Testing & Validation:**
✅ Docker build successful (backend + frontend multi-stage builds)
✅ All containers start and reach healthy state
✅ Backend API responding: `{"status":"healthy"...}`
✅ Frontend serving React app: HTTP 200
✅ MongoDB authentication verified with no credential errors
✅ CORS properly configured
✅ Health checks all containers functional

**Files Modified:**
- docker-compose.yml (dev environment)
- docker-compose.prod.yml (prod environment) 
- backend/Dockerfile (conditional builds)
- backend/config.py (env-aware config)
- backend/database.py (improved MongoDB URI)
- backend/server.py (removed redundant logic)
- docker/init-env.sh (optimized to core vars)
- .env.example (comprehensive docs)
- DOCKER_QUICK_REFERENCE.md [NEW]
- DOCKER_OPTIMIZATION_V7_15_10.md [NEW]

---

## Critical Implementation Notes

### MongoDB Authentication
- Must use full authenticated URI in docker-compose: `mongodb://user:password@mongodb:27017/db?authSource=admin`
- Do not use `mongodb://mongodb:27017/db` without credentials - will fail on connected backend
- Credentials from .env variables interpolated directly into docker-compose

### Environment Variable Priority (backend/config.py)
1. Check for explicit environment variable (e.g., MONGO_URI)
2. Fall back to building from components (MONGO_HOST, MONGO_PORT, etc.)
3. Final fallback to hardcoded defaults

### Feature Flags
- Email features enabled only if RESEND_API_KEY or SMTP_HOST is set
- WhatsApp features enabled only if WHATSAPP_ACCESS_TOKEN is set
- Razorpay features enabled only if RAZORPAY_KEY_ID is set
- API docs (/openapi.json, /docs) disabled in production

### Development vs Production
| Aspect | Dev | Prod |
|--------|-----|------|
| Requirements | requirements_local.txt | requirements.txt |
| Ports | Exposed on 8000, 3000 | Internal network only |
| Logging | Console output, DEBUG level | JSON files, INFO level |
| Resource Limits | Low for dev machines | High for production load |
| API Docs | ✅ Enabled | ❌ Disabled |
| Auto-restart | unless-stopped | always |

---

### Previous Branch: V7.15-9

Settings Consolidation and Caddy Optimization focused on:
- Admin settings UI consolidation with removal of orphaned elements
- Security tab with JWT secret and backup password fields
- .env auto-generation from database settings
- Caddy proxy with security headers and header propagation
- HTTP vs HTTPS configuration separation
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
  - richer SEO/Open Graph/Twitter/schema metadata
  - installable web app support with manifest, icons, and service worker
  - cron settings persistence now refreshes correctly in the UI
  - auto-backup entries now appear in the backup list after cron completion
  - email settings now reload the latest saved values after save/refresh
  - admin can assign payment gateway keys directly to operators
  - operator settings no longer expose payment gateway configuration
  - browser cache clear tools now exist in admin/operator settings
  - login/session switching now clears stale cache automatically
  - admin display-name changes are supported from settings
  - Resend and SMTP test mail actions are available
  - SMTP fallback now tolerates servers without AUTH support
  - operator invoice bulk upload with sample CSV/XLSX flow is now available
  - invoice settings fall back to the registration/profile address when the company address is empty
  - invoice logos persist immediately and render correctly via `/api/uploads`
  - operator dashboard monthly value stats are now shown
  - SMTP sending/testing is more tolerant, including implicit SSL on port 465
  - admin-created operators now receive referral codes automatically
  - referral benefits/settings now live in admin general settings
  - invoice image upload button is permanently disabled
  - invoice show logo toggle is always OFF and disabled
  - backend `PUT /operator/staff/{staff_id}` endpoint implemented alongside `StaffUpdate` model
  - operator UI "Account Status" toggle added to Staff Edit dialogue
- detailed view dialog added to the announcement history page via "Eye" icon
- operator plans layout upgraded to an organized data table list view
- optimized Razorpay by converting to a dynamic script loader (`lib/razorpay.js`) to eliminate global preload console warnings
- removed unnecessary legacy scripts (PostHog and error handler) from `index.html` to improve performance and code cleanliness
- migrated sensitive environment variables (JWT, Razorpay, Resend, WhatsApp) to a secure, database-backed "Env" tab in Admin Settings
- implemented centralized `env_service.py` for prioritized setting retrieval with fallbacks
- refactored WhatsApp and Razorpay services with async factory functions for dynamic configuration
- updated email and cron services to utilize database-backed environment settings
- FIXED: Resolved a `ReferenceError: fetchEmailConfig is not defined` in `Settings.jsx` that caused the Admin Settings page to crash


---

## Most Recent Delivery

### Branch Flow
- `V7.14-6` was created and pushed from `V7.14-5`
- `V7.14-7` was created and pushed from `V7.14-6`
- `V7.14-8` is the documentation update branch based on `V7.14-7`
- `V7.14-9` is the scheduler reliability fix branch based on `V7.14-8`
- `V7.14-10` is the title, email fallback, and cron-settings branch based on `V7.14-9`
- `V7.14-11` is the metadata and installable web app branch based on `V7.14-10`
- `V7.14-12` is the cache clearing, admin profile, and email test branch based on `V7.14-11`
- `V7.14-13` is the invoice bulk upload, address fallback, and logo rendering branch based on `V7.14-12`
- `V7.14-14` is the dashboard stats, SMTP stability, and referral automation branch based on `V7.14-13`
- `V7.14-15` is the operator referral codes, logo reorganization, renewal window, and announcements branch based on `V7.14-14`
- `V7.15-2` is the invoice settings restrictions and print preview optimization branch based on `V7.14-15`
- `V7.15-3` is the initial backend implementation of the staff edit endpoints branch
- `V7.15-4` is the announcement history viewing branch
- `V7.15-5` is the active branch representing combined Staff management and Announcement history additions
- `V7.15-6` is the operator plans list view layout redesign branch
- `V7.15-7` is the index.html unnecessary script cleanup branch
- `V7.15-8` is the Admin Env Settings and Service Refactor branch


### V7.15-2 Changes

Primary files:
- [frontend/src/pages/operator/Settings.jsx](/d:/eBill/frontend/src/pages/operator/Settings.jsx)

Implemented behavior:
- Disabled image upload button in operator invoice settings (appears grayed out and non-functional).
- Disabled "Show Logo" toggle switch in invoice visible fields section (always OFF, cannot be changed).

### V7.14-15 Changes

Primary files:
- [frontend/public/index.html](/d:/eBill/frontend/public/index.html)
- [frontend/public/manifest.json](/d:/eBill/frontend/public/manifest.json)
- [frontend/public/sw.js](/d:/eBill/frontend/public/sw.js)
- [frontend/public/icon-192.png](/d:/eBill/frontend/public/icon-192.png)
- [frontend/public/icon-512.png](/d:/eBill/frontend/public/icon-512.png)
- [frontend/public/apple-touch-icon.png](/d:/eBill/frontend/public/apple-touch-icon.png)
- [frontend/src/index.js](/d:/eBill/frontend/src/index.js)

Implemented behavior:
- Added richer SEO metadata, canonical tags, Open Graph tags, and Twitter card tags.
- Added JSON-LD schema markup for organization and software application identity.
- Added web app manifest and install icons.
- Added lightweight service worker registration for installability support.
- Enabled supported browsers to surface install/add-to-home-screen UI on deployed HTTPS builds.
- Settings saves now rehydrate the persisted cron/email values in the UI.
- Backup list refresh now shows scheduled auto-backups after completion.
- Admin can assign payment gateway credentials to specific operators from the admin settings dialog.
- Operator payment gateway configuration is now admin-managed and removed from the operator panel.

### V7.14-12 Changes

Primary files:
- [frontend/src/App.js](/d:/eBill/frontend/src/App.js)
- [frontend/src/pages/admin/Settings.jsx](/d:/eBill/frontend/src/pages/admin/Settings.jsx)
- [frontend/src/pages/operator/Settings.jsx](/d:/eBill/frontend/src/pages/operator/Settings.jsx)
- [frontend/public/sw.js](/d:/eBill/frontend/public/sw.js)
- [frontend/src/lib/browserCache.js](/d:/eBill/frontend/src/lib/browserCache.js)
- [backend/routers/admin.py](/d:/eBill/backend/routers/admin.py)
- [backend/routers/auth.py](/d:/eBill/backend/routers/auth.py)
- [backend/services/email_service.py](/d:/eBill/backend/services/email_service.py)
- [backend/models.py](/d:/eBill/backend/models.py)

Implemented behavior:
- Added browser/app cache clear actions in admin and operator settings.
- Automatically clears browser/app cache when login state changes or sessions switch.
- Service worker no longer caches `/api` responses.
- Admin settings now allow changing the admin display name.
- Email settings now include Resend test mail and SMTP test mail actions.
- SMTP fallback now skips login when `AUTH` is not offered by the server.

### V7.14-13 Changes

Primary files:
- [frontend/src/pages/operator/Invoices.jsx](/d:/eBill/frontend/src/pages/operator/Invoices.jsx)
- [frontend/src/pages/operator/Settings.jsx](/d:/eBill/frontend/src/pages/operator/Settings.jsx)
- [frontend/src/pages/PublicInvoice.jsx](/d:/eBill/frontend/src/pages/PublicInvoice.jsx)
- [frontend/src/lib/mediaUrl.js](/d:/eBill/frontend/src/lib/mediaUrl.js)
- [backend/server.py](/d:/eBill/backend/server.py)
- [backend/routers/operator.py](/d:/eBill/backend/routers/operator.py)
- [backend/services/invoice_view_service.py](/d:/eBill/backend/services/invoice_view_service.py)
- [backend/services/pdf_service.py](/d:/eBill/backend/services/pdf_service.py)

Implemented behavior:
- Added operator invoice bulk upload with sample CSV/XLSX flow.
- Added invoice company-address fallback from the operator registration/profile address when invoice address is empty.
- Persisted uploaded invoice logos immediately and served them through backend `/api/uploads` URLs.
- Fixed invoice logo preview in operator settings and logo rendering on the public invoice page.

### V7.14-14 Changes

Primary files:
- [frontend/src/pages/operator/Dashboard.jsx](/d:/eBill/frontend/src/pages/operator/Dashboard.jsx)
- [frontend/src/pages/admin/Settings.jsx](/d:/eBill/frontend/src/pages/admin/Settings.jsx)
- [backend/routers/admin.py](/d:/eBill/backend/routers/admin.py)
- [backend/routers/operator.py](/d:/eBill/backend/routers/operator.py)
- [backend/routers/auth.py](/d:/eBill/backend/routers/auth.py)
- [backend/services/email_service.py](/d:/eBill/backend/services/email_service.py)
- [backend/utils.py](/d:/eBill/backend/utils.py)

Implemented behavior:
- Added richer operator dashboard monthly value statistics.
- Hardened SMTP sending/testing, including implicit SSL support on port 465 and clearer timeout/disconnect errors.
- Automatically generated referral codes for admin-created operators.
- Moved referral benefits/settings into admin general settings and wired referral calculations to those values.

---

## Validation Completed Locally

- `npm run build` in `frontend/`

Build result:
- backend compile check succeeded

---

## Outstanding Validation

See [PENDING_TESTS.md](/d:/eBill/memory/PENDING_TESTS.md) for the live list.

Highest-value remaining checks:
- validate social previews against live `https://e-bill.in/`
- verify manifest/service worker behavior on production HTTPS
- verify install/add-to-home-screen UI appears on supported browsers/devices
- continue VPS scheduler and email fallback verification from `V7.14-10`
- verify settings save/reload and backup list refresh behavior in a deployed environment
- verify admin-assigned operator gateway keys work for subscriber payment links
- verify cache clear behavior across login/session switches
- verify admin display-name updates persist after refresh/login
- verify Resend and SMTP test mail actions against live providers

---

## Current Documentation State

The following files were refreshed on `V7.14-14`:
- [README.md](/d:/eBill/README.md)
- [memory/CHANGELOG.md](/d:/eBill/memory/CHANGELOG.md)
- [memory/ROADMAP.md](/d:/eBill/memory/ROADMAP.md)
- [memory/PRD.md](/d:/eBill/memory/PRD.md)
- [memory/PENDING_TESTS.md](/d:/eBill/memory/PENDING_TESTS.md)
- [memory/agent-handoff.md](/d:/eBill/memory/agent-handoff.md)
- [frontend/README.md](/d:/eBill/frontend/README.md)

---

## Recommended Next Work

1. Verify dashboard stats, SMTP stability, and referral settings in a live environment.
2. Verify invoice bulk upload, address fallback, and logo rendering in a live environment.
3. Continue payment receipt and messaging improvements.

---

## Git State At Handoff

- Current branch: `V7.15-8`
- Feature baseline under docs branch: `V7.15-8`

