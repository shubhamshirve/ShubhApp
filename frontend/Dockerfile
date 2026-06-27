# syntax=docker/dockerfile:1.4
# ─────────────────────────────────────────────────────────────────────────────
# Build stage — compile the React app
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

ARG REACT_APP_BACKEND_URL=
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

# Copy manifests first for maximum cache reuse
COPY package.json yarn.lock ./

# Mount the Yarn cache so repeated builds reuse already-downloaded packages
RUN --mount=type=cache,target=/root/.yarn,sharing=locked \
    YARN_CACHE_FOLDER=/root/.yarn yarn install --frozen-lockfile

COPY . .

RUN yarn build

# ─────────────────────────────────────────────────────────────────────────────
# Runtime stage — serve the static build
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache curl && \
    yarn global add serve

COPY --from=builder /app/build ./build

EXPOSE 3000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/index.html || exit 1

CMD ["serve", "-s", "build", "-l", "3000"]
