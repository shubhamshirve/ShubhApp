# Multi-Tenant SaaS Recurring Billing Platform
## Product Requirements Document (Updated Mar 1, 2026)

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

### What's Been Implemented

#### Phase 1 - Core MVP
- [x] Authentication (register, login, JWT tokens)
- [x] Admin: Dashboard KPIs, SaaS Plans CRUD, Operators management
- [x] Operator: Dashboard, Plans CRUD, Subscribers CRUD, Invoices CRUD
- [x] Reports: Revenue, GST Summary, Pending/Overdue
- [x] Staff management with permissions
- [x] Landing page with pricing

#### Phase 2 - Payment & Notifications (Jan 28, 2026)
- [x] Razorpay payment link generation with QR codes
- [x] Invoice PDF generation with professional design
- [x] WhatsApp Business API configuration
- [x] WhatsApp notification sending (invoice, reminder)
- [x] Bulk notification support
- [x] Auto invoice generation cron job
- [x] Auto reminder for overdue invoices cron
- [x] Subscription expiry checker cron
- [x] Webhook handler for Razorpay payments

#### Phase 3 - Staff Permissions & Admin Features (Mar 1, 2026)
- [x] Staff role restrictions: DELETE operations blocked backend (403 Forbidden)
- [x] Staff role restrictions: DELETE buttons hidden in frontend UI
- [x] Admin impersonation: Login as any operator from admin panel
- [x] Admin Settings page: General config, Payment Gateways, Add-ons management
- [x] Admin Reports page: Payment reports with KPIs, SaaS revenue, CSV export
- [x] Admin sidebar updated: Reports, Settings, Audit Logs
- [x] Razorpay test keys configured in backend
- [x] Operator activate/suspend from admin panel
- [x] Add-ons CRUD for admin (notifications, custom_gateway, etc.)

### Prioritized Backlog

#### P0 (Critical) - All Done
- [x] All core features implemented and tested

#### P1 (High Priority)
- [ ] Actual WhatsApp message template approval
- [ ] Payment reconciliation reports
- [ ] Invoice customization UI (frontend page for /api/operator/invoice-settings)
- [ ] Operator Announcements/Notifications UI page
- [ ] SaaS add-on purchase flow for operators (UI)

#### P2 (Medium Priority)
- [ ] Multi-currency support
- [ ] Email notifications as backup
- [ ] Export reports to CSV/Excel (operator-side)
- [ ] Dashboard analytics graphs
- [ ] Customer self-service portal
- [ ] Payment link expiry handling
- [ ] Payment QR code display in invoices UI
- [ ] WhatsApp Web integration option

### Next Tasks
1. Build Invoice Customization UI for operators
2. Build Announcements/Notifications management page for operators
3. Implement SaaS add-on purchase flow (operator can buy add-ons)
4. Implement operator payment reports CSV/Excel export
5. Add dashboard analytics charts

### API Endpoints
- POST /api/auth/{login, register}
- GET /api/auth/me
- GET/PUT /api/admin/settings
- GET/POST/DELETE /api/admin/payment-gateways
- GET/POST /api/admin/addons
- POST /api/admin/operators/{id}/addons/{code}
- GET /api/admin/reports/{payments, saas-revenue}
- POST /api/admin/operators/{id}/impersonate
- POST /api/admin/operators/{id}/{suspend, activate, assign-plan}
- CRUD /api/admin/{saas-plans, operators}
- GET/POST /api/admin/audit-logs
- GET /api/operator/{dashboard, profile}
- CRUD /api/operator/{plans, subscribers, invoices, staff}
- GET/PUT /api/operator/invoice-settings
- POST/GET /api/operator/announcements
- POST /api/operator/{payment-gateway, whatsapp-config}
- GET /api/operator/reports/{revenue, gst-summary, pending-overdue}
- GET /api/operator/audit-logs
- POST /api/operator/invoices/{id}/payment-link
- GET /api/operator/invoices/{id}/pdf
- POST /api/operator/{send-notification, bulk-notification}
- POST /api/webhooks/razorpay
- POST /api/admin/cron/{generate-invoices, send-reminders, check-expiry}
