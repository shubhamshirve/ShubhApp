# CI/CD Quick Start (TL;DR)

## 30-Second Setup

### 1. Add GitHub Secrets (5 min)
Go to: https://github.com/YOUR_USERNAME/ebill/settings/secrets/actions

Add these secrets:
```
DOCKER_USERNAME = your-docker-username
DOCKER_PAT = your-docker-pat-token
DEPLOY_USER = ubuntu  (or your ssh user)
DEPLOY_SSH_KEY = [contents of ~/.ssh/github-deploy]
DEV_SERVER_HOST = dev-server-ip
PROD_SERVER_HOST = prod-server-ip
```

### 2. Setup Server (10 min)
SSH to each server and run:
```bash
cd /app
git clone https://github.com/YOUR_USERNAME/ebill.git .
cat > .env << 'EOF'
DOMAIN=your-domain.com
MONGO_ROOT_PASSWORD=your-mongo-password
JWT_SECRET=your-jwt-secret
# ... other vars ...
EOF
```

### 3. Done! 
Now just push code:
```bash
git push origin develop  # Auto-deploys to dev!
git push origin main     # Auto-deploys to production!
```

---

## What Happens on Push

```
You: git push origin develop
    ↓
GitHub Actions: Build Docker images
    ↓
Docker Hub: Store images with tags (develop, abc1234, etc)
    ↓
GitHub Actions: SSH to dev server
    ↓
Dev Server: Pull images, restart containers
    ↓
Done! Your code is live ✨
```

---

## Monitoring

1. Go to: https://github.com/YOUR_USERNAME/ebill/actions
2. See build/deploy status
3. Click on run to see detailed logs
4. ✅ Green = Success, ❌ Red = Failed

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails | Check Actions logs → Docker permissions/syntax |
| Deploy fails | Check SSH key, server IP, Docker installed |
| Images not on Docker Hub | Verify DOCKER_USERNAME and DOCKER_PAT |
| Container won't start | SSH to server, check `.env` file |

---

## Manual Deploy (if needed)
```bash
ssh user@prod-server
cd /app
git pull origin main
docker pull your-username/ebill-backend:latest
docker pull your-username/ebill-frontend:latest
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
docker-compose logs backend
```

---

## Rate Limits: Not a Problem
- Docker Hub: 100 pulls per 6 hours ✅ (we use ~2 per push)
- GitHub: 3000 free minutes/month ✅ (we use ~5 per build)
- This setup is designed to stay well under limits

**No rate limiting in this implementation!**

---

## Branches & Environments

| Branch | →  | Environment | Server | Auto-Deploy? |
|--------|----|----|--------|--------------|
| `develop` | → | Dev | `DEV_SERVER_HOST` | ✅ Yes |
| `staging` | → | Staging | `STAGING_SERVER_HOST` | ✅ Yes |
| `main` | → | Production | `PROD_SERVER_HOST` | ✅ Yes |

---

## Full Setup Guide
See: [GITHUB_ACTIONS_SETUP.md](./GITHUB_ACTIONS_SETUP.md)

---

## Support
For detailed troubleshooting, see the full setup guide above.
For quick help, check GitHub Actions logs: https://github.com/YOUR_USERNAME/ebill/actions
