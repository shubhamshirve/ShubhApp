FROM node:20-slim

# Install Chromium and required system dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    curl \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Let Puppeteer know to skip its own Chromium download and use system one
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

# Copy package files and install dependencies (production only)
COPY package.json package-lock.json* ./
RUN npm ci --production

# Copy application code
COPY . .

# Create auth directory for session persistence
RUN mkdir -p .wwebjs_auth

EXPOSE 8002

# Health check - give extra time for Chromium to init on first start
HEALTHCHECK --interval=30s --timeout=15s --retries=5 --start-period=120s \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["node", "server.js"]
