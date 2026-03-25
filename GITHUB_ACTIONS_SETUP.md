# GitHub Actions CI/CD Setup Guide

## Quick Setup: 2 Environments (Local PC + Production Server)

If you're testing locally on your PC and only have a production server, use this simplified setup:

### Your Workflow
```
Feature branch (local testing):
  git push origin develop
  → GitHub builds images
  → You test on local PC: docker-compose up -d
  → Ready? Merge to live branch

Production deployment (auto-deploy):
  git push origin live
  → GitHub builds images
  → GitHub auto-deploys to production server ✨
```

### Secrets You Need (3 minimum)
1. `DOCKER_USERNAME` - Docker Hub username
2. `DOCKER_PAT` - Docker Personal Access Token
3. `PROD_SERVER_HOST` - Your production server IP/hostname
4. `DEPLOY_SSH_KEY` - Private SSH key (see Step 1.2 below)
5. `DEPLOY_USER` - SSH username (usually `ubuntu` or `root`)

**That's it!** Skip DEV_SERVER_HOST and STAGING_SERVER_HOST.

### Local Development (No Setup Needed!)
On your PC, just use docker-compose normally:
```bash
# Pull latest images (optional, for testing)
docker pull your-username/ebill-backend:develop
docker pull your-username/ebill-frontend:develop

# Or build locally
docker-compose build

# Start services locally
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop when done
docker-compose down
```

**No GitHub Actions needed for local testing!** Just normal docker-compose commands.

---

## Full Setup Guide

### Overview
This guide walks you through setting up automated CI/CD for the eBill application using GitHub Actions. The pipelines will:
- **Build** Docker images on every push
- **Test** basic functionality
- **Push** images to Docker Hub with branch tags
- **Auto-Deploy** to production environment

---

## Prerequisites
✅ Docker Hub account with active PAT (Personal Access Token)
✅ GitHub repository with Actions enabled
✅ Production server with Docker and Git installed
✅ SSH access to your production server

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

### 1.2 Deployment SSH Credentials (For Production Auto-Deploy)

#### On your production server:
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
| `PROD_SERVER_HOST` | Production server IP/hostname | `prod.example.com` or `192.168.1.100` |

---

## Step 2: Production Server Setup

On your **production server only**, set up the application:

```bash
# SSH to production server
ssh user@your-prod-server-ip

# Create app directory
sudo mkdir -p /app
sudo chown $USER:$USER /app

# Clone repository
cd /app
git clone https://github.com/YOUR_USERNAME/ebill.git .

# Create .env file (critical!)
cat > .env << 'EOF'
DOMAIN=app.e-bill.in
SERVER_IP=45.196.196.21
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=change-this-password
JWT_SECRET=change-this-password
BACKUP_PASSWORD=change-this-password
CORS_ORIGINS=http://app.e-bill.in,https://app.e-bill.in
REACT_APP_BACKEND_URL=http://app.e-bill.in:8000
EOF

# Ensure .env is not tracked by git
echo ".env" >> .gitignore

# Make docker-compose files executable
chmod +x docker-compose*.yml

# Create required directories
mkdir -p uploads logs mongodb_data
```

**That's all for server setup!** No need to set up your local PC - it's just for testing.

---

## Step 3: How the Pipeline Works (Automatic - No Action Needed!)

**This step is informational only! GitHub Actions runs these automatically when you push code.**

### Build Pipeline (`build.yml`)
**Triggers automatically on:** `push` to develop or live branch, or manual trigger

**What GitHub does automatically:**
1. Builds Backend Docker image from your code
   - Tags: `your-username/ebill-backend:develop` (for develop branch) 
   - Tags: `your-username/ebill-backend:live` + `your-username/ebill-backend:latest` (for live branch)
   - Also tags with commit hash: `your-username/ebill-backend:abc1234d`

2. Builds Frontend Docker image from your code
   - Same tagging as backend

3. Pushes both images to your Docker Hub account
4. Smart caching for faster builds (saves API calls to Docker Hub)

**You don't need to do anything** — just push your code!

### Deploy Pipeline (`deploy.yml`)
**Triggers automatically on:** `push` to live branch only, or manual trigger

**What GitHub does automatically (only for live branch):**
1. Detects you pushed to `live` branch
2. Via SSH to your production server:
   - Pulls your latest code from GitHub
   - Pulls latest Docker images from Docker Hub
   - Stops old containers
   - Starts new containers
   - Checks that everything is healthy

**You don't need to do anything** — just push to live and it deploys!

---

## Step 4: Using the Pipeline

### Your Development Workflow

**On your local PC (testing):**
```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes, commit
git add .
git commit -m "Add feature"

# Push to develop branch
git push origin develop

# GitHub builds images (automated)
# → Check Actions tab to see build status

# On your local PC, test with:
docker-compose up -d
# ... test the feature ...
docker-compose down

# If good, merge to live (production branch)
```

**Auto-deploy to production:**
```bash
# Merge develop into live
git checkout live
git merge develop

# Push to live (auto-deploys to production)
git push origin live

# GitHub builds + deploys automatically ✨
# → Images pushed to Docker Hub
# → Production server automatically updated
# → Check Actions tab to see deploy status
```

### Manual Trigger (Optional)
If you want to manually trigger the build/deploy without pushing:
1. Go to GitHub repository → Actions tab
2. Select "Build & Push to Docker Hub" workflow
3. Click "Run workflow"
4. Choose branch (develop or live)

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

### Development (Local PC)
- Branch: `develop` (or any feature branch)
- Uses: `docker-compose.yml` locally on your PC
- Exposes ports: 8000 (backend), 3000 (frontend), 27017 (MongoDB)
- For: Local feature testing
- Deployment: Manual (you run `docker-compose up -d`)

### Production (Remote Server)
- Branch: `live` (production branch)
- Uses: `docker-compose.prod.yml` on production server
- No exposed ports (reverse proxy only via Caddy)
- Resource limits: Enabled for stability
- Auto-restart: Enabled on failure
- Deployment: Automatic via GitHub Actions on push to live

---

## Step 7: Docker Hub Image Management

Your images will be organized as:

```
your-username/ebill-backend
  ├─ develop    (latest from develop branch)
  ├─ live       (latest from live/production branch)
  ├─ latest     (same as live)
  ├─ abc1234    (specific commit)
  └─ def5678    (another commit)

your-username/ebill-frontend
  ├─ develop
  ├─ live
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
git pull origin live

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

## Step 10: Your Workflow (2 Environments)

### Step-by-Step

```bash
# 1. Start new feature
git checkout -b feature/my-feature

# 2. Make changes and test locally
# ... edit code ...
docker-compose up -d
# ... manually test in browser ...
docker-compose down

# 3. Commit and push to develop
git add .
git commit -m "Add feature"
git push origin develop

# GitHub Actions automatically:
# ✅ Builds Docker images
# ✅ Pushes to Docker Hub (tag: develop)
# ❌ Does NOT deploy (only builds)

# 4. Your local testing (you do this manually)
docker-compose pull  # Get latest images from Docker Hub (optional)
docker-compose up -d
# Test thoroughly on your local PC...
# If it works, proceed to next step

# 5. Merge to live (production branch) and auto-deploy to production
git checkout live
git merge develop

# Push to live (auto-deploys to production)
git push origin live

# GitHub Actions automatically:
# ✅ Builds Docker images
# ✅ Pushes to Docker Hub (tag: latest, live)
# ✅ SSH to production server
# ✅ Pulls latest images
# ✅ Restarts containers
# ✨ YOU'RE LIVE on production!

# 6. Verify on production
ssh user@prod-server "docker-compose ps"
# See all containers running ✅
```

---

## Checklist Before Going Live

### Must Have (Critical)
- [ ] Docker installed on your local PC
- [ ] Docker Hub account created with PAT token
- [ ] `DOCKER_USERNAME` secret added to GitHub
- [ ] `DOCKER_PAT` secret added to GitHub
- [ ] SSH key generated on production server
- [ ] `DEPLOY_SSH_KEY` secret added to GitHub
- [ ] `DEPLOY_USER` secret added to GitHub (ubuntu/root)
- [ ] `PROD_SERVER_HOST` secret added to GitHub (your server IP)
- [ ] `.env` file created on production server
- [ ] Git repository cloned on production server
- [ ] Docker installed on production server

### Nice to Have (Optional)
- [ ] Test local docker-compose up/down on your PC
- [ ] SSH to production server works
- [ ] Production server has internet access for pulling images
- [ ] Monitoring logs via Actions tab

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

1. ✅ Copy SSH key from production server
2. ✅ Set up GitHub Secrets (Step 1)
3. ✅ Configure production server (Step 2) 
4. ✅ Push a test commit to develop branch
5. ✅ Watch GitHub Actions build (should succeed)
6. ✅ Verify images on Docker Hub
7. ✅ Merge to live (production branch)
8. ✅ Watch GitHub Actions deploy (should auto-deploy)
9. ✅ Verify app is running on production server
10. ✅ Celebrate! 🎉

---

## Local Development Tips

**Pull pre-built images from Docker Hub:**
```bash
# After pushing develop, wait 2-3 min for build to complete
# Then pull and test
docker pull your-username/ebill-backend:develop
docker pull your-username/ebill-frontend:develop

# Or just build locally (faster for testing)
docker-compose build
docker-compose up -d
```

**Check logs locally:**
```bash
docker-compose logs -f backend
docker-compose logs -f frontend  
docker-compose logs mongodb
```

**Rebuild and restart:**
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

---

**Last Updated:** March 26, 2026
**Version:** V7.15-11
**Status:** Ready for Production
