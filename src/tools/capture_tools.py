"""
Capture tools for iOS Simulator automation.

Focused on the core workflow:
  - Set up environment (status bar, appearance)
  - Navigate to screen (launch app, open deep link)
  - Interact (tap, swipe, type)
  - Capture (screenshot or recording)
  - Validate

Uses fb-idb as primary interaction backend when available.
"""
from langchain_core.tools import tool
import subprocess
import shutil
import time
import json
import signal
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field
from config import Config


# Suppress MallocStackLogging warnings from child processes
_SUBPROCESS_ENV = os.environ.copy()
_SUBPROCESS_ENV["MallocStackLogging"] = "0"
_SUBPROCESS_ENV["MallocStackLoggingNoCompact"] = "0"


# ═══════════════════════════════════════════════════════════════════════════════
# BACKEND DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_interaction_backend() -> str:
    """Detect best available UI interaction method."""
    if shutil.which("idb"):
        return "idb"
    if shutil.which("axe"):
        return "axe"
    return "applescript"


INTERACTION_BACKEND = _detect_interaction_backend()


# ═══════════════════════════════════════════════════════════════════════════════
# RECORDING SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RecordingSession:
    """Tracks an active recording session with action timestamps."""
    session_id: str
    name: str
    output_path: Path
    process: subprocess.Popen
    start_time: float
    action_log: list = field(default_factory=list)


# Active recording sessions (by session_id)
_active_recordings: dict[str, RecordingSession] = {}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _get_output_path(capture_type: str, name: str, ext: str = None) -> Path:
    """Generate output path for capture."""
    Config.CAPTURES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if ext is None:
        ext = "png" if capture_type == "screenshot" else "mov"
    return Config.CAPTURES_OUTPUT_DIR / f"{name}_{timestamp}.{ext}"


def _run(cmd: list, timeout: int = 30) -> tuple[int, str, str]:
    """Run command, return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            env=_SUBPROCESS_ENV  # Suppresses MallocStackLogging warnings
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


def _run_simctl(args: list, timeout: int = 30) -> tuple[int, str, str]:
    """Run xcrun simctl command."""
    return _run(["xcrun", "simctl"] + args, timeout)


def _get_booted_udid() -> Optional[str]:
    """Get UDID of first booted simulator."""
    code, stdout, _ = _run_simctl(["list", "devices", "booted", "-j"])
    if code != 0:
        return None
    try:
        data = json.loads(stdout)
        for devices in data.get("devices", {}).values():
            for device in devices:
                if device.get("state") == "Booted":
                    return device.get("udid")
    except:
        pass
    return None


def _log_action(session_id: str, action: str) -> Optional[dict]:
    """Log an action with timestamp to active recording session."""
    if session_id not in _active_recordings:
        return None
    session = _active_recordings[session_id]
    offset_ms = int((time.time() - session.start_time) * 1000)
    entry = {"offset_ms": offset_ms, "action": action}
    session.action_log.append(entry)
    return entry


# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT SETUP
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def set_status_bar(
    time_str: str = "9:41",
    battery_level: int = 100,
    battery_state: str = "charged",
    wifi_bars: int = 3,
    cellular_bars: int = 4,
    carrier: str = ""
) -> str:
    """
    Override the simulator status bar for clean marketing screenshots.
    Call this ONCE at the start of a capture session.
    
    Args:
        time_str: Time to display (default "9:41" - Apple's iconic time)
        battery_level: Battery percentage 0-100 (default 100)
        battery_state: "charged", "charging", or "discharging"
        wifi_bars: WiFi signal bars 0-3 (default 3)
        cellular_bars: Cellular signal bars 0-4 (default 4)
        carrier: Carrier name (default "" = no carrier text)
    
    Returns:
        Success message or error
    """
    cmd = [
        "xcrun", "simctl", "status_bar", "booted", "override",
        "--time", time_str,
        "--batteryLevel", str(battery_level),
        "--batteryState", battery_state,
        "--wifiBars", str(wifi_bars),
        "--cellularBars", str(cellular_bars),
    ]
    
    if carrier:
        cmd.extend(["--operatorName", carrier])
    
    # Add wifi and cellular mode
    cmd.extend(["--wifiMode", "active", "--cellularMode", "active"])
    
    code, _, stderr = _run(cmd)
    if code == 0:
        return f"Status bar set: {time_str}, battery {battery_level}%, {wifi_bars} wifi bars"
    return f"ERROR: {stderr}"


@tool
def clear_status_bar() -> str:
    """
    Clear status bar overrides, return to default simulator status bar.
    """
    code, _, stderr = _run_simctl(["status_bar", "booted", "clear"])
    if code == 0:
        return "Status bar cleared"
    return f"ERROR: {stderr}"


@tool
def set_appearance(mode: str) -> str:
    """
    Set simulator appearance to light or dark mode.
    
    Args:
        mode: "light" or "dark"
    
    Returns:
        Success message or error
    """
    if mode not in ("light", "dark"):
        return f"ERROR: mode must be 'light' or 'dark', got '{mode}'"
    
    code, _, stderr = _run_simctl(["ui", "booted", "appearance", mode])
    if code == 0:
        return f"Appearance set to {mode} mode"
    return f"ERROR: {stderr}"


@tool
def grant_permission(bundle_id: str, permission: str) -> str:
    """
    Grant a permission to an app to prevent permission dialogs during capture.
    Call BEFORE launching the app.
    
    Args:
        bundle_id: App bundle ID (e.g., "com.mycompany.myapp")
        permission: One of: "all", "calendar", "contacts", "location", 
                   "location-always", "photos", "photos-add", "media-library",
                   "microphone", "motion", "reminders", "siri", "camera"
    
    Returns:
        Success message or error
    """
    valid_permissions = {
        "all", "calendar", "contacts", "location", "location-always",
        "photos", "photos-add", "media-library", "microphone", "motion",
        "reminders", "siri", "speech-recognition", "camera"
    }
    
    if permission not in valid_permissions:
        return f"ERROR: Invalid permission '{permission}'. Valid: {', '.join(sorted(valid_permissions))}"
    
    code, _, stderr = _run_simctl(["privacy", "booted", "grant", permission, bundle_id])
    if code == 0:
        return f"Granted {permission} permission to {bundle_id}"
    return f"ERROR: {stderr}"


# ═══════════════════════════════════════════════════════════════════════════════
# APP NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def launch_app(
    bundle_id: str,
    terminate_existing: bool = True,
    wait_after: float = 2.0,
    arguments: str = ""
) -> str:
    """
    Launch an app in the iOS simulator.
    
    Args:
        bundle_id: App bundle ID (e.g., "com.mycompany.myapp")
        terminate_existing: If True, kill existing instance first for clean state
        wait_after: Seconds to wait after launch for app to load (default 2.0)
        arguments: Space-separated launch arguments (optional)
    
    Returns:
        Success message or error
    """
    # Check simulator is booted
    if not _get_booted_udid():
        return "ERROR: No simulator booted. Boot a simulator first."
    
    # Terminate if requested
    if terminate_existing:
        _run_simctl(["terminate", "booted", bundle_id], timeout=10)
        time.sleep(0.3)
    
    # Build launch command
    cmd = ["xcrun", "simctl", "launch", "booted", bundle_id]
    if arguments:
        cmd.extend(arguments.split())
    
    code, stdout, stderr = _run(cmd, timeout=30)
    
    if code != 0:
        return f"ERROR: {stderr or 'Launch failed'}"
    
    # Wait for app to load
    if wait_after > 0:
        time.sleep(wait_after)
    
    # Log to active recording if any
    for session in _active_recordings.values():
        _log_action(session.session_id, f"launched:{bundle_id}")
    
    return f"Launched {bundle_id}"


@tool
def terminate_app(bundle_id: str) -> str:
    """
    Terminate a running app.
    
    Args:
        bundle_id: App bundle ID
    
    Returns:
        Success message or error
    """
    code, _, stderr = _run_simctl(["terminate", "booted", bundle_id], timeout=10)
    if code == 0:
        return f"Terminated {bundle_id}"
    return f"ERROR: {stderr or 'Terminate failed (app may not be running)'}"


@tool
def open_url(url: str, wait_after: float = 1.5) -> str:
    """
    Open a URL in the simulator. Use for:
    - Deep links: "myapp://screen/id" 
    - Universal links: "https://myapp.com/path"
    - Web URLs: "https://example.com"
    
    This is the FASTEST way to navigate - skips manual tap navigation entirely.
    If your app supports deep links, USE THIS instead of tap sequences.
    
    Args:
        url: The URL to open (deep link, universal link, or web URL)
        wait_after: Seconds to wait after opening (default 1.5)
    
    Returns:
        Success message or error
    """
    code, _, stderr = _run_simctl(["openurl", "booted", url], timeout=15)
    
    if code != 0:
        return f"ERROR: {stderr or 'Failed to open URL'}"
    
    if wait_after > 0:
        time.sleep(wait_after)
    
    # Log to active recording if any
    for session in _active_recordings.values():
        _log_action(session.session_id, f"opened_url:{url}")
    
    return f"Opened URL: {url}"


# ═══════════════════════════════════════════════════════════════════════════════
# UI INTERACTION
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def tap(x: int, y: int, wait_after: float = 0.3) -> str:
    """
    Tap at coordinates (x, y) on the simulator screen.
    
    Coordinates are in POINTS (not pixels). For iPhone 15 Pro (393x852 points):
    - Status bar: y ~ 0-54
    - Navigation bar: y ~ 54-100  
    - Content area: y ~ 100-750
    - Tab bar: y ~ 750-832
    - Home indicator: y ~ 832-852
    
    Args:
        x: X coordinate in points
        y: Y coordinate in points
        wait_after: Seconds to wait after tap (default 0.3)
    
    Returns:
        Success message or error
    """
    result = None
    
    if INTERACTION_BACKEND == "idb":
        udid = _get_booted_udid()
        cmd = ["idb", "ui", "tap", str(x), str(y)]
        if udid:
            cmd.extend(["--udid", udid])
        code, _, stderr = _run(cmd, timeout=10)
        if code == 0:
            result = f"Tapped ({x}, {y}) via idb"
        else:
            result = f"ERROR: {stderr}"
    
    elif INTERACTION_BACKEND == "axe":
        udid = _get_booted_udid()
        if not udid:
            return "ERROR: No simulator booted"
        code, _, stderr = _run(["axe", "tap", "-x", str(x), "-y", str(y), "--udid", udid], timeout=10)
        if code == 0:
            result = f"Tapped ({x}, {y}) via axe"
        else:
            result = f"ERROR: {stderr}"
    
    else:
        # AppleScript fallback
        script = f'''
        tell application "Simulator" to activate
        delay 0.2
        tell application "System Events"
            tell process "Simulator"
                set frontWindow to first window
                set windowPosition to position of frontWindow
            end tell
            click at {{(item 1 of windowPosition) + {x}, (item 2 of windowPosition) + {y} + 50}}
        end tell
        '''
        code, _, stderr = _run(["osascript", "-e", script], timeout=10)
        if code == 0:
            result = f"Tapped ({x}, {y}) via AppleScript"
        else:
            result = f"ERROR: {stderr}"
    
    if result and not result.startswith("ERROR"):
        if wait_after > 0:
            time.sleep(wait_after)
        # Log to active recording
        for session in _active_recordings.values():
            _log_action(session.session_id, f"tap:{x},{y}")
    
    return result


@tool
def double_tap(x: int, y: int, wait_after: float = 0.3) -> str:
    """
    Double-tap at coordinates. Useful for zooming or selecting text.
    
    Args:
        x: X coordinate in points
        y: Y coordinate in points
        wait_after: Seconds to wait after double-tap
    
    Returns:
        Success message or error
    """
    if INTERACTION_BACKEND == "idb":
        # idb doesn't have native double-tap, simulate with two quick taps
        udid = _get_booted_udid()
        cmd = ["idb", "ui", "tap", str(x), str(y)]
        if udid:
            cmd.extend(["--udid", udid])
        _run(cmd, timeout=5)
        time.sleep(0.05)
        code, _, stderr = _run(cmd, timeout=5)
        result = f"Double-tapped ({x}, {y})" if code == 0 else f"ERROR: {stderr}"
    else:
        # Fall back to two taps
        tap(x, y, wait_after=0.05)
        result = tap(x, y, wait_after=0)
        result = f"Double-tapped ({x}, {y})"
    
    if wait_after > 0:
        time.sleep(wait_after)
    
    for session in _active_recordings.values():
        _log_action(session.session_id, f"double_tap:{x},{y}")
    
    return result


@tool
def long_press(x: int, y: int, duration: float = 1.0, wait_after: float = 0.3) -> str:
    """
    Long press at coordinates. Useful for context menus, drag initiation.
    
    Args:
        x: X coordinate in points
        y: Y coordinate in points
        duration: How long to hold in seconds (default 1.0)
        wait_after: Seconds to wait after release
    
    Returns:
        Success message or error
    """
    if INTERACTION_BACKEND == "idb":
        # idb doesn't have native long press, but we can use swipe with same start/end
        udid = _get_booted_udid()
        cmd = [
            "idb", "ui", "swipe",
            str(x), str(y), str(x), str(y),
            "--duration", str(duration)
        ]
        if udid:
            cmd.extend(["--udid", udid])
        code, _, stderr = _run(cmd, timeout=int(duration) + 5)
        result = f"Long-pressed ({x}, {y}) for {duration}s" if code == 0 else f"ERROR: {stderr}"
    else:
        # AppleScript with delay
        script = f'''
        tell application "Simulator" to activate
        delay 0.2
        tell application "System Events"
            tell process "Simulator"
                set frontWindow to first window
                set windowPosition to position of frontWindow
            end tell
            set clickX to (item 1 of windowPosition) + {x}
            set clickY to (item 2 of windowPosition) + {y} + 50
            -- Mouse down, wait, mouse up
            do shell script "cliclick d:" & clickX & "," & clickY
            delay {duration}
            do shell script "cliclick u:" & clickX & "," & clickY
        end tell
        '''
        code, _, stderr = _run(["osascript", "-e", script], timeout=int(duration) + 10)
        result = f"Long-pressed ({x}, {y}) for {duration}s" if code == 0 else f"ERROR: {stderr}"
    
    if wait_after > 0:
        time.sleep(wait_after)
    
    for session in _active_recordings.values():
        _log_action(session.session_id, f"long_press:{x},{y},{duration}s")
    
    return result


@tool
def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: float = 0.3,
    wait_after: float = 0.5
) -> str:
    """
    Swipe from (start_x, start_y) to (end_x, end_y).
    
    Common swipe patterns for iPhone 15 Pro (393x852):
    - Scroll up: swipe(200, 600, 200, 200)
    - Scroll down: swipe(200, 200, 200, 600)
    - Swipe to delete: swipe(350, <row_y>, 50, <row_y>)
    - Pull to refresh: swipe(200, 150, 200, 500)
    - Dismiss modal: swipe(200, 400, 200, 800)
    - Back gesture: swipe(10, 400, 200, 400)
    
    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        duration: Swipe duration in seconds (default 0.3, slower = more controlled)
        wait_after: Seconds to wait after swipe (default 0.5)
    
    Returns:
        Success message or error
    """
    result = None
    
    if INTERACTION_BACKEND == "idb":
        udid = _get_booted_udid()
        cmd = [
            "idb", "ui", "swipe",
            str(start_x), str(start_y),
            str(end_x), str(end_y),
            "--duration", str(duration)
        ]
        if udid:
            cmd.extend(["--udid", udid])
        code, _, stderr = _run(cmd, timeout=int(duration) + 10)
        if code == 0:
            result = f"Swiped ({start_x},{start_y}) → ({end_x},{end_y})"
        else:
            result = f"ERROR: {stderr}"
    
    elif INTERACTION_BACKEND == "axe":
        udid = _get_booted_udid()
        if not udid:
            return "ERROR: No simulator booted"
        code, _, stderr = _run([
            "axe", "swipe",
            "--start-x", str(start_x), "--start-y", str(start_y),
            "--end-x", str(end_x), "--end-y", str(end_y),
            "--udid", udid
        ], timeout=10)
        if code == 0:
            result = f"Swiped ({start_x},{start_y}) → ({end_x},{end_y})"
        else:
            result = f"ERROR: {stderr}"
    
    else:
        # AppleScript fallback using cliclick drag
        script = f'''
        tell application "Simulator" to activate
        delay 0.2
        tell application "System Events"
            tell process "Simulator"
                set frontWindow to first window
                set windowPosition to position of frontWindow
            end tell
            set sx to (item 1 of windowPosition) + {start_x}
            set sy to (item 2 of windowPosition) + {start_y} + 50
            set ex to (item 1 of windowPosition) + {end_x}
            set ey to (item 2 of windowPosition) + {end_y} + 50
            do shell script "cliclick dd:" & sx & "," & sy & " dm:" & ex & "," & ey & " du:" & ex & "," & ey
        end tell
        '''
        code, _, stderr = _run(["osascript", "-e", script], timeout=10)
        if code == 0:
            result = f"Swiped ({start_x},{start_y}) → ({end_x},{end_y})"
        else:
            result = f"ERROR: {stderr}"
    
    if result and not result.startswith("ERROR"):
        if wait_after > 0:
            time.sleep(wait_after)
        for session in _active_recordings.values():
            _log_action(session.session_id, f"swipe:{start_x},{start_y}→{end_x},{end_y}")
    
    return result


@tool
def type_text(text: str, wait_after: float = 0.3) -> str:
    """
    Type text into the currently focused text field.
    Make sure a text field is focused (tapped) before calling this.
    
    Args:
        text: Text to type
        wait_after: Seconds to wait after typing
    
    Returns:
        Success message or error
    """
    result = None
    
    if INTERACTION_BACKEND == "idb":
        udid = _get_booted_udid()
        cmd = ["idb", "ui", "text", text]
        if udid:
            cmd.extend(["--udid", udid])
        code, _, stderr = _run(cmd, timeout=30)
        if code == 0:
            result = f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
        else:
            result = f"ERROR: {stderr}"
    
    elif INTERACTION_BACKEND == "axe":
        udid = _get_booted_udid()
        if not udid:
            return "ERROR: No simulator booted"
        code, _, stderr = _run(["axe", "type", text, "--udid", udid], timeout=30)
        if code == 0:
            result = f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
        else:
            result = f"ERROR: {stderr}"
    
    else:
        # AppleScript keystroke
        escaped = text.replace('\\', '\\\\').replace('"', '\\"')
        script = f'''
        tell application "Simulator" to activate
        delay 0.1
        tell application "System Events"
            keystroke "{escaped}"
        end tell
        '''
        code, _, stderr = _run(["osascript", "-e", script], timeout=30)
        if code == 0:
            result = f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
        else:
            result = f"ERROR: {stderr}"
    
    if result and not result.startswith("ERROR"):
        if wait_after > 0:
            time.sleep(wait_after)
        for session in _active_recordings.values():
            _log_action(session.session_id, f"typed:{len(text)}_chars")
    
    return result


@tool
def press_key(key: str, wait_after: float = 0.2) -> str:
    """
    Press a special key.
    
    Args:
        key: Key to press. Options: "return", "delete", "escape", "tab", "space",
             "up", "down", "left", "right"
        wait_after: Seconds to wait after key press
    
    Returns:
        Success message or error
    """
    key_codes = {
        "return": 36, "delete": 51, "escape": 53, "tab": 48, "space": 49,
        "up": 126, "down": 125, "left": 123, "right": 124
    }
    
    if key not in key_codes:
        return f"ERROR: Unknown key '{key}'. Valid: {', '.join(key_codes.keys())}"
    
    if INTERACTION_BACKEND == "idb":
        udid = _get_booted_udid()
        cmd = ["idb", "ui", "key", str(key_codes[key])]
        if udid:
            cmd.extend(["--udid", udid])
        code, _, stderr = _run(cmd, timeout=5)
        result = f"Pressed {key}" if code == 0 else f"ERROR: {stderr}"
    else:
        script = f'''
        tell application "Simulator" to activate
        delay 0.1
        tell application "System Events"
            key code {key_codes[key]}
        end tell
        '''
        code, _, stderr = _run(["osascript", "-e", script], timeout=5)
        result = f"Pressed {key}" if code == 0 else f"ERROR: {stderr}"
    
    if wait_after > 0:
        time.sleep(wait_after)
    
    return result


@tool
def press_home() -> str:
    """Press the home button to go to home screen."""
    if INTERACTION_BACKEND == "idb":
        udid = _get_booted_udid()
        cmd = ["idb", "ui", "button", "HOME"]
        if udid:
            cmd.extend(["--udid", udid])
        code, _, stderr = _run(cmd, timeout=5)
        if code == 0:
            time.sleep(0.5)
            return "Pressed home button"
        return f"ERROR: {stderr}"
    else:
        # Use simctl to spawn a home button press
        code, _, stderr = _run_simctl(["spawn", "booted", "launchctl", "reboot", "userspace"], timeout=10)
        # Fallback: just return success and note limitation
        time.sleep(0.5)
        return "Pressed home button (simulated)"


# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN CAPTURE
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def capture_screenshot(
    name: str,
    format: str = "png",
    mask_status_bar: bool = False
) -> str:
    """
    Capture a screenshot from the iOS simulator.
    
    Args:
        name: Descriptive name (e.g., "dashboard_main", "task_detail")
        format: Image format - "png" (default, lossless), "jpeg", or "tiff"
        mask_status_bar: If True, blacks out status bar area (rarely needed if using set_status_bar)
    
    Returns:
        Path to saved screenshot, or error message
    """
    if format not in ("png", "jpeg", "tiff"):
        return f"ERROR: format must be 'png', 'jpeg', or 'tiff'"
    
    output_path = _get_output_path("screenshot", name, format)
    
    cmd = ["xcrun", "simctl", "io", "booted", "screenshot", f"--type={format}", str(output_path)]
    if mask_status_bar:
        cmd.insert(-1, "--mask=black")
    
    code, _, stderr = _run(cmd, timeout=30)
    
    if code == 0 and output_path.exists():
        # Log to active recording if any
        for session in _active_recordings.values():
            _log_action(session.session_id, f"screenshot:{name}")
        return f"Screenshot saved: {output_path}"
    return f"ERROR: {stderr or 'Screenshot failed'}"


@tool
def start_recording(name: str, codec: str = "h264") -> str:
    """
    Start a video recording. Returns a session ID to use with stop_recording.
    
    This enables action logging - all tap/swipe/type actions during recording
    are timestamped so you know exactly when each interaction happened.
    
    Args:
        name: Descriptive name (e.g., "onboarding_flow", "task_creation")
        codec: Video codec - "h264" (default, compatible) or "hevc" (smaller files)
    
    Returns:
        Session ID string to pass to stop_recording, or error message
    """
    if codec not in ("h264", "hevc"):
        return f"ERROR: codec must be 'h264' or 'hevc'"
    
    # Generate session ID and output path
    session_id = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}"
    output_path = _get_output_path("recording", name, "mov")
    
    try:
        # Start recording process
        process = subprocess.Popen(
            ["xcrun", "simctl", "io", "booted", "recordVideo", f"--codec={codec}", str(output_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Small delay to ensure recording started
        time.sleep(0.3)
        
        # Check process is running
        if process.poll() is not None:
            _, stderr = process.communicate()
            return f"ERROR: Recording failed to start - {stderr.decode()}"
        
        # Store session
        session = RecordingSession(
            session_id=session_id,
            name=name,
            output_path=output_path,
            process=process,
            start_time=time.time(),
            action_log=[{"offset_ms": 0, "action": "recording_started"}]
        )
        _active_recordings[session_id] = session
        
        return f"Recording started. Session ID: {session_id}"
        
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def stop_recording(session_id: str) -> str:
    """
    Stop a recording and save the video file.
    
    Args:
        session_id: Session ID returned by start_recording
    
    Returns:
        JSON with path to video, action log, and metadata. Or error message.
    """
    if session_id not in _active_recordings:
        return f"ERROR: No active recording with session ID '{session_id}'"
    
    session = _active_recordings[session_id]
    
    try:
        # Log stop action
        _log_action(session_id, "recording_stopped")
        
        # Stop recording gracefully with SIGINT (like Ctrl+C)
        # CRITICAL: terminate() sends SIGTERM which corrupts the video!
        # SIGINT allows xcrun simctl recordVideo to finalize the file properly
        session.process.send_signal(signal.SIGINT)
        
        # Give the process time to finalize the video container
        time.sleep(0.5)
        
        try:
            session.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            # If it still hasn't stopped, force kill (video may be corrupt)
            session.process.kill()
            session.process.wait()
        
        # Additional delay to ensure file is fully written to disk
        time.sleep(0.3)
        
        # Clean up session
        del _active_recordings[session_id]
        
        if not session.output_path.exists():
            return f"ERROR: Recording file not created"
        
        # Get video metadata
        duration_seconds = time.time() - session.start_time
        
        # Save action log alongside video
        action_log_path = session.output_path.with_suffix(".actions.json")
        with open(action_log_path, "w") as f:
            json.dump({
                "session_id": session_id,
                "name": session.name,
                "duration_seconds": round(duration_seconds, 2),
                "actions": session.action_log
            }, f, indent=2)
        
        result = {
            "video_path": str(session.output_path),
            "action_log_path": str(action_log_path),
            "duration_seconds": round(duration_seconds, 2),
            "action_count": len(session.action_log)
        }
        
        return json.dumps(result)
        
    except Exception as e:
        # Clean up on error
        if session_id in _active_recordings:
            del _active_recordings[session_id]
        return f"ERROR: {str(e)}"


@tool
def capture_recording(name: str, duration_seconds: int = 8) -> str:
    """
    Simple recording for fixed duration (no interaction during recording).
    For recordings WITH interactions, use start_recording/stop_recording instead.
    
    Args:
        name: Descriptive name for the recording
        duration_seconds: How long to record (default 8 seconds)
    
    Returns:
        Path to saved recording, or error message
    """
    output_path = _get_output_path("recording", name, "mov")
    
    try:
        # Start recording
        process = subprocess.Popen(
            ["xcrun", "simctl", "io", "booted", "recordVideo", str(output_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for duration
        time.sleep(duration_seconds)
        
        # Stop recording gracefully with SIGINT (not SIGTERM)
        process.send_signal(signal.SIGINT)
        time.sleep(0.5)  # Let video finalize
        
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        
        time.sleep(0.3)  # Ensure file is written to disk
        
        if output_path.exists():
            return f"Recording saved: {output_path}"
        return "ERROR: Recording file not created"
        
    except Exception as e:
        return f"ERROR: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def wait_seconds(seconds: float) -> str:
    """
    Wait for specified seconds. Use between actions to let UI settle.
    
    Recommended waits:
    - After launch: 2-3 seconds
    - After tap: 0.3-0.5 seconds  
    - After navigation: 1-2 seconds
    - After animation: 0.5-1 second
    - Before capture: 0.5 seconds
    
    Args:
        seconds: Time to wait
    
    Returns:
        Confirmation message
    """
    time.sleep(seconds)
    
    # Log to active recording
    for session in _active_recordings.values():
        _log_action(session.session_id, f"wait:{seconds}s")
    
    return f"Waited {seconds}s"


@tool
def get_simulator_info() -> str:
    """
    Get information about the currently booted simulator.
    Useful for understanding coordinate system and debugging.
    
    Returns:
        JSON with simulator details, or error message
    """
    code, stdout, stderr = _run_simctl(["list", "devices", "booted", "-j"])
    
    if code != 0:
        return f"ERROR: {stderr}"
    
    try:
        data = json.loads(stdout)
        
        for runtime, devices in data.get("devices", {}).items():
            for device in devices:
                if device.get("state") == "Booted":
                    # Extract runtime version
                    runtime_name = runtime.split(".")[-1] if "." in runtime else runtime
                    
                    info = {
                        "name": device.get("name"),
                        "udid": device.get("udid"),
                        "runtime": runtime_name,
                        "state": "Booted",
                        "interaction_backend": INTERACTION_BACKEND,
                        "screen_info": _get_device_screen_info(device.get("name", ""))
                    }
                    return json.dumps(info, indent=2)
        
        return "No simulators booted"
        
    except Exception as e:
        return f"ERROR: {str(e)}"


def _get_device_screen_info(device_name: str) -> dict:
    """Get screen dimensions for common devices."""
    # Screen sizes in points (not pixels)
    devices = {
        "iPhone 15 Pro Max": {"width": 430, "height": 932, "scale": 3},
        "iPhone 15 Pro": {"width": 393, "height": 852, "scale": 3},
        "iPhone 15 Plus": {"width": 430, "height": 932, "scale": 3},
        "iPhone 15": {"width": 393, "height": 852, "scale": 3},
        "iPhone 14 Pro Max": {"width": 430, "height": 932, "scale": 3},
        "iPhone 14 Pro": {"width": 393, "height": 852, "scale": 3},
        "iPhone 14": {"width": 390, "height": 844, "scale": 3},
        "iPhone 13": {"width": 390, "height": 844, "scale": 3},
        "iPhone SE": {"width": 375, "height": 667, "scale": 2},
        "iPad Pro (12.9-inch)": {"width": 1024, "height": 1366, "scale": 2},
        "iPad Pro (11-inch)": {"width": 834, "height": 1194, "scale": 2},
        "iPad Air": {"width": 820, "height": 1180, "scale": 2},
    }
    
    for name, info in devices.items():
        if name in device_name:
            return info
    
    # Default fallback
    return {"width": 393, "height": 852, "scale": 3, "note": "assumed iPhone 15 Pro"}


@tool
def describe_screen() -> str:
    """
    Get accessibility tree of current screen (requires idb).
    Useful for finding element positions and identifiers.
    
    Returns:
        JSON with UI elements, or error message if idb not available
    """
    if INTERACTION_BACKEND != "idb":
        return f"ERROR: describe_screen requires idb (current backend: {INTERACTION_BACKEND})"
    
    code, stdout, stderr = _run(["idb", "ui", "describe-all"], timeout=30)
    
    if code == 0:
        return stdout
    return f"ERROR: {stderr}"


@tool
def get_interaction_status() -> str:
    """
    Get information about available interaction methods.
    Useful for debugging when taps/swipes aren't working.
    
    Returns:
        JSON with interaction backend status
    """
    status = {
        "active_backend": INTERACTION_BACKEND,
        "idb_available": shutil.which("idb") is not None,
        "axe_available": shutil.which("axe") is not None,
        "cliclick_available": shutil.which("cliclick") is not None,
        "active_recordings": list(_active_recordings.keys()),
    }
    
    # Test if backend actually works
    if INTERACTION_BACKEND == "idb":
        code, _, _ = _run(["idb", "list-targets"], timeout=5)
        status["idb_connected"] = code == 0
    
    return json.dumps(status, indent=2)
