"""
Full Pipeline - Capture → Editor → Render

Combines the capture phase (orchestrator) and editor phase into
a single end-to-end pipeline.

The phases are connected via database:
- Capture phase writes to video_projects + capture_tasks
- Editor phase reads from those tables
- This allows phases to run independently or together
"""
from typing import Annotated, Optional, Literal
from typing_extensions import TypedDict
import operator

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver


# ─────────────────────────────────────────────────────────────
# Combined State
# ─────────────────────────────────────────────────────────────

class FullPipelineState(TypedDict):
    """Combined state for the full pipeline."""
    
    # ─────────────────────────────────────────────────────────
    # Capture Phase Fields
    # ─────────────────────────────────────────────────────────
    messages: list
    user_input: str
    project_path: Optional[str]
    app_bundle_id: Optional[str]
    video_project_id: Optional[str]
    intake_complete: bool
    pending_task_ids: Optional[list[str]]
    current_task_index: Optional[int]
    completed_task_ids: Optional[list[str]]
    capture_status: Optional[str]
    
    # ─────────────────────────────────────────────────────────
    # Editor Phase Fields (populated after capture)
    # ─────────────────────────────────────────────────────────
    assets: list[dict]
    analysis_summary: Optional[str]
    edit_plan_summary: Optional[str]
    clip_task_ids: list[str]
    text_task_ids: list[str]
    clip_specs: Annotated[list[dict], operator.add]
    text_specs: Annotated[list[dict], operator.add]
    pending_clip_task_ids: Optional[list[str]]
    pending_text_task_ids: Optional[list[str]]
    current_clip_index: Optional[int]
    current_text_index: Optional[int]
    video_spec: Optional[dict]
    video_spec_id: Optional[str]
    render_status: Optional[str]
    render_path: Optional[str]
    render_error: Optional[str]


# ─────────────────────────────────────────────────────────────
# Bridge Node
# ─────────────────────────────────────────────────────────────

def capture_to_editor_bridge(state: FullPipelineState) -> dict:
    """
    Bridge node: Load captured assets from DB into state for editor.
    
    This is where the database contract is fulfilled.
    The capture phase writes to video_projects + capture_tasks,
    and this node reads those tables to populate editor state.
    """
    from editor.loader import load_editor_state
    
    video_project_id = state.get("video_project_id")
    
    if not video_project_id:
        raise ValueError("No video_project_id - capture phase must complete first")
    
    print("\n" + "="*60)
    print("Bridge: Capture → Editor")
    print("="*60)
    
    # Load from DB (same as standalone editor would)
    editor_state = load_editor_state(video_project_id)
    
    print(f"   Loaded {len(editor_state['assets'])} assets")
    print(f"   User input: {editor_state['user_input'][:50]}...")
    
    # Merge into full pipeline state
    return {
        "assets": editor_state["assets"],
        "analysis_summary": editor_state["analysis_summary"],
        "clip_task_ids": [],
        "text_task_ids": [],
        "clip_specs": [],
        "text_specs": [],
        "pending_clip_task_ids": None,
        "pending_text_task_ids": None,
        "current_clip_index": None,
        "current_text_index": None,
        "video_spec": None,
        "video_spec_id": None,
        "render_status": None,
        "render_path": None,
        "render_error": None,
    }


def should_continue_to_editor(state: FullPipelineState) -> Literal["bridge", "end_capture_only"]:
    """Check if we should continue to editor phase."""
    # Check if capture was successful
    video_project_id = state.get("video_project_id")
    completed = state.get("completed_task_ids", [])
    
    if video_project_id and completed:
        return "bridge"
    else:
        print("\n⚠️  No successful captures, stopping at capture phase")
        return "end_capture_only"


# ─────────────────────────────────────────────────────────────
# Graph Builder (Subgraph Composition)
# ─────────────────────────────────────────────────────────────

def build_full_pipeline(include_render: bool = True):
    """
    Build the complete capture → edit → render pipeline.
    
    Uses subgraph composition: each phase is a compiled graph
    used as a node in the parent graph.
    
    Args:
        include_render: Whether to include the Remotion render step
    """
    from orchestrator.graph import build_pipeline as build_capture_graph
    from editor.graph import build_editor_graph
    
    # Build subgraphs
    # Note: We need to extract just the graph logic, not run functions
    # For now, we'll build a flat graph
    
    builder = StateGraph(FullPipelineState)
    
    # ─────────────────────────────────────────────────────────
    # Import capture phase nodes
    # ─────────────────────────────────────────────────────────
    from orchestrator.intake import intake_node
    from orchestrator.analyzer import analyze_and_plan_node
    from orchestrator.capturer import capture_single_task_node
    from orchestrator.aggregate import aggregate_node
    from orchestrator.graph import prepare_capture_queue, route_next_capture
    
    # ─────────────────────────────────────────────────────────
    # Import editor phase nodes
    # ─────────────────────────────────────────────────────────
    from editor.planner import edit_planner_node
    from editor.clip_composer import compose_all_clips_node
    from editor.text_composer import compose_all_texts_node
    from editor.assembler import edit_assembler_node
    from editor.graph import route_after_planning, route_after_clips, should_render
    
    # ─────────────────────────────────────────────────────────
    # Add Capture Phase Nodes
    # ─────────────────────────────────────────────────────────
    builder.add_node("intake", intake_node)
    builder.add_node("analyze_and_plan", analyze_and_plan_node)
    builder.add_node("prepare_capture_queue", prepare_capture_queue)
    builder.add_node("capture_single", capture_single_task_node)
    builder.add_node("aggregate", aggregate_node)
    
    # ─────────────────────────────────────────────────────────
    # Add Bridge Node
    # ─────────────────────────────────────────────────────────
    builder.add_node("bridge", capture_to_editor_bridge)
    
    # ─────────────────────────────────────────────────────────
    # Add Editor Phase Nodes
    # ─────────────────────────────────────────────────────────
    builder.add_node("planner", edit_planner_node)
    builder.add_node("compose_clips", compose_all_clips_node)
    builder.add_node("compose_texts", compose_all_texts_node)
    builder.add_node("assemble", edit_assembler_node)
    
    if include_render:
        from renderer.render_client import remotion_render_node
        builder.add_node("render", remotion_render_node)
    
    # ─────────────────────────────────────────────────────────
    # Capture Phase Edges
    # ─────────────────────────────────────────────────────────
    builder.add_edge(START, "intake")
    builder.add_edge("analyze_and_plan", "prepare_capture_queue")
    
    builder.add_conditional_edges(
        "prepare_capture_queue",
        route_next_capture,
        ["capture_single", "aggregate"]
    )
    builder.add_conditional_edges(
        "capture_single",
        route_next_capture,
        ["capture_single", "aggregate"]
    )
    
    # After aggregate, check if we should continue to editor
    builder.add_conditional_edges(
        "aggregate",
        should_continue_to_editor,
        {
            "bridge": "bridge",
            "end_capture_only": END,
        }
    )
    
    # ─────────────────────────────────────────────────────────
    # Editor Phase Edges
    # ─────────────────────────────────────────────────────────
    builder.add_edge("bridge", "planner")
    
    builder.add_conditional_edges(
        "planner",
        route_after_planning,
        {
            "compose_clips": "compose_clips",
            "compose_texts": "compose_texts",
            "assemble": "assemble",
        }
    )
    
    builder.add_conditional_edges(
        "compose_clips",
        route_after_clips,
        {
            "compose_texts": "compose_texts",
            "assemble": "assemble",
        }
    )
    
    builder.add_edge("compose_texts", "assemble")
    
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
    
    return builder.compile(checkpointer=InMemorySaver())


# ─────────────────────────────────────────────────────────────
# Run Functions
# ─────────────────────────────────────────────────────────────

def run_full_pipeline(user_input: str, include_render: bool = True) -> dict:
    """
    Run the complete pipeline from user input to rendered video.
    
    Args:
        user_input: Natural language description of app and video
        include_render: Whether to render (requires Remotion setup)
    
    Returns:
        Final pipeline state
    """
    from orchestrator.session import reset_session
    
    print("\n" + "="*60)
    print("StreamLine Full Pipeline")
    print("="*60)
    print(f"\nInput: {user_input[:80]}{'...' if len(user_input) > 80 else ''}")
    
    # Reset session tracking
    session = reset_session()
    session.is_running = True
    
    graph = build_full_pipeline(include_render=include_render)
    config = {"configurable": {"thread_id": "full-pipeline-session"}}
    
    initial_state = {
        "messages": [],
        "user_input": user_input,
        "project_path": None,
        "app_bundle_id": None,
        "video_project_id": None,
        "intake_complete": False,
        "pending_task_ids": [],
        "current_task_index": 0,
        "completed_task_ids": [],
        "capture_status": None,
        "assets": [],
        "analysis_summary": None,
        "edit_plan_summary": None,
        "clip_task_ids": [],
        "text_task_ids": [],
        "clip_specs": [],
        "text_specs": [],
        "pending_clip_task_ids": None,
        "pending_text_task_ids": None,
        "current_clip_index": None,
        "current_text_index": None,
        "video_spec": None,
        "video_spec_id": None,
        "render_status": None,
        "render_path": None,
        "render_error": None,
    }
    
    try:
        # Run with interrupt handling (same pattern as capture phase)
        current_input = initial_state
        
        while True:
            if session.was_interrupted:
                print("\n⏸️  Pipeline interrupted")
                break
            
            for chunk in graph.stream(current_input, config, stream_mode="values"):
                pass
            
            state = graph.get_state(config)
            
            if not state.next:
                break
            
            # Handle interrupts (same as orchestrator)
            if hasattr(state, 'tasks') and state.tasks:
                from langgraph.types import Command
                handled = False
                for task in state.tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        interrupt_data = task.interrupts[0].value
                        
                        if isinstance(interrupt_data, dict):
                            print(f"\n⚠️  {interrupt_data.get('question', 'Need info')}")
                            if interrupt_data.get('hint'):
                                print(f"   Hint: {interrupt_data['hint']}")
                            
                            response = input("\n> ").strip()
                            current_input = Command(resume=response)
                            handled = True
                            break
                
                if not handled:
                    break
            else:
                break
                
    finally:
        session.is_running = False
    
    final_state = graph.get_state(config).values
    
    # Summary
    print("\n" + "="*60)
    print("Pipeline Complete")
    print("="*60)
    
    if final_state.get("render_path"):
        print(f"✓ Video rendered: {final_state['render_path']}")
    elif final_state.get("video_spec"):
        print(f"✓ VideoSpec created (render skipped or failed)")
        if final_state.get("render_error"):
            print(f"  Render error: {final_state['render_error']}")
    elif final_state.get("video_project_id"):
        print(f"✓ Capture complete, project: {final_state['video_project_id']}")
    else:
        print("⚠️  Pipeline did not complete successfully")
    
    return final_state
