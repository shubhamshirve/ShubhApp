# E-Bill Platform — CHANGELOG

## 2026-03-18

### Task 1: Referral + Wallet System ✅
- New `operator_wallets` and `wallet_transactions` collections
- Every operator gets unique `referral_code` (REF-XXXXXX) on registration
- Register page accepts referral code → 10% discount (up to ₹500) on first payment
- Referrer earns 5% of referred operator's payments for 3 months (wallet credit)
- Wallet deducts ₹10 per invoice generated (manual + auto cron)
- Wallet balance < ₹500 → daily cron sends WhatsApp reminder
- Wallet balance < ₹100 → operator suspended (is_read_only=True, automation stopped)
- Topup via Razorpay restores service if balance ≥ ₹100
- New pages: `/operator/wallet` (balance, topup, referral, transactions), `/admin/wallets` (all wallets, drilldown)
- New router: `/app/backend/routers/wallet.py`
- Tests: 100% pass (23/23 backend)

### Task 2: Basic/Pro Plan Revamp ✅
- Added `plan_type`, `per_customer_rate`, `monthly_base_fee` to SaaS plan model
- **Basic**: ₹12/customer/month, no addons, no platform fee
- **Pro**: ₹22/customer/month + ₹1,000/month base fee (credited to operator wallet), all addons included, no platform fee
- Admin plan creator has 3-button plan type selector (Basic / Pro / Custom)
- Checkout dynamically calculates based on active subscriber count
- Pro plan wallet_credit_amount = ₹1000 * months stored in checkout order
- Custom plans retain legacy fixed-price behavior
- Modified: `models.py`, `admin.py`, `operator.py`, `SaaSPlans.jsx`, `Subscription.jsx`
- Tests: 100% pass (33/33 backend)

### Task 5: Support Ticket System ✅
- Operators/Staff can create support tickets (title, description, priority: low/medium/high/urgent)
- Threaded conversation: operator and admin can reply
- Admin auto-sets status to "in_progress" on first reply
- Status management: Open → In Progress → Resolved → Closed
- Admin page: stats cards, filters (status/priority/search), ticket detail with operator info panel
- New router: `/app/backend/routers/support.py`
- New pages: `/operator/support`, `/admin/support`
- Both sidebars updated with Support link
- Tests: 100% pass (45/45 backend, all frontend)

### Task 7: Remove Landing Page ✅
- Root `/` now redirects to `/login` instead of showing landing page
- LandingPage import removed from App.js
- Admin Landing Page builder (`/admin/landing-page`) retained for future use
- Root `.env` created at `/app/.env` with Razorpay test keys and DB config
