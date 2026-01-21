"""
Capture tools for screenshots and recordings.
"""
from langchain_core.tools import tool
import subprocess
import time
from pathlib import Path
from datetime import datetime
from src.config import Config


def _get_output_path(capture_type: str, name: str) -> Path:
    """Generate output path for capture."""
    Config.CAPTURES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = "png" if capture_type == "screenshot" else "mov"
    return Config.CAPTURES_OUTPUT_DIR / f"{name}_{timestamp}.{ext}"


@tool
def capture_screenshot(name: str) -> str:
    """
    Capture a screenshot from the iOS simulator.
    Returns the path to the saved screenshot, or error message.
    
    Args:
        name: Descriptive name for the screenshot (e.g., "dashboard_main")
    """
    output_path = _get_output_path("screenshot", name)
    
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "io", "booted", "screenshot", str(output_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return f"Screenshot saved: {output_path}"
        else:
            return f"ERROR: {result.stderr}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def capture_recording(name: str, duration_seconds: int = 8) -> str:
    """
    Record video from the iOS simulator for specified duration.
    Returns the path to the saved recording, or error message.
    
    Args:
        name: Descriptive name for the recording (e.g., "add_task_flow")
        duration_seconds: How long to record (default 8 seconds)
    """
    output_path = _get_output_path("recording", name)
    
    try:
        # Start recording in background
        process = subprocess.Popen(
            ["xcrun", "simctl", "io", "booted", "recordVideo", str(output_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for duration
        time.sleep(duration_seconds)
        
        # Stop recording (send SIGINT)
        process.terminate()
        process.wait(timeout=10)
        
        if output_path.exists():
            return f"Recording saved: {output_path}"
        else:
            return f"ERROR: Recording file not created"
            
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def tap_simulator(x: int, y: int) -> str:
    """
    Simulate a tap at coordinates (x, y) on the iOS simulator.
    Use after identifying element positions from screenshots.
    """
    # Note: This uses AppleScript which works but is fragile.
    # For production, consider using XCUITest or Appium.
    try:
        # Get simulator window position and tap
        script = f'''
        tell application "Simulator"
            activate
        end tell
        delay 0.3
        tell application "System Events"
            click at {{{x}, {y}}}
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return f"Tapped at ({x}, {y})"
        else:
            return f"ERROR: {result.stderr}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def launch_app(bundle_id: str) -> str:
    """
    Launch an app in the iOS simulator by bundle ID.
    
    Args:
        bundle_id: e.g., "com.yourcompany.appname"
    """
    try:
        # Terminate if running
        subprocess.run(
            ["xcrun", "simctl", "terminate", "booted", bundle_id],
            capture_output=True,
            timeout=10
        )
        time.sleep(0.5)
        
        # Launch
        result = subprocess.run(
            ["xcrun", "simctl", "launch", "booted", bundle_id],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            time.sleep(2)  # Wait for app to load
            return f"Launched {bundle_id}"
        else:
            return f"ERROR: {result.stderr}"
    except Exception as e:
        return f"ERROR: {str(e)}"


@tool
def wait_seconds(seconds: float) -> str:
    """
    Wait for specified seconds. Use between actions to let UI settle.
    """
    time.sleep(seconds)
    return f"Waited {seconds} seconds"
