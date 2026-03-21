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
