"""
Editor Phase Graph

Orchestrates: planner → clip_composer → assembler → render → music

Complete flow after layer-based architecture:
- Planner creates clip_tasks with rich creative notes
- Composer builds layer specs for each clip
- Assembler collects everything into VideoSpec
- Renderer produces video (without audio)
- Music phase generates aligned BGM based on clip times
- Final video is muxed with audio via FFmpeg
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
        return "assemble"


def should_render(state: EditorState) -> Literal["render", "end"]:
    """Check if we should proceed to rendering."""
    spec = state.get("video_spec")
    
    if spec and spec.get("clips"):
        return "render"
    return "end"


def should_generate_music(state: EditorState) -> Literal["music", "end"]:
    """Check if we should generate music after rendering."""
    render_path = state.get("render_path")
    render_error = state.get("render_error")
    
    # Only generate music if render succeeded
    if render_path and not render_error:
        return "music"
    return "end"


# ─────────────────────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────────────────────

def build_editor_graph(
    include_render: bool = True,
    include_music: bool = True,
):
    """
    Build the editor phase graph.
    
    Flow:
        planner → compose_clips → assemble [→ render] [→ music]
    
    Music runs AFTER render (not before), so you get:
    1. Video rendered without audio
    2. Music generated based on clip times
    3. Final muxing of video + audio
    
    Args:
        include_render: If True, includes the render step
        include_music: If True, includes music generation (requires render)
    """
    builder = StateGraph(EditorState)
    
    # ─────────────────────────────────────────────────────────
    # Nodes
    # ─────────────────────────────────────────────────────────
    builder.add_node("planner", edit_planner_node)
    builder.add_node("compose_clips", compose_all_clips_node)
    builder.add_node("assemble", edit_assembler_node)
    
    # Render node
    if include_render:
        try:
            from renderer.render_client import remotion_render_node
            builder.add_node("render", remotion_render_node)
        except ImportError:
            print("⚠️  Render client not available, skipping render node")
            include_render = False
            include_music = False  # Can't do music without render
    
    # Music generation node (runs AFTER render)
    if include_music and include_render:
        from .music_planner import music_planner_node
        from tools.music_generator import music_generator_node, mux_audio_video_node
        
        builder.add_node("music_plan", music_planner_node)
        builder.add_node("music_generate", music_generator_node)
        builder.add_node("mux_audio", mux_audio_video_node)
    
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
        
        # After render
        if include_music:
            builder.add_conditional_edges(
                "render",
                should_generate_music,
                {
                    "music": "music_plan",
                    "end": END,
                }
            )
            
            # Music flow: plan → generate → mux with video
            builder.add_edge("music_plan", "music_generate")
            builder.add_edge("music_generate", "mux_audio")
            builder.add_edge("mux_audio", END)
        else:
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
    include_music: bool = True,
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
    graph = build_editor_graph(
        include_render=include_render,
        include_music=include_music,
    )
    
    config = {"configurable": {"thread_id": f"editor-{video_project_id}"}}
    result = graph.invoke(initial_state, config=config)
    
    return result


def run_editor_test(
    test_state: EditorState = None,
    include_render: bool = False,
    include_music: bool = False,
) -> EditorState:
    """
    Run editor phase with test state, no database required.
    """
    from .loader import create_test_state
    
    print("\n" + "="*60)
    print("Editor Phase - TEST MODE")
    print("="*60)
    
    state = test_state or create_test_state()
    graph = build_editor_graph(
        include_render=include_render,
        include_music=include_music,
    )
    
    result = graph.invoke(state)
    return result


def run_editor_with_checkpointer(
    video_project_id: str,
    checkpointer=None,
    include_render: bool = True,
    include_music: bool = True,
) -> EditorState:
    """
    Run editor with custom checkpointer (for persistence).
    """
    from .loader import load_editor_state
    
    initial_state = load_editor_state(video_project_id)
    
    # Build graph
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
            include_music = False
    
    if include_music and include_render:
        from .music_planner import music_planner_node
        from tools.music_generator import music_generator_node, mux_audio_video_node
        builder.add_node("music_plan", music_planner_node)
        builder.add_node("music_generate", music_generator_node)
        builder.add_node("mux_audio", mux_audio_video_node)
    
    builder.add_edge(START, "planner")
    builder.add_conditional_edges("planner", route_after_planning, 
        {"compose_clips": "compose_clips", "assemble": "assemble"})
    builder.add_edge("compose_clips", "assemble")
    
    if include_render:
        builder.add_conditional_edges("assemble", should_render, {"render": "render", "end": END})
        if include_music:
            builder.add_conditional_edges("render", should_generate_music, {"music": "music_plan", "end": END})
            builder.add_edge("music_plan", "music_generate")
            builder.add_edge("music_generate", "mux_audio")
            builder.add_edge("mux_audio", END)
        else:
            builder.add_edge("render", END)
    else:
        builder.add_edge("assemble", END)
    
    # Compile with checkpointer
    graph = builder.compile(checkpointer=checkpointer or InMemorySaver())
    
    config = {"configurable": {"thread_id": f"editor-{video_project_id}"}}
    result = graph.invoke(initial_state, config=config)
    
    return result


# ─────────────────────────────────────────────────────────────
# Partial Execution Helpers
# ─────────────────────────────────────────────────────────────

def run_composing_only(video_project_id: str) -> EditorState:
    """Run only the clip composition phase (skip planning)."""
    from .loader import load_editor_state
    from tools.editor_tools import get_pending_clip_tasks
    
    print(f"\n{'='*60}")
    print(f"Compose Only - Project: {video_project_id}")
    print(f"{'='*60}")
    
    pending = get_pending_clip_tasks(video_project_id)
    if not pending:
        print("   ✓ No pending clip tasks to compose")
        return {}
    
    print(f"   Found {len(pending)} pending clip tasks")
    
    builder = StateGraph(EditorState)
    builder.add_node("compose_clips", compose_all_clips_node)
    builder.add_edge(START, "compose_clips")
    builder.add_edge("compose_clips", END)
    
    graph = builder.compile()
    initial_state = load_editor_state(video_project_id)
    result = graph.invoke(initial_state)
    
    return result


def run_assembly_only(video_project_id: str) -> EditorState:
    """Run only the assembly phase."""
    from .loader import load_editor_state
    
    print(f"\n{'='*60}")
    print(f"Assemble Only - Project: {video_project_id}")
    print(f"{'='*60}")
    
    builder = StateGraph(EditorState)
    builder.add_node("assemble", edit_assembler_node)
    builder.add_edge(START, "assemble")
    builder.add_edge("assemble", END)
    
    graph = builder.compile()
    initial_state = load_editor_state(video_project_id)
    result = graph.invoke(initial_state)
    
    return result


def run_music_only(video_project_id: str, video_path: str = None) -> EditorState:
    """
    Run only the music generation phase.
    
    Args:
        video_project_id: Project to generate music for
        video_path: Optional path to rendered video (for muxing)
    """
    from .loader import load_editor_state
    from .music_planner import music_planner_node
    from tools.music_generator import music_generator_node, mux_audio_video_node
    
    print(f"\n{'='*60}")
    print(f"Music Only - Project: {video_project_id}")
    print(f"{'='*60}")
    
    builder = StateGraph(EditorState)
    builder.add_node("music_plan", music_planner_node)
    builder.add_node("music_generate", music_generator_node)
    
    if video_path:
        builder.add_node("mux_audio", mux_audio_video_node)
        builder.add_edge("music_generate", "mux_audio")
        builder.add_edge("mux_audio", END)
    else:
        builder.add_edge("music_generate", END)
    
    builder.add_edge(START, "music_plan")
    builder.add_edge("music_plan", "music_generate")
    
    graph = builder.compile()
    
    initial_state = load_editor_state(video_project_id)
    if video_path:
        initial_state["render_path"] = video_path
    
    result = graph.invoke(initial_state)
    
    return result


# ─────────────────────────────────────────────────────────────
# Graph Visualization Helper
# ─────────────────────────────────────────────────────────────

def print_graph_structure():
    """Print the graph structure for debugging."""
    print("""
    Editor Phase Graph (with Post-Render Music)
    ═══════════════════════════════════════════════════════════
    
    START
       │
       ▼
    ┌─────────────────┐
    │     planner     │  Creates clip_tasks with creative notes
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  compose_clips  │  Builds layer specs for each clip
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │    assemble     │  Collects specs → VideoSpec JSON
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │     render      │  Remotion → video WITHOUT audio
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │   music_plan    │  Analyzes clip times → hit points
    │                 │  (0 LLM calls - pure Python)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ music_generate  │  ElevenLabs → aligned BGM
    │                 │  (0-1 LLM calls for refinement)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │   mux_audio     │  FFmpeg: video + audio → final.mp4
    └────────┬────────┘
             │
             ▼
           END
    """)


if __name__ == "__main__":
    print_graph_structure()
