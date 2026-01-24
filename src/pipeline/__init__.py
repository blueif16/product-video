"""
Unified Pipeline Package

Provides a single LangGraph that supports:
- Full pipeline: capture → editor → render → music
- Editor-only: load assets → editor → render → music  
- Upload mode: from uploaded files → editor → render → music
"""

from .unified_graph import (
    compile_unified_graph,
    run_unified_pipeline,
    build_unified_graph,
    print_graph_structure,
)

from .state import (
    UnifiedPipelineState,
    create_initial_state,
)

# Re-export the original run_full_pipeline for backwards compatibility
try:
    from pipeline import run_full_pipeline
except ImportError:
    # If importing from within the package
    pass

__all__ = [
    # Unified graph
    "compile_unified_graph",
    "run_unified_pipeline", 
    "build_unified_graph",
    "print_graph_structure",
    
    # State
    "UnifiedPipelineState",
    "create_initial_state",
]
