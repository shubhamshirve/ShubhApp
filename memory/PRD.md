# SaaS Billing Platform - PRD

## Product Summary

E-Bill is a multi-tenant billing platform for ISP, broadband, cable, and similar subscription operators. It supports platform admins, business operators, and staff users with role-based access, invoicing, subscription billing, reminders, wallets, support tickets, and operator-branded public invoices.

## Core Personas

### Admin
- manages operators, SaaS plans, addons, wallets, reports, settings, support, and platform-level controls

### Operator
- manages subscribers, plans, invoices, staff, settings, subscription, reports, reminders, and branded billing workflows

### Staff
- works inside an operator account with restricted permissions and no destructive delete access

## Technical Architecture

- Frontend: React, React Router, Axios, Tailwind, Radix/shadcn-style components
- Backend: FastAPI, Motor/MongoDB, APScheduler
- Auth: JWT-based auth with role support and admin impersonation
- Infra: Docker Compose, Caddy, MongoDB

## Current Product Capabilities

### Authentication and Access
- admin/operator/staff login
- admin impersonation of operators
- configurable session timeout
- single active session per user
- forced invalidation of previous session on new login
- email-based registration OTP
- email-only forgot-password OTP
- password changes and resets invalidate existing sessions

### Operator Billing Workflows
- create invoices manually
- generate multi-line invoices
- edit invoices while status is `pending`
- mark invoices `paid`, `overdue`, or `cancelled` with business-rule enforcement
- require payment mode and payment date when operator manually marks an invoice paid
- prevent operator cancellation of already-paid invoices
- allow admin cancellation of paid invoices
- generate public invoice URLs using `invoice_number`
- preserve fallback for legacy internal-id public invoice links

### Subscriber and Plan Management
- subscribers can hold multiple active plans
- plan-wise billing dates and discounts
- invoice grouping for common billing dates
- operator plans CRUD
- bulk upload support for key entities

### Branding and Invoice Presentation
- operator invoice settings
- logo upload
- field visibility toggles
- branded public invoice view
- branded PDF/print output using shared invoice view data
- invoice settings address fallback from operator registration/profile data
- invoice logo preview/persistence/rendering using backend-served uploaded assets

### Payments, Wallets, and Platform Billing
- SaaS subscription checkout
- operator wallet management
- wallet top-up with GST-exclusive credit logic
- admin wallet credit/debit/suspend controls
- admin-assigned operator payment gateway credentials
- payment links for invoices
- public online payment verification

### Platform Controls
- maintenance mode with banner/read-only behavior
- global reminder settings
- IST-based cron scheduling
- admin-configurable cron timing controls with live APScheduler reschedule on save
- scheduler startup logging and async APScheduler registration for better VPS reliability
- audit logs
- backup and restore
- support tickets
- Resend email delivery with SMTP fallback transport support
- installable web app support through manifest and service worker
- admin settings and email settings refresh persisted values after save
- auto-backup runs surface in the backup list after completion
- admin profile/name management
- browser/app cache clear tools for admin and operator dashboards
- automatic cache clear on login/session switch
- Resend and SMTP test mail actions
- SMTP fallback compatibility when `AUTH` is unavailable
- operator invoice bulk upload with sample CSV/XLSX support
- backend-served `/api/uploads` URLs for uploaded invoice assets

### Discovery and Distribution
- SEO-ready homepage metadata
- Open Graph and Twitter preview metadata for shared links
- JSON-LD schema for organization and software application identity
- install icons and mobile web app metadata for add-to-home-screen behavior

## Scheduled Jobs

The scheduler now uses `Asia/Kolkata`, with admin-editable default times.

| Job | IST Time | Purpose |
|-----|----------|---------|
| Auto Backup | 03:00 | daily backup |
| Expiry Check | 00:05 | mark expired subscriptions/trials |
| Invoice Generation | 08:00 | generate upcoming invoices |
| Wallet Check | 09:00 | low balance checks and actions |
| Reminder Processing | 10:00 | process reminders |

## Business Rules

### Session Rules
- one user account may have only one active session at a time
- new login invalidates old session
- password reset/change also invalidates prior sessions

### Invoice Rules
- pending invoices can be edited
- operator can mark pending invoice paid only after supplying payment mode and payment date
- operator cannot cancel paid invoices
- admin can cancel paid invoices
- public online payment marks payment mode as `online`

### Recovery Rules
- forgot-password recovery OTP is email-only
- WhatsApp is no longer available as a recovery OTP channel

## Important APIs

### Auth
- `POST /api/auth/login`
- `GET /api/auth/me`
- `PUT /api/auth/change-password`
- `POST /api/auth/forgot-password`
- `POST /api/auth/verify-recovery-otp`
- `POST /api/auth/reset-password`
- `POST /api/auth/resend-recovery-otp`
- `GET /api/auth/app-state`

### Operator Invoices
- `POST /api/operator/invoices`
- `GET /api/operator/invoices`
- `PUT /api/operator/invoices/{invoice_id}`
- `PUT /api/operator/invoices/{invoice_id}/status`
- `POST /api/operator/invoices/{invoice_id}/payment-link`

### Public Invoice
- `GET /api/public/invoice/{invoice_ref}`
- `POST /api/public/invoice/{invoice_ref}/verify-payment`
- `GET /api/public/invoice/{invoice_ref}/pdf`

## Current Gaps / Next Product Work

- admin-managed payment gateway assignment and operator gateway-setting removal
- dedicated payment receipt generation and delivery
- broader email + WhatsApp confirmation workflows
- richer import/export coverage
- deeper reporting and GST reconciliation

## Version Notes

This PRD is aligned with the codebase through:
- `V7.14-6` branch creation
- `V7.14-7` feature delivery
- `V7.14-8` documentation alignment
- `V7.14-9` scheduler reliability fix
- `V7.14-10` app title, email fallback, and cron settings delivery
- `V7.14-11` metadata, previews, and web app installability delivery
- `V7.14-12` cache clearing, admin profile, and email test tooling delivery
- `V7.14-13` invoice bulk upload, address fallback, and logo rendering delivery
