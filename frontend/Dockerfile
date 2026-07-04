# syntax=docker/dockerfile:1.4
# ─────────────────────────────────────────────────────────────────────────────
# Multi-stage build — React app compiled then served via nginx:alpine
# nginx is ~5x smaller than node+serve and supports gzip, caching headers.
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

ARG REACT_APP_BACKEND_URL=
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

# Copy manifests first — layer cache busts only when deps change
COPY package.json package-lock.json ./

# Mount the npm cache so repeated builds reuse already-downloaded packages
RUN --mount=type=cache,id=npm-cache,target=/root/.npm,sharing=locked \
    npm ci --cache /root/.npm --prefer-offline --legacy-peer-deps

COPY . .

RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Runtime stage — lightweight nginx:alpine (~25 MB vs ~180 MB node:alpine)
# ─────────────────────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled React build
COPY --from=builder /app/build /usr/share/nginx/html

# Custom nginx config (SPA routing + gzip + caching headers)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/index.html || exit 1

CMD ["nginx", "-g", "daemon off;"]
