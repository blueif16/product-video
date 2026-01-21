"""
Validation tool with independent multimodal LLM call.
This is a TOOL, not an agent. Fresh context per validation.
"""
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
import subprocess
import base64
from pathlib import Path
from config import get_model


def _encode_image(image_path: Path) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def _extract_frames_from_video(video_path: Path, timestamps_ms: list[int] = None) -> list[Path]:
    """
    Extract frames from video at specified timestamps.
    If no timestamps, extracts at 1fps for coverage.
    Returns list of extracted frame paths.
    """
    output_dir = video_path.parent / f"{video_path.stem}_frames"
    output_dir.mkdir(exist_ok=True)
    
    extracted = []
    
    if timestamps_ms:
        # Extract at specific timestamps
        for i, ts in enumerate(timestamps_ms):
            seconds = ts / 1000
            output_path = output_dir / f"frame_{i:03d}_{ts}ms.png"
            subprocess.run([
                "ffmpeg", "-y", "-ss", str(seconds),
                "-i", str(video_path),
                "-frames:v", "1",
                str(output_path)
            ], capture_output=True, timeout=30)
            if output_path.exists():
                extracted.append(output_path)
    else:
        # Extract at 1fps
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", "fps=1",
            str(output_dir / "frame_%03d.png")
        ], capture_output=True, timeout=60)
        extracted = sorted(output_dir.glob("frame_*.png"))
    
    return extracted


def _validate_with_vision(image_paths: list[Path], task_description: str) -> str:
    """
    Core validation logic. Sends images to multimodal LLM.
    Returns text response (success statement or failure reason).
    """
    model = get_model()
    
    # Build content with images for Gemini
    content = []
    for img_path in image_paths[:10]:  # Limit to 10 images
        img_data = _encode_image(img_path)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_data}"}
        })
    
    # Add the text prompt
    content.append({
        "type": "text",
        "text": f"""Analyze these frames from an iOS app capture.

TASK CONTEXT:
{task_description}

INSTRUCTIONS:
1. First, describe what you see in each frame objectively
2. Note any issues: loading spinners, error states, partial renders, system overlays, blurry frames, cut-off content
3. Based on the task description, determine if this capture is usable for a marketing video

Respond in this format:

OBSERVATIONS:
[What you see in the frames]

ISSUES FOUND:
[Any problems, or "None" if clean]

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
    action_timestamps_ms: str = ""
) -> str:
    """
    Validate a captured screenshot or recording against task criteria.
    Uses independent multimodal LLM call with fresh context.
    
    Args:
        asset_path: Path to screenshot (.png) or recording (.mov)
        task_description: The full task description including what to capture and validation criteria
        action_timestamps_ms: Comma-separated timestamps in ms to extract frames (for videos). 
                             Leave empty for automatic 1fps extraction.
    
    Returns:
        Text response: either "SUCCESS: ..." or "FAILED: ..."
    """
    path = Path(asset_path)
    
    if not path.exists():
        return f"FAILED: Asset file not found: {asset_path}"
    
    try:
        if path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            # Screenshot - validate directly
            return _validate_with_vision([path], task_description)
            
        elif path.suffix.lower() in [".mov", ".mp4"]:
            # Video - extract frames first
            timestamps = None
            if action_timestamps_ms:
                timestamps = [int(t.strip()) for t in action_timestamps_ms.split(",")]
            
            frames = _extract_frames_from_video(path, timestamps)
            
            if not frames:
                return "FAILED: Could not extract frames from video"
            
            return _validate_with_vision(frames, task_description)
            
        else:
            return f"FAILED: Unsupported file type: {path.suffix}"
            
    except Exception as e:
        return f"FAILED: Validation error - {str(e)}"
