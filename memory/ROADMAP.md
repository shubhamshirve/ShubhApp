# E-Bill Platform — Roadmap

## Completed (as of V8.8)

- [x] Multi-tenant auth (admin / operator / staff) with single-session JWT
- [x] Email OTP registration and password recovery
- [x] Multi-plan subscribers (up to 5 plans per subscriber)
- [x] Multi-line invoices with branding and public links
- [x] Bulk upload: subscribers (multi-plan), plans, invoices
- [x] Wallet management with GST-exclusive crediting
- [x] Razorpay payment gateway per operator
- [x] Admin impersonation and return flow
- [x] Scheduled jobs (IST, admin-configurable): backup, expiry, invoices, reminders, wallet check
- [x] Support tickets, audit logs, automated backups
- [x] Maintenance mode, cache management
- [x] Referral codes, discount codes
- [x] Installable PWA
- [x] Staff management with restricted permissions
- [x] Docker CI/CD (GitHub Actions → Docker Hub → production)
- [x] WhatsApp WebJS decommissioned (V8.6)

---

## Planned

### P1 — High Priority
- [ ] **Payment Receipts** — Generate and deliver payment confirmation receipts to subscribers
- [ ] **Email Announcements** — Bulk email delivery to subscriber segments

### P2 — Medium Priority
- [ ] **GST Reconciliation** — Tax reporting and reconciliation exports
- [ ] **Advanced Analytics** — Richer dashboards, churn analysis, revenue trends
- [ ] **Import/Export Polish** — Better error reporting in bulk uploads, download results

### P3 — Deferred
- [ ] **WhatsApp Business API** — Template-based notifications (infrastructure exists in `whatsapp_service.py`)
- [ ] **Payment Receipt PDF** — Branded PDF receipts on payment confirmation
