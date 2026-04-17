"""
FinPilot AI – Main FastAPI Application Entry Point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from finpilot import config
from finpilot.db.mongo import init_db
from finpilot.api.routers import users, ingest, agents


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for FastAPI."""
    init_db()
    yield


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
app.include_router(users.router)
app.include_router(ingest.router)
app.include_router(agents.router)


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
