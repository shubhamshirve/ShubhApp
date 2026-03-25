# Quick Reference: Docker Commands & Environment Setup

## Daily Development

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f backend       # Follow backend logs
docker-compose logs -f frontend      # Follow frontend logs
docker-compose logs mongodb --tail 50  # Last 50 lines

# Stop everything
docker-compose down

# Clean restart (remove volumes)
docker-compose down -v
docker-compose up -d

# Rebuild after code changes
docker-compose build backend
docker-compose restart backend
```

## Environment Setup

### Development (.env)
```bash
DOMAIN=localhost
SERVER_IP=
MONGO_ROOT_PASSWORD=dev-password
JWT_SECRET=dev-secret-key-32-chars
BACKUP_PASSWORD=dev-backup
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
REACT_APP_BACKEND_URL=http://localhost:8000
```

### Production (.env)
```bash
DOMAIN=yourdomain.com
SERVER_IP=YOUR.PUBLIC.IP
MONGO_ROOT_PASSWORD=<strong-random-password>
JWT_SECRET=<strong-32-char-random-secret>
BACKUP_PASSWORD=<strong-random-password>
CORS_ORIGINS=https://yourdomain.com
REACT_APP_BACKEND_URL=https://api.yourdomain.com
```

## Testing

```bash
# API Health Check
curl http://localhost:8000/api/health

# Frontend Check
curl http://localhost:3000

# MongoDB Connection (from backend container)
docker-compose exec backend python
>>> from database import db
>>> await db.command('ping')  # Should return {'ok': 1.0}
```

## Database Operations

```bash
# Backup MongoDB
docker-compose exec mongodb mongodump --archive > backup.archive

# Restore MongoDB
docker-compose exec -T mongodb mongorestore --archive < backup.archive

# Connect to MongoDB shell
docker-compose exec mongodb mongosh -u admin -p <password>
```

## Container Management

```bash
# Status
docker-compose ps

# Port forwarding (if needed)
docker-compose port backend 8000       # Shows 127.0.0.1:8000
docker-compose port frontend 3000      # Shows 127.0.0.1:3000

# Stats
docker stats                            # CPU/Memory usage

# Inspect service
docker-compose logs backend --since 10m # Last 10 minutes
docker inspect ebill_backend            # Detailed info
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend won't start | Check MongoDB is healthy: `docker-compose logs mongodb` |
| Auth errors | Verify MONGO_ROOT_PASSWORD in docker-compose.yml matches .env |
| Frontend blank page | Check REACT_APP_BACKEND_URL is correct |
| Port already in use | `docker-compose down` then restart |
| Permissions denied | Use `sudo docker-compose` on Linux |

## Production Deployment

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Monitor logs
docker-compose -f docker-compose.prod.yml logs -f

# Update backend only
docker-compose -f docker-compose.prod.yml build backend
docker-compose -f docker-compose.prod.yml up -d
```

## Key Files

- `.env` - Environment variables (DO NOT COMMIT)
- `.env.example` - Template (commit to repo)
- `docker-compose.yml` - Development configuration
- `docker-compose.prod.yml` - Production configuration
- `backend/Dockerfile` - Backend image build
- `frontend/Dockerfile` - Frontend image build
- `docker/init-env.sh` - Initialize environment on startup
- `Caddyfile` - Reverse proxy configuration

## Environment Variables

**Core (Always Required)**
- `DOMAIN` - Your domain or localhost
- `MONGO_ROOT_PASSWORD` - Database password
- `JWT_SECRET` - Token signing key (32+ chars)
- `BACKUP_PASSWORD` - Backup encryption password

**Networking**
- `CORS_ORIGINS` - Allowed frontend URLs (comma-separated)
- `REACT_APP_BACKEND_URL` - Frontend's backend URL

**Optional (Configure in Admin UI)**
- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` - Payment gateway
- `RESEND_API_KEY`, `RESEND_FROM_EMAIL` - Email service
- `WHATSAPP_*` - WhatsApp messaging

## Docker Compose Files

**docker-compose.yml** (Development)
- Includes all services (init-env, mongodb, backend, frontend, caddy)
- Builds locally with development dependencies
- Ports exposed for local testing
- Lower resource limits

**docker-compose.prod.yml** (Production)
- Optimized resource allocation
- Production logging configuration
- No local development tools
- Health checks configured
- Restart policies set to `always`

---

**Last Updated:** 2026-03-25
**Status:** ✅ All containers tested and working
