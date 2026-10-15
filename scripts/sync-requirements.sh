#!/usr/bin/env bash
# Regenerate the pip requirement files from app/backend/uv.lock.
# Run after every dependency change (uv add / uv remove / uv lock). PowerShell: scripts/sync-requirements.ps1
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../app/backend"
uv lock
uv export --frozen --format requirements-txt --no-dev --no-hashes --no-annotate -o requirements.txt >/dev/null
uv export --frozen --format requirements-txt --all-groups --no-hashes --no-annotate -o requirements-dev.txt >/dev/null
echo "Updated app/backend/requirements.txt and requirements-dev.txt from uv.lock"
