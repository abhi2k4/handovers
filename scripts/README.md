# scripts/

Optional helpers. Every script has a bash version (`.sh`, for macOS / Linux / Git Bash) and a
PowerShell version (`.ps1`, for Windows). Plain `docker compose` from the repository root does the
same job.

## stack: Docker Compose shortcuts

| Command | Does |
|---|---|
| `up` | Build and start everything (FalkorDB + backend + frontend) |
| `dev` | Keep FalkorDB running and stop the backend/frontend containers, so you can run both on the host |
| `db` | Start FalkorDB only |
| `down` | Stop and remove containers (data kept) |
| `reset` | Remove containers **and** the FalkorDB data volume (asks first) |
| `logs` | Follow logs |
| `cli` | `redis-cli` inside FalkorDB (already authenticated) |
| `status` | Container status |

**bash**
```bash
scripts/stack.sh dev
```
**PowerShell**
```powershell
.\scripts\stack.ps1 dev
```

## sync-requirements: keep pip files in sync with uv

Regenerates `app/backend/requirements.txt` and `requirements-dev.txt` from `uv.lock`. Run it after
every `uv add` / `uv remove`.

| bash | PowerShell |
|---|---|
| `scripts/sync-requirements.sh` | `.\scripts\sync-requirements.ps1` |

## Platform-specific (documented exceptions)

| Script | Runs on | Purpose |
|---|---|---|
| `falkordb-local.sh` | macOS/Linux only (optional) | FalkorDB on the host without Docker (bundled 4.x server). Everyone else, and Windows: `docker compose up -d falkordb` |
| `deploy-gce.sh` | bash with `gcloud` (macOS/Linux, or Git Bash/WSL on Windows) | Deploys to Compute Engine; see [deployment/](../deployment/README.md) |

Seeding, migrations and the benchmark run through Python and work on every OS (see
[app/backend](../app/backend/README.md)).
