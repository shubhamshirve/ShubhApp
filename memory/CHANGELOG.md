# E-Bill Platform — CHANGELOG
# Current Version: V9.12

## 2026-05-11

### V9.12 — Feature Pack: Subscriber Expiry Audit, Backup Pagination, Operator WA Stats

#### 1. Subscriber Plan Expiry Audit Trail (Operator)
- **New endpoint** `GET /api/operator/subscribers/{subscriber_id}/expiry-audit` — returns timeline of plan expiry changes derived from the subscriber's invoice line items.
- **Frontend**: Added "Expiry History" option in the subscriber row dropdown (⋮ menu). Opens a timeline dialog showing plan name, service period (start → end), invoice number (badge), invoice status, and timestamp.
- Empty state shown when no invoice-based expiry events found.

#### 2. Backup List Pagination (Admin)
- **Backend**: `GET /api/admin/backup/list` now accepts `page` (default 1) and `per_page` (default 10, max 100) query params. Returns `{ backups, total, page, per_page, total_pages }` instead of a flat array.
- **Frontend** (`admin/Backup.jsx`): Added pagination controls below the backup table (Previous/Next buttons with "Page X of Y"). Total count card updated to reflect `total` from API.

#### 3. Operator WhatsApp Stats Page
- **New endpoints**:
  - `GET /api/operator/whatsapp-stats` — stats filtered by operator's own messages (total, today, this month, sent/failed, success rate, by_category, by_trigger, recent 7-day chart).
  - `GET /api/operator/whatsapp-message-logs` — paginated message logs with filters (status, category, date range, search).
- **New page** `frontend/src/pages/operator/WhatsAppStats.jsx` — stat cards, 7-day bar chart, by-category breakdown, paginated logs table with filters.
- **Navigation**: Added "WA Stats" link to operator sidebar (visible only when `whatsapp_notifications` feature is active).
- **Route**: `/operator/whatsapp-stats` (accessible by operator and staff).



## 2026-04-26

### V9.11 — WhatsApp delivery & read tracking via Cloud API webhook

Surfaces real WhatsApp delivery state in the Admin → WhatsApp Stats → Message Logs → "View Status" modal.

#### Backend
- New webhook endpoint `GET/POST /api/webhooks/whatsapp` (`routers/webhooks.py`).
  - GET: Meta verification handshake (`hub.mode`, `hub.challenge`, `hub.verify_token`) — echoes challenge as `text/plain` only when token matches stored value. Returns 403 otherwise.
  - POST: parses `entry[].changes[].value.statuses[]` and updates the matching `whatsapp_message_logs` doc by `message_id`.
- Forward-only state machine via `_STATUS_RANK` (sent → delivered → read; failed always wins). Never downgrades.
- Sets `delivered_at`, `read_at`, `failed_at` per event. If `read` arrives without prior `delivered`, `delivered_at` is auto-filled.
- Failed events capture Meta error info: `error_code`, `error_title`, combined `error_message` from `errors[].error_data.details`.
- Each status push appends an audit record to `events[]` (status, timestamp, source).
- Orphan events (unknown `message_id`) create a placeholder row with `trigger='webhook_orphan'` so admin still sees them.
- Webhook always returns 200 to prevent Meta retry storms.
- `services/whatsapp_service.log_whatsapp_message` now seeds `delivery_status`, `delivered_at`, `read_at`, `failed_at`, `error_code`, `error_title`, `events[]` on the initial send-time row.
- `WhatsAppConfig` model adds `webhook_verify_token`. `GET /api/admin/whatsapp-config` returns masked `webhook_verify_token_preview`. `PUT` persists it; the raw token is never returned.
- `GET /api/admin/whatsapp-message-logs` accepts `delivery_status` query param (`sent | delivered | read | failed`).

#### Frontend
- WhatsApp Stats → Message Logs:
  - New "Delivery" filter dropdown (4 options: Sent / Delivered / Read / Failed).
  - Status column now renders a `DeliveryStatusBadge` (✓ / ✓✓ grey / ✓✓ blue / Failed) reflecting `delivery_status`.
  - "View Status" modal redesigned with a 3-step delivery timeline (Sent → Delivered → Read) plus an explicit "Failed at delivery" row showing `failed_at`, `error_code`, and `error_title` from Meta.
  - Modal explains "Awaiting delivery confirmation" when no webhook callbacks yet received.
- Admin → Settings → Platform WhatsApp Config: new "Webhook Verify Token" input (password-masked, current value shown as preview). Help text shows the exact webhook URL to paste into Meta.

#### Backend tests (10/10 pass)
- `/app/backend/tests/test_whatsapp_webhook_status.py` covers verify handshake (correct + wrong), config persistence + masking, sent → delivered → read pipeline, no-downgrade rule, failed-with-error-codes, orphan creation, and `delivery_status` query filter.

#### Meta dashboard configuration (manual, one-time)
1. Meta App Dashboard → WhatsApp → Configuration → Webhooks.
2. Set Callback URL: `<REACT_APP_BACKEND_URL>/api/webhooks/whatsapp` (e.g. `https://recursing-proskuriakova-9.preview.emergentagent.com/api/webhooks/whatsapp`).
3. Set Verify Token: arbitrary string — paste the same value in Admin → Settings → Platform WhatsApp Config → Webhook Verify Token, save.
4. Subscribe to the **messages** field on the WhatsApp Business Account.


## 2026-04-25

### V9.10 — Bug fix: First invoice amount on multi-tenure subscribers + workspace cleanup

#### Bug fix — First invoice billed wrong amount for non-default `selected_validity`
For a ₹500/month plan with a yearly subscriber, the first invoice showed ₹500 instead of ₹6000. Two root causes:
1. `routers/operator.py` (~L1325) grouped enriched plan rows by `op_plan.validity` (always 'monthly') instead of the subscriber's effective `selected_validity`. Fixed: group by `ep.selected_validity or op_plan.validity`.
2. `services/cron_service.py` `_create_first_invoice` used `plan["price"]` directly, ignoring tenure. Fixed: scale via `VALIDITY_MONTHS` map (`raw_price / base_months * sel_months`) and persist `selected_validity` on the line item.

Verified end-to-end via `/app/backend/tests/test_first_invoice_validity.py` (5/5 pass): monthly→500, quarterly→1500, half_yearly→3000, yearly→6000, mixed-tenure subscriber → one invoice per effective tenure group.

#### Workspace cleanup (Cat 1, 2, 3)
- Removed 15 root-level temp scripts (`/app/backend_test_v*.py`, `debug_auth.py`, `fix_gst_config.py`, etc.).
- Removed 20 old `iteration_*.json` reports + 14 stale pytest XMLs (kept latest `iteration_21.json` + `first_invoice_validity_results.xml`).
- Removed 10 superseded backend tests in `/app/backend/tests/` (`test_billing_platform.py`, `test_billing_refactor.py`, `test_task5_multi_plan.py`, `test_iteration{5,6,7}_*.py`, `test_new_features_iteration4.py`, `test_p0_features.py`, `test_task6_roles_session.py`, `test_task8_admin_wallet.py`).
- Categories 4/5/6 (backend migrations, shadcn UI, stale docs) preserved per user instruction.


## 2026-04-24

### V9.10: Bulk Upload — Multi-Tenure & Calendar-Month Expiry Support

Updated all three bulk upload modules (plans / subscribers / invoices) and their sample CSV templates to support the multi-tenure plan feature (V8.32) and calendar-month expiry calculation (V8.29).

#### Plans bulk upload (`job_queue_service.py` — `_run_bulk_plans`)
- New column **`available_validities`** — comma-separated list (e.g. `"monthly,quarterly,yearly"`).
- Base `validity` is always auto-included. Invalid tenures produce a row-level error.
- Plan document stored with `available_validities` list.

#### Subscribers bulk upload (`job_queue_service.py` — `_run_bulk_subscribers`)
- New columns **`tenure_1..5`** — selected validity per plan slot (e.g. `yearly`).
- Blank tenure defaults to the plan's base `validity`. Tenure not in `available_validities` → row error.
- Expiry date calculation changed from fixed `+N days` (old `VALIDITY_DAYS_BULK`) to **`start + N calendar months – 1 day`** using `dateutil.relativedelta` — consistent with V8.29.
- Subscriber plan entry stores `selected_validity`.

#### Invoices bulk upload (`job_queue_service.py` — `_run_bulk_invoices`)
- New column **`selected_validity`** (optional).
- When `base_amount` is blank: **auto-calculated** as `plan.price / base_months × selected_months` — consistent with V8.32 price formula.
- `selected_validity` stored in invoice line item.

#### Sample CSV templates (`routers/operator.py`)
| Endpoint | New column(s) | Example |
|---|---|---|
| `GET /plans/sample-csv` | `available_validities` | `"monthly,quarterly,half_yearly,yearly"` |
| `GET /subscribers/sample-csv` | `tenure_1..3` | `yearly`, `quarterly` |
| `GET /invoices/sample-csv` | `selected_validity` | `yearly`, blank = base |

Added `relativedelta` import to `job_queue_service.py`.

**Backend: 19/19 tests passing.**

---

### V8.32: Multi-Tenure Plan Support

Operators can now create one plan with multiple enabled tenures (monthly / quarterly / half-yearly / yearly) and choose the tenant at subscriber assignment or invoice creation time — no need to create separate plans per period.

#### Price formula
`price_for_tenure = plan.price / base_validity_months × selected_tenure_months`
_(plan.validity = base reference; plan.price = price for that base period)_

| Base (monthly ₹500) | Quarterly | Half-Yearly | Yearly |
|---|---|---|---|
| ₹500 | ₹1,500 | ₹3,000 | ₹6,000 |

#### Backend — `models.py`
- `OperatorPlanCreate` + `OperatorPlanResponse`: added `available_validities: List[str]`.
- `SubscriberPlan`: added `selected_validity: Optional[str]`.
- `InvoiceLineItem`: added `selected_validity: Optional[str]`.

#### Backend — `routers/operator.py`
- `create_plan` / `update_plan`: persist `available_validities` (base validity always included).
- `get_plans`: back-fills `available_validities = [validity]` for legacy plans with no field.
- `create_subscriber` / `update_subscriber`: expiry date uses `selected_validity` (falls back to `plan.validity`).
- Helper `_price_for_tenure(base_price, base_validity, selected_validity)` added.

#### Backend — `services/invoice_helpers.py`
- `build_invoice_payload`: when `selected_validity` differs from plan's base validity, auto-scales `base_amount` via `_price_for_tenure`. Stores `selected_validity` in enriched line item.

#### Backend — `services/cron_service.py`
- `_create_invoice_for_plans`: reads `selected_validity` from subscriber plan data; scales price accordingly.
- `_group_by_validity` block: groups by `selected_validity` (not plan validity).

#### Frontend — `Plans.jsx`
- Base Validity dropdown (price reference) + **Available Tenures checkbox grid** (4 tiles with computed prices per tenure).
- Plan table: shows Base Validity column + Available Tenures badges.

#### Frontend — `Subscribers.jsx`
- Plan assignment row: **Tenure dropdown** appears after plan select, listing only `available_validities`. Shows scaled price per tenure. Expiry auto-updates on tenure change.

#### Frontend — `Invoices.jsx`
- Plan line-item: **Tenure dropdown** after plan select. Price (`base_amount`) and `service_end_date` auto-recalc on tenure change.

---



**Backend** — `GET /api/admin/whatsapp-message-logs`:
- `per_page` default changed from 50 → 20; max enforced at 20 via `Query(20, ge=1, le=20)`.

**Frontend** — `frontend/src/pages/admin/WhatsAppStats.jsx`:

1. **Message Logs table**:
   - Removed the "Message ID" column.
   - Added a **"View" column** (last) with an Eye-icon button on every row.
   - Trigger labels updated with new triggers: `auto_invoice_create`, `first_invoice`, `manual_announcement`.

2. **Pagination**: Always visible (moved outside the `logs.length === 0` block). Shows `«`, `<`, numbered page pills (up to 5), `>`, `»` controls and "Page X of Y · Z total".

3. **"Message Status" modal** (new):  Opened by the Eye button. Shows:
   - Status banner: **"Sent & API Accepted"** (green, has message_id) / **"Sent (No Receipt)"** / **"Failed"** (red, shows error).
   - Detail grid: Sent At · Trigger · Recipient Phone · WA ID · Template · Category · Invoice # · Operator ID.
   - Full WhatsApp Message ID block with explanatory note about delivery vs acceptance.

---



#### 1. Complete WhatsApp message logging (all sends now logged)
Three previously un-logged send paths now write to `whatsapp_message_logs`:

| Location | Trigger field | What was missing |
|----------|--------------|-----------------|
| `operator.py` — announcement loop | `manual_announcement` | Result captured + `log_whatsapp_message` added |
| `operator.py` — auto-send on `POST /invoices` | `auto_invoice_create` | `wa_result` captured + log block added |
| `cron_service.py` — fallback `send_text_message` (wallet balance alert) | `cron_wallet` | Log call added after text send |

All log calls are wrapped in `try/except` so a logging failure never disrupts the send path.

#### 2. First-invoice WhatsApp send (`generate_first_invoice: true`)
`CronJobService._create_first_invoice` now sends the invoice notification via WhatsApp **and** logs it (trigger=`first_invoice`) after inserting the invoice — using the same pattern as `_create_invoice_for_plans`. Gracefully skips if WhatsApp is not configured.

**Files changed:**
- `backend/routers/operator.py`
- `backend/services/cron_service.py`

---



#### 1. Remove invoice_value_this_month from Admin Dashboard
- Removed `invoice_value_this_month` field from `GET /api/admin/dashboard` and the corresponding frontend KPI card. The subscriber overview section is back to 4 cards.

#### 2. Calendar-Month Expiry Date Calculation
Replaced fixed-day expiry arithmetic (`start + N days`) with calendar-month arithmetic (`start + N months - 1 day`) everywhere plan expiry dates are computed.

| Validity | Old | New (example start Apr 21) |
|----------|-----|---------------------------|
| Monthly | +30 days = May 21 | +1 month −1 day = **May 20** |
| Quarterly | +90 days = Jul 20 | +3 months −1 day = **Jul 20** |
| Half-Yearly | +180 days = Oct 18 | +6 months −1 day = **Oct 20** |
| Yearly | +365 days = Apr 21 | +12 months −1 day = **Apr 20** |

Edge cases handled correctly via `dateutil.relativedelta` (e.g. Jan 31 + 1 month = Feb 28/29).

**Backend changes:**
- `backend/routers/operator.py`: Added `_VALIDITY_MONTHS` constant + `_calc_plan_expiry(start, validity)` helper. Updated all 4 expiry calculation sites: `create_subscriber`, `update_subscriber`, `migrate_subscribers_to_expiry_dates`, `update_invoice_status` (mark-paid extension).
  - Mark-paid: `new_expiry = base_date + relativedelta(months=N)`, `new_start = base_date + 1 day`
- `backend/services/cron_service.py`: Updated `service_end` in `_create_invoice_for_plan` to use `relativedelta(months=N) - timedelta(days=1)`.

**Frontend changes:**
- `frontend/src/pages/operator/Subscribers.jsx`: `calcExpiry` now uses `Date.UTC + month arithmetic - 1 day` for the "Plan Expires On" preview.

---

## 2026-04-24

### V8.28: Admin Dashboard — Revised Revenue & Invoice Value Metrics

Updated the **"Subscriber Overview"** section of the admin dashboard (`/admin`):

1. **"Invoice Charges / mo"** (renamed from "Approx Revenue / mo") — now calculates the platform's expected monthly invoice-charge revenue as: Σ (operator's `per_invoice_price` × operator's active subscriber count) across all active operators. Tooltip updated accordingly.
2. **"Invoice Value (This Month)"** — new KPI card showing the total `final_amount` of all non-cancelled invoices generated this month across all operators.

**Backend** — `GET /api/admin/dashboard`:
- `approx_monthly_revenue`: replaced plan-price normalization with `per_invoice_price × active_sub_count` aggregation per operator.
- `invoice_value_this_month` (new field): sum of `final_amount` for invoices with `created_at >= start_of_month` and `status != "cancelled"`.

**Frontend** — `frontend/src/pages/admin/Dashboard.jsx`:
- 4th subscriber card title/hint updated to "Invoice Charges / mo".
- 5th card added: "Invoice Value (This Month)" (purple, `FileText` icon).
- Subscriber Overview grid updated to `grid-cols-2 md:grid-cols-3 lg:grid-cols-5`.

---

## 2026-04-23

### V8.27: Admin Dashboard — Subscriber Overview Section

Added a new **"Subscriber Overview"** section to the admin dashboard (`/admin`) sitting right below the existing Operator Overview, with 4 new KPI cards aggregated across all operators:

1. **Total Subscribers** — count of all non-deleted subscribers across the platform
2. **Active Subscribers** — subscribers with `status: "active"`
3. **Suspended Subscribers** — subscribers with `status: "suspended"`
4. **Approx Revenue / mo** — estimated monthly recurring revenue = Σ (active plan prices ÷ validity-in-months) across all active subscribers' active plans. Title tooltip: "Sum of active plan prices, normalized to monthly"

**Backend** — `GET /api/admin/dashboard` response extended with `total_subscribers`, `active_subscribers`, `suspended_subscribers`, `approx_monthly_revenue` (rounded to 2 dp).
**Frontend** — `frontend/src/pages/admin/Dashboard.jsx`: new `subscriberCards` array + new `<section>` rendered in a 2/4-col responsive grid.

Verified: current test data shows 46 active subscribers, ₹18,000/mo approx revenue.

---

## 2026-04-23

### V8.26: Pagination + Spacing Polish on Operator Invoices

- **Pagination** on `/operator/invoices` with fixed page size of **20 items per page**. Works in both view modes:
  - Flat view: 20 invoices per page
  - By Subscriber view: 20 subscriber groups per page (each group's nested invoices not paginated — operators can see all invoices for a given subscriber at once)
- Pagination bar shows `Showing X–Y of N invoices/subscribers` and `Previous / Page i of N / Next` controls. Hides automatically when total items ≤ 20.
- Page resets to 1 when search term, status filter, or view mode changes.
- **Spacing**: bumped the main page container from `space-y-6` → `space-y-8` so the list no longer looks glued to the search/filter bar above.

**Files**
- `frontend/src/pages/operator/Invoices.jsx`: `currentPage` + `PAGE_SIZE=20` state, effect to reset page on filter/view change, inline `PaginationBar` component, paged slice rendered in both flat and grouped branches.

---

## 2026-04-23

### V8.25: Consolidated "By Subscriber" View on Operator Invoices Page

Added a new view toggle on the operator `/operator/invoices` page. Operators can flip between the original **Flat** table (unchanged) and a new **By Subscriber** grouped view where each subscriber with invoices becomes an expandable card.

**What each subscriber card shows**
- Subscriber name
- Validity mix pills (e.g. `Monthly × 6`, `Half-Yearly × 1`, `Custom × 2`)
- Aggregate totals: **Outstanding** (₹), **Paid** (₹), **Invoices** (count)
- Click to expand → nested table with all their invoices (same row actions: Mark as Paid, Download PDF, Send WhatsApp, Edit, Cancel, etc.)

**Why this matters**
After the `plan_expiry_date` billing refactor, each validity (Monthly / Quarterly / Half-Yearly / Yearly) gets its own independent invoice per billing cycle. A subscriber with Monthly + Half-Yearly plans now has multiple concurrent invoices. This view lets operators see at a glance: "Rajesh owes ₹1,050 across 2 invoices (1 Monthly pending + 1 Half-Yearly pending)" instead of hunting through a flat list.

**Extras**
- "Expand all" / "Collapse all" controls
- Groups sorted by outstanding amount desc, then name
- Each line-item pill now shows its validity inferred from its service window (e.g. `Broadband Basic | Monthly`)
- Filters/search work identically in both views (the view toggle is purely a rendering choice)

**Files**
- `frontend/src/pages/operator/Invoices.jsx` — new `viewMode` + `expandedSubscribers` state, `getValidityLabel()`, `groupedBySubscriber` (memoized), `renderInvoiceRow()` extracted helper for reuse, view-aware rendering block.

**Testing**
- Testing agent (iteration 20) verified **9/9 scenarios passing**: toggle, expand/collapse, filter/search integration, regression on row actions, mixed-validity subscriber card.

---


## 2026-04-23

### V8.24: Billing Engine Refactor — `plan_expiry_date` Architecture (COMPLETE)

Switched the entire billing engine from the legacy `billing_date` (day-of-month) approach to an exact `plan_expiry_date` approach. This fixes yearly-plan over-invoicing and makes billing windows precise.

**Backend**
- `backend/models.py`: `SubscriberPlan` gained `plan_start_date` + `plan_expiry_date` (ISO YYYY-MM-DD). `SubscriberCreate` gained `generate_first_invoice: bool`.
- `backend/routers/operator.py`:
  - `create_subscriber` now computes `plan_expiry_date = plan_start_date + validity_days` per plan and (optionally) triggers `_create_first_invoice` immediately.
  - `update_invoice_status` (mark-paid) extends each matching `plans[].plan_expiry_date` by the plan's validity days, using `base_date = max(old_expiry, paid_date)` so early payments don't shorten the cycle.
  - Added `POST /api/operator/subscribers/migrate-to-expiry-dates` — idempotent backfill.
- `backend/services/cron_service.py`:
  - `generate_upcoming_invoices` now queries `plans.plan_expiry_date` within the `days_before` notice window (no more 28-day hardcoded yearly bug). Legacy `billing_date` fallback preserved for unmigrated subscribers.
  - New `_create_first_invoice` helper for on-creation invoicing.
  - Operator query relaxed to `status: {$nin: ['suspended','deleted']}` so legacy docs without a status field are still processed.
- `backend/services/job_queue_service.py`: Bulk CSV upload now parses `plan_start_date_1..5` columns (legacy `billing_date_1..5` still accepted as fallback).
- `backend/seed_test_data.py`: Seeded test operator now always has `status: 'active'`.

**Frontend**
- `frontend/src/pages/operator/Subscribers.jsx`:
  - Plan rows now show **Plan Start Date** input with auto-computed **Plan Expires On** preview (via `calcExpiry(start, validity)`).
  - Added **"Generate First Invoice Now?"** toggle in the Add/Edit Subscriber dialog.
  - Added **"Migrate to Expiry Billing"** action button that calls the migration endpoint.
  - Bulk Upload CSV template and instructions updated to use `plan_start_date_1..5` columns.

**Bug Fixes (during refactor)**
- `_create_first_invoice` was calling a non-existent `self._get_next_invoice_number(...)` — fixed to use `utils.generate_invoice_number_atomic(self.db)`.
- Silent `except Exception` in `create_subscriber` first-invoice branch was masking the above bug — promoted to `logger.error(..., exc_info=True)`.
- Backfilled all legacy operators missing the `status` field (`{status: {$exists: false}}` → `'active'`).

**Tests**
- `/app/backend/tests/test_billing_expiry_refactor.py` — **11/11 passing** (default start/expiry math, explicit start date, first-invoice on/off, mark-paid extension, migration idempotency, sample CSV headers, cron no-error, cron skips far-future, cron creates in notice window).

---

## 2026-04-19

### V8.23: GST Control Settings for SAAS Plans & Wallet Topups

#### New Feature: Configurable GST Charges
- **Admin Settings:** Added toggle controls to enable/disable GST charges independently for:
  - SAAS Plan subscriptions (purchases and renewals)
  - Wallet topups
- **Default Behavior:** Both GST toggles enabled by default (maintains existing behavior)
- **Backend Logic:** Checkout and topup endpoints now check GST enablement settings before calculating GST
- **Flexibility:** Admin can disable GST for specific transaction types while keeping it enabled for others

**Changes:**
- `frontend/src/pages/admin/Settings.jsx`: Added two Switch controls under Platform Settings
  - "Apply GST on SAAS Plans" toggle
  - "Apply GST on Wallet Topups" toggle
- `backend/routers/wallet.py`: Wallet topup endpoint checks `gst_enabled_on_wallet_topup` setting
- `backend/routers/operator.py`: Checkout endpoint checks `gst_enabled_on_saas_plans` setting
- Both settings stored in `global_settings.platform` document

**Use Cases:**
- Disable GST for international operators
- Promotional periods without GST
- Regional tax compliance variations
- Testing without tax calculations

---

### V8.22: Critical Security Enhancement - HttpOnly Cookie Authentication

#### 🔒 Security Fix: localStorage to HttpOnly Cookies Migration
- **CRITICAL SECURITY UPGRADE:** Migrated authentication from localStorage to secure httpOnly cookies
- **XSS Protection:** Auth tokens no longer accessible via JavaScript, preventing XSS token theft
- **CSRF Protection:** Implemented SameSite=lax cookie policy
- **Secure Transport:** Cookies marked as secure (HTTPS-only)

**Backend Changes:**
- `backend/routers/auth.py`:
  - `/auth/login` endpoint now sets httpOnly cookie instead of returning token in body
  - `/auth/verify-otp` (registration) endpoint sets httpOnly cookie
  - Added `/auth/logout` endpoint to properly clear cookies
  - Cookie settings: httpOnly, secure, samesite=lax, 24-hour expiry
- `backend/dependencies.py`:
  - `get_current_user()` now reads from cookie first, fallback to Authorization header
  - Maintains backward compatibility during migration period

**Frontend Changes:**
- `frontend/src/App.js`:
  - Removed all `localStorage.getItem("token")` and `localStorage.setItem("token")` calls
  - Removed token state management
  - All axios requests now use `withCredentials: true` to send cookies
  - Login/register flows updated to work with cookies
  - Logout now calls `/auth/logout` endpoint to clear server-side session

**Security Improvements:**
- ✅ Tokens no longer stored in localStorage (XSS-proof)
- ✅ HttpOnly flag prevents JavaScript access to auth tokens
- ✅ Secure flag ensures cookies only sent over HTTPS
- ✅ SameSite=lax provides CSRF protection
- ✅ Server-side session invalidation on logout

**Migration Notes:**
- Existing users will be logged out once (cookies replace localStorage)
- No action required from end users
- Backend maintains compatibility with Authorization header for API clients

---

### V8.21: Wallet Suspension Threshold Adjustment

#### UI Standardization: Date Pickers
- **Standardized date pickers** across the entire application
- Replaced custom PopoverDatePicker (calendar popup) with standard HTML5 `<Input type="date">`
- **Affected locations:**
  - Operator Invoices page: Due date, service start/end dates, payment confirmation date
  - Operator Reports page: Start date and end date filters
  - Now matches the date picker style used in Admin Payment Reports page
- **Benefits:** Consistent UX, better mobile support, native browser date picker
- **Files:** `frontend/src/pages/operator/Invoices.jsx`, `frontend/src/pages/operator/Reports.jsx`

#### Enhancement: Search Bar on Plans Page
- **Added search functionality** to Plans page
- Search by plan name, description, or price
- Real-time filtering as you type
- Shows appropriate empty state for no results
- **File:** `frontend/src/pages/operator/Plans.jsx`

#### Enhancement: Audit Logs Pagination
- **Reduced pagination limit** from 50 to 20 items per page
- Better performance and faster load times
- **File:** `frontend/src/pages/admin/AuditLogs.jsx`

#### Enhancement: Payment Mode on Invoice Receipt
- **Added payment mode** display to public invoice receipts
- Shows in "Payment Details" section for paid invoices
- **Display format:** Capitalizes and formats payment mode (e.g., "Bank Transfer", "Cash", "Own Upi")
- **Visible only when:** Invoice status is "paid" and payment_mode exists
- **File:** `frontend/src/pages/PublicInvoice.jsx`

#### Bug Fix: System Reset Email Service
- **Issue:** System reset OTP emails failed with "No email delivery provider is configured" even when email settings were configured in Admin UI
- **Root Cause:** `request_system_reset_otp` endpoint was using `get_email_service()` (sync) which only reads from environment variables, ignoring database configuration
- **Fix:** Changed to `get_email_service_async()` which properly loads email settings from database (Admin Settings UI)
- **Impact:** System reset OTP, password reset, and all transactional emails now work with database-configured email settings
- **File:** `backend/routers/admin.py` (Line 1738)
- **Note:** Users must configure email settings in Admin → Settings → Email Settings (SMTP or Resend)

#### UI Enhancement: Login Page Logo
- **Desktop view:** Logo now has a white rounded square background (10% larger than logo size)
- Improves visibility of logo against blue gradient background
- Mobile view unchanged
- File: `frontend/src/pages/Login.jsx`

#### Wallet Balance Thresholds Updated
- **Suspension threshold reduced:** ₹100 → ₹50
  - Operators now suspended when wallet balance drops below ₹50 (was ₹100)
  - Auto-unsuspend when balance reaches ₹50 or above
- **Low balance warning threshold reduced:** ₹500 → ₹100
  - Daily cron now sends WhatsApp low-balance warnings when balance < ₹100 (was < ₹500)
- **Files modified:** 
  - `backend/routers/wallet.py` — suspension/unsuspension logic in `deduct_wallet()`, topup handlers, admin credit endpoints
  - `backend/services/cron_service.py` — daily wallet check cron job, warning message text updated

**New Threshold Summary:**
```
₹50   → Suspension threshold (account read-only mode)
₹100  → Low balance warning (WhatsApp notification sent)
```

### V8.20: Welcome Modal, Operator WA Notifications, Invoice Limit Removal

#### 1. Welcome Modal (Admin → Settings → General)
- **Admin-configurable announcement popup** shown to users on first login (or when version is incremented)
- Settings: `welcome_modal_enabled`, `welcome_modal_title`, `welcome_modal_content`, `welcome_modal_show_for` (all/operators/admins), `welcome_modal_version`
- New endpoint: `GET /admin/welcome-modal` — accessible to all authenticated roles
- Frontend: `WelcomeModal.jsx` component added to Admin and Operator dashboards
- Version-tracked per user in localStorage — increment version to force re-show to all users

#### 2. Cron & WhatsApp Analysis — Fixes
- **Removed dead code:** `send_overdue_reminders` + `run_hourly_reminder_check` were defined but never scheduled; removed to avoid confusion
- **Wallet check WA upgraded to template-based**: Previously used `send_text_message` (only works within 24h conversation window); now uses `operator_low_balance_template` if configured, falls back to text only if no template assigned
- **Expiry check WA added**: `run_daily_expiry_check` now sends WA to operator when trial ends or subscription expires using `operator_account_expiry_template`
- **Renewal reminders added**: 7, 3, 1 day before subscription expiry sends WA using `operator_renewal_template`

#### 3. Remove Invoice Generation Wallet Limit
- Removed the ₹50 minimum wallet balance requirement from manual invoice creation (`POST /operator/invoices`)
- Removed the ₹50 minimum wallet balance check from auto-invoice cron (`generate_upcoming_invoices`)
- Wallet deduction (₹10 per invoice) still happens; only the blocking minimum check is removed

#### 4. Operator WhatsApp Notifications (New Template Categories)
- **4 new WA template types** in `WhatsAppTemplates.jsx`: `operator_low_balance`, `operator_account_expiry`, `operator_renewal`, `operator_daily_report`
- **Operator-specific variable options** in template editor: `operator_name`, `balance`, `expiry_date`, `days_to_expiry`, `report_date`, `total_invoices`, `collected_today`, `pending_count`, `overdue_count`
- **4 new template assignment fields** in Admin Settings → WhatsApp tab (under "Operator Notifications" section)
- **New cron job**: `daily_operator_report` (default 09:30 IST) — sends daily billing summary WA to each operator
- **New cron time setting**: `cron_daily_report_time` (configurable in Admin Settings → General → Cron Schedule Times)
- **`_resolve_operator_variables()`** helper function in cron_service.py maps template variable names to operator context data

## 2026-04-17

### V8.19: Code Review & Cleanup
- **Unused files removed:** Deleted `cron_service_restored.py`, `cron_service_utf8.py` (orphaned duplicates), `test_out.txt`, `diff.txt`, `backend_test.py`, three `feature*_summary.md` files, `announcement_whatsapp_template_guide.md` (duplicate), `CLAUDE.md`, `GEMINI.md`
- **server.py:** Removed duplicate `import logging`; updated module docstring to reflect current architecture
- **README, CHANGELOG, agent-handoff:** Updated to V8.19 with all recent features

### V8.18: WhatsApp Template Testing
- **Test button per template:** Flask icon button on every row in the Templates table opens a "Test Template" dialog
- **Test dialog:** Shows template metadata, per-variable editable fields (pre-filled with sensible defaults), optional header image URL and button URL fields, and a result banner (success/failure with WhatsApp message ID)
- **Backend endpoint:** `POST /admin/whatsapp-test-template` — fetches template from DB, auto-fills missing variable slots, calls WhatsApp Cloud API, logs errors, returns human-readable error messages for common failure cases (phone not in allowed list, template name mismatch, etc.)

### V8.17: Invoice & Wallet Rule Hardening
- **Wallet minimum Rs 50:** Invoice creation (manual and cron auto-generate) now blocked when operator wallet balance < ₹50 (was ₹100). Error message updated. Cron service skips operators with insufficient balance before attempting auto-invoice creation.
- **Generate Payment Link visibility:** Button now requires ALL of: `status === "pending"`, payment_gateway add-on active, operator has payment gateway keys configured (`/operator/payment-gateway → configured: true`), AND `accept_payment_gateway === true` in invoice settings. Previously showed for any non-paid invoice with the add-on.

### V8.16: WhatsApp Stats & Message Logging
- **whatsapp_message_logs collection:** Every WhatsApp send (cron reminders, auto-invoice, manual operator sends) is logged with operator_id, template_name, template_category, recipient_phone, status, message_id, wa_id, invoice reference, and trigger type
- **Stats page `/admin/whatsapp-stats`:** Overview cards (Total, Today, This Month, Success Rate), 7-day bar chart, breakdown by category and trigger, paginated message logs table with filters (status, category, date range, search), and WhatsApp error logs section
- **API endpoints:** `GET /admin/whatsapp-stats`, `GET /admin/whatsapp-message-logs` (paginated + filterable), `DELETE /admin/whatsapp-message-logs`
- **"WA Stats" sidebar link** added to admin navigation

### V8.15: Payment Due Reminders Template Category
- **New template category `payment_due_reminder`:** Separate from `payment_reminder` (before/on due date) — intended for overdue invoices only; shown in red badge
- **Cron logic:** `days_diff < 0` → `payment_due_reminder_template`; `days_diff == 0` → `reminder_template`; `days_diff > 0` → `invoice_template` (previously `days_diff <= 0` used the same template)
- **Template assignment UI:** New "Payment Due Reminders (Overdue)" field in admin Settings → Template Assignment
- **Quick Setup preset** added for payment_due_reminder type

### V8.14: Operator Dashboard & UX Fixes
- **Cancelled invoices card:** Added 5th stat card (Cancelled) to operator dashboard alongside Total, Pending, Overdue, Paid
- **Invoice action menu:** "Send via WhatsApp API" relabelled to "Send via WhatsApp API (Rs 0.5)"; added "Send via WhatsApp Web" button (opens wa.me link, no feature flag required)
- **OperatorResponse model:** Made `owner_name` and `status` Optional with safe defaults to prevent `KeyError` / Pydantic validation errors on older operator documents missing these fields

## 2026-04-15

### V8.13: WhatsApp Template Header Support & Media Handling
- **Dynamic Headers:** Added support for Text and Image headers in WhatsApp templates.
- **Media Parameter Support:** The WhatsApp service now correctly handles header parameters for Image-type templates, preventing the "Format mismatch" error.
- **Variable-to-Header Mapping:** Operators can now map variables like `Company Logo` directly to the template header.
- **Absolute Media URLs:** Implemented automatic resolution of relative file paths (e.g., logos) to absolute URLs required by the WhatsApp API.

### V8.12: WhatsApp Template Variable Resolver
- **Dynamic Variable Mapping:** Implemented `resolve_template_variables` to automatically map placeholders like `{{1}}`, `{{2}}` to database fields (Customer Name, Invoice No, etc.).
- **Admin Variable Selection:** Updated the WhatsApp Template management UI to allow selection of variables for body text.

### V8.11: UPI Payment Message Prefill & Invoice Enhancements
- **UPI Transaction Note (`tn`):** Plan name and service tenure (start–end date) are now automatically prefilled as the payment note when a subscriber pays via any UPI app, giving the operator clear transaction context.
- **Plan Description on Invoice:** The public invoice now shows the plan's description as an italicised sub-line below the service tenure in the line items table.
- **Payment Method Selector:** Replaced individual payment-type toggles with an explicit dropdown in Invoice Customization — options are Both, Gateway Only, UPI Only, or None.
- **UPI App Chooser Modal:** Tapping "Pay with UPI" now opens a modal letting the subscriber choose Google Pay, PhonePe, Paytm, BHIM, or any other app, preventing automatic OS hijacking.
- **Gateway Key Enforcement:** Payment gateway is now only enabled when the operator has their own dedicated keys configured; no platform gateway fallback for subscriber payments.

## 2026-04-14

### V8.10: Direct UPI Payments Integration
- **Direct UPI App Payments (Intent Link):** Added the ability for operators to accept direct peer-to-peer UPI payments without a payment gateway.
- **Business Profile Settings:** Added a new field for `UPI ID` in the operator's business profile.
- **Invoice Preferences:** Operators can now independently toggle "Accept Payment via Gateway" and "Accept Payment via UPI Apps".
- **Dynamic Invoice UI:** The public invoice page dynamically displays "Pay Online" and/or "Pay via UPI App" buttons based on operator settings.

### V8.9: Payment Link Generation & UI Enhancements
- **Manual Payment Links:** Operators can now generate manual payment links for individual invoices via the Invoices page.
- **Dynamic Payment Routing:** Integrated operator-specific gateway credentials for manual payment links to ensure correct fund routing.
- **Invoice UI Update:** Added "Generate Payment Link" action button to the Invoices table for faster operator access.

## 2026-04-03

### V8.8: Bulk Subscriber Upload — Multi-Plan Support
- **Multi-Plan CSV Format:** Bulk subscriber upload now supports up to 5 plans per subscriber via `plan_name_1..5`, `billing_date_1..5`, `discount_1..5` columns (one row per subscriber)
- **Route Ordering Fix:** Moved `sample-csv` and `bulk-upload` routes before `{subscriber_id}` parameterized routes to prevent FastAPI matching `sample-csv` as a subscriber ID (was causing 404)
- **CSV Download Fix:** Fixed silent download failure across Subscribers, Plans, Invoices, and Reports pages — anchor element must be appended to DOM before `.click()`

### V8.7: CSV Download Fix
- Fixed bulk upload sample file download (404) — static routes must precede parameterized routes in FastAPI
- Fixed programmatic CSV/file downloads across all pages (anchor not appended to DOM)

### V8.6: Remove WhatsApp Web Service
- **WhatsApp WebJS Removed:** Removed `whatsapp-service` Docker container from `docker-compose.prod.yml` and GitHub Actions build pipeline
- **Deployment Log Capture:** Added backend and MongoDB log dump to CI/CD script on deployment failure for easier debugging
- Deleted `whatsapp-service/` source directory

## 2026-04-02

### V8.4: Decommission WhatsApp & Automation Enhancements
- **WhatsApp WebJS Decommissioned:** Removed WhatsApp Web UI from operator settings and invoice actions
- **Automated Operator Wallets:** Wallet auto-initialized with SaaS plan `monthly_price` when admin creates an operator
- **Consolidated Payment Gateways:** Unified gateway configs; public invoice payments enforce operator-assigned keys exclusively

### V8.3: Production Deployment Hardening
- Removed `container_name` from `docker-compose.prod.yml` to prevent name conflicts during redeployment
- Added `docker-compose down --remove-orphans` before `up` for clean deploys
- Fixed WhatsApp image tag alignment in CI/CD workflow

## 2026-03-25

### V7.15-10: Docker Infrastructure Optimization
- Reduced `.env` from 40+ to 8-10 core variables
- Fixed MongoDB authentication (`authSource=admin` in URI)
- Dual compose files: `docker-compose.yml` (dev) + `docker-compose.prod.yml` (prod)
- Multi-stage backend Dockerfile with `BUILD_ENV` arg (dev vs prod requirements)
- Environment-aware config (`IS_PRODUCTION`, `LOG_LEVEL`, feature flags)

### V7.15-9: Settings Consolidation
- Removed orphaned "Env Tab"; added Security Tab with JWT + backup password fields
- Added `env_generator.py` for `.env` auto-generation from database
- Caddy proxy with security headers

### V7.15-8: Service Refactor
- Migrated JWT, Razorpay, Resend credentials to database-backed storage
- `env_service.py` with database-first priority
- Async factory functions for all services

### Earlier Versions (V7.14–V7.15-7)
- Single-session JWT enforcement
- Invoice bulk upload with sample CSV/XLSX
- Invoice branding, public links, and public payment verification
- Multi-plan subscribers and multi-line invoices
- Global IST cron scheduling (configurable from admin UI)
- Admin impersonation and return flow
- Email OTP registration + SMTP fallback
- Wallet accounting, referral codes, discount codes
- Support tickets, audit logs, automated backups
- SEO metadata, PWA support (manifest + service worker)
- Staff management with account status toggle
- Operator payment gateway delegation
- Dashboard monthly value statistics
- SMTP fallback tolerates servers without AUTH support


### V8.13: WhatsApp Template Header Support & Media Handling
- **Dynamic Headers:** Added support for Text and Image headers in WhatsApp templates.
- **Media Parameter Support:** The WhatsApp service now correctly handles header parameters for Image-type templates, preventing the "Format mismatch" error.
- **Variable-to-Header Mapping:** Operators can now map variables like `Company Logo` directly to the template header.
- **Absolute Media URLs:** Implemented automatic resolution of relative file paths (e.g., logos) to absolute URLs required by the WhatsApp API.

### V8.12: WhatsApp Template Variable Resolver
- **Dynamic Variable Mapping:** Implemented `resolve_template_variables` to automatically map placeholders like `{{1}}`, `{{2}}` to database fields (Customer Name, Invoice No, etc.).
- **Admin Variable Selection:** Updated the WhatsApp Template management UI to allow selection of variables for body text.

### V8.11: UPI Payment Message Prefill & Invoice Enhancements
- **UPI Transaction Note (`tn`):** Plan name and service tenure (start–end date) are now automatically prefilled as the payment note when a subscriber pays via any UPI app, giving the operator clear transaction context.
- **Plan Description on Invoice:** The public invoice now shows the plan's description as an italicised sub-line below the service tenure in the line items table.
- **Payment Method Selector:** Replaced individual payment-type toggles with an explicit dropdown in Invoice Customization — options are Both, Gateway Only, UPI Only, or None.
- **UPI App Chooser Modal:** Tapping "Pay with UPI" now opens a modal letting the subscriber choose Google Pay, PhonePe, Paytm, BHIM, or any other app, preventing automatic OS hijacking.
- **Gateway Key Enforcement:** Payment gateway is now only enabled when the operator has their own dedicated keys configured; no platform gateway fallback for subscriber payments.

## 2026-04-14

### V8.10: Direct UPI Payments Integration
- **Direct UPI App Payments (Intent Link):** Added the ability for operators to accept direct peer-to-peer UPI payments without a payment gateway. 
- **Business Profile Settings:** Added a new field for `UPI ID` in the operator's business profile.
- **Invoice Preferences:** Operators can now independently toggle "Accept Payment via Gateway" and "Accept Payment via UPI Apps".
- **Dynamic Invoice UI:** The public invoice page dynamically displays "Pay Online" and/or "Pay via UPI App" buttons based on operator settings.

### V8.9: Payment Link Generation & UI Enhancements
- **Manual Payment Links:** Operators can now generate manual payment links for individual invoices via the Invoices page.
- **Dynamic Payment Routing:** Integrated operator-specific gateway credentials for manual payment links to ensure correct fund routing.
- **Invoice UI Update:** Added "Generate Payment Link" action button to the Invoices table for faster operator access.

## 2026-04-03

### V8.8: Bulk Subscriber Upload — Multi-Plan Support
- **Multi-Plan CSV Format:** Bulk subscriber upload now supports up to 5 plans per subscriber via `plan_name_1..5`, `billing_date_1..5`, `discount_1..5` columns (one row per subscriber)
- **Route Ordering Fix:** Moved `sample-csv` and `bulk-upload` routes before `{subscriber_id}` parameterized routes to prevent FastAPI matching `sample-csv` as a subscriber ID (was causing 404)
- **CSV Download Fix:** Fixed silent download failure across Subscribers, Plans, Invoices, and Reports pages — anchor element must be appended to DOM before `.click()`

### V8.7: CSV Download Fix
- Fixed bulk upload sample file download (404) — static routes must precede parameterized routes in FastAPI
- Fixed programmatic CSV/file downloads across all pages (anchor not appended to DOM)

### V8.6: Remove WhatsApp Web Service
- **WhatsApp WebJS Removed:** Removed `whatsapp-service` Docker container from `docker-compose.prod.yml` and GitHub Actions build pipeline
- **Deployment Log Capture:** Added backend and MongoDB log dump to CI/CD script on deployment failure for easier debugging
- Deleted `whatsapp-service/` source directory

## 2026-04-02

### V8.4: Decommission WhatsApp & Automation Enhancements
- **WhatsApp WebJS Decommissioned:** Removed WhatsApp Web UI from operator settings and invoice actions
- **Automated Operator Wallets:** Wallet auto-initialized with SaaS plan `monthly_price` when admin creates an operator
- **Consolidated Payment Gateways:** Unified gateway configs; public invoice payments enforce operator-assigned keys exclusively

### V8.3: Production Deployment Hardening
- Removed `container_name` from `docker-compose.prod.yml` to prevent name conflicts during redeployment
- Added `docker-compose down --remove-orphans` before `up` for clean deploys
- Fixed WhatsApp image tag alignment in CI/CD workflow

## 2026-03-25

### V7.15-10: Docker Infrastructure Optimization
- Reduced `.env` from 40+ to 8-10 core variables
- Fixed MongoDB authentication (`authSource=admin` in URI)
- Dual compose files: `docker-compose.yml` (dev) + `docker-compose.prod.yml` (prod)
- Multi-stage backend Dockerfile with `BUILD_ENV` arg (dev vs prod requirements)
- Environment-aware config (`IS_PRODUCTION`, `LOG_LEVEL`, feature flags)

### V7.15-9: Settings Consolidation
- Removed orphaned "Env Tab"; added Security Tab with JWT + backup password fields
- Added `env_generator.py` for `.env` auto-generation from database
- Caddy proxy with security headers

### V7.15-8: Service Refactor
- Migrated JWT, Razorpay, Resend credentials to database-backed storage
- `env_service.py` with database-first priority
- Async factory functions for all services

### Earlier Versions (V7.14–V7.15-7)
- Single-session JWT enforcement
- Invoice bulk upload with sample CSV/XLSX
- Invoice branding, public links, and public payment verification
- Multi-plan subscribers and multi-line invoices
- Global IST cron scheduling (configurable from admin UI)
- Admin impersonation and return flow
- Email OTP registration + SMTP fallback
- Wallet accounting, referral codes, discount codes
- Support tickets, audit logs, automated backups
- SEO metadata, PWA support (manifest + service worker)
- Staff management with account status toggle
- Operator payment gateway delegation
- Dashboard monthly value statistics
- SMTP fallback tolerates servers without AUTH support
