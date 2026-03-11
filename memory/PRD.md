# SaaS Billing Platform - PRD

## Original Problem Statement
Refactor and build a multi-tenant SaaS billing platform. Initial request: analyze code, remove obsolete PHP files, modularize backend. Then implement two batches of features.

## Architecture
- **Frontend**: React SPA, Tailwind CSS, React Router, Axios, Shadcn/UI
- **Backend**: FastAPI (modular routers), MongoDB, APScheduler
- **Structure**:
  ```
  /app/
  ├── backend/
  │   ├── routers/ (admin.py, auth.py, backup.py, operator.py)
  │   ├── services/ (cron_service.py, pdf_service.py, razorpay_service.py, whatsapp_service.py)
  │   ├── models.py, database.py, config.py, dependencies.py, audit.py, utils.py
  │   └── server.py
  └── frontend/src/
      ├── App.js (AuthProvider + FeaturesContext + Routes)
      ├── components/Layout.jsx (AdminLayout, OperatorLayout, sidebars)
      └── pages/ (admin/, operator/)
  ```

## What's Been Implemented

### Batch 0 — Refactoring (Completed)
- Removed PHP files, modularized server.py into routers

### Batch 1 — Features (Completed, Tested)
- Bulk CSV/XLSX upload for subscribers and plans
- Add-on management UI moved into SaaS Plans admin page
- Audit log before/after details modal
- Backup & Restore system (manual + daily scheduled at 02:00 UTC)

### Batch 2 — Features (Completed Mar 2026, Tested 11/11)
1. **Dynamic SaaS Plan Pricing**: Tier dropdowns (subscribers: 250–3000, staff: 0–20), real-time price breakdown = subscriber_tier + staff_tier + addons
2. **Conditional Operator Settings tabs**: Payment Gateway & WhatsApp tabs only visible when admin is impersonating
3. **Addon-gated sidebar links**: Announcements (announcement addon), Audit Logs (audit_log addon)
4. **Operator Audit Logs page**: /operator/audit-logs (feature-gated, 403 if no addon)
5. **Invoice WhatsApp button logic**: "Send via WhatsApp API" when payment_reminder addon active, else "Send via WhatsApp Web"
6. **Addon-gating backend**: audit_log, announcement (3/day limit), payment_gateway addons gate their respective endpoints
7. **Auto WhatsApp on invoice creation**: If payment_reminder addon active
8. **Admin Settings**: 3 tabs — General, Payment Gateways, Backup & Restore (Addons tab removed)

## Pricing Tiers (backend models.py)
```python
SUBSCRIBER_TIERS = {250: 500, 500: 1000, 750: 1500, 1000: 2000, 1500: 3000, 2000: 4000, 3000: 5500}
STAFF_TIERS = {0: 0, 5: 100, 10: 200, 20: 300}
```

## Key API Endpoints
- `GET /api/operator/features` — Returns active features for current operator
- `POST /api/admin/saas-plans` / `PUT /api/admin/saas-plans/{id}` — Tier-based plan creation
- `GET /api/operator/audit-logs` — Requires audit_log addon
- `POST /api/operator/announcements` — Requires announcement addon, 3/day limit
- `POST /api/operator/payment-gateway` — Requires payment_gateway addon
- `GET /api/admin/backup/list`, `POST /api/admin/backup/create`, etc.

## Test Credentials
- **Admin**: admin@saas.com / admin123
- **Seed**: POST /api/seed

## Backlog (P2)
- Better 403 page for feature-gated routes (currently shows empty state + toast)
- authAxios useMemo optimization in App.js
- Operator plan page showing which addons are active/available
- Payment reminder automation scheduling (currently triggers on invoice creation only if WhatsApp configured)
