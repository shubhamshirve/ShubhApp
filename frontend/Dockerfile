# Build stage
FROM node:20-alpine as builder

WORKDIR /app

ARG REACT_APP_BACKEND_URL=
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

COPY package*.json ./

# Use npm ci for more reliable builds than npm install
RUN npm ci --legacy-peer-deps

COPY . .

RUN npm run build && npm prune --production

# Runtime stage with minimal footprint
FROM node:20-alpine

WORKDIR /app

# Install serve globally in runtime stage only if needed
RUN apk add --no-cache curl
RUN npm install -g serve

COPY --from=builder /app/build ./build

EXPOSE 3000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/index.html || exit 1

CMD ["serve", "-s", "build", "-l", "3000"]
