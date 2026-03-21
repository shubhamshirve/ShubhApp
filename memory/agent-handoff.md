# Agent Handoff - E-Bill Platform

**Last Updated:** 2026-03-21  
**Active Branch:** `V7.14`  
**Status:** Planning sync completed, implementation not yet started

---

## Current Snapshot

The repository has been moved from `V7.13-1` to `V7.14`.

What changed in `V7.14` so far:
- Updated [ROADMAP.md](d:/eBill/memory/ROADMAP.md) to reflect a codebase-aware delivery plan
- Reviewed deferred work and pulled two items into active sprint planning:
  - Payment receipts and confirmation delivery
  - Import/export enhancements
- Pushed branch `V7.14` to `origin`

No product feature implementation has started yet on this branch.

---

## Current Working Plan

The active source of truth is [ROADMAP.md](d:/eBill/memory/ROADMAP.md).

### Sprint 1
1. Wallet accounting and billing integrity
2. Auth and OTP production hardening
3. Platform maintenance mode

### Sprint 2
4. Invoice branding and public invoice consistency
5. Multi-plan subscribers and multi-line invoices
6. Session timeout and strong role validation

### Sprint 3
7. Global reminder control and IST scheduling
8. Admin wallet operations

### Sprint 4
9. Messaging and reporting polish
10. Payment receipts and confirmation delivery
11. Import/export enhancements

Deferred:
- Cashfree gateway
- SMS and email invoice/reminder delivery
- GST reconciliation (R1 / 3B)
- Advanced analytics

---

## Immediate Next Task

Start with:

### Task 1: Wallet Accounting and Billing Integrity

Why this is first:
- It affects real money movement
- It has drift between code, tests, and historical docs
- Later billing/invoice work depends on getting wallet behavior correct

Main concerns already identified:
- Subscription wallet credit behavior appears inconsistent with older tests/docs
- Wallet top-up currently credits the paid total directly
- Top-up flow does not yet support GST-exclusive entry with GST computed separately
- Need to verify invoice deduction always uses the active plan's `per_invoice_price`

---

## Key Findings from Code Review

### Wallet and Subscription
- `backend/routers/wallet.py`
  - Wallet top-up order stores `base_amount` and `total_amount`
  - Verify flow currently credits `order["total_amount"]` directly to wallet
- `backend/routers/operator.py`
  - Subscription checkout currently stores `wallet_credit_amount: 0`
  - There is still conditional subscription wallet credit logic during checkout verification
- `backend/services/cron_service.py`
  - Auto-generated invoices deduct wallet via `deduct_wallet_for_invoice`
- `backend/models.py`
  - SaaS plans use `monthly_price` and `per_invoice_price`

### Auth and OTP
- `backend/routers/auth.py`
  - Registration OTP test bypass still exists
  - Recovery OTP test bypass still exists
  - Forgot-password email flow is still mocked/logged instead of real delivery
- `frontend/src/pages/Login.jsx`
  - Demo credentials are still shown
- `frontend/src/pages/ForgotPassword.jsx`
  - Test OTP hint is still shown

### Maintenance / Read-Only
- `backend/dependencies.py`
  - Read-only check exists
- `backend/services/cron_service.py`
  - Read-only mode is currently triggered from wallet suspension/expiry paths only
- `backend/routers/admin.py`
  - No true platform maintenance mode yet

### Invoice and Public Invoice
- `backend/routers/public.py`
  - Public invoice fetch still uses internal invoice ID
- `backend/routers/operator.py`
  - Public invoice URLs currently point to `/invoice/{invoice.id}`
- `frontend/src/pages/PublicInvoice.jsx`
  - Public view already supports payment status and GST display
- `backend/services/pdf_service.py`
  - PDF generation already exists and can be extended for receipts

### Reminder and Scheduling
- `backend/server.py`
  - Scheduler jobs are configured in UTC
- `frontend/src/pages/operator/Settings.jsx`
  - Reminder management still lives under operator settings
- `frontend/src/pages/admin/Settings.jsx`
  - Global WhatsApp credentials/template assignment already exist

### Reports / Import / Export
- Operator and admin CSV export already exist in report screens
- Subscriber and plan CSV/XLSX import already exist
- Frontend already includes `recharts`, but analytics work is not yet expanded

---

## Important Files for the Next Session

### Start here for Task 1
- [wallet.py](d:/eBill/backend/routers/wallet.py)
- [operator.py](d:/eBill/backend/routers/operator.py)
- [cron_service.py](d:/eBill/backend/services/cron_service.py)
- [models.py](d:/eBill/backend/models.py)
- [test_wallet_referral.py](d:/eBill/backend/tests/test_wallet_referral.py)
- [test_plan_revamp.py](d:/eBill/backend/tests/test_plan_revamp.py)

### Related planning context
- [ROADMAP.md](d:/eBill/memory/ROADMAP.md)
- [PRD.md](d:/eBill/memory/PRD.md)
- [CHANGELOG.md](d:/eBill/memory/CHANGELOG.md)

---

## Risks to Keep in Mind

- Wallet behavior may already be relied on by existing data or tests
- Historical docs mention older Pro-plan wallet credit behavior that may no longer match the branch
- Changing top-up accounting can affect referral reward calculations
- OTP hardening will remove current test shortcuts, so dev/test strategy may need adjustment
- Multi-plan billing should not begin before wallet/invoice/auth foundations are stable

---

## Recommended Next Execution Order

1. Reconcile wallet behavior in code vs tests vs intended business rule
2. Patch wallet top-up accounting and subscription wallet handling
3. Run targeted wallet/subscription tests
4. Move to auth/OTP hardening only after wallet logic is stable

---

## Branch / Git State at Handoff

- Branch: `V7.14`
- Remote tracking: `origin/V7.14`
- Latest planning commit before feature work:
  - `de12b72` - `Update roadmap for V7.14 delivery plan`

If continuing from here, update this file again after Task 1 is implemented or materially re-scoped.
