# E-Bill Multi-Tenant Billing Platform

Production-oriented billing platform for ISP, broadband, and cable operators. The stack uses React on the frontend, FastAPI on the backend, MongoDB for persistence, and Docker Compose with Caddy for deployment.

## Current Version

- Documentation updated for branch line `V7.14-14`
- Latest feature and fix delivery implemented through `V7.14-14`
- Current release focus:
  - single active session per user
  - email-only password recovery OTP
  - pending invoice edit support
  - payment confirmation dialog with mode/date capture
  - VPS cron scheduler reliability fix
  - app title updated to `E-Bill | Invoice Automation Software`
  - Resend email fallback via SMTP/local transport support
  - admin-configurable cron timings in settings
  - richer SEO metadata, Open Graph, Twitter cards, and schema markup
  - installable web app support with manifest, icons, and service worker
  - cron timing persistence refresh in settings after save
  - auto-backup entries refresh correctly in the backup list
  - email settings refresh correctly after save/reload
  - admin can assign payment gateway keys directly to operators
  - operator-side payment gateway settings removed from the panel
  - browser and app cache clear tools in admin/operator settings
  - automatic cache clear on login/session switch
  - admin display-name edits from settings
  - Resend and SMTP test mail actions
  - SMTP fallback compatibility when AUTH is unavailable
  - operator invoice bulk upload with sample CSV/XLSX flow
  - invoice address fallback from registration/profile data
  - invoice logo preview/persistence/render fixes
  - backend-served `/api/uploads` asset URLs

## Architecture

```text
d:\eBill
|-- backend/
|   |-- routers/          FastAPI route modules
|   |-- services/         email, PDF, cron, Razorpay, WhatsApp helpers
|   |-- tests/            pytest suites
|   |-- server.py         FastAPI entrypoint + scheduler bootstrap
|   |-- models.py         Pydantic models
|   |-- dependencies.py   auth/session/role guards
|   |-- database.py       Mongo connection
|   `-- utils.py          JWT, password, ids, invoice helpers
|-- frontend/
|   |-- src/
|   |   |-- pages/admin/
|   |   |-- pages/operator/
|   |   |-- components/
|   |   `-- App.js
|   `-- package.json
|-- docker/
|-- memory/
|   |-- PRD.md
|   |-- ROADMAP.md
|   |-- CHANGELOG.md
|   |-- PENDING_TESTS.md
|   `-- agent-handoff.md
|-- docker-compose.yml
|-- Caddyfile
`-- .env.example
```

## Roles

| Role | Access |
|------|--------|
| Admin | platform settings, operators, plans, addons, wallets, reports, support, impersonation |
| Operator | subscribers, plans, invoices, staff, settings, subscription, reports |
| Staff | operator-side access with permission limits; destructive delete routes remain blocked |

## Key Features

- JWT auth with admin, operator, and staff roles
- configurable session timeout plus single-session enforcement
- admin impersonation and return flow
- email OTP registration and password recovery
- multi-plan subscribers and multi-line invoices
- operator invoice branding, logo upload, and public invoice links
- invoice-number based public invoice URLs with legacy fallback
- operator payment links and public payment verification
- payment mode/date capture when invoices are manually marked paid
- admin wallet credit, debit, and suspend operations
- maintenance mode with app-wide read-only behavior
- global reminder scheduling and IST-based cron execution
- admin-configurable cron timings for backup, expiry, invoices, wallet checks, and reminders
- WhatsApp notifications and reminders
- support tickets, audit logs, backups, discount codes, referral wallet flows
- Resend email delivery with SMTP fallback support
- richer homepage metadata for search and link previews
- installable web app support for supported browsers/devices
- admin-managed operator payment gateway assignment
- browser cache clear tools and stale-cache protection on login/session switch
- admin display-name management
- email test actions for Resend and SMTP fallback
- SMTP fallback compatibility for servers without AUTH support
- operator invoice bulk upload with sample file support
- invoice settings address fallback from registration/profile data
- invoice logo preview and public invoice rendering fixes
- backend-served `/api/uploads` URLs for uploaded assets

## Recent Functional Changes

### Auth and Sessions
- A user can be active on only one session/device at a time.
- Logging in on a second device invalidates the previous session.
- Password change and password reset also invalidate prior sessions.
- Forgot-password recovery OTP is now email-only.

### Invoices
- Pending invoices can now be edited.
- Operators cannot cancel a paid invoice.
- Admin can still cancel a paid invoice through the status API.
- When an operator marks an invoice as paid, the UI now requires:
  - payment mode: `Cash`, `Own UPI`, `Bank Transfer`, or `Cheque`
  - payment date

### Scheduler and VPS Reliability
- Backend cron jobs now register async APScheduler jobs directly instead of wrapping them in manual `lambda` task creation.
- Scheduler startup now logs registered jobs and job execution failures/successes more clearly for VPS troubleshooting.

### Email Delivery and Cron Controls
- Browser app title is now `E-Bill | Invoice Automation Software`.
- Email delivery now tries Resend first and automatically falls back to SMTP if the API call fails.
- Email settings now support SMTP host, port, username, password, from-address, and TLS controls.
- Admin platform settings now expose cron times for:
  - backup
  - expiry checks
  - invoice generation
  - wallet checks
  - reminder processing
- Saving cron settings reschedules APScheduler jobs immediately, and invoice generation now respects the configured `auto_invoice_days_before` value during cron/manual runs.
- Saved cron and email settings now reload the current persisted values in the UI after refresh.
- Auto-generated backup jobs now appear in the backup list after completion.

### Cache, Admin Profile, and Email Testing
- Admin and operator settings now include cache-clear tools for refreshing stale dashboard data.
- Login/session switching now clears browser/app cache automatically.
- Service worker caching no longer stores `/api` responses.
- Admins can update the admin display name from settings.
- Email settings now support sending test mail through Resend and SMTP fallback.
- SMTP fallback now skips login when the server does not advertise `AUTH`.

### Invoice Upload and Branding
- Operator invoices now support bulk upload with sample CSV/XLSX flow similar to subscriber import.
- Invoice settings now fall back to the operator registration/profile address when the invoice company address is empty.
- Uploaded invoice logos now persist immediately, preview correctly in operator settings, and render correctly on the public invoice page.
- Uploaded assets are now served through backend `/api/uploads` URLs.

### SEO and Installable Web App
- The app shell now includes stronger SEO metadata in `frontend/public/index.html`.
- Added Open Graph and Twitter metadata so shared links have better preview titles, descriptions, and images.
- Added schema markup for `Organization` and `SoftwareApplication`.
- Added a web app manifest, install icons, Apple touch icon, and a lightweight service worker.
- Supported browsers can now show add-to-home-screen or install UI when served over HTTPS.

### Payment Gateway Assignment
- Admin payment gateway settings can now assign keys directly to a specific operator from the same gateway dialog.
- The admin gateway list now shows whether credentials are for platform SaaS payments or a named operator.
- Operator-side payment gateway configuration has been removed from the settings panel.
- Custom gateway operators are now directed to contact admin for key assignment.

## Scheduled Jobs

All core cron jobs now run on `Asia/Kolkata` time in the backend scheduler.

| Job | Default Schedule (IST) | Description |
|------|----------------|-------------|
| Auto Backup | 03:00 | create daily backup |
| Expiry Check | 00:05 | expire trials/subscriptions |
| Invoice Generation | 08:00 | create upcoming invoices |
| Reminder Processing | 10:00 | send reminders |
| Wallet Check | 09:00 | low-wallet checks and actions |

These times are now editable in admin settings and reschedule the running backend scheduler after save.

## Local Development

### Backend

Use the local requirements file if needed:

```bash
cd backend
pip install -r requirements_local.txt
uvicorn server:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm start
```

### Tests

```bash
cd backend
pytest -v
```

```bash
cd frontend
npm run build
```

## Docker Deployment

```bash
docker compose up -d --build
```

Seed the environment after startup if needed:

```bash
docker compose exec backend python -c "import asyncio, json; from server import seed_data; print(json.dumps(asyncio.run(seed_data()), indent=2))"
```

Notes:
- Caddy is the public entrypoint.
- Root `.env` is the main configuration source.
- `backend/.env` and `frontend/.env.local` are no longer required.
- Mongo credentials are read from the root env and passed safely into containers.

## Credentials

- Admin: `admin@saas.com / admin123`
- Seed endpoint: `POST /api/seed`

## Documentation Map

- Product and architecture summary: [PRD.md](/d:/eBill/memory/PRD.md)
- Active roadmap and pending work: [ROADMAP.md](/d:/eBill/memory/ROADMAP.md)
- Release history: [CHANGELOG.md](/d:/eBill/memory/CHANGELOG.md)
- Validation backlog: [PENDING_TESTS.md](/d:/eBill/memory/PENDING_TESTS.md)
- Handoff summary: [agent-handoff.md](/d:/eBill/memory/agent-handoff.md)
