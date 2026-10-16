"""Test defaults: pinned clock, no LLM (deterministic templates), never the dev tenant."""

import os

os.environ["DEMO_NOW"] = "2026-10-12T10:00:00+05:30"
os.environ["LLM_PROVIDER"] = "none"
os.environ["ALLOW_RESET"] = "false"
os.environ["JOBS_ENABLED"] = "false"  # tests run jobs explicitly (services.jobs.run_due)

from core.config import get_settings

get_settings.cache_clear()
