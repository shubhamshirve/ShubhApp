# Multi-Tenant SaaS Recurring Billing Platform
## Product Requirements Document (Updated Jan 28, 2026)

### Original Problem Statement
Build a scalable multi-tenant SaaS recurring billing web application for India-focused, GST compliant operations. Platform allows operators to manage subscribers, generate invoices, and collect payments through operator-owned payment gateways.

### User Personas
1. **Super Admin**: Platform owner managing all operators and SaaS plans
2. **Operator**: Business owner using the platform for billing
3. **Staff**: Operator's team members with limited permissions
4. **Subscriber**: End customers receiving invoices (no login)

### Core Requirements (Implemented)
- Multi-tenant data isolation via operator_id
- Soft delete only (no hard deletes)
- JWT-based authentication
- Role-based access control
- GST compliance (inclusive/exclusive calculations)
- Payment gateway abstraction (Razorpay ready)

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

### Technical Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, MongoDB
- **Services**: Razorpay, WhatsApp Business API
- **PDF**: ReportLab
- **Also available**: PHP/MySQL version for XAMPP/cPanel

### Default Credentials
- Admin: admin@saas.com / admin123

### API Endpoints Added (Phase 2)
- POST /api/operator/invoices/{id}/payment-link - Generate Razorpay payment link
- GET /api/operator/invoices/{id}/pdf - Download invoice PDF
- POST /api/operator/whatsapp-config - Configure WhatsApp API
- POST /api/operator/send-notification - Send WhatsApp notification
- POST /api/operator/bulk-notification - Send bulk notifications
- POST /api/webhooks/razorpay - Razorpay webhook handler
- POST /api/admin/cron/generate-invoices - Trigger invoice generation
- POST /api/admin/cron/send-reminders - Trigger reminder sending
- POST /api/admin/cron/check-expiry - Check subscription expiry

### Prioritized Backlog

#### P0 (Critical) - All Done ✓
- [x] Razorpay payment links
- [x] PDF generation
- [x] Cron jobs

#### P1 (High Priority)
- [ ] Actual WhatsApp message template approval
- [ ] Payment reconciliation reports
- [ ] Multi-currency support
- [ ] Email notifications as backup

#### P2 (Medium Priority)
- [ ] Export reports to CSV/Excel
- [ ] Dashboard analytics graphs
- [ ] Customer self-service portal
- [ ] Payment link expiry handling

### Next Tasks
1. Approve WhatsApp message templates in Meta Business Suite
2. Add test mode toggle for payment gateway
3. Implement payment reconciliation
4. Add export functionality for reports
