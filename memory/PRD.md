# Multi-Tenant SaaS Recurring Billing Platform
## Product Requirements Document (Updated Mar 4, 2026)

### Original Problem Statement
Build a scalable multi-tenant SaaS recurring billing web application for India-focused, GST compliant operations. Platform allows operators to manage subscribers, generate invoices, and collect payments through operator-owned payment gateways.

### User Personas
1. **Super Admin**: Platform owner managing all operators and SaaS plans
2. **Operator**: Business owner using the platform for billing
3. **Staff**: Operator's team members with limited permissions (no delete)
4. **Subscriber**: End customers receiving invoices (no login)

### Technical Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, MongoDB
- **Services**: Razorpay, WhatsApp Business API
- **PDF**: ReportLab

### Default Credentials
- Admin: admin@saas.com / admin123
- Demo Operator: demo@democorp.com / demo123
- Demo Staff: staff@democorp.com / staff123
- Razorpay: rzp_test_sFaXdx3kATIGiw / dOvQqMbfE2sPkYulgTeU2SpW

### What's Been Implemented

#### Phase 1 - Core MVP
- [x] Authentication (register, login, JWT tokens)
- [x] Admin: Dashboard KPIs, SaaS Plans CRUD, Operators management
- [x] Operator: Dashboard, Plans CRUD, Subscribers CRUD, Invoices CRUD
- [x] Reports: Revenue, GST Summary, Pending/Overdue
- [x] Staff management with permissions
- [x] Landing page with pricing

#### Phase 2 - Payment & Notifications
- [x] Razorpay payment link generation with QR codes
- [x] Invoice PDF generation with professional design
- [x] WhatsApp Business API configuration (MOCKED)
- [x] Bulk notification support
- [x] Auto invoice generation cron job
- [x] Webhook handler for Razorpay payments

#### Phase 3 - Staff Permissions & Admin Features (Mar 1, 2026)
- [x] Staff role restrictions: DELETE operations blocked (403)
- [x] Staff: DELETE buttons hidden in frontend
- [x] Admin impersonation: Login as any operator
- [x] Admin Settings page: General, Payment Gateways, Add-ons
- [x] Admin Reports page: KPIs, SaaS revenue, CSV export
- [x] Razorpay test keys configured

#### Phase 4 - User-Requested Fixes (Mar 4, 2026)
- [x] Create Operator dialog: aligned fields with registration form (Company Name, Owner Name, Email, Phone, Password, GST, Bank, Plan sections)
- [x] Delete operators from admin panel: dropdown option with confirmation dialog
- [x] SaaS Plans + Addons: plans can include addons (checkbox selection + tags display)
- [x] Payment Gateways context: info banner for Operator-to-Admin SaaS payments
- [x] Admin addon full CRUD: table view with edit (PUT) and delete (soft DELETE) per add-on
- [x] ResizeObserver error fix (Radix UI / Shadcn)

### Prioritized Backlog

#### P1 (High Priority)
- [ ] Invoice customization UI (operator settings for company logo, colors, etc.)
- [ ] Operator Announcements/Notifications management page
- [ ] SaaS add-on purchase flow for operators (buy add-ons from UI)
- [ ] Payment reconciliation reports
- [ ] Actual WhatsApp message template approval

#### P2 (Medium Priority)
- [ ] Multi-currency support
- [ ] Email notifications as backup
- [ ] Export reports to CSV/Excel (operator-side)
- [ ] Dashboard analytics graphs
- [ ] Customer self-service portal
- [ ] Payment link expiry handling
- [ ] Payment QR code display in invoices UI
- [ ] WhatsApp Web integration option

### API Endpoints
- POST /api/auth/{login, register}
- GET /api/auth/me
- GET/PUT /api/admin/settings
- GET/POST/DELETE /api/admin/payment-gateways
- GET/POST/PUT/DELETE /api/admin/addons
- POST /api/admin/operators/{id}/addons/{code}
- GET /api/admin/reports/{payments, saas-revenue}
- POST /api/admin/operators/{id}/impersonate
- POST /api/admin/operators/{id}/{suspend, activate, assign-plan, extend-subscription}
- POST /api/admin/operators/create
- DELETE /api/admin/operators/{id}
- CRUD /api/admin/saas-plans (with included_addons field)
- GET/POST /api/admin/audit-logs
- GET /api/operator/{dashboard, profile}
- CRUD /api/operator/{plans, subscribers, invoices, staff}
- GET/PUT /api/operator/invoice-settings
- POST/GET /api/operator/announcements
- POST /api/operator/{payment-gateway, whatsapp-config}
- GET /api/operator/reports/{revenue, gst-summary, pending-overdue}
- GET /api/operator/audit-logs
- GET /api/operator/invoices/{id}/pdf
- POST /api/operator/invoices/{id}/payment-link
- POST /api/webhooks/razorpay
