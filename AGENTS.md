# AGENTS.md

Rules for everyone working in this repository: humans and AI coding assistants alike.
Read this file fully before making any change.

## 1. Orientation

1. Start at [README.md](README.md) for what Handovers is.
2. Every folder has a `README.md` that explains its purpose, layout and commands. **Read the folder's
   README before working in it**, and keep it accurate.
   - [app/](app/README.md) → [app/backend/](app/backend/README.md), [app/frontend/](app/frontend/README.md)
   - [graph/](graph/README.md) · [docs/](docs/README.md) · [scripts/](scripts/README.md) ·
     [deployment/](deployment/README.md) · [assets/](assets/README.md)
3. Design decisions live in [docs/](docs/README.md). The graph model in
   [docs/graph-model.md](docs/graph-model.md) is the source of truth for labels, relationships
   and properties.

## 2. Hackathon compliance (hard rules)

- Event window: **2026-10-15 00:01 IST → 2026-10-18 23:59 IST**. Submissions close at the end of it.
- FalkorDB must stay the primary database and do central work. Never move core logic to another
  store, and never reduce the graph to a visualisation.
- Every team member must be able to explain the graph model, the queries and the architecture.
  Keep queries readable and documented.
- AI assistance must be disclosed in the README's "AI assistance disclosure" section. Keep it
  current.

## 3. Root markdown policy

Exactly **two** markdown files live at the repository root: `README.md` and `AGENTS.md`.
Everything else goes in a folder (`docs/` for design documents, a folder `README.md` for folder
documentation). Do not add root-level markdown files.

## 3a. Media assets

All media lives in [`assets/`](assets/README.md): logos in `assets/logos/`, backgrounds in
`assets/backgrounds/`, plus screenshots, exported diagrams and video thumbnails in clearly named
subfolders. Do not scatter images across feature folders. Reference them from `assets/`, or copy
them at build time. Follow the naming and size rules in `assets/README.md`, and never overwrite
`assets/logos/master-logo.png`.

README screenshots (`assets/screenshots/01-…` to `17-…`, numbered in demo order) are 1920×1080
captures of the seeded sample company in the light theme. Retake them whenever the screens they
show change, so the README never shows an older UI.

## 4. Git and commits

- Commit with your own configured git identity. Do not override or impersonate another author.
- **No** `Co-Authored-By` trailers, no AI attribution lines, no session links or tool URLs in
  commit messages or PR descriptions.
- Conventional Commits: `type(scope): summary` (imperative, ≤ 72 chars). The body explains *what*
  and *why*. One logical change per commit.
- Do not commit secrets, `.env`, generated data dumps or `node_modules`.
- Do not force-push `main`.

## 4a. Platform-agnostic by default (Windows, macOS, Linux)

The team develops on Windows and macOS. Nothing may work on one and break on the other.

- **Docker is the universal fallback.** If something needs a Unix-only tool (e.g. a bundled
  server, a native binary), the documented default must be the Docker path that works everywhere
  (`docker compose up -d falkordb`). The Unix-only route can exist only as an optional extra,
  labelled "macOS/Linux only" in its README and script header.
- **Platform-specific dependencies get environment markers**, e.g.
  `"pkg>=1.0; sys_platform != 'win32'"`, so `uv sync` and `pip install` never fail on another OS.
- **Every helper script ships as a pair:** `name.sh` (bash) and `name.ps1` (PowerShell), unless
  it is deployment-only and runs on Linux (say so in its header). Exception: the root `setup.py`
  is one Python file using only the standard library, so it runs the same everywhere.
- **`.env.example` is the template `setup.py` fills in.** Add every new setting there (with a
  comment and a safe default); mark values setup must generate in `GENERATED` in `setup.py`.
- **Scripts must not leave the caller in a different directory** (PowerShell: `Push-Location` /
  `Pop-Location`).
- **Line endings are LF everywhere** (enforced by `.gitattributes`). `.sh` files must be committed
  executable: `git update-index --chmod=+x <file>` (Windows git does not record it on its own).
- **No OS assumptions in code:** use `pathlib` / `path` APIs, not hard-coded `/` or `\`;
  console output in plain ASCII; UI shortcut labels per platform (⌘ on macOS, Ctrl elsewhere).
- **CI is the referee:** the `cross-platform` job sets up and tests the project on Windows, macOS
  and Linux on every push and PR. Do not merge if it fails, and do not "fix" one OS by breaking
  another.

## 5. Engineering standards

- Keep the backend flat and simple: `main.py`, `core/` (config, logging, FalkorDB client, security,
  Keycloak), `api/` (routers), `services/`, `ingestion/`, `connectors/` (one package per data
  platform) and `identity/` (one package per sign-in provider). No deeper nesting. Pure logic (scoring, policies) stays free of I/O so it is
  unit-testable.
- Run the backend with `uv run uvicorn main:app --reload`, not `fastapi dev` (the FastAPI CLI prints
  emoji banners; console output stays plain ASCII).
- Credentials (connector tokens, sign-in client secrets) are entered in the app, where they are
  stored encrypted or in Keycloak, or set in your local `.env`. Never in code, docs, tests or commits.
- Cypher lives in `graph/queries/*.cypher`, is parameterised, and is never built with string
  formatting from user input. Agent-facing reads use `GRAPH.RO_QUERY`.
- Tenant and agent identity come from server-side context, never from LLM tool arguments.
- Knowledge is never overwritten or deleted. Use `SUPERSEDES` / retraction (see graph model).
- Times are integer epoch milliseconds; open intervals use `253402300799000`.
- **Python dependencies must work with both uv and pip.** Change them only with `uv add` /
  `uv remove` in `app/backend`, then run `scripts/sync-requirements.sh` (or `.ps1`) to regenerate
  `requirements.txt` and `requirements-dev.txt`. Commit `pyproject.toml`, `uv.lock` and both
  requirement files in the same commit. Never edit the requirement files by hand. CI checks that
  they are in sync.
- **Every setup or run command is documented for both bash and PowerShell.**
- Typed code: mypy (backend), `tsc --noEmit` (frontend). Lint/format: ruff (backend), oxlint (frontend).
- Tests accompany behaviour changes. Query changes need a query test against the seeded graph.
- No metric is written in any doc or README unless it comes from a committed benchmark run.
- When code diverges from a design doc, update the doc in the same commit.
