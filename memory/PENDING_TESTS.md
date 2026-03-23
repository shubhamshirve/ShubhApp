# Pending Tests

## High Priority

### Single Session Enforcement
- Log in with the same operator account in browser A and browser B.
- Confirm browser A is forced out after browser B logs in.
- Confirm the old browser/session is rejected by API on next request.
- Confirm focus-based session check logs the old session out without needing a full refresh.
- Repeat for admin account.

### Password Change / Reset Session Invalidation
- Change password while logged in and confirm old tokens/sessions stop working.
- Run forgot-password flow and confirm previous sessions are invalidated after reset.

### Forgot Password Email-Only Flow
- Confirm forgot-password UI shows email-only recovery.
- Confirm API rejects non-email recovery method requests.
- Live test email OTP send, verify, resend, and reset with valid Resend credentials.

## Invoice Workflow Validation

### Pending Invoice Editing
- Edit a pending invoice with one line item and confirm totals remain correct.
- Edit a pending multi-line invoice and confirm item updates persist.
- Edit subscriber, due date, and service periods, then reload invoice list and public invoice.

### Mark Paid Confirmation
- Mark a pending invoice as paid using each payment mode:
  - Cash
  - Own UPI
  - Bank Transfer
  - Cheque
- Confirm payment date is saved correctly.
- Confirm invoice list/public invoice/PDF surfaces paid state correctly after manual update.

### Cancellation Rules
- Attempt to cancel a paid invoice as operator and confirm it is blocked.
- Cancel a paid invoice as admin and confirm it succeeds.
- Confirm cancelled invoice state is reflected consistently after admin action.

### Public Payment Regression
- Pay an invoice through the public online route and confirm `payment_mode` is stored as `online`.
- Verify public payment route still works with invoice-number URLs and legacy fallback URLs.

## Existing Validation Still Pending

### Wallet Accounting and Billing Integrity
- Manual Razorpay top-up verification for credited amount vs paid amount
- Manual wallet transaction/history verification after top-up
- Manual subscription renewal regression check to confirm no stale subscription wallet credit

### Platform Maintenance Mode
- Manual admin maintenance toggle and custom-message persistence
- Manual operator/staff write-block verification with read-only reads still working
- Manual banner visibility verification
- Manual cron skip verification while maintenance mode is enabled

### Invoice Branding and Public Invoice Consistency
- Manual logo upload and visibility-toggle verification
- Public invoice branding/address/payment-state verification
- PDF/print verification for branding parity and invoice metadata

### Multi-Plan Subscribers and Multi-Line Invoices
- Manual creation of subscriber with multiple plans on different billing dates
- Manual creation of a multi-line invoice
- Automated billing cron verification for grouped multi-line invoice generation

### Admin Wallet Operations
- Manual admin credit, debit, and suspend verification
- Validate audit trail and transaction list after each wallet action

## Automated Test Follow-Ups

- Add backend tests for single-session invalidation on second login.
- Add backend tests for operator/admin cancellation behavior on paid invoices.
- Add backend tests for `PUT /operator/invoices/{invoice_id}` pending-only edit rule.
- Add backend tests for `PUT /operator/invoices/{invoice_id}/status` requiring payment mode/date for manual paid status.
- Add forgot-password tests to confirm WhatsApp recovery is no longer accepted.
