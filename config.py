"""
config.py
---------
Central configuration for SHADOW.

Loads secrets from a .env file (never hardcode secrets), and defines
shared constants/paths used across the whole application.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is optional at this stage; env vars can still be
    # provided by the real environment. We warn once via LOG in main.py.
    pass


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "shadow.db"
LOGS_DIR = BASE_DIR / "logs"
SCREENSHOTS_DIR = BASE_DIR / "logs" / "screenshots"

for _dir in (DATABASE_DIR, LOGS_DIR, SCREENSHOTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Secrets / API keys (never hardcode these — set them in .env)
# ---------------------------------------------------------------------------
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")  # anthropic | openai | none
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")

# ---------------------------------------------------------------------------
# Behavior toggles
# ---------------------------------------------------------------------------
VOICE_ENABLED = os.getenv("VOICE_ENABLED", "false").lower() == "true"
WAKE_WORD = os.getenv("WAKE_WORD", "hey shadow")
ASSISTANT_NAME = "SHADOW"

# Safety: risk levels that require confirmation before executing.
# LOW = auto-execute, MEDIUM = show plan then execute, HIGH = require explicit yes/no.
CONFIRM_MEDIUM_RISK = os.getenv("CONFIRM_MEDIUM_RISK", "false").lower() == "true"

# Max steps a single plan may contain (guards against runaway plans).
MAX_PLAN_STEPS = int(os.getenv("MAX_PLAN_STEPS", "25"))

# Max automatic retries per step before SHADOW gives up and reports failure.
MAX_STEP_RETRIES = int(os.getenv("MAX_STEP_RETRIES", "1"))
