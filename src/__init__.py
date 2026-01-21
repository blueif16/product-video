"""
Product Video Pipeline

AI-powered end-to-end product video generation.

Usage:
    # Interactive mode
    python -m src.main
    
    # Analysis only
    python -m src.main --analyze-only
    
    # Programmatic
    from src.main import run_from_string
    result = run_from_string("My app FocusFlow is... ~/Code/FocusFlow.xcodeproj")
"""
from .main import main, run_from_string
from .orchestrator import build_pipeline, run_pipeline_interactive

__all__ = ["main", "run_from_string", "build_pipeline", "run_pipeline_interactive"]
