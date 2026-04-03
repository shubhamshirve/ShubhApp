# Agent Handoff — E-Bill Platform

**Last Updated:** 2026-04-03
**Active Branch:** `live` (auto-deploys to production)
**Latest Version:** V8.8

---

## Current State

### Infrastructure
- Production server: `/root/ShubhApp` on VPS
- Docker Compose: `docker-compose.prod.yml` (backend, frontend, mongodb, caddy, init-env)
- CI/CD: GitHub Actions on push to `live` → builds images → Docker Hub → SSH deploy
- WhatsApp WebJS service: **fully removed** (decommissioned in V8.6, source deleted)

### Auth & Sessions
- JWT with single active session enforcement per user
- Email OTP registration and password recovery (Resend + SMTP fallback)
- Admin impersonation flow with return capability

### Subscribers
- Up to 5 plans per subscriber (stored as embedded array in subscriber document)
- Bulk upload via CSV/XLSX: columns `plan_name_1..5`, `billing_date_1..5`, `discount_1..5`
- Duplicate WhatsApp check on bulk upload; subscriber limit enforced from SaaS plan

### Invoices
- Multi-line invoices with operator branding
- Public links and public payment verification
- Bulk upload via CSV/XLSX

### Payments
- Razorpay integration; operator-assigned keys enforced (no platform fallback)
- Payment mode and date captured when operator manually marks paid

### Scheduled Jobs (IST, configurable from admin UI)
- Auto Backup: 03:00 | Expiry Check: 00:05 | Invoice Generation: 08:00
- Reminder Processing: 10:00 | Wallet Check: 09:00

### Wallets
- GST-exclusive crediting
- Auto-initialized with SaaS plan `monthly_price` when admin creates operator

### Other
- Support tickets, audit logs, automated backups
- Maintenance mode, browser cache clear tools
- Discount codes, referral codes
- Installable PWA
- Staff management (no destructive delete access)

---

## Critical Notes

- **MongoDB auth:** Credentials in `.env.production` must match the volume's initialization credentials. Mismatch = `SCRAM authentication failed` → requires `docker-compose down -v` (data loss)
- **Route ordering:** In FastAPI, static routes (`/subscribers/sample-csv`) must be defined before parameterized ones (`/subscribers/{id}`)
- **Dev vs Prod:** Backend uses `requirements_local.txt` (dev) vs `requirements.txt` (prod) via `BUILD_ENV` Dockerfile arg
- **API docs:** Disabled in production

---

## Outstanding Validation

- Social preview / Open Graph tags on production HTTPS
- Web app install (manifest + service worker) on production
- SMTP test mail and fallback delivery in live environment
- Scheduler persistence after server restart
- Payment gateway delegation end-to-end on production
