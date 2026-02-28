# Multi-Tenant SaaS Recurring Billing Platform

## Deployment Guide for XAMPP and cPanel Hosting

### Quick Start (XAMPP)

1. **Copy files to htdocs**
   ```
   Copy the entire `php_xampp_version` folder to:
   C:\xampp\htdocs\saas-billing
   ```

2. **Import Database**
   - Open phpMyAdmin: http://localhost/phpmyadmin
   - Create database named `saas_billing`
   - Import `database.sql` file

3. **Configure**
   - Edit `config.php`:
     - Update DB_HOST, DB_NAME, DB_USER, DB_PASS
     - Change JWT_SECRET for security
     - Update APP_URL

4. **Setup .htaccess for API routing**
   Create `.htaccess` in `/api/` folder:
   ```apache
   RewriteEngine On
   RewriteCond %{REQUEST_FILENAME} !-f
   RewriteCond %{REQUEST_FILENAME} !-d
   RewriteRule ^(.*)$ index.php [QSA,L]
   ```

5. **Access**
   - API: http://localhost/saas-billing/api/
   - Frontend: Deploy React build or use the Emergent version

### Deployment on cPanel Shared Hosting

1. **Upload Files**
   - Use File Manager or FTP
   - Upload to `public_html/saas-billing/`

2. **Create MySQL Database**
   - Go to MySQL Databases in cPanel
   - Create database and user
   - Assign all privileges

3. **Import SQL**
   - Open phpMyAdmin
   - Select your database
   - Import `database.sql`

4. **Update Config**
   - Edit `config.php` with your credentials

5. **Setup Cron Jobs** (cPanel → Cron Jobs)
   ```
   # Daily invoice generation - 6:00 AM
   0 6 * * * /usr/bin/php /home/user/public_html/saas-billing/cron/generate_invoices.php

   # Daily reminder - 9:00 AM
   0 9 * * * /usr/bin/php /home/user/public_html/saas-billing/cron/send_reminders.php

   # Trial/subscription expiry check - midnight
   0 0 * * * /usr/bin/php /home/user/public_html/saas-billing/cron/check_expiry.php

   # Database backup - 2:00 AM
   0 2 * * * /usr/bin/php /home/user/public_html/saas-billing/cron/backup.php
   ```

### Default Credentials

- **Admin Login**: admin@saas.com / admin123

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Register new operator |
| POST | /auth/login | Login |
| GET | /auth/me | Get current user |
| GET | /admin/dashboard | Admin KPIs |
| GET | /admin/saas-plans | List SaaS plans |
| POST | /admin/saas-plans | Create SaaS plan |
| GET | /admin/operators | List operators |
| POST | /admin/operators/{id}/assign-plan | Assign plan |
| GET | /operator/dashboard | Operator KPIs |
| GET | /operator/plans | List service plans |
| POST | /operator/plans | Create service plan |
| GET | /operator/subscribers | List subscribers |
| POST | /operator/subscribers | Add subscriber |
| GET | /operator/invoices | List invoices |
| POST | /operator/invoices | Create invoice |
| GET | /operator/reports/revenue | Revenue report |
| GET | /operator/reports/gst-summary | GST summary |
| GET | /operator/reports/pending-overdue | Pending report |

### Security Notes

1. Change `JWT_SECRET` in production
2. Use HTTPS in production
3. Disable error display in production
4. Regular database backups

### File Structure

```
saas-billing/
├── api/
│   ├── index.php          # Main API router
│   └── .htaccess          # URL rewriting
├── cron/
│   ├── generate_invoices.php
│   ├── send_reminders.php
│   ├── check_expiry.php
│   └── backup.php
├── config.php             # Configuration
├── database.sql           # Database schema
└── README.md
```

### Razorpay Integration

1. Get API keys from https://dashboard.razorpay.com/
2. Configure in Operator Settings → Payment Gateway
3. Setup webhook URL: `https://yoursite.com/saas-billing/api/webhooks/razorpay`

### WhatsApp Business API

1. Apply for WhatsApp Business API access
2. Get Phone Number ID and Access Token
3. Configure in Admin settings
4. Create message templates for:
   - Invoice notification
   - Payment reminder
   - Bulk notifications
