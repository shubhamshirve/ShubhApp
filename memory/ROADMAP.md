# E-Bill Platform - Roadmap

## Completed
- [x] Referral + Wallet system
- [x] Basic/Pro SaaS plan revamp
- [x] Support ticket system
- [x] Landing page removal / login redirect
- [x] Codebase cleanup: settlement removal, platform fee removal, dead code cleanup
- [x] KYC fields in registration and admin operator management
- [x] Reminder scheduling framework and WhatsApp template assignment
- [x] Docker/Caddy deployment setup and root `.env` consolidation

---

## Active Delivery Plan

This roadmap replaces the older generic backlog with a codebase-aware implementation order based on the current implementation branch.

Priority logic:
- Fix money correctness before adding new billing features.
- Remove auth/demo/test weaknesses before rollout hardening.
- Land platform-wide control features before large schema refactors.
- Defer broad model changes until the current wallet/invoice/auth flows are stable.

Legend:
- `Priority`: `P0`, `P1`, `P2`, `P3`
- `Importance`: `Critical`, `High`, `Medium`
- `Effort`: `S`, `M`, `L`, `XL`

---

## Sprint 1

### 1. Wallet Accounting and Billing Integrity
- Status: `implemented-in-code / pending live verification`
- Priority: `P0`
- Importance: `Critical`
- Effort: `L`
- Why first:
  - Impacts real money movement and operator trust.
  - Current code shows drift between roadmap/tests and live behavior around subscription wallet credit.
  - Wallet top-up currently credits the paid total directly, which conflicts with GST-exclusive top-up requirements.
- Scope:
  - Fix subscription payment to operator wallet or remove stale wallet-credit logic consistently.
  - Verify invoice generation always deducts current SaaS plan `per_invoice_price`.
  - Make wallet top-up amount GST-exclusive, compute GST separately, and preserve breakup in storage.
  - Ensure referral reward uses the correct basis after top-up/subscription changes.
  - Add or update tests for wallet top-up, deductions, referral reward, suspend/resume thresholds.
- Merged user tasks:
  - Subscription payment not going to operator wallet
  - Deduct amount from wallet according to plan only
  - Wallet top-up should be GST-exclusive with GST added before payment
- Dependencies:
  - None
- Current implementation notes:
  - Wallet top-up now treats the entered amount as pre-GST wallet credit, stores GST breakup in `checkout_orders`, and credits only the base amount after payment verification.
  - Referral reward on wallet top-up now uses the credited amount instead of the GST-inclusive paid amount.
  - Stale subscription wallet-credit logic was removed from SaaS checkout verification to align with the simplified flat subscription pricing model.
- Pending tests:
  - Manual Razorpay top-up flow with live/test keys to confirm paid amount vs credited amount.
  - Manual wallet transaction verification in UI after top-up.
  - Subscription renewal regression check to confirm no `subscription_credit` transaction is created.
  - Optional targeted API/integration run for `/operator/wallet/topup/create-order` and `/operator/wallet/topup/verify`.

### 2. Auth and OTP Production Hardening
- Status: `implemented-in-code / pending provider verification`
- Priority: `P0`
- Importance: `Critical`
- Effort: `M`
- Why first:
  - Registration and password recovery still contain test/demo behavior.
  - This is the largest production-readiness and security gap.
- Scope:
  - Remove hardcoded OTP bypasses from backend.
  - Remove demo credentials and test OTP hints from frontend.
  - Send registration OTPs via Resend.
  - Replace forgot-password fake email flow with real provider-backed delivery.
  - Add resend throttling, expiry handling, attempt limits, and tests.
- Merged user tasks:
  - Remove demo id/pass and test OTP details
  - Make registration OTPs send via Resend API
- Dependencies:
  - Resend credentials
- Current implementation notes:
  - Registration OTP and email-based recovery OTP now use a new Resend-backed email service.
  - Hardcoded registration/recovery OTP bypasses were removed.
  - Registration and recovery resend endpoints now enforce cooldown and resend limits.
  - Login and forgot-password demo/test UI hints were removed, and registration copy now reflects email OTP delivery.
- Pending tests:
  - Live registration OTP send/verify using valid `RESEND_API_KEY` and `RESEND_FROM_EMAIL`.
  - Live forgot-password email OTP send/verify/reset flow.
  - WhatsApp recovery OTP regression check for operators using WhatsApp method.
  - Add dedicated automated tests for OTP expiry, resend throttling, invalid OTP attempts, and Resend failure handling.

### 3. Platform Maintenance Mode
- Status: `implemented-in-code / pending live verification`
- Priority: `P0`
- Importance: `High`
- Effort: `M`
- Why now:
  - Platform already has partial read-only behavior for low wallet and expiry, but no admin-controlled global stop.
  - This should exist before we continue expanding automation.
- Scope:
  - Add maintenance mode in admin settings.
  - Stop all automation and cron-triggered writes while enabled.
  - Force non-admin users into read-only mode.
  - Show a clear app-wide maintenance popup/banner.
  - Audit log state changes.
- Merged user tasks:
  - Add maintenance mode into admin settings
- Dependencies:
  - None
- Current implementation notes:
  - Admin global settings now store `maintenance_mode` and a configurable `maintenance_message`.
  - Effective operator access now merges operator-level read-only with platform maintenance state.
  - Operator dashboard, subscription, and wallet APIs now expose maintenance state so the UI can render correctly.
  - Wallet top-up and subscription checkout/renew endpoints now block while maintenance mode is active.
  - Cron automation now short-circuits during maintenance instead of performing writes.
  - Admin and operator layouts now show maintenance banners, and operator actions are disabled in wallet/subscription flows.
- Pending tests:
  - Manual admin settings toggle test for maintenance on/off with custom message persistence.
  - Manual operator/staff verification that write actions are blocked while reads still work.
  - Manual banner visibility check in admin and operator layouts.
  - Manual cron validation to confirm scheduled jobs skip work during maintenance.
  - Frontend runtime smoke test after startup to confirm settings save and layout banner behavior.

---

## Sprint 2

### 4. Invoice Branding and Public Invoice Consistency
- Status: `implemented-in-code / pending live verification`
- Priority: `P1`
- Importance: `High`
- Effort: `L`
- Why here:
  - Public invoice flow exists, but URLs, branding, and PDF parity are incomplete.
  - This is customer-visible and improves professionalism quickly after Sprint 1.
- Scope:
  - Use `invoice_number` in public invoice URLs instead of internal IDs.
  - Keep backward compatibility for existing invoice links if practical.
  - Include operator address and logo consistently in public and downloaded invoices.
  - Align PDF output with invoice page view and payment status as closely as possible.
  - Add operator logo upload support.
  - Add invoice field visibility controls for configurable non-plan fields.
- Merged user tasks:
  - Public invoice URL should use invoice number
  - Invoice should show operator address and logo; PDF should match page view
  - Invoice customization should support logo upload and selectable fields
- Dependencies:
  - Best after Sprint 1 wallet/auth stabilization
- Current implementation notes:
  - Public invoice routes now resolve by `invoice_number` first, with legacy `invoice.id` fallback for older links.
  - Manual invoice creation now returns invoice-number-based public URLs.
  - Invoice settings now support logo upload plus field-level visibility toggles for branding/contact/subscriber/bank sections.
  - Public invoice page now renders operator logo, address, payment status, and field visibility rules from shared invoice settings.
  - PDF generation now uses the same merged invoice settings object as the public page and supports logo rendering.
- Pending tests:
  - Manual public invoice URL test using `invoice_number`, plus fallback verification for old id-based links.
  - Manual operator invoice settings test for logo upload, preview, save, and reload persistence.
  - Manual PDF verification for logo, address, payment status, and visible-field toggles.
  - Manual payment create/verify flow through the public invoice route after moving to invoice-number URLs.
  - Targeted regression check for WhatsApp/shared public invoice links opened from operator invoices.

### 5. Multi-Plan Subscribers and Multi-Line Invoices
- Status: `planned`
- Priority: `P1`
- Importance: `High`
- Effort: `XL`
- Why later:
  - This is the biggest data-model change in the backlog.
  - Current subscriber and invoice schema are single-plan centric.
- Scope:
  - Support multiple plans per subscriber.
  - Add single-billing vs multi-billing selection.
  - Allow create-invoice flow to select multiple plans.
  - Update auto-invoice logic, invoice rendering, totals, taxes, and payment links.
  - Create migration strategy for existing subscribers/invoices.
- Merged user tasks:
  - Let operators add multiple plans to subscribers with common/new billing date selection
  - In create invoice option also support multiple plans
- Dependencies:
  - Strongly depends on Sprint 1 stability

### 6. Session Timeout and Strong Role Validation
- Status: `planned`
- Priority: `P1`
- Importance: `Medium`
- Effort: `M`
- Why here:
  - JWT expiry exists, but idle-session controls and route-role hardening are still limited.
  - Better handled after auth/OTP cleanup, while we are already in access-control code.
- Scope:
  - Add configurable session timeout policy.
  - Improve expired session handling in frontend.
  - Review and tighten backend role checks for operator/admin/staff flows.
  - Revalidate impersonation and write-guard behavior.
  - Add tests for expired token and invalid role access.
- Merged user tasks:
  - Add session time and force session user role validations
- Dependencies:
  - Benefits from Sprint 1 auth work

---

## Sprint 3

### 7. Global Reminder Control and IST Scheduling
- Status: `planned`
- Priority: `P2`
- Importance: `Medium`
- Effort: `M`
- Why here:
  - Global WhatsApp credentials/template assignment already exist.
  - Remaining work is centralizing reminder scheduling and changing automation from UTC-centric behavior to IST.
- Scope:
  - Move reminder scheduling control into admin settings.
  - Apply settings globally across operators where intended.
  - Convert cron scheduling and user-facing copy from UTC to IST.
  - Review reminder and invoice timing calculations for timezone correctness.
- Merged user tasks:
  - Move WhatsApp reminders tab to admin settings and make it global
  - All cron jobs have IST timings
- Dependencies:
  - Maintenance mode should exist first to simplify safe rollout of scheduler changes

### 8. Admin Wallet Operations
- Status: `planned`
- Priority: `P2`
- Importance: `Medium`
- Effort: `M`
- Why after wallet fixes:
  - Admin wallet UI already exists in read-only form.
  - We should not add manual adjustments before core wallet math is correct.
- Scope:
  - Add admin credit/debit actions.
  - Add suspend/unsuspend wallet controls where needed.
  - Capture reasons and audit logs for all wallet actions.
  - Expose adjustment history in admin wallet transaction view.
- Merged user tasks:
  - Wallet CRUD options for admin
- Dependencies:
  - Depends on Task 1

---

## Sprint 4

### 9. Messaging and Reporting Polish
- Status: `planned`
- Priority: `P3`
- Importance: `Medium`
- Effort: `S-M`
- Why last:
  - Valuable, but lower risk than money/auth/platform-control work.
  - Existing announcement and reporting features are already functional in limited form.
- Scope:
  - Send announcements by email in addition to WhatsApp.
  - Hide GST tab for operators without GST number.
  - Review message templates and delivery consistency.
- Merged user tasks:
  - Announcements to be sent as E-mail with WhatsApp
  - Hide GST tab for operators which do not have GST number
- Dependencies:
  - Email provider configuration for announcement email delivery

### 10. Payment Receipts and Confirmation Delivery
- Status: `planned`
- Priority: `P3`
- Importance: `Medium`
- Effort: `M`
- Why here:
  - Existing PDF and WhatsApp template infrastructure makes this achievable without major architecture changes.
  - Better to land after wallet/auth/core invoice flows are stable.
- Scope:
  - Generate payment receipts for SaaS payments and relevant subscriber payment flows.
  - Reuse or extend PDF generation infrastructure for receipt documents.
  - Send payment confirmation/receipt via WhatsApp where configured.
  - Expose receipt download or retrieval path in the UI where appropriate.
- Source backlog item:
  - Payment receipt generation + WhatsApp
- Dependencies:
  - Best after Task 1 and Task 4

### 11. Import/Export Enhancements
- Status: `planned`
- Priority: `P3`
- Importance: `Medium`
- Effort: `S-M`
- Why here:
  - Import/export foundation already exists for subscribers, plans, and reports.
  - This is useful operationally and lower risk than payment/auth work.
- Scope:
  - Improve existing CSV/XLSX import/export coverage where gaps remain.
  - Add missing export paths for invoices, subscribers, and payments where useful.
  - Standardize formatting, filenames, and error feedback for import/export actions.
- Source backlog item:
  - Import/Export (CSV/Excel) improvements
- Dependencies:
  - None, but easier after invoice/report work is stable

---

## Deferred Review / Sprint Fit

These items were reviewed against the current codebase to decide whether they should remain deferred or be pulled into a sprint.

### Cashfree Gateway
- Status: `deferred`
- Reason:
  - Data model and UI already mention Cashfree, but the actual gateway service and webhook/payment flows are not implemented.
  - This needs full provider integration, testing, and credentials.
- Recommendation:
  - Keep deferred unless payment-provider expansion becomes a business priority immediately.

### SMS and Email Invoice/Reminder Delivery
- Status: `deferred`
- Reason:
  - Depends on provider choice and operational setup.
  - Notification surface is broad and should follow OTP and reminder centralization work.
- Recommendation:
  - Keep deferred for now, except announcement email can still be handled under Sprint 4 messaging polish.

### GST Reconciliation (R1 / 3B)
- Status: `deferred`
- Reason:
  - This is materially larger than normal reporting.
  - Requires tax-domain correctness, reconciliation rules, and likely export formats beyond the current reporting layer.
- Recommendation:
  - Keep deferred until after core billing, invoice, and reporting flows stabilize.

### Advanced Analytics
- Status: `deferred`
- Reason:
  - Charting support exists in frontend dependencies, but the higher-value analytics work should follow stabilization of billing, invoice, and multi-plan behavior.
- Recommendation:
  - Revisit after Tasks 4, 5, and 11

---

## Execution Notes

Recommended implementation order inside Sprint 1:
1. Wallet accounting and top-up math
2. Auth/OTP hardening
3. Maintenance mode

Recommended implementation order after Sprint 1:
1. Invoice/public URL consistency
2. Session/role hardening
3. Reminder centralization and IST scheduler updates
4. Multi-plan schema work

Risk notes:
- Task 1 can affect live balances and existing tests.
- Task 2 removes current test shortcuts; local/dev workflows may need a controlled non-production strategy.
- Task 5 requires schema migration and careful backward compatibility handling.
- Task 7 requires validating exact IST schedule expectations with the business before rollout.
