# Agent Handoff - E-Bill Platform

**Last Updated:** 2026-03-24  
**Active Branch:** `V7.14-11`
**Latest Feature Branch:** `V7.14-11`

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

---

## Current Documentation State

The following files were refreshed on `V7.14-11`:
- [README.md](/d:/eBill/README.md)
- [memory/CHANGELOG.md](/d:/eBill/memory/CHANGELOG.md)
- [memory/ROADMAP.md](/d:/eBill/memory/ROADMAP.md)
- [memory/PRD.md](/d:/eBill/memory/PRD.md)
- [memory/PENDING_TESTS.md](/d:/eBill/memory/PENDING_TESTS.md)
- [memory/agent-handoff.md](/d:/eBill/memory/agent-handoff.md)
- [frontend/README.md](/d:/eBill/frontend/README.md)

---

## Recommended Next Work

1. Add richer SEO/social preview metadata to `frontend/public/index.html`.
2. Add installable web app support with manifest/service worker wiring.
3. Deploy and verify `V7.14-11` on VPS.
4. Continue payment receipt and messaging improvements.

---

## Git State At Handoff

- Current branch: `V7.14-11`
- Feature baseline under docs branch: `V7.14-11`
