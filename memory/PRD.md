# SaaS Billing Platform - PRD

## Original Problem Statement
Multi-tenant SaaS billing platform for ISP/broadband operators. Features 3-role system (Admin, Operator, Staff) with JWT auth, feature-gating via add-ons, SaaS subscription billing via Razorpay, end-customer invoicing with PDF generation, and automated cron jobs.

## Architecture
- **Frontend**: React SPA, Tailwind CSS, React Router, Axios, Shadcn/UI
- **Backend**: FastAPI (modular routers), MongoDB (Motor async driver), APScheduler
- **Auth**: JWT with 3 roles + impersonation
- **Structure**:
  ```
  /app/
  ├── backend/
  │   ├── routers/ (admin.py, auth.py, backup.py, operator.py, webhooks.py)
  │   ├── services/ (cron_service.py, pdf_service.py, razorpay_service.py, whatsapp_service.py)
  │   ├── tests/ (pytest suites)
  │   ├── models.py, database.py, config.py, dependencies.py, audit.py, utils.py
  │   └── server.py
  └── frontend/src/
      ├── App.js (AuthProvider + FeaturesContext + Routes)
      ├── components/Layout.jsx (AdminLayout, OperatorLayout, sidebars)
      └── pages/ (admin/, operator/)
  ```

## Pricing Tiers
```python
SUBSCRIBER_TIERS = {250: 500, 500: 1000, 750: 1500, 1000: 2000, 1500: 3000, 2000: 4000, 3000: 5500}
STAFF_TIERS = {0: 0, 5: 100, 10: 200, 20: 300}
```

## Scheduled Jobs (APScheduler)
| Job | Schedule | Description |
|-----|----------|-------------|
| Auto Backup | 02:00 UTC daily | Gzipped JSON backup |
| Expiry Check | 01:00 UTC daily | Mark expired trials/subscriptions |
| Invoice Generation | 06:00 UTC daily | Auto-generate invoices 3 days before billing |
| Reminder Processing | 07:00 UTC daily | Send reminders per operator schedule |

## What's Been Implemented

### Core Platform (Completed)
- Full admin management (operators, SaaS plans, addons, settings, audit logs, reports)
- Operator dashboard (profile, plans, subscribers, invoices, staff, reports)
- JWT auth with 3 roles + impersonation
- Feature-gating via addon system
- Razorpay payment integration
- WhatsApp Business API integration

### Batch 0 — Refactoring (Completed)
- Modularized server.py into routers

### Batch 1 — Features (Completed)
- Bulk CSV/XLSX upload for subscribers and plans
- Add-on management UI in SaaS Plans admin page
- Audit log before/after details modal
- Backup & Restore system (manual + daily scheduled)

### Batch 2 — Features (Completed, Tested 11/11)
1. Dynamic SaaS Plan Pricing (tier dropdowns, real-time price breakdown)
2. Conditional Operator Settings tabs (Payment Gateway & WhatsApp only when impersonating)
3. Addon-gated sidebar links (Announcements, Audit Logs)
4. Operator Audit Logs page (feature-gated)
5. Invoice WhatsApp button logic (API vs Web)
6. Addon-gating backend (audit_log, announcement, payment_gateway)
7. Auto WhatsApp on invoice creation
8. Admin Settings: 3 tabs (General, Payment Gateways, Backup & Restore)

### Batch 3 — Features (Completed)
- Discount codes system (admin CRUD, operator checkout validation)
- Subscription renewal with addon bundling
- Subscriber suspend/activate
- Admin-only subscriber deletion
- Trial plan restrictions (addon purchase, staff creation)

### Batch 4 — Bug Fixes & Features (Completed, Tested 100%)
- Fixed `db.settings` vs `db.global_settings` bug in checkout
- Admin change password (Security tab)
- Backup download feature
- Two invoice templates (Classic/Modern) with operator selection
- Fixed admin settings payment gateway display (masked keys)
- Admin audit log search, filter, pagination
- Auto-invoice generation logic fixes (4 bugs fixed)

### Batch 5 — Payment Reminder Scheduling (Completed Mar 2026, Tested 100%)
1. **Reminder Settings API**: GET/PUT /api/operator/reminder-settings (addon-gated)
2. **Schedule Configuration**: Before due (1,2,3,5,7 days), on due date, after due (1,3,5,7,14,30 days)
3. **Max reminders per invoice**: Configurable limit (1-20)
4. **Cron Processing**: Daily at 07:00 UTC, processes all operator schedules
5. **Duplicate Prevention**: Tracks sent reminders per invoice, prevents same-day duplicates
6. **Admin Manual Trigger**: POST /api/admin/cron/process-scheduled-reminders
7. **Frontend Reminders Tab**: In operator Settings, gated by payment_reminder feature
8. **File Cleanup**: Removed stale root-level test files, updated README

### Deployment and Infra Updates (Mar 2026)
- Dockerized app with `docker-compose.yml` using `init-env`, `mongodb`, `backend`, `frontend`, and `caddy`.
- Added Caddy reverse proxy in `Caddyfile`:
  - serves frontend
  - proxies `/api/*` to FastAPI
  - uses automatic HTTPS for `DOMAIN`
  - uses `tls internal` fallback for `SERVER_IP`
- Mongo image pinned to `mongo:4.4` because the target VM CPU lacks AVX support and Mongo 5+ failed to start.
- Backend Docker env is normalized to container-safe Mongo values:
  - `MONGO_URL=mongodb://mongodb:27017/${DB_NAME}`
  - `MONGO_URI=mongodb://mongodb:27017/${DB_NAME}`
  - `DB_NAME=saas_db` by default
- Backend code now accepts both `MONGO_URL` and `MONGO_URI`.
- Frontend was adjusted for same-origin deployment behind Caddy, so `REACT_APP_BACKEND_URL` can be blank in production.

### Environment Strategy (Current)
- Standard is now a single shared root `.env`.
- `backend/.env` and `frontend/.env.local` are no longer required.
- Docker bootstraps a missing root `.env` via `docker/init-env.sh`.
- Backend local/dev code loads root `.env` and falls back to:
  - `mongodb://localhost:27017/saas_db`
  - `DB_NAME=saas_db`
- Frontend CRACO config reads env from the root `.env`.
- `setup.bat` now creates only one root `.env` containing backend, frontend, Docker, Caddy, Razorpay, WhatsApp, and backup variables.
- Seed/bootstrap code in `backend/server.py` also creates the root `.env` if missing.
- Test `backend/tests/test_iteration7_impersonation.py` was updated to read `/app/.env`.

### Workspace Cleanup and Repo Hygiene (Mar 2026)
- Removed archived/local clutter from the repo:
  - `v7/`
  - `eBill.zip`
  - `backups/`
  - multiple root-level standalone test/debug scripts
- Cleaned generated artifacts like `frontend/build/` and stray `__pycache__` directories.
- Updated ignore rules and kept `.env.example` as the tracked template.

### Branch History Relevant to Current State
- `V7.6` contains Docker/Caddy setup, Mongo compatibility fixes, SSL fallback, workspace cleanup, and deployment fixes.
- `V7.7` is branched from `V7.6` and adds the single-root-`.env` consolidation.
- Latest important commits:
  - `8c28d18` Update frontend index page
  - `3b1a7f7` Consolidate app configuration into root env

### Known Deployment Notes
- If HTTPS shows `ERR_SSL_PROTOCOL_ERROR`, first confirm the root `.env` exists and `DOMAIN` is set correctly before recreating Caddy.
- Production values used during debugging:
  - domain: `e-bill.in`
  - server IP: `45.196.196.21`
- For publicly trusted SSL, DNS must point to the server and ports `80` and `443` must be open.
- Visiting by raw IP uses Caddy internal TLS and may show a browser certificate warning.
- A `401` on `/api/auth/me` is expected when not logged in and is not itself a deployment failure.

## Key API Endpoints
- `GET /api/operator/features` — Active features for current operator
- `GET/PUT /api/operator/reminder-settings` — Reminder schedule configuration
- `POST /api/admin/cron/process-scheduled-reminders` — Manual trigger
- `POST /api/admin/cron/generate-invoices` — Manual invoice generation
- `GET /api/admin/audit-logs` — Filterable audit logs
- `PUT /api/auth/change-password` — Change password
- `GET /api/admin/backup/download/{id}` — Download backup

## Test Credentials
- **Admin**: admin@saas.com / admin123
- **Seed**: POST /api/seed

## Backlog

### P1
- Better 403 page for feature-gated routes
- Operator plan page showing active vs available addons

### P2
- MongoDB indexes on high-cardinality fields
- Pagination on high-volume lists (subscribers, invoices)

### P3
- authAxios useMemo optimization in App.js
- Invoice number generation concurrency safety
- Review/deprecate legacy renew-subscription endpoint
- Configurable WhatsApp template names
