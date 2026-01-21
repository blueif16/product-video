"""
Graph builder and run functions.

Implements graph-level retry control:
- Graph tracks attempt count per task
- Routing decides whether to retry or move on
- Agent reports ONE result and exits
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver

from config import Config
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
    
    Initializes:
    - pending_task_ids: All tasks to capture
    - current_task_index: Which task we're on (0-indexed)
    - current_task_attempts: How many tries on current task (reset per task)
    - completed_task_ids: Successfully captured tasks
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
            "current_task_attempts": 0,
            "completed_task_ids": [],
            "last_capture_success": None,
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
        "current_task_attempts": 0,
        "completed_task_ids": [],
        "last_capture_success": None,
    }


def route_after_capture(state: PipelineState) -> Literal["capture_single", "move_to_next", "aggregate"]:
    """
    Route after a capture attempt. Graph-level retry control.
    
    Logic:
    1. If success → move to next task
    2. If failed AND attempts < max → retry same task
    3. If failed AND attempts >= max → move to next task (give up)
    4. If no more tasks → aggregate
    """
    pending = state.get("pending_task_ids", [])
    current_idx = state.get("current_task_index", 0)
    attempts = state.get("current_task_attempts", 0)
    success = state.get("last_capture_success")
    
    # Check if we have more tasks
    if current_idx >= len(pending):
        return "aggregate"
    
    # Check capture result
    if success:
        # Success - move to next task
        return "move_to_next"
    elif success is False and attempts < Config.MAX_CAPTURE_ATTEMPTS:
        # Failed but can retry
        print(f"   🔄 Retrying (attempt {attempts + 1}/{Config.MAX_CAPTURE_ATTEMPTS})")
        return "capture_single"
    else:
        # Failed and out of retries, or first attempt - move on
        if success is False:
            print(f"   ⏭️  Max attempts reached, moving to next task")
        return "move_to_next"


def move_to_next_task(state: PipelineState) -> dict:
    """
    Move to next task in queue. Reset attempt counter.
    """
    current_idx = state.get("current_task_index", 0)
    completed = state.get("completed_task_ids", [])
    pending = state.get("pending_task_ids", [])
    success = state.get("last_capture_success")
    
    # Track completed task if successful
    if success and current_idx < len(pending):
        task_id = pending[current_idx]
        completed = completed + [task_id]
    
    return {
        "current_task_index": current_idx + 1,
        "current_task_attempts": 0,  # Reset for new task
        "completed_task_ids": completed,
        "last_capture_success": None,  # Reset
    }


def route_next_capture(state: PipelineState) -> Literal["capture_single", "aggregate"]:
    """
    Route after moving to next task. Check if more tasks remain.
    """
    pending = state.get("pending_task_ids", [])
    current_idx = state.get("current_task_index", 0)
    
    if current_idx < len(pending):
        return "capture_single"
    else:
        return "aggregate"


def increment_attempts(state: PipelineState) -> dict:
    """Increment attempt counter before capture."""
    return {
        "current_task_attempts": (state.get("current_task_attempts", 0) or 0) + 1,
    }


# ─────────────────────────────────────────────────────────────
# Graph
# ─────────────────────────────────────────────────────────────

def build_pipeline():
    """
    Build the pipeline graph with graph-level retry control.
    
    Flow:
    START → intake → analyze_and_plan → prepare_capture_queue 
          → increment_attempts → capture_single → route_after_capture
              ↓                                          ↓
         (retry same)                              (move_to_next)
              ↓                                          ↓
         capture_single                           route_next_capture
                                                        ↓
                                            (more tasks) | (done)
                                                  ↓           ↓
                                          capture_single   aggregate
    
    Key: Graph controls retry loop, not the agent.
    """
    builder = StateGraph(PipelineState)
    
    # Nodes
    builder.add_node("intake", intake_node, destinations=["intake", "analyze_and_plan"])
    builder.add_node("analyze_and_plan", analyze_and_plan_node)
    builder.add_node("prepare_capture_queue", prepare_capture_queue)
    builder.add_node("increment_attempts", increment_attempts)
    builder.add_node("capture_single", capture_single_task_node)
    builder.add_node("move_to_next", move_to_next_task)
    builder.add_node("aggregate", aggregate_node)
    
    # Edges
    builder.add_edge(START, "intake")
    builder.add_edge("analyze_and_plan", "prepare_capture_queue")
    
    # Initial queue to first capture
    builder.add_conditional_edges(
        "prepare_capture_queue",
        route_next_capture,
        ["capture_single", "aggregate"]
    )
    
    # Before each capture, increment attempts
    # (This ensures we track attempt count at graph level)
    builder.add_edge("increment_attempts", "capture_single")
    
    # After capture, decide: retry, move on, or done
    builder.add_conditional_edges(
        "capture_single",
        route_after_capture,
        {
            "capture_single": "increment_attempts",  # Retry goes through increment
            "move_to_next": "move_to_next",
            "aggregate": "aggregate",
        }
    )
    
    # After moving to next task, check if more remain
    builder.add_conditional_edges(
        "move_to_next",
        route_next_capture,
        {
            "capture_single": "increment_attempts",  # New task goes through increment
            "aggregate": "aggregate",
        }
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
        "url_schemes": [],
        "app_manifest": None,
        "video_project_id": None,
        "intake_complete": False,
        # Sequential capture state
        "pending_task_ids": [],
        "current_task_index": 0,
        "current_task_attempts": 0,
        "completed_task_ids": [],
        "last_capture_success": None,
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
