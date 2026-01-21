"""
Graph builder and run functions.
"""
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, Command
from langgraph.checkpoint.memory import InMemorySaver

from src.db.supabase_client import get_pending_tasks, update_video_project_status

from .state import PipelineState, CaptureTaskState
from .intake import intake_node
from .analyzer import analyze_and_plan_node
from .capturer import capture_task_node
from .aggregate import aggregate_node


# ─────────────────────────────────────────────────────────────
# Routing
# ─────────────────────────────────────────────────────────────

def route_to_capturers(state: PipelineState) -> list[Send]:
    """Route to capture tasks based on DB."""
    app_bundle_id = state.get("app_bundle_id", "com.app.unknown")
    tasks = get_pending_tasks(app_bundle_id)
    
    if not tasks:
        print("⚠️  No capture tasks found.")
        return [Send("aggregate", state)]
    
    # Update status to capturing
    if state.get("video_project_id"):
        update_video_project_status(state["video_project_id"], "capturing")
    
    print(f"\n📸 Dispatching {len(tasks)} capture tasks...")
    
    sends = []
    for task in tasks:
        sends.append(Send("capture_task", CaptureTaskState(
            task_id=task["id"],
            task_description=task["task_description"],
            capture_type=task["capture_type"],
            app_bundle_id=task["app_bundle_id"],
            messages=[]
        )))
    
    return sends


# ─────────────────────────────────────────────────────────────
# Graph
# ─────────────────────────────────────────────────────────────

def build_pipeline():
    """Build the pipeline graph."""
    builder = StateGraph(PipelineState)
    
    builder.add_node("intake", intake_node, destinations=["intake", "analyze_and_plan"])
    builder.add_node("analyze_and_plan", analyze_and_plan_node)
    builder.add_node("capture_task", capture_task_node)
    builder.add_node("aggregate", aggregate_node)
    
    builder.add_edge(START, "intake")
    builder.add_conditional_edges(
        "analyze_and_plan",
        route_to_capturers,
        ["capture_task", "aggregate"]
    )
    builder.add_edge("capture_task", "aggregate")
    builder.add_edge("aggregate", END)
    
    return builder.compile(checkpointer=InMemorySaver())


# ─────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────

def run_pipeline(user_input: str) -> dict:
    """Run pipeline with human-in-the-loop support."""
    graph = build_pipeline()
    config = {"configurable": {"thread_id": "session-1"}}
    
    initial_state = {
        "messages": [],
        "user_input": user_input,
        "project_path": None,
        "app_bundle_id": None,
        "video_project_id": None,
        "intake_complete": False,
    }
    
    print(f"\n🎬 Starting pipeline...")
    print(f"   {user_input[:80]}{'...' if len(user_input) > 80 else ''}")
    
    current_input = initial_state
    
    while True:
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
    
    return graph.get_state(config).values
