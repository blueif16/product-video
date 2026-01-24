"""
Validation tool with independent multimodal LLM call.
This is a TOOL, not an agent. Fresh context per validation.

Auto-detects action logs from recordings for intelligent frame extraction.
Now accepts app_context so validator knows what app it's looking at.
"""
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
import subprocess
import base64
import json
import os
from pathlib import Path
from config import get_model


# Suppress MallocStackLogging warnings from child processes (FFmpeg, ffprobe)
_SUBPROCESS_ENV = os.environ.copy()
_SUBPROCESS_ENV["MallocStackLogging"] = "0"
_SUBPROCESS_ENV["MallocStackLoggingNoCompact"] = "0"


def _encode_image(image_path: Path) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def _get_action_log_timestamps(video_path: Path) -> list[int]:
    """
    Try to find and read the action log for a video.
    Returns list of timestamps in ms where actions occurred.
    """
    action_log_path = video_path.with_suffix(".actions.json")
    
    if not action_log_path.exists():
        return []
    
    try:
        with open(action_log_path) as f:
            data = json.load(f)
        
        actions = data.get("actions", [])
        
        timestamps = []
        for action in actions:
            offset_ms = action.get("offset_ms", 0)
            action_type = action.get("action", "")
            
            if any(skip in action_type for skip in ["recording_", "wait:"]):
                continue
            
            timestamps.append(offset_ms)
        
        if timestamps:
            if timestamps[0] > 500:
                timestamps.insert(0, 200)
            duration_ms = int(data.get("duration_seconds", 8) * 1000)
            if timestamps[-1] < duration_ms - 500:
                timestamps.append(duration_ms - 200)
        
        return sorted(set(timestamps))
        
    except Exception:
        return []


def _extract_frames_from_video(video_path: Path, timestamps_ms: list[int] = None) -> list[Path]:
    """
    Extract frames from video at specified timestamps.
    If no timestamps, extracts at 1fps for coverage.
    """
    import time as time_module
    
    # Ensure video file is fully written before attempting extraction
    time_module.sleep(0.5)
    
    # Verify video file exists and has content
    if not video_path.exists():
        return []
    
    file_size = video_path.stat().st_size
    if file_size < 1000:  # Less than 1KB is likely corrupt
        return []
    
    output_dir = video_path.parent / f"{video_path.stem}_frames"
    output_dir.mkdir(exist_ok=True)
    
    extracted = []
    
    # First, verify the video is readable with ffprobe
    probe_result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", 
         "-show_entries", "stream=duration,nb_frames", "-of", "csv=p=0", str(video_path)],
        capture_output=True, timeout=10, env=_SUBPROCESS_ENV
    )
    if probe_result.returncode != 0:
        # Video might be corrupt or not finalized
        return []
    
    if timestamps_ms:
        for i, ts in enumerate(timestamps_ms):
            seconds = ts / 1000
            output_path = output_dir / f"frame_{i:03d}_{ts}ms.png"
            result = subprocess.run([
                "ffmpeg", "-y", "-ss", str(seconds),
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "2",  # High quality
                str(output_path)
            ], capture_output=True, timeout=30, env=_SUBPROCESS_ENV)
            if output_path.exists() and output_path.stat().st_size > 0:
                extracted.append(output_path)
    else:
        # Extract at 1fps - use slower but more reliable method
        result = subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", "fps=1",
            "-q:v", "2",  # High quality
            str(output_dir / "frame_%03d.png")
        ], capture_output=True, timeout=60, env=_SUBPROCESS_ENV)
        
        # Only include frames that actually have content
        for frame_path in sorted(output_dir.glob("frame_*.png")):
            if frame_path.stat().st_size > 0:
                extracted.append(frame_path)
    
    return extracted


def _validate_with_vision(
    image_paths: list[Path],
    task_description: str,
    app_context: str = "",
    action_context: str = ""
) -> str:
    """
    Core validation logic. Sends images to multimodal LLM.
    
    Args:
        image_paths: List of image paths to validate
        task_description: What we're trying to capture
        app_context: CRITICAL - What app this is and what screens look like
        action_context: Timeline of actions (for recordings)
    
    Returns text response (success statement or failure reason).
    """
    model = get_model()
    
    content = []
    for img_path in image_paths[:10]:
        img_data = _encode_image(img_path)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_data}"}
        })
    
    # Build context sections
    app_section = ""
    if app_context:
        app_section = f"""
APP CONTEXT (important - use this to understand what you're looking at):
{app_context}
"""
    
    frame_section = ""
    if action_context:
        frame_section = f"""
FRAME TIMESTAMPS:
{action_context}
"""
    
    content.append({
        "type": "text",
        "text": f"""Analyze these frames from an iOS app capture.
{app_section}
CAPTURE TASK:
{task_description}
{frame_section}
INSTRUCTIONS:
1. First, describe what you see in each frame objectively
2. Based on the APP CONTEXT above, identify which screen this is
3. Note any issues: loading spinners, error states, partial renders, system overlays, blurry frames
4. Determine if this capture is usable for a marketing video

IMPORTANT: Use the APP CONTEXT to understand what app this is. For example, if the context says
"This is Yiban, a closet app. Home screen shows weather-based outfit suggestions" - then a screen
showing weather IS correct for the Home screen, not a sign of wrong app.

Respond in this format:

OBSERVATIONS:
[What you see in the frames]

SCREEN IDENTIFIED:
[Which screen from the app this appears to be, based on APP CONTEXT]

ISSUES FOUND:
[Any problems, or "None" if clean]

VISUAL DESIGN (note these for video styling):
- Theme: light or dark
- Background color: approximate hex (e.g., #F5F2ED)
- Text color: approximate hex
- Accent colors: any prominent UI colors
- Aesthetic: (e.g., minimal, playful, premium, technical)

VERDICT:
[Either "SUCCESS: [brief reason]" or "FAILED: [specific reason why not usable]"]
"""
    })
    
    response = model.invoke([HumanMessage(content=content)])
    return response.content


@tool
def validate_capture(
    asset_path: str,
    task_description: str,
    app_context: str,
    action_timestamps_ms: str = ""
) -> str:
    """
    Validate a captured screenshot or recording against task criteria.
    Uses independent multimodal LLM call with fresh context.
    
    Args:
        asset_path: Path to screenshot (.png) or recording (.mov)
        task_description: What was being captured and validation criteria
        app_context: REQUIRED. What app this is and what its screens look like.
                    Without this, validation WILL fail due to misidentified screens.
                    Example: "Yiban is a closet app. Home screen shows weather-based
                    outfit suggestions. Closet screen (tab 2) shows clothing grid."
        action_timestamps_ms: Optional comma-separated timestamps in ms
    
    Returns:
        "SUCCESS: [reason]" or "FAILED: [reason]"
    """
    path = Path(asset_path)
    
    if not path.exists():
        return f"FAILED: Asset file not found: {asset_path}"
    
    try:
        if path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            return _validate_with_vision([path], task_description, app_context)
            
        elif path.suffix.lower() in [".mov", ".mp4"]:
            timestamps = None
            action_context = ""
            
            if action_timestamps_ms:
                timestamps = [int(t.strip()) for t in action_timestamps_ms.split(",")]
                action_context = f"Frames extracted at: {action_timestamps_ms}ms"
            else:
                auto_timestamps = _get_action_log_timestamps(path)
                if auto_timestamps:
                    timestamps = auto_timestamps
                    action_log_path = path.with_suffix(".actions.json")
                    try:
                        with open(action_log_path) as f:
                            data = json.load(f)
                        actions = data.get("actions", [])
                        action_context = "Actions during recording:\n"
                        for action in actions:
                            if "recording_" not in action.get("action", ""):
                                action_context += f"  - {action['offset_ms']}ms: {action['action']}\n"
                    except:
                        action_context = f"Frames extracted at action points: {timestamps}"
            
            frames = _extract_frames_from_video(path, timestamps)
            
            if not frames:
                return "FAILED: Could not extract frames from video"
            
            return _validate_with_vision(frames, task_description, app_context, action_context)
            
        else:
            return f"FAILED: Unsupported file type: {path.suffix}"
            
    except Exception as e:
        return f"FAILED: Validation error - {str(e)}"


@tool
def verify_screen(expected_screen: str, expected_description: str) -> str:
    """
    Verify current simulator screen matches expectation BEFORE capturing.
    Takes a temporary screenshot and checks if we're on the right screen.
    
    Use this after navigation to confirm you reached the target screen
    before wasting a capture attempt.
    
    Args:
        expected_screen: Name of expected screen (e.g., "Closet", "Settings")
        expected_description: What should be visible (e.g., "grid of clothing items")
    
    Returns:
        "VERIFIED: [what was seen]" or "WRONG_SCREEN: [what was actually seen]"
    """
    import tempfile
    import time
    from pathlib import Path
    
    # Take temp screenshot
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        temp_path = f.name
    
    result = subprocess.run(
        ["xcrun", "simctl", "io", "booted", "screenshot", temp_path],
        capture_output=True, timeout=10, env=_SUBPROCESS_ENV
    )
    
    if result.returncode != 0:
        return f"ERROR: Could not take screenshot - {result.stderr.decode()}"
    
    temp_file = Path(temp_path)
    if not temp_file.exists():
        return "ERROR: Screenshot file not created"
    
    try:
        model = get_model()
        img_data = _encode_image(temp_file)
        
        content = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_data}"}
            },
            {
                "type": "text",
                "text": f"""Describe what screen this iOS app is showing.

EXPECTED: {expected_screen}
SHOULD SHOW: {expected_description}

Respond in ONE line:
- If it matches: "VERIFIED: [brief description of what you see]"
- If it doesn't match: "WRONG_SCREEN: This appears to be [actual screen] showing [what you see]"
"""
            }
        ]
        
        response = model.invoke([HumanMessage(content=content)])
        
        # Handle both string and list response content (Gemini with include_thoughts=True returns list)
        response_content = response.content
        if isinstance(response_content, list):
            # Extract text from content blocks
            text_parts = []
            for block in response_content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            response_content = "\n".join(text_parts)
        
        return response_content.strip() if response_content else "ERROR: Empty response from model"
        
    finally:
        temp_file.unlink(missing_ok=True)


@tool
def get_recording_action_log(video_path: str) -> str:
    """
    Read the action log for a recording (if available).
    
    Action logs are created automatically when using start_recording/stop_recording.
    They contain timestamps of all tap/swipe/type actions during recording.
    """
    path = Path(video_path)
    action_log_path = path.with_suffix(".actions.json")
    
    if not action_log_path.exists():
        return f"No action log found for {video_path}"
    
    try:
        with open(action_log_path) as f:
            return f.read()
    except Exception as e:
        return f"ERROR reading action log: {str(e)}"
