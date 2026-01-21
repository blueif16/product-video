"""
Capturer node: Executes individual capture tasks.
"""
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from src.config import get_model, Config
from src.tools import CAPTURER_TOOLS
from src.db.supabase_client import update_task_status
from .state import CaptureTaskState


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
        return f"Recorded: {status}"
    
    return report_capture_result


# ─────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────

def capture_task_node(state: CaptureTaskState) -> dict:
    """Execute a single capture task."""
    tools = CAPTURER_TOOLS + [create_result_tool(state["task_id"])]
    
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
        "messages": state["messages"] + [HumanMessage(content=f"""Execute:

BUNDLE ID: {state['app_bundle_id']}
TYPE: {state['capture_type']}

TASK:
{state['task_description']}

Call report_capture_result when done.""")]
    })
    
    print(f"  → {state['task_id'][:8]}... done")
    return {"messages": result["messages"]}
