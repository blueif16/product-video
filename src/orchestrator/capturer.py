"""
Capturer node: Executes individual capture tasks SEQUENTIALLY.

One task at a time since only one simulator is available.
"""
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from config import get_model, Config
from tools import CAPTURER_TOOLS
from db.supabase_client import get_task, update_task_status
from .state import PipelineState
from .session import get_session


# ─────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────

def create_result_tool(task_id: str):
    """Create result reporting tool bound to task_id."""
    
    @tool
    def report_capture_result(success: bool, asset_path: str, notes: str) -> str:
        """
        Report the result of a capture attempt. YOU MUST CALL THIS when done.
        
        Args:
            success: True if capture is usable for marketing video
            asset_path: Path to the captured file
            notes: Explanation of result or what went wrong
        
        Returns:
            Confirmation
        """
        status = "success" if success else "failed"
        update_task_status(task_id, status, asset_path=asset_path, validation_notes=notes)
        
        # Track completion in session
        if success:
            session = get_session()
            session.mark_task_complete(task_id)
        
        return f"Recorded: {status}"
    
    return report_capture_result


# ─────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────

def capture_single_task_node(state: PipelineState) -> dict:
    """
    Execute a single capture task from the sequential queue.
    
    Reads current_task_index, executes that task, increments index.
    """
    session = get_session()
    
    # Check for interrupt before starting
    if session.was_interrupted:
        print("⏸️  Capture interrupted before starting")
        return {}
    
    pending = state.get("pending_task_ids", [])
    current_idx = state.get("current_task_index", 0)
    completed = state.get("completed_task_ids", [])
    
    if current_idx >= len(pending):
        print("⚠️  No more tasks to capture")
        return {}
    
    task_id = pending[current_idx]
    task = get_task(task_id)
    
    if not task:
        print(f"⚠️  Task {task_id[:8]}... not found in DB")
        return {
            "current_task_index": current_idx + 1,
        }
    
    print(f"\n📷 Capturing task {current_idx + 1}/{len(pending)}: {task_id[:8]}...")
    
    # Create agent with tools
    tools = CAPTURER_TOOLS + [create_result_tool(task_id)]
    
    agent = create_react_agent(
        model=get_model(),
        tools=tools,
        name="capturer",
        prompt=f"""You are capturing iOS app content for a marketing video.

YOUR TOOLS:
- launch_app, tap_simulator, wait_seconds: Control the app
- capture_screenshot, capture_recording: Capture content
- validate_capture: Check if capture is good
- report_capture_result: Report your result (REQUIRED)

PROCESS:
1. Launch the app
2. Navigate to target screen
3. Capture (screenshot or recording)
4. Validate
5. Call report_capture_result

Max {Config.MAX_CAPTURE_ATTEMPTS} attempts. MUST call report_capture_result when done.""",
    )
    
    result = agent.invoke({
        "messages": [HumanMessage(content=f"""Execute capture task:

BUNDLE ID: {task['app_bundle_id']}
TYPE: {task['capture_type']}

TASK:
{task['task_description']}

Call report_capture_result when done.""")]
    })
    
    print(f"  ✓ Task {task_id[:8]}... complete")
    
    # Update state for next iteration
    return {
        "current_task_index": current_idx + 1,
        "completed_task_ids": completed + [task_id],
        "messages": result["messages"],
    }
