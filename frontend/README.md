# E-Bill Frontend

React frontend for the E-Bill platform.

## Stack

- React 19
- React Router
- Axios
- Tailwind CSS
- CRACO
- Radix/shadcn-style UI components

## Main Areas

- `src/App.js`
  - auth bootstrap
  - route protection
  - session expiry handling
  - single-session revalidation on focus/interval
- `src/pages/admin/`
  - admin dashboards and platform controls
- `src/pages/operator/`
  - operator billing, subscribers, invoices, settings, wallet, reports
- `src/components/`
  - layouts and shared UI primitives

## Notable Current Behavior

- forgot-password is email-only
- old session is logged out when the same account logs in elsewhere
- pending invoices can be edited
- marking invoice paid requires payment mode and payment date
- app/browser title is `E-Bill | Invoice Automation Software`
- admin settings now allow editing cron times in IST for backup, expiry, invoice, wallet, and reminder jobs
- admin email settings now support Resend plus SMTP fallback configuration
- backend cron scheduler was hardened in `V7.14-9` for VPS reliability; check backend logs for scheduled job registration lines after deploy
- homepage metadata now includes canonical, Open Graph, Twitter, and JSON-LD schema markup
- installable web app support is enabled via `manifest.json`, generated icons, and `sw.js` registration in production

## Scripts

```bash
npm start
```

```bash
npm run build
```

```bash
npm test
```

## Build Notes

- Production build currently succeeds.
- The repo still has existing `react-hooks/exhaustive-deps` warnings in several files.
- Those warnings are not new to `V7.14-10` and do not block the build.
