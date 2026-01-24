"""
Unified Pipeline Graph

Single graph that supports:
1. Full pipeline: capture → editor → render → music
2. Editor-only: load assets from DB → editor → render → music
3. Upload mode: create project from uploads → editor → render → music

Entry point is determined by pipeline_mode in state.
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from .state import UnifiedPipelineState, create_initial_state

# Import capture nodes
from orchestrator.intake import intake_node
from orchestrator.analyzer import analyze_and_plan_node
from orchestrator.capturer import capture_single_task_node
from orchestrator.aggregate import aggregate_node
from orchestrator.graph import (
    prepare_capture_queue,
    route_after_capture,
    move_to_next_task,
    route_next_capture,
    increment_attempts,
)

# Import editor nodes
from editor.planners import edit_planner_node
from editor.composers import compose_all_clips_node
from editor.core.assembler import edit_assembler_node

# Import render/music nodes (conditional)
try:
    from renderer.render_client import remotion_render_node
    HAS_RENDERER = True
except ImportError:
    HAS_RENDERER = False

try:
    from editor.core.music_planner import music_planner_node
    from tools.music_generator import music_generator_node, mux_audio_video_node
    HAS_MUSIC = True
except ImportError:
    HAS_MUSIC = False


# ─────────────────────────────────────────────────────────────
# Entry Routing
# ─────────────────────────────────────────────────────────────

def route_entry(state: UnifiedPipelineState) -> str:
    """
    Route based on pipeline_mode.
    
    - full: Start with intake (capture phase)
    - editor_only: Skip to load_assets (editor phase)
    - upload: Skip to load_assets (same as editor_only, assets already in DB)
    """
    mode = state.get("pipeline_mode", "full")
    
    if mode in ("editor_only", "upload"):
        return "load_assets"
    return "intake"


# ─────────────────────────────────────────────────────────────
# Bridge Nodes (Capture → Editor)
# ─────────────────────────────────────────────────────────────

def load_assets_node(state: UnifiedPipelineState) -> dict:
    """
    Load assets from DB for editor phase.
    
    Called when:
    - pipeline_mode is "editor_only" or "upload"
    - After capture phase completes (aggregated)
    """
    from editor.core.loader import load_editor_state
    
    project_id = state["video_project_id"]
    
    if not project_id:
        raise ValueError("video_project_id required for editor phase")
    
    print(f"\n📂 Loading assets for project: {project_id[:8]}...")
    
    # Load from DB
    editor_state = load_editor_state(project_id)
    
    return {
        "assets": editor_state.get("assets", []),
        "analysis_summary": editor_state.get("analysis_summary", state.get("user_input", "")),
        "user_input": editor_state.get("user_input", state.get("user_input", "")),
        "current_stage": "planning",
        "stage_message": f"Loaded {len(editor_state.get('assets', []))} assets",
        "status": "editing",
    }


def bridge_to_editor(state: UnifiedPipelineState) -> dict:
    """
    Transition from capture to editor phase.
    Updates status and prepares for editor.
    """
    return {
        "current_stage": "loading_assets",
        "stage_message": "Capture complete, preparing editor...",
        "status": "aggregated",
    }


# ─────────────────────────────────────────────────────────────
# Render/Music Routing
# ─────────────────────────────────────────────────────────────

def should_render(state: UnifiedPipelineState) -> Literal["render", "end"]:
    """Check if we should proceed to rendering."""
    spec = state.get("video_spec")
    if spec and spec.get("clips") and HAS_RENDERER:
        return "render"
    return "end"


def should_generate_music(state: UnifiedPipelineState) -> Literal["music", "end"]:
    """Check if we should generate music."""
    render_path = state.get("render_path")
    if render_path and not state.get("render_error") and HAS_MUSIC:
        return "music"
    return "end"


# ─────────────────────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────────────────────

def build_unified_graph(
    include_render: bool = True,
    include_music: bool = True,
) -> StateGraph:
    """
    Build the unified pipeline graph.
    
    Topology:
    
        START
          │
          ├─[full]──────→ intake → analyze → capture_queue → [capture_loop] → aggregate
          │                                                                        │
          │                                                                        ▼
          └─[editor_only/upload]──→ load_assets ──────────────────────────────────→│
                                                                                   │
                                                                                   ▼
                                                                              planner
                                                                                   │
                                                                                   ▼
                                                                            compose_clips
                                                                                   │
                                                                                   ▼
                                                                              assemble
                                                                                   │
                                                                    ┌──────────────┼──────────────┐
                                                                    │              │              │
                                                                    ▼              │              │
                                                                 render            │              │
                                                                    │              │              │
                                                                    ▼              │              │
                                                               music_plan          │              │
                                                                    │              │              │
                                                                    ▼              │              │
                                                             music_generate        │              │
                                                                    │              │              │
                                                                    ▼              │              │
                                                                mux_audio          │              │
                                                                    │              │              │
                                                                    └──────────────┴──────────────┘
                                                                                   │
                                                                                   ▼
                                                                                  END
    """
    builder = StateGraph(UnifiedPipelineState)
    
    # ─────────────────────────────────────────────────────────
    # Capture Phase Nodes
    # ─────────────────────────────────────────────────────────
    builder.add_node("intake", intake_node)
    builder.add_node("analyze_and_plan", analyze_and_plan_node)
    builder.add_node("prepare_capture_queue", prepare_capture_queue)
    builder.add_node("increment_attempts", increment_attempts)
    builder.add_node("capture_single", capture_single_task_node)
    builder.add_node("move_to_next", move_to_next_task)
    builder.add_node("aggregate", aggregate_node)
    builder.add_node("bridge_to_editor", bridge_to_editor)
    
    # ─────────────────────────────────────────────────────────
    # Editor Phase Nodes
    # ─────────────────────────────────────────────────────────
    builder.add_node("load_assets", load_assets_node)
    builder.add_node("planner", edit_planner_node)
    builder.add_node("compose_clips", compose_all_clips_node)
    builder.add_node("assemble", edit_assembler_node)
    
    # ─────────────────────────────────────────────────────────
    # Render Phase Nodes
    # ─────────────────────────────────────────────────────────
    if include_render and HAS_RENDERER:
        builder.add_node("render", remotion_render_node)
    
    # ─────────────────────────────────────────────────────────
    # Music Phase Nodes
    # ─────────────────────────────────────────────────────────
    if include_music and HAS_MUSIC:
        builder.add_node("music_plan", music_planner_node)
        builder.add_node("music_generate", music_generator_node)
        builder.add_node("mux_audio", mux_audio_video_node)
    
    # ─────────────────────────────────────────────────────────
    # Entry Routing
    # ─────────────────────────────────────────────────────────
    builder.add_conditional_edges(
        START,
        route_entry,
        {
            "intake": "intake",
            "load_assets": "load_assets",
        }
    )
    
    # ─────────────────────────────────────────────────────────
    # Capture Phase Edges
    # ─────────────────────────────────────────────────────────
    builder.add_edge("analyze_and_plan", "prepare_capture_queue")
    
    builder.add_conditional_edges(
        "prepare_capture_queue",
        route_next_capture,
        {"capture_single": "increment_attempts", "aggregate": "aggregate"}
    )
    
    builder.add_edge("increment_attempts", "capture_single")
    
    builder.add_conditional_edges(
        "capture_single",
        route_after_capture,
        {
            "capture_single": "increment_attempts",
            "move_to_next": "move_to_next",
            "aggregate": "aggregate",
        }
    )
    
    builder.add_conditional_edges(
        "move_to_next",
        route_next_capture,
        {"capture_single": "increment_attempts", "aggregate": "aggregate"}
    )
    
    # Capture → Editor bridge
    builder.add_edge("aggregate", "bridge_to_editor")
    builder.add_edge("bridge_to_editor", "load_assets")
    
    # ─────────────────────────────────────────────────────────
    # Editor Phase Edges
    # ─────────────────────────────────────────────────────────
    builder.add_edge("load_assets", "planner")
    builder.add_edge("planner", "compose_clips")
    builder.add_edge("compose_clips", "assemble")
    
    # ─────────────────────────────────────────────────────────
    # Render & Music Edges
    # ─────────────────────────────────────────────────────────
    if include_render and HAS_RENDERER:
        builder.add_conditional_edges(
            "assemble",
            should_render,
            {"render": "render", "end": END}
        )
        
        if include_music and HAS_MUSIC:
            builder.add_conditional_edges(
                "render",
                should_generate_music,
                {"music": "music_plan", "end": END}
            )
            builder.add_edge("music_plan", "music_generate")
            builder.add_edge("music_generate", "mux_audio")
            builder.add_edge("mux_audio", END)
        else:
            builder.add_edge("render", END)
    else:
        builder.add_edge("assemble", END)
    
    return builder


def compile_unified_graph(
    include_render: bool = True,
    include_music: bool = True,
    checkpointer=None,
):
    """Compile the unified graph with optional checkpointer."""
    builder = build_unified_graph(
        include_render=include_render,
        include_music=include_music,
    )
    return builder.compile(checkpointer=checkpointer or InMemorySaver())


# ─────────────────────────────────────────────────────────────
# Run Functions
# ─────────────────────────────────────────────────────────────

def run_unified_pipeline(
    user_input: str,
    mode: Literal["full", "editor_only", "upload"] = "full",
    video_project_id: str = None,
    include_render: bool = True,
    include_music: bool = True,
) -> dict:
    """
    Run the unified pipeline.
    
    Args:
        user_input: User's description
        mode: Pipeline mode
        video_project_id: Required for editor_only/upload modes
        include_render: Whether to render video
        include_music: Whether to generate music
    
    Returns:
        Final pipeline state
    """
    if mode in ("editor_only", "upload") and not video_project_id:
        raise ValueError(f"video_project_id required for mode={mode}")
    
    graph = compile_unified_graph(
        include_render=include_render,
        include_music=include_music,
    )
    
    initial_state = create_initial_state(
        user_input=user_input,
        mode=mode,
        video_project_id=video_project_id,
    )
    
    config = {"configurable": {"thread_id": f"pipeline-{video_project_id or 'new'}"}}
    
    result = graph.invoke(initial_state, config=config)
    
    return result


# ─────────────────────────────────────────────────────────────
# Visualization Helper
# ─────────────────────────────────────────────────────────────

def print_graph_structure():
    """Print the graph structure for debugging."""
    print("""
    Unified Pipeline Graph
    ═══════════════════════════════════════════════════════════
    
    START
       │
       ├─[mode=full]────────────→ intake
       │                            │
       │                            ▼
       │                       analyze_and_plan
       │                            │
       │                            ▼
       │                    prepare_capture_queue
       │                            │
       │                            ▼
       │                     [capture loop]
       │                            │
       │                            ▼
       │                        aggregate
       │                            │
       │                            ▼
       │                    bridge_to_editor
       │                            │
       └─[mode=editor_only/upload]──┼──→ load_assets
                                    │
                                    ▼
                                 planner
                                    │
                                    ▼
                              compose_clips
                                    │
                                    ▼
                                assemble
                                    │
                         ┌──────────┼──────────┐
                         ▼          │          │
                      render        │          │
                         │          │          │
                         ▼          │          │
                    music_plan      │          │
                         │          │          │
                         ▼          │          │
                  music_generate    │          │
                         │          │          │
                         ▼          │          │
                     mux_audio      │          │
                         │          │          │
                         └──────────┴──────────┘
                                    │
                                    ▼
                                   END
    """)


if __name__ == "__main__":
    print_graph_structure()
