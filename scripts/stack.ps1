# Handovers stack helper (Windows PowerShell). Optional: plain
# `docker compose ...` from the repository root does the same. Bash: scripts/stack.sh
#
# Usage: .\scripts\stack.ps1 <command>
#   up       Build and start everything (FalkorDB + backend + frontend)
#   dev      Stop the backend and frontend containers; FalkorDB keeps running (run apps on the host)
#   db       Start FalkorDB only
#   down     Stop and remove all containers (data is kept)
#   reset    Remove all containers AND the FalkorDB data volume (asks first)
#   logs     Follow logs of all running services
#   cli      Open redis-cli inside the FalkorDB container (authenticated)
#   status   Show container status
param([Parameter(Position = 0)][string]$Command = "")

function Invoke-Compose {
    # docker writes progress to stderr; in Windows PowerShell 5.1 that must not count as an error.
    $ErrorActionPreference = "Continue"
    docker compose @args
    if ($LASTEXITCODE -ne 0) { throw "docker compose failed (exit $LASTEXITCODE)" }
}

# Run from the repository root, and return the caller to their own folder afterwards.
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example"
    }

    switch ($Command) {
        "up" {
            Invoke-Compose up -d --build --wait
            Write-Host "App: http://localhost:5173  API: http://localhost:8000/docs  FalkorDB Browser: http://localhost:3000"
        }
        "dev" {
            Invoke-Compose up -d --wait falkordb
            Invoke-Compose stop backend frontend
            Write-Host "FalkorDB running. Start the backend and frontend on the host (see their READMEs)."
        }
        "db" { Invoke-Compose up -d --wait falkordb }
        "down" { Invoke-Compose down }
        "reset" {
            $answer = Read-Host "Delete ALL FalkorDB data in the handovers volume? [y/N]"
            if ($answer -match '^[Yy]$') { Invoke-Compose down -v } else { Write-Host "Cancelled." }
        }
        "logs" { Invoke-Compose logs -f }
        "cli" { Invoke-Compose exec falkordb redis-cli }
        "status" { Invoke-Compose ps -a }
        default {
            Get-Content $PSCommandPath | Select-Object -Skip 1 -First 12
            exit 1
        }
    }
} finally {
    Pop-Location
}
