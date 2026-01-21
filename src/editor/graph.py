"""
Editor Phase Graph

Orchestrates: planner → clip_composer → assembler

Simplified flow after layer-based architecture:
- No separate text_composer (text is a layer within clips)
- Each clip is a self-contained "moment" with multiple layers
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from .state import EditorState
from .planner import edit_planner_node
from .clip_composer import compose_all_clips_node
from .assembler import edit_assembler_node


# ─────────────────────────────────────────────────────────────
# Routing
# ─────────────────────────────────────────────────────────────

def route_after_planning(state: EditorState) -> Literal["compose_clips", "assemble"]:
    """Route after planning based on what tasks were created."""
    clip_ids = state.get("clip_task_ids", [])
    
    if clip_ids:
        return "compose_clips"
    else:
        # No tasks? Go straight to assembly (edge case)
        return "assemble"


def should_render(state: EditorState) -> Literal["render", "end"]:
    """Check if we should proceed to rendering."""
    spec = state.get("video_spec")
    
    if spec and spec.get("clips"):
        return "render"
    return "end"


# ─────────────────────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────────────────────

def build_editor_graph(include_render: bool = True):
    """
    Build the editor phase graph.
    
    Flow:
        planner → compose_clips → assemble [→ render]
    
    Args:
        include_render: If True, includes the render step.
                       Set False for testing composition logic only.
    """
    builder = StateGraph(EditorState)
    
    # ─────────────────────────────────────────────────────────
    # Nodes
    # ─────────────────────────────────────────────────────────
    builder.add_node("planner", edit_planner_node)
    builder.add_node("compose_clips", compose_all_clips_node)
    builder.add_node("assemble", edit_assembler_node)
    
    if include_render:
        try:
            from renderer.render_client import remotion_render_node
            builder.add_node("render", remotion_render_node)
        except ImportError:
            print("⚠️  Render client not available, skipping render node")
            include_render = False
    
    # ─────────────────────────────────────────────────────────
    # Edges
    # ─────────────────────────────────────────────────────────
    builder.add_edge(START, "planner")
    
    # After planning, route based on what tasks exist
    builder.add_conditional_edges(
        "planner",
        route_after_planning,
        {
            "compose_clips": "compose_clips",
            "assemble": "assemble",
        }
    )
    
    # After clip composition, go to assembly
    builder.add_edge("compose_clips", "assemble")
    
    # After assembly
    if include_render:
        builder.add_conditional_edges(
            "assemble",
            should_render,
            {
                "render": "render",
                "end": END,
            }
        )
        builder.add_edge("render", END)
    else:
        builder.add_edge("assemble", END)
    
    return builder.compile()


# ─────────────────────────────────────────────────────────────
# Standalone Execution Helpers
# ─────────────────────────────────────────────────────────────

def run_editor_standalone(
    video_project_id: str,
    include_render: bool = True,
) -> EditorState:
    """
    Run editor phase standalone, loading state from database.
    
    Usage:
        result = run_editor_standalone("project-uuid-here")
        print(result["video_spec"])
    """
    from .loader import load_editor_state
    
    print(f"\n{'='*60}")
    print(f"Editor Phase - Project: {video_project_id}")
    print(f"{'='*60}")
    
    initial_state = load_editor_state(video_project_id)
    graph = build_editor_graph(include_render=include_render)
    
    config = {"configurable": {"thread_id": f"editor-{video_project_id}"}}
    result = graph.invoke(initial_state, config=config)
    
    return result


def run_editor_test(
    test_state: EditorState = None,
    include_render: bool = False,
) -> EditorState:
    """
    Run editor phase with test state, no database required.
    
    Note: This won't actually work without DB since tools write to DB.
    Use for testing the graph structure.
    """
    from .loader import create_test_state
    
    print("\n" + "="*60)
    print("Editor Phase - TEST MODE")
    print("="*60)
    
    state = test_state or create_test_state()
    graph = build_editor_graph(include_render=include_render)
    
    result = graph.invoke(state)
    return result


def run_editor_with_checkpointer(
    video_project_id: str,
    checkpointer=None,
    include_render: bool = True,
) -> EditorState:
    """
    Run editor with custom checkpointer (for persistence).
    """
    from .loader import load_editor_state
    
    initial_state = load_editor_state(video_project_id)
    
    # Build graph (not compiled yet)
    builder = StateGraph(EditorState)
    
    builder.add_node("planner", edit_planner_node)
    builder.add_node("compose_clips", compose_all_clips_node)
    builder.add_node("assemble", edit_assembler_node)
    
    if include_render:
        try:
            from renderer.render_client import remotion_render_node
            builder.add_node("render", remotion_render_node)
        except ImportError:
            include_render = False
    
    builder.add_edge(START, "planner")
    builder.add_conditional_edges("planner", route_after_planning, 
        {"compose_clips": "compose_clips", "assemble": "assemble"})
    builder.add_edge("compose_clips", "assemble")
    
    if include_render:
        builder.add_conditional_edges("assemble", should_render, {"render": "render", "end": END})
        builder.add_edge("render", END)
    else:
        builder.add_edge("assemble", END)
    
    # Compile with checkpointer
    graph = builder.compile(checkpointer=checkpointer or InMemorySaver())
    
    config = {"configurable": {"thread_id": f"editor-{video_project_id}"}}
    result = graph.invoke(initial_state, config=config)
    
    return result


# ─────────────────────────────────────────────────────────────
# Graph Visualization Helper
# ─────────────────────────────────────────────────────────────

def print_graph_structure():
    """Print the graph structure for debugging."""
    print("""
    Editor Phase Graph (Layer-Based)
    ═══════════════════════════════════════════
    
    START
       │
       ▼
    ┌─────────────────┐
    │     planner     │  Creates clip_tasks with rich creative notes
    │                 │  Each task is a "moment" (can have layers)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  compose_clips  │  Reads creative notes, builds layer specs
    │                 │  - Image layers (original assets)
    │                 │  - Generated layers (AI-enhanced)
    │                 │  - Text layers (typography)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │    assemble     │  Collects composed specs → VideoSpec
    │                 │  Deterministic assembly (no LLM)
    └────────┬────────┘
             │
             ▼ (optional)
    ┌─────────────────┐
    │     render      │  Remotion rendering
    └────────┬────────┘
             │
             ▼
           END
    """)


if __name__ == "__main__":
    print_graph_structure()
