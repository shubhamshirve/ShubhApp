# Multi-Tenant SaaS Recurring Billing Platform
## Product Requirements Document (Updated Mar 5, 2026)

### Original Problem Statement
Build a scalable multi-tenant SaaS recurring billing web application for India-focused, GST compliant operations.

### Technical Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, MongoDB
- **Services**: Razorpay, WhatsApp Business API (MOCKED - keys in .env but empty)
- **PDF**: ReportLab

### Default Credentials
- Admin: admin@saas.com / admin123
- Operator: demo@democorp.com / demo123
- Staff: staff@democorp.com / staff123
- Razorpay: rzp_test_sFaXdx3kATIGiw / dOvQqMbfE2sPkYulgTeU2SpW

### What's Been Implemented

#### Phase 1-2: Core MVP + Payments
- [x] Auth, Multi-tenant isolation, Admin/Operator/Staff CRUD
- [x] Razorpay payment links, Invoice PDF, WhatsApp config UI
- [x] Auto invoice cron, Webhook handler, Landing page

#### Phase 3: Staff Permissions & Admin Features (Mar 1)
- [x] Staff DELETE blocked (403 + hidden buttons)
- [x] Admin impersonation, Settings (General/Gateways/Add-ons), Reports

#### Phase 4: User-Requested Fixes (Mar 4)
- [x] Create Operator dialog aligned with registration form
- [x] Delete operators, SaaS Plans + included add-ons
- [x] Payment Gateways context, Admin addon full CRUD

#### Phase 5-6: Invoice Customization, Subscription, Announcements (Mar 4)
- [x] Invoice customization UI (operator Settings > Invoice tab)
- [x] Subscription renewal with Razorpay payment links
- [x] Announcements page (create + history)
- [x] CSV export on operator Reports (Invoices + GST)

#### Phase 7: Impersonation UX, WhatsApp Web, Audit Logs (Mar 5)
- [x] "Return to Admin" indigo banner when impersonating operator
- [x] JWT token carries impersonated_by, return-from-impersonate endpoint
- [x] WhatsApp Web integration: wa.me links on Invoices + Subscribers pages
- [x] Admin WhatsApp API keys added to .env (WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_BUSINESS_ACCOUNT_ID)
- [x] Admin audit logs fixed: handles malformed old_value/new_value, skips broken entries

#### Phase 8: Add-on Purchase Flow (Mar 5)
- [x] Operator Add-ons Store page with purchase via Razorpay
- [x] Free activation for plan-included add-ons
- [x] Razorpay payment link for paid add-ons
- [x] "I've Paid — Activate Now" manual activation button
- [x] Sidebar link with Puzzle icon

#### Phase 9: Razorpay Fast Checkout Refactor (Mar 10)
- [x] Backend: `/api/operator/checkout/create-order` endpoint (subscription + addon)
- [x] Backend: `/api/operator/checkout/verify` endpoint (signature verify + activate)
- [x] Frontend: Razorpay JS checkout script added to index.html
- [x] Frontend: Add-ons store merged into Subscription page (unified view)
- [x] Frontend: Subscription renewal uses Fast Checkout modal ("Platform Name" / "Monthly Recurring")
- [x] Frontend: Add-on purchase uses Fast Checkout modal
- [x] Frontend: Removed standalone Addons.jsx page, route, and sidebar link
- [x] Customer invoices retain Payment Links (unchanged)

#### Phase 10: Revenue Dashboards & Payment History (Mar 10)
- [x] Admin dashboard: Real SaaS revenue from saas_payments (subscription + addon + GST, this month + all-time)
- [x] Admin dashboard: Recent payments table (operator name, type, amounts, date)
- [x] Operator dashboard: Revenue label clarified as "Invoice Revenue (Collected)" with sub-label
- [x] Subscription page: Payment History tab with full table (type, description, base, GST, total, date) + running total
- [x] Backend: `/api/operator/payment-history` endpoint

### Prioritized Backlog

#### P1 (High Priority)
- [ ] QR Codes for Invoice Payment Links
- [ ] Admin Payment Reports (placeholder needs real data/KPIs)
- [ ] Dashboard analytics graphs/charts
- [ ] Operator audit logs page UI

#### P2 (Medium Priority)
- [ ] Multi-currency support
- [ ] Email notifications as backup
- [ ] Customer self-service portal
- [ ] Payment QR code display in invoices UI
- [ ] WhatsApp message template approval flow
