# E-Bill — Multi-Tenant ISP & Cable Billing Platform

**Version:** V8.13 | **Branch:** `live` → auto-deploys to production

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
| Admin | Operators, SaaS plans, wallets, gateways, reports, impersonation |
| Operator | Subscribers, plans, invoices, staff, settings, subscription |
| Staff | Operator-side access, restricted permissions (no deletes) |

## Key Features

- JWT auth with single active session enforcement per user
- Multi-plan subscribers — up to 5 plans per subscriber
- Multi-line invoices with branding and public payment links
- Bulk upload: subscribers (multi-plan CSV), plans, invoices
- Wallet management with GST-exclusive crediting
- Payment gateway assignment per operator (Razorpay)
- Admin impersonation and return flow
- Email OTP registration and password recovery (Resend + SMTP fallback)
- Support tickets, audit logs, automated backups
- Maintenance mode, cache management
- Installable PWA (manifest + service worker)
- Admin-configurable scheduled jobs (IST timezone)

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
memory/                   Project docs (changelog, roadmap, PRD)
Caddyfile                 Reverse proxy config
docker-compose.yml        Local dev
docker-compose.prod.yml   Production
```
