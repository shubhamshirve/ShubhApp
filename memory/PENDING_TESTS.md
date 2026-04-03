# Pending Tests & Validation

## Recently Verified (V8.6–V8.8)

- [x] WhatsApp service removed from docker-compose and CI/CD — confirmed not starting
- [x] CSV sample download works (Subscribers, Plans, Invoices, Reports) — anchor DOM fix
- [x] Bulk subscriber upload with multiple plans (up to 5) — new CSV format
- [x] Route ordering fix — `sample-csv` no longer returns 404
- [x] Local docker-compose up — all containers healthy (backend, frontend, mongodb, caddy)
- [x] MongoDB auth error diagnosed — SCRAM storedKey mismatch on production (resolved with volume reset)

## Outstanding Validations

### Production Environment
- [ ] Social preview / Open Graph tags render correctly on production HTTPS
- [ ] PWA install prompt appears on production (manifest + service worker)
- [ ] SMTP test mail delivers in live environment
- [ ] SMTP fallback triggers when Resend fails
- [ ] Scheduler jobs persist and fire after server restart
- [ ] Payment gateway delegation — operator key used on public payment page
- [ ] Browser cache clear works from admin and operator settings

### Feature Regression
- [ ] Admin impersonation and return flow
- [ ] Single-session enforcement across devices (new login invalidates old token)
- [ ] Bulk subscriber upload: duplicate phone skipped, limit check enforced
- [ ] Bulk invoice upload: correct subscriber + plan lookup
- [ ] Wallet auto-initialization on operator creation by admin
- [ ] Referral code auto-generation for new operators
- [ ] Backup list refresh after auto-backup cron completes
- [ ] Cron schedule changes take effect immediately (live reschedule)
