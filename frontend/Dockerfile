# syntax=docker/dockerfile:1.4
# ─────────────────────────────────────────────────────────────────────────────
# Build stage — compile the React app with pnpm
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

# Enable Corepack so pnpm is available without a separate install step
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

WORKDIR /app

ARG REACT_APP_BACKEND_URL=
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

# Copy manifests first — pnpm only re-downloads packages when these change
COPY package.json pnpm-lock.yaml ./

# Mount the pnpm content-addressable store for fast, cached installs
RUN --mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store,sharing=locked \
    pnpm install --frozen-lockfile

COPY . .

RUN pnpm build

# ─────────────────────────────────────────────────────────────────────────────
# Runtime stage — serve the static build
# pnpm is only needed to BUILD; the runtime just needs `serve` (installed via npm)
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine

RUN apk add --no-cache curl && \
    npm install -g serve --prefer-offline

COPY --from=builder /app/build ./build

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/index.html || exit 1

CMD ["serve", "-s", "build", "-l", "3000"]
