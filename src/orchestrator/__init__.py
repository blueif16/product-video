"""
Orchestrator package.

Architecture:
    START → intake → analyze_and_plan → prepare_capture_queue 
          → capture_single ⟲ (loops sequentially)
          → aggregate → END

Each node is a separate module with its own context and tools.
Single simulator = sequential execution.
"""
from .graph import build_pipeline, run_pipeline
from .session import get_session, reset_session, end_session, PipelineSession

__all__ = [
    "build_pipeline", 
    "run_pipeline",
    "get_session",
    "reset_session", 
    "end_session",
    "PipelineSession",
]
