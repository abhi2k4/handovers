"""Handovers: write a working .env, then start everything with one command.

    python setup.py            create .env (asks a few questions), refusing to touch an existing one
    python setup.py --update   add keys a newer .env.example has and .env lacks; keeps your values
    python setup.py --force    replace .env, keeping a .env.bak copy
    python setup.py --print    show what would be written, write nothing
    python setup.py --yes      accept every default without asking (CI, scripts)

`.env.example` is the template. Everything is copied through untouched (comments, order) except:

- secrets, generated with `secrets`: FALKORDB_PASSWORD, APP_SECRET_KEY, KEYCLOAK_CLIENT_SECRET,
  KC_BOOTSTRAP_ADMIN_PASSWORD and DEMO_USER_PASSWORD (a placeholder that boots is worse than one
  that does not: it ships);
- ports: a port another program already uses moves to the next free one;
- values derived from those ports: APP_PUBLIC_URL, CORS_ORIGINS, KEYCLOAK_URL, KEYCLOAK_PUBLIC_URL;
- your answers: a Groq API key for the AI features (optional) and whether to run Keycloak sign-in.

Standard library only, so it runs on a fresh machine before anything is installed. Modelled on
kenz-intent's setup.py.
"""

from __future__ import annotations

import argparse
import getpass
import secrets
import shutil
import socket
import string
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / ".env.example"
ENV = ROOT / ".env"
BACKUP = ROOT / ".env.bak"

MIN_PYTHON = (3, 10)

# Generated fresh for every new .env (and for any of these --update adds).
GENERATED: dict[str, Callable[[], str]] = {
    "FALKORDB_PASSWORD": lambda: password(24),
    "APP_SECRET_KEY": lambda: secrets.token_urlsafe(48),
    "KEYCLOAK_CLIENT_SECRET": lambda: password(32),
    "KC_BOOTSTRAP_ADMIN_PASSWORD": lambda: password(20),
    "DEMO_USER_PASSWORD": lambda: password(12),
    "PLATFORM_ADMIN_PASSWORD": lambda: password(16),
}

# Host ports, probed in this order; a taken one moves to the next free number.
PORTS = ["FRONTEND_PORT", "BACKEND_PORT", "FALKORDB_PORT", "FALKORDB_BROWSER_PORT", "KEYCLOAK_PORT"]

# Needed to run the stack, and (optional) to work on the code outside Docker.
REQUIRED_TOOLS = [
    ("docker", ["docker", "--version"], "https://docs.docker.com/get-docker/"),
    (
        "docker compose",
        ["docker", "compose", "version"],
        "https://docs.docker.com/compose/install/",
    ),
    ("git", ["git", "--version"], "https://git-scm.com/downloads"),
]
DEV_TOOLS = [
    ("uv (backend on the host)", ["uv", "--version"], "https://docs.astral.sh/uv/"),
    ("node (frontend on the host)", ["node", "--version"], "https://nodejs.org/"),
]


# ---- output (plain ASCII: AGENTS.md section 4a) --------------------------------------------


def _colour(code: str) -> str:
    return code if sys.stdout.isatty() else ""


RESET, BOLD = _colour("\033[0m"), _colour("\033[1m")
GREEN, YELLOW, RED, CYAN = (_colour(f"\033[{c}m") for c in (32, 33, 31, 36))


def ok(msg: str) -> None:
    print(f"{GREEN}  ok{RESET}    {msg}")


def note(msg: str) -> None:
    print(f"{CYAN}  note{RESET}  {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}  warn{RESET}  {msg}")


def fail(msg: str) -> None:
    print(f"{RED}  error{RESET} {msg}", file=sys.stderr)


def header(msg: str) -> None:
    print(f"\n{BOLD}{msg}{RESET}")


# ---- values -------------------------------------------------------------------------------


def password(length: int) -> str:
    """Letters and digits only: safe in URLs, shells and Compose files without escaping."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def is_free(port: int) -> bool:
    """Binding is the honest test: it asks the question Docker will ask."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def free_port(preferred: int, taken: set[int]) -> int:
    port = preferred
    while port < 65536:
        if port not in taken and is_free(port):
            return port
        port += 1
    raise RuntimeError(f"No free port at or above {preferred}")


def read_values(lines: list[str]) -> dict[str, str]:
    values = {}
    for line in lines:
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def render(lines: list[str], values: dict[str, str]) -> list[str]:
    """The template with these values filled in; comments, blank lines and order kept."""
    out = []
    for line in lines:
        key = line.partition("=")[0].strip()
        if line and not line.startswith("#") and "=" in line and key in values:
            out.append(f"{key}={values[key]}")
        else:
            out.append(line)
    return out


# ---- questions ----------------------------------------------------------------------------


def ask_yes(question: str, default: bool, interactive: bool) -> bool:
    if not interactive:
        return default
    hint = "Y/n" if default else "y/N"
    answer = input(f"  ?     {question} [{hint}] ").strip().lower()
    return default if not answer else answer.startswith("y")


def ask_secret(question: str, interactive: bool) -> str:
    if not interactive:
        return ""
    return getpass.getpass(f"  ?     {question} (input hidden; Enter to skip): ").strip()


# ---- checks -------------------------------------------------------------------------------


def check_tools(tools: list[tuple[str, list[str], str]], required: bool) -> bool:
    good = True
    for name, command, url in tools:
        found = shutil.which(command[0]) is not None
        if found:
            try:
                found = subprocess.run(command, capture_output=True, timeout=20).returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                found = False
        if found:
            ok(name)
        elif required:
            warn(f"{name} not found: install it from {url}")
            good = False
        else:
            note(f"{name} not found (only needed to work on the code outside Docker): {url}")
    return good


# ---- modes --------------------------------------------------------------------------------


def build(template: dict[str, str], interactive: bool, keep: dict[str, str]) -> dict[str, str]:
    """Fresh values. `keep`: secrets from an existing .env, reused because data already depends on
    them (Keycloak keeps its client secret from its first start; saved connector tokens are
    encrypted with APP_SECRET_KEY)."""
    values = dict(template)
    for key, make in GENERATED.items():
        if key in values:
            values[key] = keep.get(key) or make()

    header("Ports")
    taken: set[int] = set()
    for key in PORTS:
        preferred = int(values[key])
        port = free_port(preferred, taken)
        taken.add(port)
        values[key] = str(port)
        if port != preferred:
            warn(f"{key}: {preferred} is in use, using {port}")
    if all(values[k] == template[k] for k in PORTS):
        ok("every default port is free")
    else:
        note(
            "if Handovers itself is already running, stop it (docker compose down) and run setup again"
        )

    header("AI features (optional)")
    note("Without a key the app works on templates. A free Groq key: https://console.groq.com/keys")
    key = ask_secret("GROQ_API_KEY", interactive)
    if key:
        values |= {"LLM_PROVIDER": "groq", "GROQ_API_KEY": key}
        ok("AI: Groq")
    else:
        values |= {"LLM_PROVIDER": "none", "GROQ_API_KEY": ""}
        ok("AI: off (templates); add GROQ_API_KEY to .env later and restart the backend")

    header("Sign-in")
    note("Keycloak adds email sign-in for the demo people, and Google and Microsoft later.")
    sign_in = ask_yes("Run Keycloak sign-in in Docker?", True, interactive)
    frontend = f"http://localhost:{values['FRONTEND_PORT']}"
    values |= {"APP_PUBLIC_URL": frontend, "CORS_ORIGINS": frontend}
    if sign_in:
        keycloak = f"http://localhost:{values['KEYCLOAK_PORT']}"
        values |= {
            "COMPOSE_PROFILES": "auth",
            "KEYCLOAK_URL": keycloak,
            "KEYCLOAK_PUBLIC_URL": keycloak,
        }
        ok("sign-in: on (Keycloak starts with the stack)")
    else:
        values |= {
            "COMPOSE_PROFILES": "",
            "KEYCLOAK_URL": "",
            "KEYCLOAK_PUBLIC_URL": "",
            "DEMO_USER_PASSWORD": "",
            "PLATFORM_ADMIN_PASSWORD": "",
        }
        ok("sign-in: off (the View-as guest switcher only)")
    return values


def update(lines: list[str], current: dict[str, str]) -> list[str] | None:
    """Append template keys .env lacks (generating secrets); None when nothing is missing."""
    missing = [k for k in read_values(lines) if k not in current]
    if not missing:
        ok(".env already has every key in .env.example")
        return None
    template = read_values(lines)
    added = []
    for key in missing:
        # Generate only what has no default: anything already running (Keycloak) started with the
        # template's development default, and a new random value would no longer match it.
        value = GENERATED[key]() if key in GENERATED and not template[key] else template[key]
        added.append(f"{key}={value}")
        ok(f"added {key}")
    return ["", "# ---- Added by setup.py --update ----", *added]


def next_steps(values: dict[str, str]) -> None:
    header("Next")
    app = values.get("APP_PUBLIC_URL", "http://localhost:5173")
    print("  1. docker compose up -d --build")
    print(f"  2. Open {app}  (first start takes a few minutes: images build, sample data loads)")
    if values.get("DEMO_USER_PASSWORD"):
        print(f"     Sign in: {app}/login -> Continue with email -> meera@northwind.example")
        print(f"     Demo password (DEMO_USER_PASSWORD in .env): {values['DEMO_USER_PASSWORD']}")
    if values.get("PLATFORM_ADMIN_PASSWORD"):
        email = values.get("PLATFORM_ADMIN_EMAIL", "admin@handovers.local")
        print(f"     Platform admin (integrations, sign-in): {email} / {values['PLATFORM_ADMIN_PASSWORD']}")
    if not values.get("SMTP_HOST"):
        print("     Alert emails land in Mailpit: http://localhost:8025")
    print("     Or: Explore the demo as a guest.")
    header("Working on the code (live reload)")
    port = values.get("BACKEND_PORT", "8000")
    print("  docker compose stop backend frontend")
    print(f"  cd app/backend  && uv sync && uv run uvicorn main:app --reload --port {port}")
    print("  cd app/frontend && npm install && npm run dev")
    print("  (PowerShell: the same commands; use cd app\\backend and cd app\\frontend)")
    print("  Back to all-Docker: docker compose up -d backend frontend")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a working .env for Handovers.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--update", action="store_true", help="add missing keys, keep your values")
    mode.add_argument("--force", action="store_true", help="replace .env, keeping .env.bak")
    mode.add_argument("--print", action="store_true", help="show the result, write nothing")
    parser.add_argument("--yes", action="store_true", help="accept every default without asking")
    args = parser.parse_args()
    interactive = not args.yes and sys.stdin.isatty()

    print(f"{BOLD}Handovers setup{RESET}")
    header("Machine")
    if sys.version_info < MIN_PYTHON:
        fail(
            f"Python {'.'.join(map(str, MIN_PYTHON))}+ is needed, this is {sys.version.split()[0]}"
        )
        return 1
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    tools_ok = check_tools(REQUIRED_TOOLS, required=True)
    check_tools(DEV_TOOLS, required=False)

    if not TEMPLATE.exists():
        fail(".env.example is missing: run this from a checkout of the repository")
        return 1
    lines = TEMPLATE.read_text(encoding="utf-8").splitlines()

    if args.update:
        header("Update")
        if not ENV.exists():
            fail(".env does not exist yet: run python setup.py first")
            return 1
        current = ENV.read_text(encoding="utf-8").splitlines()
        added = update(lines, read_values(current))
        if added:
            ENV.write_text("\n".join([*current, *added]) + "\n", encoding="utf-8", newline="\n")
            ok("written .env (your existing values unchanged)")
        return 0

    if ENV.exists() and not (args.force or args.print):
        header("Already set up")
        ok(".env exists, so nothing was changed")
        note("python setup.py --update   adds keys a newer .env.example has")
        note("python setup.py --force    starts over (keeps your old file as .env.bak)")
        next_steps(read_values(ENV.read_text(encoding="utf-8").splitlines()))
        return 0

    keep: dict[str, str] = {}
    if ENV.exists():
        # This machine already ran the stack: keep its secrets, and where .env has none, the
        # template default its services started with (same rule as --update).
        existing = read_values(ENV.read_text(encoding="utf-8").splitlines())
        defaults = read_values(lines)
        keep = {k: existing.get(k) or defaults.get(k, "") for k in GENERATED}
        keep = {k: v for k, v in keep.items() if v}
        if keep:
            note(f"keeping existing secrets: {', '.join(sorted(keep))}")
    values = build(read_values(lines), interactive, keep)
    rendered = "\n".join(render(lines, values)) + "\n"

    if args.print:
        header(".env (not written)")
        print(rendered)
        return 0

    if ENV.exists():
        shutil.copyfile(ENV, BACKUP)
        note("old .env kept as .env.bak")
    ENV.write_text(rendered, encoding="utf-8", newline="\n")
    header("Written")
    ok(".env (secrets generated; it is git-ignored, never commit it)")
    if not tools_ok:
        warn("install the missing tools above before starting the stack")
    next_steps(values)
    return 0


if __name__ == "__main__":
    sys.exit(main())
