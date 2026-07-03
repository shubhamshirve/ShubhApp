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
# Runtime stage — serve the static build
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine

RUN apk add --no-cache curl && \
    npm install -g serve

COPY --from=builder /app/build ./build

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/index.html || exit 1

CMD ["serve", "-s", "build", "-l", "3000"]
