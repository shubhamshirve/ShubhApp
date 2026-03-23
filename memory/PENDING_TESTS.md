# Pending Tests

## High Priority

### V7.14-12 Cache / Admin / Email Validation
- Verify cache-clear tools remove stale dashboard data after login/session switch.
- Verify service worker no longer caches `/api` responses.
- Verify admin display-name changes persist and surface in the UI after refresh/login.
- Verify Resend test mail works from admin settings.
- Verify SMTP test mail works from admin settings.
- Verify SMTP fallback succeeds when the server does not advertise `AUTH`.

### Next Requested Batch
- Verify homepage source contains canonical, Open Graph, Twitter card, and JSON-LD metadata.
- Test link preview output using WhatsApp, Facebook Sharing Debugger, LinkedIn Post Inspector, and X Card Validator.
- Verify `manifest.json` loads correctly and install icons render properly.
- Verify service worker registers in production and app can be installed on supported Chrome/Edge/Android browsers.
- Verify add-to-home-screen behavior on mobile and install button visibility on desktop Chromium browsers over HTTPS.

### V7.14-10 Delivery Validation
- Verify the browser tab title shows `E-Bill | Invoice Automation Software`.
- Confirm cron timing values persist in the settings UI after save and reload.
- Confirm auto-backup entries appear in the backup list after the cron job completes.
- Confirm email settings page reloads the latest saved values after save or refresh.
- After saving cron times, confirm backend logs or scheduler state reflect the updated next run times.
- Verify manual and scheduled invoice generation both use the configured `auto_invoice_days_before` value.
- Configure Resend and SMTP together, force a Resend failure, and confirm SMTP fallback sends successfully.
- Verify SMTP-only configuration works when Resend is left blank.

### Admin Payment Gateway Assignment
- Add a platform gateway from admin settings and confirm it appears as `Platform / SaaS Payments`.
- Add operator-specific gateway keys from the admin dialog and confirm the correct operator name appears in the list.
- Verify updating an operator's assigned keys replaces the existing operator gateway instead of creating duplicates.
- Confirm the operator settings panel no longer shows payment gateway configuration.
- Confirm custom-payment-gateway operators can still generate subscriber payment links when admin-assigned keys exist.
- Confirm operators can no longer configure gateway keys through the old operator endpoint/UI flow.

### VPS Cron / Scheduler Verification
- Deploy `V7.14-9` to the VPS and restart the backend container/service.
- Check backend logs for `Scheduled job registered: id=... next_run=...` lines on startup.
- Verify each expected job is registered:
  - `daily_backup`
  - `daily_expiry`
  - `daily_invoices`
  - `daily_wallet_check`
  - `daily_reminders`
- Trigger or wait for at least one scheduled run and verify success/error logging appears in backend logs.
- Confirm jobs execute on VPS time according to configured `Asia/Kolkata` schedule handling.

### Single Session Enforcement - CHECKED & WORKING
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

## Invoice Workflow Validation - CHECKED & WORKING

### Pending Invoice Editing - CHECKED & WORKING
- Edit a pending invoice with one line item and confirm totals remain correct.
- Edit a pending multi-line invoice and confirm item updates persist.
- Edit subscriber, due date, and service periods, then reload invoice list and public invoice.

### Mark Paid Confirmation - CHECKED & WORKING
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

### Public Payment Regression - CHECKED & WORKING
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

### Invoice Branding and Public Invoice Consistency - CHECKED & WORKING
- Manual logo upload and visibility-toggle verification
- Public invoice branding/address/payment-state verification
- PDF/print verification for branding parity and invoice metadata

### Multi-Plan Subscribers and Multi-Line Invoices - CHECKED & WORKING
- Manual creation of subscriber with multiple plans on different billing dates
- Manual creation of a multi-line invoice
- Automated billing cron verification for grouped multi-line invoice generation

### Admin Wallet Operations - CHECKED & WORKING
- Manual admin credit, debit, and suspend verification
- Validate audit trail and transaction list after each wallet action

## Automated Test Follow-Ups

- Add backend tests for single-session invalidation on second login.
- Add backend tests for operator/admin cancellation behavior on paid invoices.
- Add backend tests for `PUT /operator/invoices/{invoice_id}` pending-only edit rule.
- Add backend tests for `PUT /operator/invoices/{invoice_id}/status` requiring payment mode/date for manual paid status.
- Add forgot-password tests to confirm WhatsApp recovery is no longer accepted.

## Next Requested Batch

- Verify admin can assign payment gateway keys to an operator from the admin dialog.
- Verify operator-side payment gateway settings are no longer visible.
- Payment receipt generation and delivery flow
- Messaging/reporting polish
- Import/export refinement
