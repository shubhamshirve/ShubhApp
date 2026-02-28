# Multi-Tenant SaaS Recurring Billing Platform
## Product Requirements Document

### Original Problem Statement
Build a scalable multi-tenant SaaS recurring billing web application for India-focused, GST compliant operations. Platform allows operators to manage subscribers, generate invoices, and collect payments through operator-owned payment gateways.

### User Personas
1. **Super Admin**: Platform owner managing all operators and SaaS plans
2. **Operator**: Business owner using the platform for billing
3. **Staff**: Operator's team members with limited permissions
4. **Subscriber**: End customers receiving invoices (no login)

### Core Requirements
- Multi-tenant data isolation via operator_id
- Soft delete only (no hard deletes)
- JWT-based authentication
- Role-based access control
- GST compliance (inclusive/exclusive calculations)
- Payment gateway abstraction (Razorpay, Cashfree, PhonePe)

### What's Been Implemented (Jan 28, 2026)

#### Backend (FastAPI + MongoDB)
- [x] Authentication (register, login, JWT tokens)
- [x] Admin: Dashboard KPIs, SaaS Plans CRUD, Operators management
- [x] Operator: Dashboard, Plans CRUD, Subscribers CRUD, Invoices CRUD
- [x] Reports: Revenue, GST Summary, Pending/Overdue
- [x] Staff management with permissions
- [x] Payment gateway configuration storage
- [x] Audit logging structure

#### Frontend (React + Shadcn UI)
- [x] Login and Registration pages
- [x] Admin Dashboard with KPIs
- [x] Admin Operators management
- [x] Admin SaaS Plans CRUD
- [x] Admin Audit Logs
- [x] Operator Dashboard
- [x] Operator Subscribers CRUD
- [x] Operator Plans CRUD
- [x] Operator Invoices CRUD
- [x] Operator Staff management
- [x] Operator Reports
- [x] Operator Settings (profile + payment gateway)

#### PHP/MySQL Version for XAMPP
- [x] Database schema with all tables
- [x] API router with all endpoints
- [x] Configuration file
- [x] Deployment guide

### Prioritized Backlog

#### P0 (Critical)
- [ ] Auto invoice generation cron job (5 days before billing)
- [ ] Razorpay payment link generation
- [ ] Webhook handler for payment confirmation

#### P1 (High Priority)
- [ ] WhatsApp Business API integration
- [ ] Auto reminder cron job
- [ ] Invoice PDF generation
- [ ] Read-only mode enforcement

#### P2 (Medium Priority)
- [ ] Bulk notification module
- [ ] Trial expiry checker cron
- [ ] Database backup system
- [ ] Export reports to CSV/Excel

### Next Tasks
1. Implement Razorpay createPaymentLink() method
2. Create cron jobs for invoice generation
3. Add WhatsApp notification sending
4. Invoice PDF template
5. Admin reports and revenue tracking
