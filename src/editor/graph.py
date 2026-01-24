"""
Editor Phase Graph V2

FIXES:
1. Send-based fan-out for parallel clip composition
2. Style guide flows from planner to all composers
3. Clean convergence to assembler

Architecture:
                    
    planner (generates style_guide)
       ├─→ compose_clip (clip 1) ──┐
       ├─→ compose_clip (clip 2) ──┼─→ assemble
       ├─→ compose_clip (clip 3) ──┤
       └─→ compose_clip (clip 4) ──┘
       
All composers run in PARALLEL with shared style_guide.
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.memory import InMemorySaver

from .core.state import EditorState
from .planners import edit_planner_node
from .composers import compose_single_clip_node, compose_all_clips_node
from .core.assembler import edit_assembler_node


# ─────────────────────────────────────────────────────────────
# Routing with Send (Fan-Out)
# ─────────────────────────────────────────────────────────────

def route_to_composers(state: EditorState):
    """
    Fan out to multiple composer nodes in parallel.
    
    Returns a list of Send objects, one per clip.
    Each composer gets:
    - clip_id: The specific clip to compose
    - video_project_id: For DB access
    - style_guide: Shared foundation for consistency
    """
    clip_ids = state.get("clip_task_ids", [])
    video_project_id = state["video_project_id"]
    style_guide = state.get("style_guide", {})
    
    if not clip_ids:
        # No clips to compose, go straight to assembly
        return END
    
    print(f"\n🎨 Composing {len(clip_ids)} clips...")
    
    # Create a Send for each clip
    return [
        Send(
            "compose_clip",
            {
                "clip_id": clip_id,
                "video_project_id": video_project_id,
                "style_guide": style_guide,
            }
        )
        for clip_id in clip_ids
    ]


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
    
    if render_path and not render_error:
        return "music"
    return "end"


# ─────────────────────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────────────────────

def build_editor_graph(
    use_parallel_composition: bool = False,  # Default to sequential for stability
    include_render: bool = True,
    include_music: bool = True,
):
    """
    Build the editor phase graph with V2 planner and composer.
    
    Flow:
        planner → compose_clips → assemble [→ render] [→ music]
    
    Args:
        use_parallel_composition: Use Send-based fan-out (experimental)
        include_render: Include render step
        include_music: Include music generation (requires render)
    """
    builder = StateGraph(EditorState)
    
    # ─────────────────────────────────────────────────────────
    # Nodes
    # ─────────────────────────────────────────────────────────
    builder.add_node("planner", edit_planner_node)
    
    if use_parallel_composition:
        # Single clip composer for parallel execution
        builder.add_node("compose_clip", compose_single_clip_node)
    else:
        # Sequential composition (stable)
        builder.add_node("compose_clips", compose_all_clips_node)
    
    builder.add_node("assemble", edit_assembler_node)
    
    # Render
    if include_render:
        try:
            from renderer.render_client import remotion_render_node
            builder.add_node("render", remotion_render_node)
        except ImportError:
            print("⚠️  Render client not available, skipping render node")
            include_render = False
            include_music = False
    
    # Music generation node (runs AFTER render)
    if include_music and include_render:
        from .core.music_planner import music_planner_node
        from tools.music_generator import music_generator_node, mux_audio_video_node
        
        builder.add_node("music_plan", music_planner_node)
        builder.add_node("music_generate", music_generator_node)
        builder.add_node("mux_audio", mux_audio_video_node)
    
    # ─────────────────────────────────────────────────────────
    # Edges
    # ─────────────────────────────────────────────────────────
    builder.add_edge(START, "planner")
    
    if use_parallel_composition:
        # Fan-out to multiple composers
        builder.add_conditional_edges(
            "planner",
            route_to_composers,  # Returns list of Send or END
        )
        # All composers converge to assembler
        builder.add_edge("compose_clip", "assemble")
    else:
        # Sequential composition
        builder.add_edge("planner", "compose_clips")
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
    use_parallel: bool = False,
) -> EditorState:
    """
    Run editor phase standalone, loading state from database.
    
    Usage:
        result = run_editor_standalone("project-uuid-here")
        print(result["video_spec"])
    """
    from .core.loader import load_editor_state
    
    print(f"\n{'='*60}")
    print(f"Editor Phase V2 - Project: {video_project_id}")
    print(f"{'='*60}")
    
    initial_state = load_editor_state(video_project_id)
    graph = build_editor_graph(
        use_parallel_composition=use_parallel,
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
    from .core.loader import create_test_state
    
    print("\n" + "="*60)
    print("Editor Phase V2 - TEST MODE")
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
    from .core.loader import load_editor_state
    
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
        from .core.music_planner import music_planner_node
        from tools.music_generator import music_generator_node, mux_audio_video_node
        builder.add_node("music_plan", music_planner_node)
        builder.add_node("music_generate", music_generator_node)
        builder.add_node("mux_audio", mux_audio_video_node)
    
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "compose_clips")
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
    from .core.loader import load_editor_state
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
    from .core.loader import load_editor_state
    
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
    from .core.loader import load_editor_state
    from .core.music_planner import music_planner_node
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
    Editor Phase Graph V2
    ═══════════════════════════════════════════════════════════
    
    START
       │
       ▼
    ┌─────────────────┐
    │     planner     │  V2: Sequential timeline + cognitive load durations
    │                 │  - Screenshots: 2-3s (not 0.8s!)
    │                 │  - Text: 0.4-1.2s based on word count
    │                 │  - NO overlaps, NO duplicates
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  compose_clips  │  V2: Style guide enforced consistency
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
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ music_generate  │  ElevenLabs → aligned BGM
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
