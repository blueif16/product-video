"""
AG-UI Integration Layer

Provides AG-UI protocol compatibility for StreamLine pipeline.

Usage:
    # Start server
    python -m uvicorn src.ag_ui.server:app --reload --port 8000
    
    # Or from project root
    cd /Users/tk/Desktop/productvideo
    python -m uvicorn ag_ui.server:app --reload --port 8000
"""

from .adapter import run_pipeline_stream, SSE_CONTENT_TYPE
from .event_translator import EventTranslator, extract_ui_state, make_json_safe
from .server import app

__all__ = [
    "run_pipeline_stream",
    "SSE_CONTENT_TYPE",
    "EventTranslator",
    "extract_ui_state",
    "make_json_safe",
    "app",
]
