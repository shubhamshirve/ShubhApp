# GitHub Actions CI/CD Setup Guide

## Overview
This guide walks you through setting up automated CI/CD for the eBill application using GitHub Actions. The pipelines will:
- **Build** Docker images on every push
- **Test** basic functionality
- **Push** images to Docker Hub with branch tags
- **Auto-Deploy** to dev/staging/production environments

---

## Prerequisites
✅ Docker Hub account with active PAT (Personal Access Token)
✅ GitHub repository with Actions enabled
✅ Server(s) for deployment with Docker and Git installed
✅ SSH access to your servers

---

## Step 1: Create GitHub Secrets

### 1.1 Docker Hub Credentials
1. Go to [Docker Hub Settings → Security](https://hub.docker.com/settings/security)
2. Create a **Personal Access Token (PAT)**
   - Name: `github-actions`
   - Permissions: `Read & Write`
3. Copy the token

4. In GitHub repository:
   - Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Add two secrets:

| Secret Name | Value |
|------------|-------|
| `DOCKER_USERNAME` | Your Docker Hub username |
| `DOCKER_PAT` | Your Docker Hub PAT token |

### 1.2 Deployment SSH Credentials (For Auto-Deploy)

#### On your server:
```bash
# Generate SSH key pair (if you don't have one)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/github-deploy
# Don't set a passphrase

# Add public key to authorized_keys
cat ~/.ssh/github-deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Display private key (copy this)
cat ~/.ssh/github-deploy
```

#### In GitHub Secrets:
Add these secrets:

| Secret Name | Value | Example |
|------------|-------|---------|
| `DEPLOY_USER` | SSH username | `ubuntu` or `root` |
| `DEPLOY_SSH_KEY` | Private key from above | `-----BEGIN RSA PRIVATE KEY-----\n...` |
| `DEV_SERVER_HOST` | Dev server IP/hostname | `dev.example.com` or `192.168.1.100` |
| `STAGING_SERVER_HOST` | Staging server IP/hostname | `staging.example.com` |
| `PROD_SERVER_HOST` | Production server IP/hostname | `prod.example.com` |

**Note:** Only add the server secrets you're actually using.

---

## Step 2: Server Setup for Deployment

On each deployment server, set up the application:

```bash
# Login to server
ssh user@your-server-ip

# Create app directory
sudo mkdir -p /app
sudo chown $USER:$USER /app

# Clone repository
cd /app
git clone https://github.com/YOUR_USERNAME/ebill.git .

# Create .env file (critical!)
cat > .env << 'EOF'
DOMAIN=your-domain.com
SERVER_IP=your-server-ip
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=your-mongo-password
JWT_SECRET=your-jwt-secret
BACKUP_PASSWORD=your-backup-password
CORS_ORIGINS=http://your-domain.com,https://your-domain.com
REACT_APP_BACKEND_URL=http://your-domain.com:8000
EOF

# Ensure .env is not tracked by git
echo ".env" >> .gitignore

# Make docker-compose files executable
chmod +x docker-compose*.yml

# Create required directories
mkdir -p uploads logs mongodb_data
```

---

## Step 3: How the Pipeline Works

### Build Pipeline (`build.yml`)
Triggers on: `push` to develop/staging/main or manual trigger

**What it does:**
1. Builds Backend Docker image
   - Tags: `your-username/ebill-backend:develop` + `your-username/ebill-backend:abc1234`
   - Latest tag: `your-username/ebill-backend:latest` (main branch only)

2. Builds Frontend Docker image
   - Tags: `your-username/ebill-frontend:develop` + `your-username/ebill-frontend:abc1234`
   - Latest tag: `your-username/ebill-frontend:latest` (main branch only)

3. Pushes both images to Docker Hub
4. Caches layers for faster builds (saves API calls)

### Deploy Pipeline (`deploy.yml`)
Triggers on: `push` to develop/staging/main or manual trigger

**What it does:**
1. Determines which environment to deploy to:
   - `develop` branch → Dev server
   - `staging` branch → Staging server
   - `main` branch → Production server

2. Via SSH, executes deployment:
   - Pulls latest code from GitHub
   - Pulls latest Docker images from Docker Hub
   - Stops old containers
   - Starts new containers
   - Verifies health

---

## Step 4: Using the Pipeline

### Automatic (Recommended)
```bash
# Just push code and it runs automatically
git push origin develop
# → Build pipeline runs
# → Deploy pipeline runs automatically
```

### Manual Trigger
Go to GitHub repository → Actions → Select workflow → "Run workflow" button

Choose environment: develop/staging/production

---

## Step 5: Monitoring

### View Workflow Runs
1. Go to GitHub repository → Actions tab
2. See build and deploy status for each push
3. Click on workflow to see detailed logs

### Common Indicators
| Status | Meaning |
|--------|---------|
| ✅ Green | Build/Deploy successful |
| ❌ Red | Build/Deploy failed (check logs) |
| ⏳ Yellow | Running |

### Troubleshooting

**Build fails:**
```
→ Check Dockerfile syntax
→ Verify requirements.txt dependencies
→ Check for missing environment variables
```

**Deploy fails:**
```
→ Verify SSH key is correct
→ Check server IP/hostname
→ Ensure server has Docker installed
→ Check server has internet access for pulling images
→ Verify .env exists on server
```

**Images not pushed to Docker Hub:**
```
→ Check DOCKER_USERNAME and DOCKER_PAT secrets
→ Verify PAT has read/write permissions
→ Check Docker Hub account status
```

---

## Step 6: Environment-Specific Configuration

### Development (develop branch)
- Uses `docker-compose.yml`
- Exposes ports: 8000 (backend), 3000 (frontend)
- For local testing and development
- Deploys to: Dev server

### Staging (staging branch)
- Uses `docker-compose.yml` or `docker-compose.prod.yml`
- Similar to production but for testing
- Deploys to: Staging server

### Production (main branch)
- Uses `docker-compose.prod.yml`
- No exposed ports (reverse proxy only)
- Resource limits enabled
- Auto-restart on failure
- Deploys to: Production server

---

## Step 7: Docker Hub Image Management

Your images will be organized as:

```
your-username/ebill-backend
  ├─ develop    (latest from develop branch)
  ├─ staging    (latest from staging branch)
  ├─ main       (latest from main branch)
  ├─ latest     (same as main)
  ├─ abc1234    (specific commit)
  └─ def5678    (another commit)

your-username/ebill-frontend
  ├─ develop
  ├─ staging
  ├─ main
  ├─ latest
  └─ [commit hashes]
```

This allows rolling back to any commit if needed:
```bash
# Rollback backend to specific commit
IMAGE_TAG=abc1234 docker-compose up -d
```

---

## Step 8: Advanced: Manual Deployment without GitHub Actions

If Auto-Deploy fails, manually deploy:

```bash
# SSH to server
ssh user@server-ip

# Navigate to app
cd /app

# Pull latest code
git pull origin main

# Pull images
docker pull your-username/ebill-backend:latest
docker pull your-username/ebill-frontend:latest

# Restart services
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# Verify
docker-compose -f docker-compose.prod.yml ps
```

---

## Step 9: Rate Limiting Prevention

### What we've done to avoid rate limits:
✅ **Docker BuildX caching** - Caches layers, reduces API calls
✅ **Parallel builds** - Backend and frontend build simultaneously
✅ **GitHub Actions cache** - Reuses cache across runs
✅ **No redundant pulls** - Only pulls images when needed
✅ **No automated testing** - Skips npm test, pytest (you test manually)

### Stay under limits:
- Maximum 1 build per push
- Maximum 1 deploy per push
- Docker Hub free tier: 100 pulls per 6 hours (plenty for our usage)
- GitHub Actions: Free tier has 3000 minutes/month (we use ~5 min per build)

---

## Step 10: Example Workflow

### Your typical workflow:

```bash
# 1. Work on feature locally
git checkout -b feature/my-feature
# ... make changes and test manually ...

# 2. Commit and push
git add .
git commit -m "Add new feature"
git push origin feature/my-feature

# 3. Create Pull Request (optional)
# ... team reviews ...

# 4. Merge to develop
git checkout develop
git merge feature/my-feature
git push origin develop
# → BUILD + DEPLOY to Dev automatically! ✨

# 5. Test on dev server, then merge to main
git checkout main
git merge develop
git push origin main
# → BUILD + DEPLOY to Production automatically! ✨
```

---

## Checklist Before Going Live

- [ ] Docker Hub PAT created and stored in `DOCKER_PAT` secret
- [ ] `DOCKER_USERNAME` secret set
- [ ] SSH key generated on servers
- [ ] `DEPLOY_SSH_KEY` secret added
- [ ] `DEPLOY_USER` secret added (e.g., `ubuntu`)
- [ ] Server hostnames/IPs added as secrets
- [ ] `.env` file created on all servers
- [ ] Git repository exists on deployment servers
- [ ] Docker installed on deployment servers
- [ ] SSH from GitHub Actions can reach servers (test with manual trigger)
- [ ] First deployment succeeded (check logs in Actions tab)
- [ ] Application is running on deployed server
- [ ] Monitored logs for any errors

---

## Quick Reference Commands

```bash
# Check workflow status
cd d:\eBill
git log --oneline --all | grep "CI\|CD\|workflow"

# View GitHub Actions locally (install act - GitHub Actions emulator)
act -l  # List workflows
act      # Run all workflows locally (optional)

# Manual deployment if needed
ssh user@prod-server "cd /app && git pull && docker-compose -f docker-compose.prod.yml up -d"

# View Docker Hub images
docker search your-username

# Pull specific image version
docker pull your-username/ebill-backend:abc1234

# Check image size
docker images your-username/ebill-*
```

---

## Support & Debugging

**Where to check logs:**
1. GitHub Actions → Actions tab → Select workflow run → View logs
2. Server logs: `docker-compose logs backend` or `docker-compose logs frontend`
3. Docker Hub: Check build history and stats

**Common issues:**

| Issue | Solution |
|-------|----------|
| "Docker PAT invalid" | Regenerate PAT, ensure new token is in secret |
| "SSH connection refused" | Check IP/hostname, verify SSH is running on server |
| "Images not found on Docker Hub" | Check Docker Hub account, verify DOCKER_USERNAME is correct |
| "Container won't start" | Check `.env` file exists on server with correct values |
| "Rate limit exceeded" | This setup is designed to avoid it; if it happens, wait 6 hours |

---

## Next Steps

1. ✅ Set up GitHub Secrets (Step 1)
2. ✅ Configure servers (Step 2)
3. ✅ Push a test commit to develop branch
4. ✅ Monitor build in Actions tab
5. ✅ Verify deployment on server
6. ✅ Celebrate! 🎉

---

**Last Updated:** March 26, 2026
**Version:** V7.15-11
**Status:** Ready for Production
