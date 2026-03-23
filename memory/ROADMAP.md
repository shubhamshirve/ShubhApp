# E-Bill Platform - Roadmap

## Completed
- [x] Referral + wallet system
- [x] SaaS plan revamp and simplified pricing
- [x] Support ticket system
- [x] Landing page removal and login redirect
- [x] KYC fields in registration and admin operator management
- [x] Maintenance mode
- [x] Global reminder controls and IST cron scheduling
- [x] Multi-plan subscribers and multi-line invoices
- [x] Admin wallet actions
- [x] Invoice branding and public invoice consistency
- [x] Single-session enforcement and stronger invoice payment controls

---

## Current Release State

Latest shipped functional branch: `V7.14-10`

What is now live in code:
- single active session per user
- email-only password recovery OTP
- pending invoice editing
- paid invoice protection against operator cancellation
- payment mode and payment date confirmation when operators mark invoices as paid
- hardened APScheduler startup for VPS cron reliability with explicit job registration logging
- app title update to `E-Bill | Invoice Automation Software`
- Resend plus SMTP fallback email delivery
- admin-configurable cron timings with live scheduler reschedule

What is still mostly pending:
- deeper payment receipt/confirmation flows
- broader messaging improvements
- import/export polishing
- advanced reporting and reconciliation work
- public metadata / SEO / web app installability polish

---

## Active Priorities

### 1. Payment Receipts and Confirmation Delivery
- Status: `planned`
- Priority: `P1`
- Importance: `High`
- Effort: `M`
- Scope:
  - generate payment receipt documents for subscriber payments and SaaS/platform payments where relevant
  - expose receipt download or retrieval in UI
  - optionally send receipt or payment confirmation through WhatsApp/email
- Why next:
  - invoice payment mode/date capture is now stored for manual payments
  - public online payment verification is already in place
  - the system now has enough payment metadata to support receipt generation cleanly

### 2. Messaging and Reporting Polish
- Status: `planned`
- Priority: `P2`
- Importance: `Medium`
- Effort: `S-M`
- Scope:
  - send announcements by email in addition to WhatsApp where configured
  - review message template consistency across reminders, invoices, and confirmations
  - hide GST-specific reporting UX where operator GST is not enabled

### 2A. Delivery Reliability and Scheduler Configuration
- Status: `completed`
- Priority: `P1`
- Importance: `High`
- Effort: `M`
- Scope:
  - changed app/browser title to the requested product wording
  - added fallback mail delivery when Resend API fails
  - exposed cron timing configuration in admin settings

### 3. Import/Export Enhancements
- Status: `planned`
- Priority: `P2`
- Importance: `Medium`
- Effort: `S-M`
- Scope:
  - improve CSV/XLSX coverage where gaps remain
  - standardize export formatting and filenames
  - improve import validation feedback

### 4. GST Reconciliation and Tax Reporting
- Status: `deferred`
- Priority: `P3`
- Importance: `Medium`
- Effort: `L`
- Scope:
  - R1 / 3B style reconciliation outputs
  - tax-domain correctness review before rollout

### 5. Advanced Analytics and Operational Reporting
- Status: `deferred`
- Priority: `P3`
- Importance: `Medium`
- Effort: `M-L`
- Scope:
  - richer dashboards
  - business trends and payment analytics
  - operator-side deeper reporting

---

## Completed Work Notes

### Wallet and Billing Integrity
- wallet top-up is GST-exclusive for crediting
- stored breakup fields support auditability
- referral rewards use credited amount basis

### Auth and OTP Hardening
- registration OTP via email
- forgot-password OTP via email
- resend throttling and invalid-attempt limits
- demo hints removed from frontend

### Session and Role Security
- configurable JWT timeout exists
- destructive staff restrictions remain enforced
- only one active login session is allowed per user
- password changes and resets invalidate existing sessions

### Invoices
- invoice-number public links with legacy fallback
- branding, logo upload, field visibility settings
- multi-line invoice creation and rendering
- pending invoice edit support
- mark-paid confirmation with payment metadata capture
- operator cannot cancel paid invoice; admin can

### Platform Controls
- maintenance mode
- global reminders
- IST-based cron scheduling
- admin wallet controls

---

## Pending Validation Themes

These are implemented in code but still need more manual/live verification in some cases:

- single-session login behavior across two devices/browsers
- admin cancellation path for already-paid invoices
- pending-invoice edit regression with line items and totals
- manual payment mode/date storage and reporting consistency
- provider-backed OTP delivery using valid email credentials
- Resend-to-SMTP fallback email delivery with valid credentials
- admin cron-setting persistence and live scheduler reschedule behavior
- public payment and branded PDF/print receipt consistency

Detailed validation backlog is tracked in [PENDING_TESTS.md](/d:/eBill/memory/PENDING_TESTS.md).

---

## Recommended Next Execution Order

1. Verify `V7.14-10` flows in browser and with real/test providers.
2. Build payment receipt generation on top of the new stored payment metadata.
3. Expand confirmation delivery through WhatsApp/email.
4. Finish messaging/reporting polish.
5. Revisit reconciliation and analytics after receipt and reporting layers stabilize.

---

## Risk Notes

- Single-session auth is security-positive, but any flow issuing tokens must continue to set `active_session_id` correctly.
- Invoice status changes now carry more business rules; future admin invoice UI must respect operator/admin differences.
- Receipt generation should reuse the existing public invoice/PDF stack where possible to avoid duplicate payment formatting logic.
