# Regenerate the pip requirement files from app/backend/uv.lock.
# Run after every dependency change (uv add / uv remove / uv lock). Bash: scripts/sync-requirements.sh
$ErrorActionPreference = "Continue"
Push-Location (Join-Path (Split-Path -Parent $PSScriptRoot) "app/backend")
try {
    uv lock
    if ($LASTEXITCODE -ne 0) { throw "uv lock failed" }
    uv export --frozen --format requirements-txt --no-dev --no-hashes --no-annotate -o requirements.txt | Out-Null
    uv export --frozen --format requirements-txt --all-groups --no-hashes --no-annotate -o requirements-dev.txt | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "uv export failed" }
    Write-Host "Updated app/backend/requirements.txt and requirements-dev.txt from uv.lock"
} finally {
    Pop-Location
}
