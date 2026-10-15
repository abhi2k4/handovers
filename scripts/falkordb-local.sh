#!/usr/bin/env bash
# Run FalkorDB on the host without Docker, using the server binary bundled in the
# `falkordblite` dev dependency. Listens on FALKORDB_PORT (default 6379) with
# FALKORDB_PASSWORD from .env. Data persists in ./data/falkordb-local.
#
# Note: falkordblite bundles an older FalkorDB module (4.x). The Docker stack and the
# live deployment run falkordb/falkordb:6.0.1; CI runs the query tests against 6.0.1.
#
# macOS/Linux only (optional). On Windows, or anywhere, use Docker: docker compose up -d falkordb
# Usage: scripts/falkordb-local.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PORT="${FALKORDB_PORT:-6379}"
PASSWORD="${FALKORDB_PASSWORD:-handovers-dev}"
DATA_DIR="$ROOT/data/falkordb-local"
mkdir -p "$DATA_DIR"

BIN_DIR="$(cd app/backend && uv run --quiet python -c 'import os, redislite; print(os.path.join(os.path.dirname(redislite.__file__), "bin"))')"

exec "$BIN_DIR/redis-server" \
  --port "$PORT" \
  --bind 127.0.0.1 \
  --requirepass "$PASSWORD" \
  --dir "$DATA_DIR" \
  --appendonly yes \
  --loadmodule "$BIN_DIR/falkordb.so" TIMEOUT_DEFAULT 15000 TIMEOUT_MAX 60000
