"""
Orchestrator package.

Architecture:
    START → intake → analyze_and_plan → [capture_tasks] → aggregate → END

Each node is a separate module with its own context and tools.
"""
from .graph import build_pipeline, run_pipeline

__all__ = ["build_pipeline", "run_pipeline"]
