#!/usr/bin/env bash
# Handovers stack helper (macOS / Linux / Git Bash on Windows). Optional: plain
# `docker compose ...` from the repository root does the same. PowerShell: scripts/stack.ps1
#
# Usage: scripts/stack.sh <command>
#   up       Build and start everything (FalkorDB + backend + frontend)
#   dev      Stop the backend and frontend containers; FalkorDB keeps running (run apps on the host)
#   db       Start FalkorDB only
#   down     Stop and remove all containers (data is kept)
#   reset    Remove all containers AND the FalkorDB data volume (asks first)
#   logs     Follow logs of all running services
#   cli      Open redis-cli inside the FalkorDB container (authenticated)
#   status   Show container status
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

case "${1:-}" in
  up)
    docker compose up -d --build --wait
    echo "App: http://localhost:5173  API: http://localhost:8000/docs  FalkorDB Browser: http://localhost:3000"
    ;;
  dev)
    docker compose up -d --wait falkordb
    docker compose stop backend frontend
    echo "FalkorDB running. Start the backend and frontend on the host (see their READMEs)."
    ;;
  db)     docker compose up -d --wait falkordb ;;
  down)   docker compose down ;;
  reset)
    read -r -p "Delete ALL FalkorDB data in the handovers volume? [y/N] " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then docker compose down -v; else echo "Cancelled."; fi
    ;;
  logs)   docker compose logs -f ;;
  cli)    docker compose exec falkordb redis-cli ;;
  status) docker compose ps -a ;;
  *)
    sed -n '2,15p' "$0"
    exit 1
    ;;
esac
