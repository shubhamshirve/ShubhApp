# E-Bill — Multi-Tenant ISP & Cable Billing Platform

**Version:** V9.48 | **Branch:** `live` → auto-deploys to production

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React + Tailwind + shadcn/ui |
| Backend | FastAPI + Motor + MongoDB |
| Reverse Proxy | Caddy (auto HTTPS) |
| Infra | Docker Compose (dev + prod) |
| CI/CD | GitHub Actions → Docker Hub → SSH deploy |

## CI/CD Flow

```
git push origin live
  → GitHub Actions builds backend + frontend images
  → Pushes to Docker Hub
  → SSHs into /root/ShubhApp on production server
  → docker-compose pull + up -d
```

## Roles

| Role | Capabilities |
|------|-------------|
| Admin | Operators, SaaS plans, wallets, gateways, reports, impersonation, WA stats |
| Operator | Subscribers, plans, invoices, staff, settings, subscription |
| Staff | Operator-side access, restricted permissions (no deletes) |

## Key Features

### Billing & Invoicing
- Multi-plan subscribers — up to 5 plans per subscriber
- Multi-line invoices with operator branding and public payment links
- Bulk upload: subscribers (multi-plan CSV), plans, invoices
- Auto invoice generation via scheduled cron (blocked if wallet < ₹50)
- Cancelled invoice tracking in operator dashboard

### Payments
- Razorpay payment gateway per operator (own keys required)
- Direct UPI payments via intent links (Google Pay, PhonePe, Paytm, BHIM)
- Payment link generation — visible only for pending invoices with gateway configured and accepted in invoice settings
- UPI transaction note auto-prefilled with plan + tenure

### WhatsApp
- WhatsApp Cloud API integration (Meta Business)
- Template categories: Invoice Notification, Payment Reminder, **Payment Due Reminders** (overdue), Payment Confirmation, Announcement, Custom
- Overdue invoices use a dedicated `payment_due_reminder` template (separate from on-due-date reminders)
- Template assignment per category in admin settings
- **Template testing:** Send test messages to any phone number directly from the template list
- **WA Stats page:** Message logs, delivery stats, 7-day chart, error logs
- All sends logged to `whatsapp_message_logs` collection (operator, template, status, message ID)

### Auth & Access
- JWT with single active session enforcement per user
- Email OTP registration and password recovery (Resend + SMTP fallback)
- Admin impersonation with return flow

### Admin
- Wallet management with GST-exclusive crediting (auto-init on operator create)
- WhatsApp Stats & Reports dashboard
- Support tickets, audit logs, automated backups
- Maintenance mode, cache management
- Discount codes, referral codes

### Infrastructure
- Installable PWA (manifest + service worker)
- Admin-configurable scheduled jobs (IST timezone)
- DB-backed env settings (`env_service.py`)

## Scheduled Jobs (IST)

| Job | Time |
|-----|------|
| Auto Backup | 03:00 |
| Expiry Check | 00:05 |
| Invoice Generation | 08:00 |
| Reminder Processing | 10:00 |
| Wallet Check | 09:00 |

## Dev Quick Start

```bash
cp .env.development .env
docker-compose up -d --build
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000/docs
```

## Production Setup

```bash
# /root/ShubhApp/.env.production must contain:
# DOMAIN, MONGO_ROOT_USERNAME, MONGO_ROOT_PASSWORD, JWT_SECRET,
# REACT_APP_BACKEND_URL, CORS_ORIGINS, BACKUP_PASSWORD

docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

> **MongoDB Auth Note:** Credentials in `.env.production` must match what MongoDB was
> first initialized with. A mismatch requires a volume reset: `docker-compose down -v`

## Project Structure

```
backend/                  FastAPI app (routers, services, models)
frontend/                 React app (CRA + craco)
docker/                   Init scripts
.github/workflows/        GitHub Actions CI/CD
memory/                   Project docs (changelog, roadmap, PRD, agent-handoff)
Caddyfile                 Reverse proxy config
docker-compose.yml        Local dev
docker-compose.prod.yml   Production
```

## Key Business Rules

- Invoice generation blocked when operator wallet balance < **₹50**
- WhatsApp API send costs **₹0.50** per message (deducted from operator wallet)
- Payment link button only visible for **pending** invoices with gateway keys configured
- Overdue reminders use `payment_due_reminder` template; on-due-date uses `payment_reminder`
