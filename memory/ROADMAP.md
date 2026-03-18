# E-Bill Platform — ROADMAP

## Completed (P0)
- [x] Task 1: Referral + Wallet System
- [x] Task 2: Basic/Pro Plan Revamp (₹12 basic, ₹22+₹1000 pro)
- [x] Task 5: Support Ticket System
- [x] Task 7: Remove Landing Page → redirect to /login
- [x] Task 8: Codebase Cleanup — Settlement system, Platform fee logic, Dead files & code

---

## P1 — Needs External Credentials (Next Up)

### Task 3: Email/SMS/WhatsApp OTP + Admin Toggle
- OTP via Resend (email), SMS provider, WhatsApp (already integrated)
- Admin Settings toggle to enable/disable each channel
- **Needs**: Resend API key, SMS provider credentials

### Task 4: Cashfree Payment Gateway
- Add Cashfree alongside Razorpay
- Admin setting to select active gateway (Razorpay / Cashfree / Both)
- **Needs**: Cashfree API key + secret

### Task 6: Payment Receipt Generation + WhatsApp
- Generate PDF receipt for each payment
- Send receipt via WhatsApp (existing integration)
- Optional: WhatsApp Web sharing link

### Task 8: SMS & Email Invoice/Reminder
- Invoice delivery via SMS and Email (alongside existing WhatsApp)
- Reminder delivery via SMS and Email
- **Needs**: SMS/Email provider credentials

---

## P2 — No External Deps

### Task 9: GST R1 & 3B Reconciliation
- Automated reconciliation from collections data
- Admin: platform-level GST
- Operator: GST report if GST-enabled
- Very complex; requires domain knowledge of GSTR1/3B format

### Better Subscriber Self-Service Portal
- Subscriber can view invoices and make payments
- Public URL per operator

### Import/Export (CSV/Excel)
- Bulk import subscribers
- Export invoices, subscribers, payments

### Advanced Reporting & Analytics
- Revenue charts, subscriber growth, churn analysis
- Per-operator analytics for admin

---

## P3 — Maintenance/Optimization

- authAxios useMemo optimization in App.js
- Invoice number concurrency safety
- Deprecate legacy renew-subscription endpoint
- Configurable WhatsApp template names
- MongoDB indexes on high-cardinality fields
- Pagination on high-volume lists
- Custom domain support for operators
