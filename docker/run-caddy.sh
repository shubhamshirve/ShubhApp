#!/bin/sh
set -eu

if [ -f /workspace/.env ]; then
  set -a
  . /workspace/.env
  set +a
fi

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
