FROM node:20-slim

# Install Chromium and dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Set Puppeteer to use system Chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

# Copy package files and install
COPY package.json package-lock.json* ./
RUN npm ci --production

# Copy application code
COPY . .

# Create auth directory for session persistence
RUN mkdir -p .wwebjs_auth

EXPOSE 8002

CMD ["node", "server.js"]
