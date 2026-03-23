# Agent Handoff - E-Bill Platform

**Last Updated:** 2026-03-24  
**Active Branch:** `V7.14-12`
**Latest Feature Branch:** `V7.14-12`

---

## Current Snapshot

The codebase now includes:

- wallet accounting corrections
- email-backed OTP hardening
- maintenance mode
- invoice branding and invoice-number public links
- multi-plan subscribers and multi-line invoices
- global reminder controls with IST scheduling
- admin wallet actions
- single active session enforcement
- email-only password recovery OTP
- pending invoice edit support
- payment mode and payment date confirmation when operators manually mark invoices paid
- VPS cron scheduler reliability fix with direct async job registration and startup/job logging
- app title update to `E-Bill | Invoice Automation Software`
- Resend email delivery with SMTP fallback
- admin-configurable cron timings with live scheduler reschedule
- richer SEO/Open Graph/Twitter/schema metadata
- installable web app support with manifest, icons, and service worker
- cron settings persistence now refreshes correctly in the UI
- auto-backup entries now appear in the backup list after cron completion
- email settings now reload the latest saved values after save/refresh
- admin can assign payment gateway keys directly to operators
- operator settings no longer expose payment gateway configuration
- browser cache clear tools now exist in admin/operator settings
- login/session switching now clears stale cache automatically
- admin display-name changes are supported from settings
- Resend and SMTP test mail actions are available
- SMTP fallback now tolerates servers without AUTH support

---

## Most Recent Delivery

### Branch Flow
- `V7.14-6` was created and pushed from `V7.14-5`
- `V7.14-7` was created and pushed from `V7.14-6`
- `V7.14-8` is the documentation update branch based on `V7.14-7`
- `V7.14-9` is the scheduler reliability fix branch based on `V7.14-8`
- `V7.14-10` is the title, email fallback, and cron-settings branch based on `V7.14-9`
- `V7.14-11` is the metadata and installable web app branch based on `V7.14-10`

### V7.14-11 Changes

Primary files:
- [frontend/public/index.html](/d:/eBill/frontend/public/index.html)
- [frontend/public/manifest.json](/d:/eBill/frontend/public/manifest.json)
- [frontend/public/sw.js](/d:/eBill/frontend/public/sw.js)
- [frontend/public/icon-192.png](/d:/eBill/frontend/public/icon-192.png)
- [frontend/public/icon-512.png](/d:/eBill/frontend/public/icon-512.png)
- [frontend/public/apple-touch-icon.png](/d:/eBill/frontend/public/apple-touch-icon.png)
- [frontend/src/index.js](/d:/eBill/frontend/src/index.js)

Implemented behavior:
- Added richer SEO metadata, canonical tags, Open Graph tags, and Twitter card tags.
- Added JSON-LD schema markup for organization and software application identity.
- Added web app manifest and install icons.
- Added lightweight service worker registration for installability support.
- Enabled supported browsers to surface install/add-to-home-screen UI on deployed HTTPS builds.
- Settings saves now rehydrate the persisted cron/email values in the UI.
- Backup list refresh now shows scheduled auto-backups after completion.
- Admin can assign payment gateway credentials to specific operators from the admin settings dialog.
- Operator payment gateway configuration is now admin-managed and removed from the operator panel.

### V7.14-12 Changes

Primary files:
- [frontend/src/App.js](/d:/eBill/frontend/src/App.js)
- [frontend/src/pages/admin/Settings.jsx](/d:/eBill/frontend/src/pages/admin/Settings.jsx)
- [frontend/src/pages/operator/Settings.jsx](/d:/eBill/frontend/src/pages/operator/Settings.jsx)
- [frontend/public/sw.js](/d:/eBill/frontend/public/sw.js)
- [frontend/src/lib/browserCache.js](/d:/eBill/frontend/src/lib/browserCache.js)
- [backend/routers/admin.py](/d:/eBill/backend/routers/admin.py)
- [backend/routers/auth.py](/d:/eBill/backend/routers/auth.py)
- [backend/services/email_service.py](/d:/eBill/backend/services/email_service.py)
- [backend/models.py](/d:/eBill/backend/models.py)

Implemented behavior:
- Added browser/app cache clear actions in admin and operator settings.
- Automatically clears browser/app cache when login state changes or sessions switch.
- Service worker no longer caches `/api` responses.
- Admin settings now allow changing the admin display name.
- Email settings now include Resend test mail and SMTP test mail actions.
- SMTP fallback now skips login when `AUTH` is not offered by the server.

---

## Validation Completed Locally

- `npm run build` in `frontend/`

Build result:
- backend compile check succeeded

---

## Outstanding Validation

See [PENDING_TESTS.md](/d:/eBill/memory/PENDING_TESTS.md) for the live list.

Highest-value remaining checks:
- validate social previews against live `https://e-bill.in/`
- verify manifest/service worker behavior on production HTTPS
- verify install/add-to-home-screen UI appears on supported browsers/devices
- continue VPS scheduler and email fallback verification from `V7.14-10`
- verify settings save/reload and backup list refresh behavior in a deployed environment
- verify admin-assigned operator gateway keys work for subscriber payment links
- verify cache clear behavior across login/session switches
- verify admin display-name updates persist after refresh/login
- verify Resend and SMTP test mail actions against live providers

---

## Current Documentation State

The following files were refreshed on `V7.14-12`:
- [README.md](/d:/eBill/README.md)
- [memory/CHANGELOG.md](/d:/eBill/memory/CHANGELOG.md)
- [memory/ROADMAP.md](/d:/eBill/memory/ROADMAP.md)
- [memory/PRD.md](/d:/eBill/memory/PRD.md)
- [memory/PENDING_TESTS.md](/d:/eBill/memory/PENDING_TESTS.md)
- [memory/agent-handoff.md](/d:/eBill/memory/agent-handoff.md)
- [frontend/README.md](/d:/eBill/frontend/README.md)

---

## Recommended Next Work

1. Continue payment receipt and messaging improvements.
2. Verify cache clearing, admin-name updates, and email test tooling in a live environment.
3. Keep refining operator/admin gateway workflows where needed.

---

## Git State At Handoff

- Current branch: `V7.14-12`
- Feature baseline under docs branch: `V7.14-12`
