"""
Voice Agent FastAPI App Wrapper
This file exposes the voice agent FastAPI app from finpilot.services.voice_agent
to be mounted at /voice-agent in the main backend app.
"""

from finpilot.services.voice_agent import app

__all__ = ["app"]
