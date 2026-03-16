# Multi-Tenant SaaS Billing Platform

A production-grade billing platform for ISP/broadband operators. Built with React, FastAPI, and MongoDB.

## Architecture

```
/app/
├── backend/
│   ├── routers/        # API routes (admin, auth, operator, backup, webhooks)
│   ├── services/       # Business logic (cron, PDF, Razorpay, WhatsApp)
│   ├── tests/          # Pytest test suites
│   ├── server.py       # FastAPI entry point + scheduler
│   ├── models.py       # Pydantic schemas
│   ├── database.py     # MongoDB connection
│   ├── config.py       # JWT config
│   ├── dependencies.py # Auth guards
│   ├── audit.py        # Audit logging
│   └── utils.py        # Helpers (ID gen, passwords, invoice numbers)
├── frontend/
│   └── src/
│       ├── pages/admin/     # Admin dashboard pages
│       ├── pages/operator/  # Operator dashboard pages
│       ├── components/      # Layout + Shadcn UI components
│       └── App.js           # Auth provider + routing
└── memory/
    └── PRD.md               # Product requirements
```

## Roles

| Role     | Access                                              |
|----------|-----------------------------------------------------|
| Admin    | Platform management, operator CRUD, SaaS plans, cron triggers |
| Operator | Subscriber billing, invoices, plans, staff, settings |
| Staff    | Read-only access to operator data (no delete)       |

## Key Features

- SaaS subscription billing with Razorpay
- Feature-gating via add-on system
- Auto invoice generation (daily cron at 06:00 UTC)
- Payment reminder scheduling (daily cron at 07:00 UTC)
- Subscription expiry checks (daily at 01:00 UTC)
- WhatsApp Business API integration
- PDF invoice generation (Classic & Modern templates)
- Admin impersonation for operator support
- Audit logging with search/filter/pagination
- Backup & restore system

## Credentials

- **Admin**: admin@saas.com / admin123
- **Seed**: `POST /api/seed`

## Local Setup

See `requirements_local.txt` in both `backend/` and `frontend/` for dependency lists.

## Docker Deployment

The app is Docker-ready with Caddy in front of the React frontend and FastAPI backend.

1. Set a public DNS record for your domain to this server's IP.
2. Start the stack once. Docker will create a missing root `.env` automatically with placeholder values.
3. Update the generated `.env` with your real domain, secrets, and provider credentials.
4. Restart the stack:

```bash
docker compose up -d --build
```

Notes:
- Caddy serves HTTPS automatically on port `443` and redirects/provisions certificates for `DOMAIN`.
- Keep ports `80` and `443` open publicly for automatic certificate issuance and renewal.
- Backend and frontend are only exposed inside the Docker network; Caddy is the only public entrypoint.
- All app settings now live in the root `.env`; `backend/.env` and `frontend/.env.local` are no longer required.
- Default env templates are also available in `.env.example`.
