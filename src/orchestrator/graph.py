"""
Graph builder and run functions.
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver

from db.supabase_client import get_pending_tasks, update_video_project_status

from .state import PipelineState
from .intake import intake_node
from .analyzer import analyze_and_plan_node
from .capturer import capture_single_task_node
from .aggregate import aggregate_node
from .session import get_session


# ─────────────────────────────────────────────────────────────
# Sequential Capture Nodes
# ─────────────────────────────────────────────────────────────

def prepare_capture_queue(state: PipelineState) -> dict:
    """
    Load pending tasks from DB and set up sequential queue.
    
    Instead of fanning out with Send (parallel), we:
    1. Load all task IDs
    2. Store them in state
    3. Process one at a time via loop
    """
    session = get_session()
    session.current_stage = "capturing"
    
    app_bundle_id = state.get("app_bundle_id", "com.app.unknown")
    tasks = get_pending_tasks(app_bundle_id)
    
    if not tasks:
        print("⚠️  No capture tasks found.")
        return {
            "pending_task_ids": [],
            "current_task_index": 0,
            "completed_task_ids": [],
        }
    
    # Update status to capturing
    if state.get("video_project_id"):
        update_video_project_status(state["video_project_id"], "capturing")
    
    task_ids = [task["id"] for task in tasks]
    
    # Update session tracking
    session.total_tasks = len(task_ids)
    for tid in task_ids:
        session.add_task(tid)
    
    print(f"\n📸 Queued {len(task_ids)} capture tasks for sequential execution...")
    
    return {
        "pending_task_ids": task_ids,
        "current_task_index": 0,
        "completed_task_ids": [],
    }


def route_next_capture(state: PipelineState) -> Literal["capture_single", "aggregate"]:
    """
    Route to next capture task or aggregate when done.
    
    This creates a loop:
    prepare_queue → capture_single → route_next → capture_single → ... → aggregate
    """
    pending = state.get("pending_task_ids", [])
    current_idx = state.get("current_task_index", 0)
    
    if current_idx < len(pending):
        return "capture_single"
    else:
        return "aggregate"


# ─────────────────────────────────────────────────────────────
# Graph
# ─────────────────────────────────────────────────────────────

def build_pipeline():
    """
    Build the pipeline graph with SEQUENTIAL capture execution.
    
    Flow:
    START → intake → analyze_and_plan → prepare_capture_queue 
          → capture_single ⟲ (loops via route_next_capture)
          → aggregate → END
    
    Single simulator means tasks MUST run one at a time.
    """
    builder = StateGraph(PipelineState)
    
    # Nodes
    builder.add_node("intake", intake_node, destinations=["intake", "analyze_and_plan"])
    builder.add_node("analyze_and_plan", analyze_and_plan_node)
    builder.add_node("prepare_capture_queue", prepare_capture_queue)
    builder.add_node("capture_single", capture_single_task_node)
    builder.add_node("aggregate", aggregate_node)
    
    # Edges
    builder.add_edge(START, "intake")
    builder.add_edge("analyze_and_plan", "prepare_capture_queue")
    
    # Sequential loop: prepare → capture → route → (capture again or aggregate)
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
    builder.add_edge("aggregate", END)
    
    return builder.compile(checkpointer=InMemorySaver())


# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────

def run_pipeline(user_input: str) -> dict:
    """Run pipeline with human-in-the-loop support."""
    from .session import reset_session
    
    # Initialize fresh session for this run
    session = reset_session()
    session.is_running = True
    session.current_stage = "intake"
    
    graph = build_pipeline()
    config = {"configurable": {"thread_id": "session-1"}}
    
    initial_state = {
        "messages": [],
        "user_input": user_input,
        "project_path": None,
        "app_bundle_id": None,
        "video_project_id": None,
        "intake_complete": False,
        # Sequential capture state
        "pending_task_ids": [],
        "current_task_index": 0,
        "completed_task_ids": [],
    }
    
    print(f"\n🎬 Starting pipeline...")
    print(f"   {user_input[:80]}{'...' if len(user_input) > 80 else ''}")
    
    current_input = initial_state
    
    try:
        while True:
            # Check if interrupted
            if session.was_interrupted:
                print("\n⏸️  Pipeline interrupted")
                break
            
            for chunk in graph.stream(current_input, config, stream_mode="values"):
                pass
            
            state = graph.get_state(config)
            
            if not state.next:
                break
            
            # Handle interrupts
            if hasattr(state, 'tasks') and state.tasks:
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
        if not session.was_interrupted:
            session.current_stage = "completed"
    
    return graph.get_state(config).values
