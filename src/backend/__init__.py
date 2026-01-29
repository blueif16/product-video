"""
AG-UI Integration Layer

Provides AG-UI protocol compatibility for StreamLine pipeline.

Usage:
    # Start server
    python -m uvicorn src.backend.server:app --reload --port 8000
"""

from src.backend.adapter import run_pipeline_stream, SSE_CONTENT_TYPE
from src.backend.event_translator import EventTranslator, extract_ui_state, make_json_safe
from src.backend.server import app

__all__ = [
    "run_pipeline_stream",
    "SSE_CONTENT_TYPE",
    "EventTranslator",
    "extract_ui_state",
    "make_json_safe",
    "app",
]
