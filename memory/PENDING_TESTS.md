# Pending Tests

## Task 1: Wallet Accounting and Billing Integrity
- Manual Razorpay top-up verification for credited amount vs paid amount
- Manual wallet transaction/history verification after top-up
- Manual subscription renewal regression check to confirm no stale subscription wallet credit
- Optional targeted API verification for wallet top-up create/verify endpoints

## Task 2: Auth and OTP Production Hardening
- Live registration OTP send/verify with valid Resend credentials
- Live forgot-password OTP send/verify/reset flow
- WhatsApp recovery OTP regression check
- Automated OTP edge-case coverage: expiry, resend throttling, invalid attempts, provider failures

## Task 3: Platform Maintenance Mode
- Manual admin maintenance toggle and custom-message persistence
- Manual operator/staff write-block verification with read-only reads still working
- Manual admin/operator banner visibility verification
- Manual cron skip verification while maintenance mode is enabled
- Frontend smoke test for `/auth/app-state` and disabled action states

## Task 4: Invoice Branding and Public Invoice Consistency
- Public invoice route verification for invoice-number URLs and legacy id fallback
- Manual public invoice render verification with operator logo, address, and payment status
- PDF verification to confirm branding and field-visibility settings match public invoice data
- Operator invoice-settings upload-logo flow verification
- Regression check for payment creation and verification using invoice-number public routes

## Task 5: Multi-Plan Subscribers and Multi-Line Invoices
- Manual creation of subscriber with multiple plans on different billing dates
- Manual creation of a multi-line invoice
- Automated billing cron execution verification for multi-line grouping
- Verify `backend/tests/test_task5_multi_plan.py` executes successfully in a stable environment

## Task 6: Session Timeout and Strong Role Validation
- Manual save of `session_timeout_hours` in Admin settings
- Force expiration of token and verify frontend Axios interceptor logs the user out gracefully
- Attempt to delete a subscriber/staff using a staff account to verify 403 Forbidden
- Verify `backend/tests/test_task6_roles_session.py` executes successfully in a stable environment

## 2026-03-22: Invoice & Admin Fixes

### Invoice Add-Row / Calendar
- [ ] Open the Create Invoice dialog, add a second line item, verify no crash occurs.
- [ ] Verify due date and service period date pickers open, close on select, and have correct layout.

### PDF Invoice Logo
- Upload a company logo in Operator → Settings → Invoice.
- Download a generated PDF invoice and verify the logo appears.

### Subscription GST & Wallet Credit
- Create a SaaS checkout order; verify the Razorpay amount is base_price + 18%.
- Complete the payment flow; verify the operator wallet is credited with pre-GST amount only.

### Admin SaaS Plans GST Text
- Navigate to Admin → SaaS Plans; verify all price labels say "Excl. GST" not "GST Inclusive".

### Admin Email Settings
- Navigate to Admin → Settings → Email API tab.
- Save a Resend API key and from-email; verify it persists on reload.
- Trigger an OTP flow and verify the email uses DB credentials (not ENV if DB key is set).

### Admin Sidebar Landing Page Removal
- Log in as admin; verify "Landing Page" is no longer in the sidebar navigation.

