"""
Centralized configuration for FinPilot backend.

All runtime values are read from environment variables (or a .env file).
No hardcoded secrets or environment-specific strings anywhere else in the codebase.
Copy .env.example → .env and fill in your values before running.
"""

import os
from dotenv import load_dotenv

# Load .env from the backend directory (or any parent that contains it)
load_dotenv()

# ── MongoDB ────────────────────────────────────────────────────────────────────
MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME: str = os.getenv("DB_NAME", "finpilot")

# ── API Server ─────────────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")

# ── OpenAI (optional – GST agent AI fallback) ─────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── Seeder script ──────────────────────────────────────────────────────────────
API_BASE: str = os.getenv("API_BASE", "http://localhost:8000")
