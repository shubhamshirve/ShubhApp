# Agent Handoff — E-Bill Platform

**Last Updated:** 2026-04-17
**Active Branch:** `live` (auto-deploys to production)
**Latest Version:** V8.19

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
- Manual payment link generation for operators
- Bulk upload via CSV/XLSX
- **Invoice generation blocked when wallet balance < ₹50** (was ₹100)
- **Generate Payment Link button** only visible for `status=pending` + gateway configured + `accept_payment_gateway=true` in invoice settings
- **Cancelled invoices** shown as 5th card in operator dashboard

### Payments
- Razorpay integration; operator-assigned keys enforced (no platform fallback)
- Direct UPI intent payments (Google Pay, PhonePe, Paytm, BHIM)
- Payment mode and date captured when operator manually marks paid

### WhatsApp
- WhatsApp Cloud API (Meta Business) via `WhatsAppService` in `whatsapp_service.py`
- **Template categories:**
  - `invoice_notification` — new invoice (before due date cron + auto-invoice)
  - `payment_reminder` — on due date
  - `payment_due_reminder` — **overdue** (days_diff < 0); separate template assigned in settings
  - `payment_confirmation` — payment confirmed
  - `announcement` — bulk announcements
  - `custom` — generic
- **Cron reminder logic** (`process_scheduled_reminders`):
  - `days_diff < 0` → uses `payment_due_reminder_template` setting (falls back to `reminder_template`)
  - `days_diff == 0` → uses `reminder_template`
  - `days_diff > 0` → uses `invoice_template`
- **Message logging:** Every send logged to `whatsapp_message_logs` collection with operator_id, template_name, template_category, recipient_phone, status, message_id, wa_id, invoice_id, invoice_number, trigger (`cron`/`manual`/`auto_invoice`), created_at
- **Template testing:** `POST /admin/whatsapp-test-template` — send test to any phone, auto-fill variables with defaults

### WhatsApp Stats (`/admin/whatsapp-stats`)
- Stats: total, today, this month, sent, failed, success rate
- 7-day bar chart, breakdown by category and trigger
- Paginated message logs table (filterable by status, category, date range, search)
- WhatsApp error logs section (from `error_logs` filtered by module)
- API: `GET /admin/whatsapp-stats`, `GET /admin/whatsapp-message-logs`, `DELETE /admin/whatsapp-message-logs`

### Wallets
- GST-exclusive crediting
- Auto-initialized with SaaS plan `monthly_price` when admin creates operator
- **Minimum balance ₹50** to generate invoices (cron skips, manual returns HTTP 402)

### Scheduled Jobs (IST, configurable from admin UI)
- Auto Backup: 03:00 | Expiry Check: 00:05 | Invoice Generation: 08:00
- Reminder Processing: 10:00 | Wallet Check: 09:00

### Other
- Support tickets, audit logs, automated backups
- Maintenance mode, browser cache clear tools
- Discount codes, referral codes
- Installable PWA
- Staff management (no destructive delete access)

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/routers/admin.py` | Admin API (operators, WA templates, WA stats, settings) |
| `backend/routers/operator.py` | Operator API (invoices, subscribers, WA sends, payment links) |
| `backend/services/cron_service.py` | Auto invoice gen, reminder cron, wallet check |
| `backend/services/whatsapp_service.py` | WhatsApp Cloud API + `log_whatsapp_message()` |
| `backend/models.py` | All Pydantic models incl. `WhatsAppTemplateTestRequest` |
| `frontend/src/pages/admin/WhatsAppTemplates.jsx` | Template CRUD + test dialog |
| `frontend/src/pages/admin/WhatsAppStats.jsx` | Stats, logs, error logs |
| `frontend/src/pages/admin/Settings.jsx` | Template assignment (incl. payment_due_reminder) |

---

## Critical Notes

- **MongoDB auth:** Credentials in `.env.production` must match the volume’s initialization credentials. Mismatch = `SCRAM authentication failed` → requires `docker-compose down -v` (data loss)
- **Route ordering:** In FastAPI, static routes (`/subscribers/sample-csv`) must be defined before parameterized ones (`/subscribers/{id}`)
- **Dev vs Prod:** Backend uses `requirements_local.txt` (dev) vs `requirements.txt` (prod) via `BUILD_ENV` Dockerfile arg
- **API docs:** Disabled in production
- **OperatorResponse:** `owner_name` and `status` are Optional with defaults — older operator documents may not have these fields; do NOT make them required again
- **DB name:** Config defaults to `ebill_db` (loaded from `DB_NAME` env var, defaults if absent)

---

## Outstanding Validation

- Social preview / Open Graph tags on production HTTPS
- Web app install (manifest + service worker) on production
- SMTP test mail and fallback delivery in live environment
- Scheduler persistence after server restart
- Payment gateway delegation end-to-end on production
- WhatsApp message log delivery confirmation in production (needs real WA config)
