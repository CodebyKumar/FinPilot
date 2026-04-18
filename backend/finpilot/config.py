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

PROFILE_ENCRYPTION_SECRET: str = os.getenv("PROFILE_ENCRYPTION_SECRET", "finpilot-dev-secret")
DEADLINE_SCAN_INTERVAL_SECONDS: int = int(os.getenv("DEADLINE_SCAN_INTERVAL_SECONDS", "3600"))

# ── Email / Gmail SMTP ────────────────────────────────────────────────────────
SMTP_HOST: str = os.getenv("SMTP_HOST", "")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes"}
REMINDER_EMAIL_TO: str = os.getenv("REMINDER_EMAIL_TO", "")

# ── Report Export ──────────────────────────────────────────────────────────────
OVERALL_REPORT_OUTPUT_DIR: str = os.getenv("OVERALL_REPORT_OUTPUT_DIR", "data/generated/overall_reports")

# ── Seeder script ──────────────────────────────────────────────────────────────
API_BASE: str = os.getenv("API_BASE", "http://localhost:8000")
