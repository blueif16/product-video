"""
Capturer node: Executes individual capture tasks SEQUENTIALLY.

One task at a time since only one simulator is available.
Streams agent execution for real-time progress visibility.
Receives app_manifest from analyzer for navigation and context.
"""
from typing import Optional
import json

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from config import get_model, Config
from tools import CAPTURER_TOOLS, INTERACTION_BACKEND
from db.supabase_client import get_task, update_task_status
from .state import PipelineState, AppManifest
from .session import get_session


# ─────────────────────────────────────────────────────────────
# Capture Result Tracking
# ─────────────────────────────────────────────────────────────

class CaptureResult:
    """Track the result of a capture for logging."""
    def __init__(self):
        self.success: Optional[bool] = None
        self.asset_path: Optional[str] = None
        self.notes: Optional[str] = None

_result = CaptureResult()


def reset_result():
    global _result
    _result = CaptureResult()


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
        
        # Track for logging
        _result.success = success
        _result.asset_path = asset_path
        _result.notes = notes
        
        # Track completion in session
        if success:
            session = get_session()
            session.mark_task_complete(task_id)
        
        return f"Recorded: {status}"
    
    return report_capture_result


# ─────────────────────────────────────────────────────────────
# Progress Display
# ─────────────────────────────────────────────────────────────

def log(message: str) -> None:
    """Print with immediate flush."""
    print(message, flush=True)


def debug(message: str) -> None:
    """Print debug message if DEBUG mode enabled."""
    if Config.DEBUG:
        print(f"   [DEBUG] {message}", flush=True)


def print_task_header(idx: int, total: int, task: dict) -> None:
    """Print the task header with type and description."""
    capture_type = task['capture_type'].upper()
    description = task['task_description']
    
    # Truncate description to first 120 chars or first newline
    if '\n' in description:
        description = description.split('\n')[0]
    if len(description) > 120:
        description = description[:117] + "..."
    
    log(f"\n{'━' * 60}")
    log(f"📷 [{idx + 1}/{total}] {capture_type}")
    log(f"{'━' * 60}")
    log(f"{description}")
    log("")


def format_tool_call(tool_name: str, tool_args: dict) -> str:
    """Format a tool call for display with relevant args."""
    
    if tool_name == "wait_seconds":
        secs = tool_args.get("seconds", "?")
        return f"wait_seconds({secs}s)"
    
    elif tool_name == "capture_recording":
        name = tool_args.get("name", "?")
        dur = tool_args.get("duration_seconds", 8)
        return f"capture_recording(\"{name}\", {dur}s)"
    
    elif tool_name == "start_recording":
        name = tool_args.get("name", "?")
        return f"start_recording(\"{name}\")"
    
    elif tool_name == "stop_recording":
        session_id = tool_args.get("session_id", "?")
        if len(session_id) > 20:
            session_id = session_id[:17] + "..."
        return f"stop_recording({session_id})"
    
    elif tool_name == "capture_screenshot":
        name = tool_args.get("name", "?")
        return f"capture_screenshot(\"{name}\")"
    
    elif tool_name in ("tap", "tap_simulator"):
        x = tool_args.get("x", "?")
        y = tool_args.get("y", "?")
        return f"tap({x}, {y})"
    
    elif tool_name == "swipe":
        sx = tool_args.get("start_x", "?")
        sy = tool_args.get("start_y", "?")
        ex = tool_args.get("end_x", "?")
        ey = tool_args.get("end_y", "?")
        return f"swipe({sx},{sy}→{ex},{ey})"
    
    elif tool_name == "type_text":
        text = tool_args.get("text", "?")
        if len(text) > 20:
            text = text[:17] + "..."
        return f"type_text(\"{text}\")"
    
    elif tool_name == "launch_app":
        bundle = tool_args.get("bundle_id", "?")
        if len(bundle) > 30:
            bundle = "..." + bundle[-27:]
        return f"launch_app({bundle})"
    
    elif tool_name == "open_url":
        url = tool_args.get("url", "?")
        if len(url) > 40:
            url = url[:37] + "..."
        return f"open_url({url})"
    
    elif tool_name == "set_status_bar":
        time_str = tool_args.get("time_str", "9:41")
        return f"set_status_bar(time={time_str})"
    
    elif tool_name == "set_appearance":
        mode = tool_args.get("mode", "?")
        return f"set_appearance({mode})"
    
    elif tool_name == "grant_permission":
        perm = tool_args.get("permission", "?")
        return f"grant_permission({perm})"
    
    elif tool_name == "validate_capture":
        path = tool_args.get("asset_path", "?")
        if "/" in path:
            path = path.split("/")[-1]
        if len(path) > 30:
            path = path[:27] + "..."
        return f"validate_capture({path})"
    
    elif tool_name == "report_capture_result":
        success = tool_args.get("success", "?")
        icon = "✓" if success else "✗"
        return f"report_capture_result({icon})"
    
    elif tool_name == "run_bash":
        cmd = tool_args.get("command", "?")
        if len(cmd) > 40:
            cmd = cmd[:37] + "..."
        return f"run_bash({cmd})"
    
    elif tool_name == "get_simulator_info":
        return "get_simulator_info()"
    
    elif tool_name == "describe_screen":
        return "describe_screen()"
    
    elif tool_name == "verify_screen":
        screen = tool_args.get("expected_screen", "?")
        return f"verify_screen(\"{screen}\")"
    
    else:
        return tool_name


def print_tool_call(tool_name: str, tool_args: dict) -> None:
    """Print a tool call with formatting."""
    formatted = format_tool_call(tool_name, tool_args)
    log(f"   → {formatted}")


def extract_verdict(content: str) -> str:
    """Extract the verdict line from validation response."""
    # Look for VERDICT: line
    if "VERDICT:" in content:
        verdict_start = content.find("VERDICT:")
        verdict = content[verdict_start + 8:].strip()
        # Get first line of verdict
        if '\n' in verdict:
            verdict = verdict.split('\n')[0]
        return verdict
    
    # Fallback: look for SUCCESS/FAILED prefix
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith("SUCCESS:") or line.startswith("FAILED:"):
            return line
    
    # Last resort: truncate content
    if len(content) > 80:
        return content[:77] + "..."
    return content


def print_validation_result(content: str, is_failure: bool) -> None:
    """Print validation result details."""
    verdict = extract_verdict(content)
    
    # Truncate if needed
    if len(verdict) > 70:
        verdict = verdict[:67] + "..."
    
    if is_failure:
        log(f"   ⚠️  {verdict}")
    else:
        log(f"   ✓  {verdict}")


def print_task_result() -> None:
    """Print the final result of the task."""
    if _result.success is None:
        log(f"\n❓ No result reported")
    elif _result.success:
        path = _result.asset_path or "unknown"
        # Shorten path - show just filename
        if "/" in path:
            path = path.split("/")[-1]
        log(f"\n✅ Success → {path}")
    else:
        notes = _result.notes or "Unknown error"
        if len(notes) > 60:
            notes = notes[:57] + "..."
        log(f"\n❌ Failed: {notes}")


# ─────────────────────────────────────────────────────────────
# App Manifest Formatting
# ─────────────────────────────────────────────────────────────

def format_manifest_for_prompt(manifest: Optional[AppManifest]) -> str:
    """Format app manifest as context for capturer prompt."""
    if not manifest:
        return ""
    
    lines = [
        "",
        "═══════════════════════════════════════════════════════════════",
        "APP KNOWLEDGE (from analyzer)",
        "═══════════════════════════════════════════════════════════════",
        f"App: {manifest.get('app_name', 'Unknown')}",
        f"Bundle ID: {manifest.get('bundle_id', 'Unknown')}",
    ]
    
    # URL schemes / deep links
    url_schemes = manifest.get('url_schemes', [])
    if url_schemes:
        lines.append(f"URL Schemes: {', '.join(url_schemes)}")
        lines.append("  → Use open_url(\"{scheme}://path\") for fast navigation!")
    
    # Tab structure
    tabs = manifest.get('tab_structure', [])
    if tabs:
        lines.append(f"Tabs (bottom bar): {' | '.join(tabs)}")
        lines.append("  → Tab bar is at y=750-832. Tap center of each tab.")
    
    # Screens
    screens = manifest.get('screens', [])
    if screens:
        lines.append("\nScreens:")
        for screen in screens:
            name = screen.get('name', 'Unknown')
            desc = screen.get('description', '')
            tab_idx = screen.get('tab_index')
            deep_link = screen.get('deep_link')
            
            screen_line = f"  • {name}"
            if tab_idx is not None:
                screen_line += f" (tab {tab_idx})"
            if deep_link:
                screen_line += f" → {deep_link}"
            lines.append(screen_line)
            if desc:
                lines.append(f"    {desc}")
    
    # Navigation notes
    nav_notes = manifest.get('navigation_notes', '')
    if nav_notes:
        lines.append(f"\nNavigation notes: {nav_notes}")
    
    lines.append("")
    
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Capture Agent Prompt
# ─────────────────────────────────────────────────────────────

def build_capture_prompt(manifest: Optional[AppManifest]) -> str:
    """Build the capturer prompt with app manifest context."""
    
    manifest_section = format_manifest_for_prompt(manifest)
    
    return f"""You are capturing iOS app content for a marketing video.

INTERACTION BACKEND: {INTERACTION_BACKEND}
{manifest_section}
═══════════════════════════════════════════════════════════════
WORKFLOW FOR SCREENSHOTS
═══════════════════════════════════════════════════════════════
1. set_status_bar(time_str="9:41", battery_level=100)  # Clean status bar
2. set_appearance("light")  # Or "dark" if task requires
3. launch_app(bundle_id)  # OR open_url("scheme://path") if deep link available
4. wait_seconds(2)  # Let app load
5. [Navigate with tap/swipe if needed, wait between actions]
6. wait_seconds(0.5)  # Let animations settle
7. capture_screenshot(name)
8. validate_capture(path, description, app_context)  # Include app context!
9. report_capture_result(success, path, notes)

═══════════════════════════════════════════════════════════════
WORKFLOW FOR RECORDINGS
═══════════════════════════════════════════════════════════════
1. set_status_bar(time_str="9:41", battery_level=100)
2. set_appearance("light")
3. launch_app(bundle_id)
4. wait_seconds(2)
5. session_id = start_recording(name)  # Actions are timestamped!
6. [Perform interactions: tap, swipe, type]
7. wait_seconds(1)  # Let animations complete
8. result = stop_recording(session_id)  # Returns video_path
9. validate_capture(video_path, description, app_context)
10. report_capture_result(success, path, notes)

═══════════════════════════════════════════════════════════════
COORDINATES (iPhone 15 Pro - 393x852 points)
═══════════════════════════════════════════════════════════════
• Nav bar: y = 54-100
• Content: y = 100-750
• Tab bar: y = 750-832 (tap here for tabs)
• Common swipes:
  - Scroll up: swipe(200, 600, 200, 200)
  - Scroll down: swipe(200, 200, 200, 600)
  - Pull refresh: swipe(200, 150, 200, 450)

═══════════════════════════════════════════════════════════════
NAVIGATION TIPS
═══════════════════════════════════════════════════════════════
• USE DEEP LINKS when available - they're faster and more reliable than taps
• If you see tabs listed above, tap the tab bar (y≈790) to switch tabs
• Use verify_screen() before capturing to confirm you're on the right screen
• If navigation fails, try describe_screen() to see what's actually visible

═══════════════════════════════════════════════════════════════
VALIDATION
═══════════════════════════════════════════════════════════════
• Pass app_context to validate_capture so validator knows what to expect
• Example: "This is Yiban, a closet app. Home screen shows weather-based outfit suggestions."
• This prevents validator from thinking it's the wrong app!

═══════════════════════════════════════════════════════════════
IMPORTANT
═══════════════════════════════════════════════════════════════
• ALWAYS set_status_bar first — ugly status bars ruin marketing shots
• YOU MUST call report_capture_result when done
• Max {Config.MAX_CAPTURE_ATTEMPTS} attempts if validation fails
"""


# ─────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────

def capture_single_task_node(state: PipelineState) -> dict:
    """
    Execute a single capture task from the sequential queue.
    
    Receives app_manifest from analyzer to know:
    - Available screens and what they look like
    - Tab structure for navigation
    - Deep links for fast navigation
    - App context for validation
    """
    reset_result()
    session = get_session()
    
    # Check for interrupt before starting
    if session.was_interrupted:
        log("⏸️  Capture interrupted before starting")
        return {}
    
    pending = state.get("pending_task_ids", [])
    current_idx = state.get("current_task_index", 0)
    completed = state.get("completed_task_ids", [])
    total = len(pending)
    
    if current_idx >= total:
        log("⚠️  No more tasks to capture")
        return {}
    
    task_id = pending[current_idx]
    task = get_task(task_id)
    
    if not task:
        log(f"⚠️  Task {task_id[:8]}... not found in DB")
        return {
            "current_task_index": current_idx + 1,
        }
    
    # Print task header
    print_task_header(current_idx, total, task)
    
    # Get app manifest from state
    manifest = state.get("app_manifest")
    
    # Create agent with tools and manifest-aware prompt
    tools = CAPTURER_TOOLS + [create_result_tool(task_id)]
    
    debug(f"Creating agent with {len(tools)} tools (backend: {INTERACTION_BACKEND})")
    if manifest:
        debug(f"App manifest: {manifest.get('app_name', 'Unknown')} with {len(manifest.get('screens', []))} screens")
    
    prompt = build_capture_prompt(manifest)
    
    agent = create_react_agent(
        model=get_model(),
        tools=tools,
        name="capturer",
        prompt=prompt,
    )
    
    # Indicate we're waiting for the model
    log("   ⏳ Agent thinking...")
    
    # Build app context string for validator
    app_context = ""
    if manifest:
        app_name = manifest.get('app_name', '')
        app_desc = manifest.get('app_description', '')
        if app_name and app_desc:
            app_context = f"\n\nAPP CONTEXT for validation: This is {app_name}. {app_desc}"
    
    input_messages = [HumanMessage(content=f"""Execute capture task:

BUNDLE ID: {task['app_bundle_id']}
TYPE: {task['capture_type']}

TASK:
{task['task_description']}{app_context}

Start with set_status_bar, then launch_app (or use deep link), navigate, capture, validate with app context, and report_capture_result.""")]
    
    debug(f"Invoking agent...")
    
    # Stream execution for real-time progress
    last_messages = []
    seen_tool_calls = set()
    attempt_count = 1
    just_failed_validation = False
    first_tool_call = True
    event_count = 0
    
    try:
        for event in agent.stream({"messages": input_messages}):
            event_count += 1
            debug(f"Event #{event_count}: keys={list(event.keys())}")
            
            for node_name, node_output in event.items():
                debug(f"  Node '{node_name}': type={type(node_output).__name__}")
                
                if not isinstance(node_output, dict):
                    debug(f"  Skipping non-dict output")
                    continue
                
                messages = node_output.get("messages", [])
                debug(f"  Messages: {len(messages)}")
                
                for msg in messages:
                    msg_type = type(msg).__name__
                    debug(f"    Message type: {msg_type}")
                    
                    last_messages.append(msg)
                    
                    if isinstance(msg, AIMessage):
                        if msg.tool_calls:
                            debug(f"    Tool calls: {len(msg.tool_calls)}")
                            for tool_call in msg.tool_calls:
                                call_id = tool_call.get("id", "")
                                if call_id not in seen_tool_calls:
                                    seen_tool_calls.add(call_id)
                                    tool_name = tool_call.get("name", "unknown")
                                    tool_args = tool_call.get("args", {})
                                    
                                    if first_tool_call:
                                        first_tool_call = False
                                    
                                    if just_failed_validation and tool_name != "report_capture_result":
                                        attempt_count += 1
                                        log(f"\n   🔄 Attempt {attempt_count}/{Config.MAX_CAPTURE_ATTEMPTS}")
                                        log("")
                                        just_failed_validation = False
                                    
                                    print_tool_call(tool_name, tool_args)
                        else:
                            content = msg.content if msg.content else ""
                            if content and len(content) > 0:
                                debug(f"    AI content (no tools): {content[:100]}...")
                    
                    if isinstance(msg, ToolMessage):
                        content = msg.content if isinstance(msg.content, str) else str(msg.content)
                        debug(f"    Tool result from '{msg.name}': {content[:50]}...")
                        
                        if msg.name == "validate_capture":
                            is_failure = "FAILED" in content.upper()
                            print_validation_result(content, is_failure)
                            
                            if is_failure:
                                just_failed_validation = True
    
    except Exception as e:
        log(f"\n   ❌ Agent error: {str(e)}")
        import traceback
        if Config.DEBUG:
            traceback.print_exc()
    
    debug(f"Total events: {event_count}")
    
    print_task_result()
    
    return {
        "current_task_index": current_idx + 1,
        "completed_task_ids": completed + [task_id],
        "last_capture_success": _result.success,
        "messages": last_messages[-5:] if last_messages else [],
    }
