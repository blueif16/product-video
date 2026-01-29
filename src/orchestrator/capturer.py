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

from src.config import get_model, Config
from src.tools import CAPTURER_TOOLS, INTERACTION_BACKEND, reset_exploration_state, get_exploration_state
from src.db.supabase_client import get_task, update_task_status
from src.orchestrator.state import PipelineState, AppManifest
from src.orchestrator.session import get_session


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


class ValidationState:
    """
    Track validation state to prevent reporting success when validation failed.
    This enforces the rule: you can only report success if the last validation passed.
    """
    def __init__(self):
        self.last_validation_passed: Optional[bool] = None
        self.last_validated_path: Optional[str] = None
        self.validation_count: int = 0
        self.success_count: int = 0
    
    def record_validation(self, passed: bool, asset_path: str):
        self.last_validation_passed = passed
        self.last_validated_path = asset_path
        self.validation_count += 1
        if passed:
            self.success_count += 1
    
    def can_report_success(self, asset_path: str) -> tuple[bool, str]:
        """
        Check if we can report success for this asset.
        Returns (allowed, reason).
        """
        # If no validation was done, we can't report success
        if self.validation_count == 0:
            return False, "No validation was performed"
        
        # If no validation ever passed, we can't report success
        if self.success_count == 0:
            return False, "No validation passed"
        
        # If the last validation failed, we can't report success
        if not self.last_validation_passed:
            return False, "Last validation failed - capture again or report failure"
        
        return True, "OK"

_validation_state = ValidationState()


def reset_result():
    global _result, _validation_state
    _result = CaptureResult()
    _validation_state = ValidationState()


# ─────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────

def create_result_tool(task_id: str, video_project_id: str):
    """Create result reporting tool bound to task_id and project."""
    
    @tool
    def report_capture_result(success: bool, asset_path: str, notes: str) -> str:
        """
        Report the result of a capture attempt. YOU MUST CALL THIS when done.
        
        IMPORTANT: You can only report success=True if the last validation passed.
        If validation failed, you must either:
        1. Capture again and get a passing validation
        2. Report success=False with explanation
        
        On success, the asset is automatically uploaded to cloud storage.
        
        Args:
            success: True if capture is usable for marketing video
            asset_path: Path to the captured file
            notes: Explanation of result or what went wrong
        
        Returns:
            Confirmation or error if trying to report success without valid validation
        """
        # Enforce validation state - can't report success if validation failed
        if success:
            allowed, reason = _validation_state.can_report_success(asset_path)
            if not allowed:
                return f"BLOCKED: Cannot report success - {reason}. Either capture again with passing validation, or report failure."
        
        status = "success" if success else "failed"
        
        # Auto-trim static frames from video before upload
        if success and asset_path.endswith('.mp4') and Config.AUTO_TRIM_STATIC_FRAMES:
            try:
                import sys
                from pathlib import Path as PathLib

                # Add scripts directory to path
                scripts_dir = PathLib(__file__).parent.parent.parent / "scripts"
                if str(scripts_dir) not in sys.path:
                    sys.path.insert(0, str(scripts_dir))

                from trim_static_frames import trim_video

                trimmed_path = trim_video(
                    input_path=asset_path,
                    threshold=Config.MOTION_DETECTION_THRESHOLD,
                    min_motion_duration=Config.MIN_MOTION_DURATION,
                    merge_gap=Config.MERGE_GAP,
                    buffer=Config.BUFFER_TIME,
                    verbose=True
                )

                # Update asset_path if trimmed
                if trimmed_path != asset_path:
                    asset_path = trimmed_path
                    log(f"   ✂️  Trimmed to: {trimmed_path.split('/')[-1]}")

            except Exception as e:
                # Trimming failure should not break the pipeline
                log(f"   ⚠️  Video trim failed (keeping original): {str(e)}")
        
        # Cloud-first: Upload to Supabase Storage on success
        asset_url = None
        if success:
            try:
                from src.tools.storage import upload_asset
                
                # Determine capture type from file extension
                capture_type = "recording" if asset_path.endswith('.mp4') else "screenshot"
                subfolder = "recordings" if capture_type == "recording" else "screenshots"
                
                log(f"   ☁️  Uploading to cloud...")
                asset_url = upload_asset(asset_path, video_project_id, subfolder=subfolder)
                log(f"   ☁️  Uploaded → {asset_url.split('/')[-1]}")
                
            except Exception as e:
                # Upload failure is logged but doesn't fail the capture
                # The local asset_path is still valid
                log(f"   ⚠️  Cloud upload failed (local file saved): {str(e)}")
        
        # Update DB with both local path and cloud URL
        update_task_status(
            task_id, 
            status, 
            asset_path=asset_path, 
            asset_url=asset_url,
            validation_notes=notes
        )

        # Track for logging
        _result.success = success
        _result.asset_path = asset_path
        _result.notes = notes
        
        # Track completion in session
        if success:
            session = get_session()
            session.mark_task_complete(task_id)
        
        return f"Recorded: {status}" + (f" (cloud: {asset_url is not None})" if success else "")
    
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
    
    elif tool_name == "request_human_guidance":
        question = tool_args.get("specific_question", "?")
        if len(question) > 40:
            question = question[:37] + "..."
        return f"request_human_guidance(\"{question}\")"
    
    elif tool_name == "check_exploration_budget":
        return "check_exploration_budget()"
    
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
    
    return f"""You are an expert iOS capture agent. Your job is to capture HIGH-QUALITY screenshots and recordings for marketing videos.

INTERACTION BACKEND: {INTERACTION_BACKEND}
{manifest_section}

╔═══════════════════════════════════════════════════════════════════════════════╗
║  CORE PRINCIPLE: OBSERVE → UNDERSTAND → ACT → VERIFY                         ║
║                                                                               ║
║  NEVER tap blindly. ALWAYS know what's on screen before acting.              ║
║  NEVER guess coordinates. ALWAYS use describe_screen() to find elements.     ║
║  NEVER start recording until you've verified the full flow works.            ║
╚═══════════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════
METHODOLOGY FOR RECORDINGS (Complex Flows)
═══════════════════════════════════════════════════════════════

PHASE 1: SETUP
  1. set_status_bar(time_str="9:41")
  2. set_appearance("light")  
  3. open_url(deep_link) OR launch_app(bundle_id)
  4. wait_seconds(2)

PHASE 2: RECONNAISSANCE (CRITICAL - Do this BEFORE recording!)
  5. describe_screen() → Read the output carefully!
     - What elements are visible?
     - What are their approximate positions?
     - Is this the screen you expected?
  
  6. DRY RUN: Perform the navigation/interaction WITHOUT recording
     - Tap where you think the button is
     - describe_screen() → Did the screen change as expected?
     - If not, adjust and try again
     - Continue until you can complete the FULL flow
  
  7. Return to starting state (open_url again or navigate back)

PHASE 3: EXECUTE (Only after dry run succeeds!)
  8. describe_screen() → Confirm you're at the starting point
  9. start_recording(name)
  10. Execute the SAME actions that worked in dry run
      - After EACH tap/swipe/type: wait_seconds(1.0)  ← MINIMUM 1.0s for video encoder!
      - NEVER use wait < 1.0s during recording
  11. wait_seconds(2.0) → MINIMUM 2.0s before stop (let encoder flush)
  12. stop_recording(session_id)

PHASE 4: VALIDATE & REPORT
  13. validate_capture(video_path, description, app_context)
  14. report_capture_result(success, path, notes)

RECORDING TIMING REQUIREMENTS (CRITICAL for video quality):
  - Minimum 1.0s wait after EACH interaction (tap, swipe, type_text)
  - Minimum 2.0s wait before stop_recording
  - Total recording duration should be at least 4-5 seconds
  - Short waits (0.3-0.5s) cause "Could not extract frames" errors!

═══════════════════════════════════════════════════════════════
METHODOLOGY FOR SCREENSHOTS (Simpler)
═══════════════════════════════════════════════════════════════
1. set_status_bar + set_appearance
2. Navigate to target screen
3. describe_screen() → Verify you're on the right screen
4. wait_seconds(0.5) → Let UI settle
5. capture_screenshot(name)
6. validate_capture → report_capture_result

═══════════════════════════════════════════════════════════════
HOW TO READ describe_screen() OUTPUT
═══════════════════════════════════════════════════════════════
The output is an accessibility tree. Look for:
  - "AXButton" with "AXLabel" → Tappable buttons
  - "AXTextField" → Text input fields  
  - "AXStaticText" → Labels/text
  - "AXFrame": "{{{{x, y}}}}, {{{{width, height}}}}" → Element position

To tap an element, use the CENTER of its frame:
  tap_x = x + (width / 2)
  tap_y = y + (height / 2)

═══════════════════════════════════════════════════════════════
COORDINATE REFERENCE (iPhone 15 Pro - 393x852 points)
═══════════════════════════════════════════════════════════════
• Status bar: y = 0-54
• Nav bar: y = 54-100
• Content area: y = 100-750
• Tab bar: y = 750-832
• Home indicator: y = 832-852

Common swipes:
  - Scroll up (reveal more below): swipe(200, 600, 200, 200)
  - Scroll down (reveal more above): swipe(200, 200, 200, 600)

═══════════════════════════════════════════════════════════════
FEW-SHOT EXAMPLES
═══════════════════════════════════════════════════════════════

▼ EXAMPLE 1: Recording a "tap button → see result" flow
─────────────────────────────────────────────────────
TASK: Record tapping the "Add Task" button and seeing the modal

✗ WRONG (blind execution):
  open_url(myapp://tasks)
  start_recording("add_task")
  tap(200, 400)  ← Guessing!
  stop_recording
  validate_capture  ← Fails because tap missed

✓ CORRECT (observe-act-verify):
  open_url(myapp://tasks)
  wait_seconds(2)
  
  # RECON: Find the button
  describe_screen()
  # Output shows: AXButton "Add Task" at frame {{{{320, 720}}}}, {{{{60, 44}}}}
  # Calculate: tap_x = 320 + 30 = 350, tap_y = 720 + 22 = 742
  
  # DRY RUN: Test the tap
  tap(350, 742)
  wait_seconds(0.5)
  describe_screen()
  # Output shows: Modal with "New Task" title ✓
  
  # Reset to starting point
  open_url(myapp://tasks)
  wait_seconds(1)
  describe_screen()  ← Confirm back at start
  
  # NOW record (we know it works)
  start_recording("add_task_flow")
  tap(350, 742)
  wait_seconds(1)
  stop_recording(session_id)
  validate_capture(...)
  report_capture_result(True, ...)


▼ EXAMPLE 2: Recording carousel swipe + tap
─────────────────────────────────────────────────────
TASK: Record swiping through outfit carousel and tapping an item

✓ CORRECT approach:
  open_url(yiban://outfit)
  wait_seconds(2)
  
  # RECON: Understand the layout
  describe_screen()
  # Output shows:
  #   - "Outfit" header at top  
  #   - Horizontal scroll view at y=300-500
  #   - Outfit cards at x=50, x=200, x=350
  
  # DRY RUN: Test swipe
  swipe(300, 400, 100, 400)  ← Swipe left in carousel area
  wait_seconds(0.5)
  describe_screen()
  # Verify: New items visible? Yes ✓
  
  # DRY RUN: Test tap on item
  tap(200, 400)
  wait_seconds(0.5)
  describe_screen()
  # Verify: Detail view appeared? Yes ✓
  
  # Reset
  open_url(yiban://outfit)
  wait_seconds(1)
  describe_screen()  ← Confirm reset
  
  # Execute with recording
  start_recording("outfit_browse")
  swipe(300, 400, 100, 400)
  wait_seconds(0.5)
  swipe(100, 400, 300, 400)
  wait_seconds(0.5)
  tap(200, 400)
  wait_seconds(1)
  stop_recording(session_id)
  validate_capture(...)


▼ EXAMPLE 3: Handling unexpected screen
─────────────────────────────────────────────────────
  open_url(myapp://settings)
  wait_seconds(2)
  describe_screen()
  # Output shows: Login screen with email/password!
  # UNEXPECTED! Wanted Settings, got Login
  
  # Adapt: Try alternative navigation
  press_home()
  launch_app(bundle_id)
  wait_seconds(2)
  describe_screen()
  # Shows: Home screen with tab bar at bottom
  
  # Navigate via tabs instead
  tap(350, 790)  ← Settings tab (rightmost)
  wait_seconds(1)
  describe_screen()
  # Shows: Settings screen ✓ - now proceed

═══════════════════════════════════════════════════════════════
VALIDATION CONTEXT
═══════════════════════════════════════════════════════════════
ALWAYS include app_context when validating:

  validate_capture(
    asset_path=video_path,
    task_description="Recording of outfit browsing",
    app_context="This is Yiban, a closet/outfit app. Outfit screen shows a carousel of outfit suggestions that can be swiped."
  )

═══════════════════════════════════════════════════════════════
HANDLING FAILURES (Distinguish failure types!)
═══════════════════════════════════════════════════════════════

▼ TECHNICAL FAILURE: "Could not extract frames from video"
  → This is a RECORDING problem, NOT a navigation problem
  → The video file is corrupt or too short
  → Root cause: wait_seconds too short during recording

  FIX:
    1. Re-navigate to starting state (open_url or launch_app)
    2. Re-do FULL recon (describe_screen, dry run)
    3. Record again with LONGER waits:
       - wait_seconds(1.0) after EACH tap/swipe (not 0.5!)
       - wait_seconds(2.0) before stop_recording
    4. Validate again

▼ NAVIGATION FAILURE: "wrong screen" / "tap missed" / "element not found"
  → This is a NAVIGATION problem
  → Your coordinates were wrong or screen state unexpected

  FIX:
    1. describe_screen() → See where you actually are
    2. Find correct element coordinates from accessibility tree
    3. Try alternative navigation (different deep link, tab tap, etc.)
    4. Re-do dry run with corrected approach

▼ ON ANY RETRY (MANDATORY):
  → ALWAYS re-navigate to starting state (open_url/launch_app)
  → ALWAYS re-do describe_screen() recon
  → ALWAYS re-do dry run to verify flow works
  → NEVER just re-validate the same broken file
  → NEVER skip recon and jump straight to recording

═══════════════════════════════════════════════════════════════
EXPLORATION LIMITS & ASKING FOR HELP
═══════════════════════════════════════════════════════════════

You have a LIMITED EXPLORATION BUDGET:
  • Max {Config.MAX_DESCRIBE_CALLS} describe_screen() calls
  • Max {Config.MAX_NAVIGATION_ATTEMPTS} navigation attempts (tap, swipe, open_url)

If you're exploring and can't find the target screen:
  1. First, try the obvious paths (deep links, tabs, menu items)
  2. If those fail, use check_exploration_budget() to see remaining attempts
  3. If budget is LOW (≤3 describes or ≤5 nav attempts left), ASK FOR HELP

WHEN TO ASK FOR HELP (use request_human_guidance tool):
  • You've tried 3+ different navigation paths and none work
  • The deep link doesn't work and you don't know the UI path
  • You're going in circles (same screens appearing repeatedly)
  • You're below 3 describe calls or 5 nav attempts remaining

HOW TO ASK FOR HELP:
  request_human_guidance(
    situation="I'm on the main dashboard, see tabs for Home/Chat/Profile",
    what_i_tried="Tried yiban://inventory, tapped all tabs, searched menus",
    specific_question="How do I reach the Inventory/Closet screen?"
  )

The human can provide:
  • Specific coordinates: "tap 200 400"
  • A working deep link: "open yiban://closet"
  • Step-by-step instructions
  • "skip" if the screen doesn't exist

DO NOT loop forever trying random taps! Ask for help early.

═══════════════════════════════════════════════════════════════
CRITICAL RULES
═══════════════════════════════════════════════════════════════
1. ALWAYS describe_screen() after navigation, BEFORE any taps
2. NEVER start recording until dry run succeeds
3. After EACH action in recon, describe_screen() to verify
4. If tap doesn't work → describe_screen() → find correct position
5. YOU MUST call report_capture_result when done
6. Max {Config.MAX_CAPTURE_ATTEMPTS} attempts - use recon to succeed first try!
7. On retry: FULL reset + recon (see HANDLING FAILURES above)
8. If exploration budget is LOW → request_human_guidance() instead of looping!
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
    
    # Reset exploration state for this task
    target_desc = task['task_description'][:100] if task['task_description'] else "Unknown target"
    reset_exploration_state(target_description=target_desc)
    
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
    pending_validation_path = None  # Track asset_path for validation state
    
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
                                    
                                    # Track asset_path when validate_capture is called
                                    if tool_name == "validate_capture":
                                        pending_validation_path = tool_args.get("asset_path", "")
                                    
                                    # Note: Navigation tools (tap, swipe, open_url) now track their own
                                    # exploration budget internally - see _check_navigation_budget()
                                    
                                    print_tool_call(tool_name, tool_args)
                        else:
                            content = msg.content if msg.content else ""
                            if content and len(content) > 0:
                                debug(f"    AI content (no tools): {content[:100]}...")
                    
                    if isinstance(msg, ToolMessage):
                        content = msg.content if isinstance(msg.content, str) else str(msg.content)
                        debug(f"    Tool result from '{msg.name}': {content[:50]}...")
                        
                        # Note: describe_screen now tracks its own exploration budget
                        # internally - see the describe_screen tool implementation
                        
                        if msg.name == "validate_capture":
                            is_failure = "FAILED" in content.upper()
                            print_validation_result(content, is_failure)
                            
                            # Record validation result in state tracker
                            _validation_state.record_validation(
                                passed=not is_failure,
                                asset_path=pending_validation_path or ""
                            )
                            
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
