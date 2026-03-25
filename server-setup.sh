#!/bin/bash
# VPS Server Deployment Setup Script
# Run this on your production server: bash server-setup.sh

set -e

echo "════════════════════════════════════════"
echo "E-Bill Platform - VPS Setup Script"
echo "════════════════════════════════════════"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run this script as root: sudo bash server-setup.sh"
  exit 1
fi

APP_DIR="/app/ebill"
APP_USER="ebill"

echo "📦 Step 1: Update system packages..."
apt-get update
apt-get upgrade -y

echo "🐳 Step 2: Install Docker (if not already installed)..."
if ! command -v docker &> /dev/null; then
  apt-get install -y curl gnupg2 software-properties-common
  curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable docker
  systemctl start docker
  echo "✅ Docker installed"
else
  echo "✅ Docker already installed"
fi

echo "👤 Step 3: Create app user..."
if ! id "$APP_USER" &>/dev/null; then
  useradd -m -s /bin/bash -G docker "$APP_USER"
  echo "✅ User '$APP_USER' created and added to docker group"
else
  echo "✅ User '$APP_USER' already exists"
fi

echo "📁 Step 4: Create application directory..."
mkdir -p "$APP_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 755 "$APP_DIR"
echo "✅ Directory created: $APP_DIR"

echo "🔑 Step 5: Setting up for git deployment..."
echo "To enable automatic deployments:"
echo ""
echo "1. Generate an SSH key pair on your local machine:"
echo "   ssh-keygen -t ed25519 -f ~/.ssh/ebill_deploy -C 'ebill-deploy'"
echo ""
echo "2. Add public key to server authorized_keys:"
echo "   cat ~/.ssh/ebill_deploy.pub >> ~/.ssh/authorized_keys"
echo "   chmod 600 ~/.ssh/authorized_keys"
echo ""
echo "3. Add the PRIVATE key to GitHub Secrets as 'DEPLOY_KEY'"
echo "4. Add these to GitHub Secrets:"
echo "   - DOCKER_USERNAME: your Docker Hub username"
echo "   - DOCKER_PASSWORD: your Docker Hub password"
echo "   - PROD_SERVER_IP: 45.196.196.21"
echo "   - SERVER_USER: $APP_USER"
echo "   - REACT_APP_BACKEND_URL: https://app.e-bill.in"

echo ""
echo "🔒 Step 6: Secure SSH configuration..."
# Backup original sshd_config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Verify SSH config
if sshd -t; then
  echo "✅ SSH configuration is valid"
else
  echo "⚠️  SSH configuration has issues, restoring backup"
  cp /etc/ssh/sshd_config.backup /etc/ssh/sshd_config
fi

echo ""
echo "📝 Step 7: Create .env files for server..."

# Create production env file template
cat > "$APP_DIR/.env.production" <<'EOF'
# Production Environment - app.e-bill.in
DOMAIN=app.e-bill.in
SERVER_IP=45.196.196.21
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=CHANGE_ME_STRONG_PASSWORD
JWT_SECRET=CHANGE_ME_STRONG_SECRET_32_CHARS
BACKUP_PASSWORD=CHANGE_ME_STRONG_PASSWORD
REACT_APP_BACKEND_URL=https://app.e-bill.in
MONGO_URI=mongodb://admin:CHANGE_ME@mongodb:27017/saas_db?authSource=admin
MONGO_URL=mongodb://admin:CHANGE_ME@localhost:27017/saas_db?authSource=admin
DB_NAME=saas_db
CORS_ORIGINS=https://app.e-bill.in,http://app.e-bill.in
MONGO_BIND_ADDRESS=0.0.0.0
DOCKER_USERNAME=CHANGE_ME_YOUR_DOCKERHUB_USERNAME
EOF

chown "$APP_USER:$APP_USER" "$APP_DIR/.env.production"
chmod 600 "$APP_DIR/.env.production"

echo "⚠️  IMPORTANT: Update .env.production with strong passwords!"
echo "   Location: $APP_DIR/.env.production"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps on server:"
echo "1. Update $APP_DIR/.env.production with strong credentials"
echo "2. Clone the repository:"
echo "   cd $APP_DIR"
echo "   git clone -b live <your-repo-url> ."
echo "3. First deployment (manual):"
echo "   sudo -u $APP_USER docker-compose -f docker-compose.prod.yml --env-file .env.production up -d"
echo ""
echo "Monitor logs:"
echo "   docker-compose -f docker-compose.prod.yml logs -f"
