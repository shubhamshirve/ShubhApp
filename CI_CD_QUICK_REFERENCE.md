# CI/CD Quick Start (TL;DR)

## Setup for 2 Environments (Local PC + Production Server)

### 30-Second Secret Setup

Go to: https://github.com/YOUR_USERNAME/ebill/settings/secrets/actions

Add **5 secrets ONLY:**
```
DOCKER_USERNAME  = your-docker-username
DOCKER_PAT       = your-docker-pat-token  
DEPLOY_USER      = ubuntu  (or root)
DEPLOY_SSH_KEY   = [your-prod-server-ssh-private-key]
PROD_SERVER_HOST = your-prod-server-ip
```

Done! ✨

### Setup Console on Production Server (5 min)

```bash
ssh user@prod-server-ip

# Generate SSH key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/github-deploy
cat ~/.ssh/github-deploy  # Copy content to DEPLOY_SSH_KEY secret

# Setup app directory
cd /app
git clone https://github.com/YOUR_USERNAME/ebill.git .

# Create .env
cat > .env << 'EOF'
DOMAIN=prod-domain.com
MONGO_ROOT_PASSWORD=your-password
JWT_SECRET=your-secret
# ... other vars ...
EOF
```

### No Setup Needed on Local PC!
Just use docker-compose normally:
```bash
docker-compose up -d
docker-compose logs -f backend
docker-compose down
```

---

## Your Workflow

```
Feature branch:
  1. git push origin develop
  2. GitHub builds images (automated)
  3. You test locally: docker-compose up -d
  4. Testing good? Continue...

Production deploy:
  1. git push origin main
  2. GitHub builds images (automated)
  3. GitHub auto-deploys to production (automated)
  4. Your app is live! ✨
```

---

## What Happens on Each Push

### Push to develop (branch):
```
You: git push origin develop
    ↓
GitHub Actions: Build backend + frontend images
    ↓
Docker Hub: Store images (tag: develop, abc1234)
    ↓
You: docker-compose up -d (manual testing on local PC)
    ↓
Done! Ready to merge to main when tested
```

### Push to live (branch):
```
You: git push origin live
    ↓
GitHub Actions: Build backend + frontend images
    ↓
Docker Hub: Store images (tag: latest, live, abc1234)
    ↓
GitHub Actions: SSH to production server
    ↓
Production: Pull images, restart containers
    ↓
Done! App is live in production! 🎉
```

---

## Monitoring

1. Go to: https://github.com/YOUR_USERNAME/ebill/actions
2. See build status (blue=running, green=success, red=failed)
3. Click workflow run to see detailed logs
4. Look for: "Build & Push to Docker Hub" and "Deploy" steps

---

## Local Testing Commands

```bash
# Build from local Dockerfile
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop everything
docker-compose down

# Pull pre-built images from Docker Hub
docker pull your-username/ebill-backend:develop
docker pull your-username/ebill-frontend:develop
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails | Check Actions logs → Dockerfile syntax |
| Deploy fails | SSH key wrong? Server IP wrong? Check logs |
| Images not on Docker Hub | Verify DOCKER_USERNAME and DOCKER_PAT |
| Container won't start | SSH to production, check `.env` file |
| Local containers won't start | Install Docker, check disk space |

---

## Manual Production Deploy (if needed)

```bash
ssh user@prod-server
cd /app
git pull origin main
docker pull your-username/ebill-backend:latest
docker pull your-username/ebill-frontend:latest
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
docker-compose ps
```

---

## Branches & What They Do

| Branch | Action | Auto-Deploy? |
|--------|--------|--------------|
| `feature/*` | Build only | ❌ No |
| `develop` | Build only | ❌ No |
| `live` | Build + Deploy | ✅ Yes (to PROD_SERVER_HOST) |

---

## Full Setup Guide
See: [GITHUB_ACTIONS_SETUP.md](./GITHUB_ACTIONS_SETUP.md)

For more details on environment variables, Docker Hub management, and advanced topics.

---

## Support
- Detailed guide: [GITHUB_ACTIONS_SETUP.md](./GITHUB_ACTIONS_SETUP.md)
- GitHub Actions logs: https://github.com/YOUR_USERNAME/ebill/actions
- Production server: `ssh user@prod-server-ip && docker-compose ps`
