"""
FinPilot AI – Main FastAPI Application Entry Point.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from finpilot import config
from finpilot.db.mongo import init_db
from finpilot.tasks.deadline_worker import run_deadline_worker

from finpilot.api.routers import (
    profile,
    bookkeeping,
    report,
    overall_report,
    financial_report,
    deadline,
    assistant,
)

try:
    from voice_agent import app as voice_agent_app
except Exception:
    voice_agent_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for FastAPI."""
    init_db()
    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(run_deadline_worker(stop_event))
    app.state.deadline_worker_stop_event = stop_event
    app.state.deadline_worker_task = worker_task
    yield
    stop_event.set()
    try:
        await asyncio.wait_for(worker_task, timeout=5)
    except Exception:
        worker_task.cancel()


app = FastAPI(
    title="FinPilot AI Backend",
    description="Intelligent financial compliance and intelligence platform.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all modular routers
app.include_router(profile.router)
app.include_router(bookkeeping.router)
app.include_router(report.router)
app.include_router(overall_report.router)
app.include_router(financial_report.router)
app.include_router(deadline.router)
app.include_router(assistant.router)

# Mount voice-agent endpoints under a dedicated prefix
if voice_agent_app is not None:
    app.mount("/voice-agent", voice_agent_app)


@app.get("/health", tags=["System"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


def start():
    """CLI entry point for running the server (via `uv run serve`)."""
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
        log_level=config.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    start()
