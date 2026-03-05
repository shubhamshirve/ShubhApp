# Multi-Tenant SaaS Recurring Billing Platform
## Product Requirements Document (Updated Mar 4, 2026)

### Original Problem Statement
Build a scalable multi-tenant SaaS recurring billing web application for India-focused, GST compliant operations. Platform allows operators to manage subscribers, generate invoices, and collect payments through operator-owned payment gateways.

### Technical Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, MongoDB
- **Services**: Razorpay, WhatsApp Business API (MOCKED)
- **PDF**: ReportLab

### Default Credentials
- Admin: admin@saas.com / admin123
- Demo Operator: demo@democorp.com / demo123
- Demo Staff: staff@democorp.com / staff123
- Razorpay: rzp_test_sFaXdx3kATIGiw / dOvQqMbfE2sPkYulgTeU2SpW

### What's Been Implemented

#### Phase 1 - Core MVP
- [x] Auth (register, login, JWT), Multi-tenant data isolation
- [x] Admin: Dashboard, SaaS Plans CRUD, Operators CRUD (create/suspend/activate/delete)
- [x] Operator: Dashboard, Plans CRUD, Subscribers CRUD, Invoices CRUD
- [x] Staff management with permissions, Landing page

#### Phase 2 - Payment & Notifications
- [x] Razorpay payment link generation, Invoice PDF generation
- [x] WhatsApp Business API config UI (MOCKED), Bulk notification support
- [x] Auto invoice generation cron, Webhook handler for Razorpay

#### Phase 3 - Staff Permissions & Admin Features (Mar 1, 2026)
- [x] Staff DELETE blocked (403 backend + hidden buttons frontend)
- [x] Admin impersonation, Admin Settings (General/Gateways/Add-ons)
- [x] Admin Reports (KPIs, SaaS revenue, CSV export)

#### Phase 4 - User-Requested Fixes (Mar 4, 2026)
- [x] Create Operator dialog aligned with registration form
- [x] Delete operators from admin panel
- [x] SaaS Plans + included add-ons (checkbox + tags)
- [x] Payment Gateways context for SaaS payments
- [x] Admin addon full CRUD (add/update/delete)

#### Phase 5 - Invoice Customization & Subscription Renewal (Mar 4, 2026)
- [x] Invoice customization UI (operator Settings > Invoice tab)
- [x] Subscription renewal flow with Razorpay payment link generation
- [x] Renew Now button fixed (navigates to /operator/subscription)
- [x] Subscription page with plan status, available plans, renewal dialog

#### Phase 6 - Announcements & Reports Export (Mar 4, 2026)
- [x] Announcements page for operators (create + history table)
- [x] WhatsApp-gated sending (blocks if addon not enabled)
- [x] CSV export on operator Reports (Invoices CSV, GST CSV)
- [x] Sidebar updated with Announcements + Subscription links

### Prioritized Backlog

#### P1 (High Priority)
- [ ] SaaS add-on purchase flow for operators (buy add-ons from UI via Razorpay)
- [ ] Dashboard analytics graphs/charts
- [ ] Operator audit logs page UI

#### P2 (Medium Priority)
- [ ] Multi-currency support
- [ ] Email notifications as backup
- [ ] Customer self-service portal
- [ ] Payment link expiry handling
- [ ] Payment QR code display in invoices UI
- [ ] WhatsApp Web integration option
- [ ] WhatsApp message template approval flow

### API Endpoints
- POST /api/auth/{login, register}, GET /api/auth/me
- GET/PUT /api/admin/settings
- GET/POST/DELETE /api/admin/payment-gateways
- GET/POST/PUT/DELETE /api/admin/addons
- GET /api/admin/reports/{payments, saas-revenue}
- POST /api/admin/operators/{id}/{impersonate, suspend, activate, assign-plan, extend-subscription}
- POST /api/admin/operators/create, DELETE /api/admin/operators/{id}
- CRUD /api/admin/saas-plans (with included_addons)
- GET/POST /api/admin/audit-logs
- GET /api/operator/{dashboard, profile, subscription}
- POST /api/operator/renew-subscription
- CRUD /api/operator/{plans, subscribers, invoices, staff}
- GET/PUT /api/operator/invoice-settings
- POST/GET /api/operator/announcements
- POST /api/operator/{payment-gateway, whatsapp-config}
- GET /api/operator/reports/{revenue, gst-summary, pending-overdue}
- GET /api/operator/audit-logs
- GET /api/operator/invoices/{id}/pdf
- POST /api/operator/invoices/{id}/payment-link
- POST /api/webhooks/razorpay
