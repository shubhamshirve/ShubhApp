# eBill — Deployment Guide (GHCR + 1GB VPS)

## How it works

```
Push to 'live' branch
    └── GitHub Actions: Lint → [Build Backend + Build Frontend] (parallel)
                               └── Push images to GHCR
                                       └── SSH into VPS → docker pull + restart
                                               └── Watchtower polls GHCR every 5min (fallback)
```

No Docker build happens on the VPS. Only `docker pull` + `docker compose up`.

---

## Step 1 — Create a GitHub Personal Access Token (PAT)

You need a PAT with `read:packages` scope so the VPS can pull images from GHCR.

1. Go to: https://github.com/settings/tokens?type=beta  
   *(or classic: https://github.com/settings/tokens/new)*
2. Click **"Generate new token (classic)"**
3. Give it a name: `ebill-vps-ghcr`
4. Set expiration: **No expiration** (or 1 year)
5. Tick only: **`read:packages`**
6. Click **Generate token**
7. **Copy the token** — you won't see it again (starts with `ghp_...`)

---

## Step 2 — Add GitHub Actions Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name           | Value                                        |
|-----------------------|----------------------------------------------|
| `CR_PAT`              | Your PAT from Step 1 (`ghp_...`)             |
| `DEPLOY_HOST`         | Your VPS IP address (e.g. `123.456.78.90`)   |
| `DEPLOY_USER`         | SSH username (e.g. `root` or `ubuntu`)       |
| `DEPLOY_SSH_KEY`      | Your SSH **private key** content             |
| `DEPLOY_PORT`         | SSH port (default: `22`)                     |
| `DEPLOY_PATH`         | App path on VPS (e.g. `/opt/ebill`)          |
| `REACT_APP_BACKEND_URL` | Your domain URL (e.g. `https://yourdomain.com`) |

### How to get your SSH private key:
```bash
# On your local machine:
cat ~/.ssh/id_rsa        # Copy entire content including -----BEGIN/END----- lines
```
If you don't have one:
```bash
ssh-keygen -t ed25519 -C "github-deploy"
cat ~/.ssh/id_ed25519    # private key → add to GitHub Secret
cat ~/.ssh/id_ed25519.pub  # public key → paste into VPS: ~/.ssh/authorized_keys
```

---

## Step 3 — VPS Initial Setup (run once)

SSH into your VPS and run:

```bash
# 1. Clone the repo
mkdir -p /opt/ebill && cd /opt/ebill
git clone https://github.com/shubhamshirve/ShubhApp.git .
git checkout live

# 2. Create your .env file
cp .env.example .env    # or create manually
nano .env               # fill in all required values

# 3. Login to GHCR (uses your CR_PAT)
export CR_PAT=ghp_your_token_here
make ghcr-login

# 4. Pull and start services (first time)
make deploy-ghcr

# 5. (Optional) Start Watchtower for auto-deploy
make watchtower-up
```

---

## Step 4 — Make GHCR Packages Public (recommended)

This removes the need for GHCR auth on the VPS entirely.

1. Go to: https://github.com/shubhamshirve?tab=packages
2. Click **shubhapp-backend** → **Package settings**
3. Scroll to "Danger Zone" → **Change visibility** → **Public**
4. Repeat for **shubhapp-frontend**

After this, remove the `make ghcr-login` step from VPS setup.

---

## Day-to-day Usage

| Action | How |
|--------|-----|
| **Deploy** | Push to `live` branch — GitHub Actions handles everything |
| **Manual deploy on VPS** | `make deploy-ghcr` |
| **Pull latest images only** | `make pull-images` |
| **View logs** | `make logs` |
| **Rollback** | `make rollback-ghcr TAG=abc1234` |
| **Stop Watchtower** | `make watchtower-down` |
| **Check status** | `make status` |

---

## Option B vs C explained

| | Option B (SSH Deploy) | Option C (Watchtower) |
|---|---|---|
| **How** | GitHub Actions SSHes into VPS and runs docker pull+restart | Container on VPS polls GHCR every 5min for new images |
| **Speed** | Immediate on push | Up to 5 min delay |
| **Requires SSH secrets?** | Yes | No |
| **This setup** | Primary (runs on every push) | Fallback/secondary |

Both run together in this setup. SSH deploy is primary (instant); Watchtower is a safety net.

---

## Environment Variables (.env on VPS)

```env
DOMAIN=yourdomain.com
SERVER_IP=your.vps.ip
MONGO_ROOT_USERNAME=ebilladmin
MONGO_ROOT_PASSWORD=strongpassword
JWT_SECRET=your-64-char-secret
BACKUP_PASSWORD=your-backup-password
CORS_ORIGINS=https://yourdomain.com
REACT_APP_BACKEND_URL=https://yourdomain.com
DB_NAME=saas_db
```
