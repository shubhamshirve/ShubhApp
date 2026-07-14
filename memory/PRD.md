# E-Bill — Product Requirements Document
<!-- Current Version: V9.47 -->

## Product Summary

Multi-tenant SaaS billing platform for ISP, broadband, and cable operators. Supports platform admins, business operators, and staff with role-based access.

## Roles

| Role | Key Capabilities |
|------|----------------|
| **Admin** | Manage operators, SaaS plans, addons, wallets, payment gateways, reports, impersonation, platform settings |
| **Operator** | Manage subscribers, plans, invoices, staff, settings, subscription, reports |
| **Staff** | Operator-side access with no destructive delete permissions |

## Tech Stack

- **Frontend:** React, React Router, Axios, Tailwind, shadcn/ui (Radix)
- **Backend:** FastAPI, Motor/PyMongo, APScheduler
- **Auth:** JWT (single active session per user), admin impersonation
- **Infra:** Docker Compose, Caddy, MongoDB 4.4

## Core Business Rules

- One active session per user — new login invalidates previous token
- Pending invoices are editable; paid invoices protected from operator cancellation
- Password recovery via email OTP only (WhatsApp discontinued)
- Public online payments store mode as `"online"`
- Subscriber plans stored as embedded array (up to 5 per subscriber)
- Subscriber `plan_expiry_date` syncs from invoice **creation/update** (not payment); hybrid rule: only move forward — `new_expiry = max(old_plan_expiry_date, line_item.service_end_date)`. New plans on an invoice are auto-added to `subscriber.plans[]`. Custom line items are skipped.
- Bulk subscriber CSV: one row per subscriber, plan columns suffixed `_1` through `_5`
- Wallet crediting is GST-exclusive
- Operator payment gateway keys enforced on public payments (no platform fallback)
- Staff cannot perform destructive deletes

## Key Workflows

1. **Subscriber lifecycle:** Create (with 1–5 plans) → Invoice auto-generated → Reminder sent → Expiry check → Renewal
2. **Payment flow:** Invoice generated → Payment link shared → Payment via Razorpay → Status updated → Receipt (planned)
3. **Bulk upload:** Download sample CSV → Fill data → Upload → Background job → Poll for result
4. **Admin impersonation:** Admin selects operator → Assumes operator session → Return to admin

## Scheduled Automation (IST, admin-configurable)

| Job | Default Time |
|-----|-------------|
| Auto Backup | 03:00 |
| Expiry Check | 00:05 |
| Invoice Generation | 08:00 |
| Reminder Processing | 10:00 |
| Wallet Balance Check | 09:00 |

## CI/CD Architecture (GHCR)

- **Branch:** `live` (triggers GitHub Actions)
- **Pipeline:** Lint → Build Backend (parallel) + Build Frontend (parallel) → SSH Deploy to VPS
- **Registry:** GHCR (`ghcr.io/shubhamshirve/shubhapp-backend` + `-frontend`)
- **VPS Deploy (Option B):** GitHub Actions SSHes in, runs `docker pull` + `docker compose up` (no build on VPS)
- **Watchtower (Option C):** Polls GHCR every 5 min, auto-restarts updated containers
- **Key files:** `.github/workflows/deploy.yml`, `docker-compose.ghcr.yml`, `Makefile`, `DEPLOYMENT.md`
- **Required GitHub Secrets:** `CR_PAT`, `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`, `REACT_APP_BACKEND_URL`

## Current Gaps

- Payment receipt generation and delivery
- Email announcement broadcasts
- GST reconciliation reporting
- WhatsApp Business API notifications (infrastructure ready, not wired to UI)
