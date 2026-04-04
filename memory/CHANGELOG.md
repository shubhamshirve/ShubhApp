# E-Bill Platform — CHANGELOG

## 2026-04-04

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
