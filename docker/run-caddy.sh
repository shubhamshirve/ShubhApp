#!/bin/sh
set -eu

# The root directory is where the script is run from or /app by default
ROOT_DIR="/app"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  . "$ROOT_DIR/.env"
  set +a
fi

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
