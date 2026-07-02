# syntax=docker/dockerfile:1.4
# ─────────────────────────────────────────────────────────────────────────────
# Build stage — compile the React app with npm
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

ARG REACT_APP_BACKEND_URL=
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

# Copy manifests first — npm only re-downloads when these change
COPY package.json package-lock.json ./

# Mount the npm cache so repeated builds reuse already-downloaded packages
RUN --mount=type=cache,id=npm-cache,target=/root/.npm,sharing=locked \
    npm ci --cache /root/.npm --prefer-offline --legacy-peer-deps

COPY . .

RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Runtime stage — nginx:alpine (~5MB RAM vs node+serve ~50MB RAM)
# ─────────────────────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Copy built React app
COPY --from=builder /app/build /usr/share/nginx/html

# Custom nginx config: SPA routing, gzip, caching, security headers
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Remove default nginx config
RUN rm -f /etc/nginx/conf.d/default.conf.bak

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
