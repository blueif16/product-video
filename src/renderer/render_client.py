"""
Remotion Render Client

Python interface for calling the Remotion TypeScript renderer.
"""
import subprocess
import os
import json
from typing import Optional
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

# Path to Remotion project (relative to productvideo root)
REMOTION_PROJECT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "remotion"
)

# Output directory for rendered videos
RENDERS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "assets", "renders"
)

# Specs directory (where VideoSpec JSON files are saved)
SPECS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "assets", "specs"
)


# ─────────────────────────────────────────────────────────────
# Render Functions
# ─────────────────────────────────────────────────────────────

def render_video(
    video_spec: dict,
    output_filename: str,
    composition_id: str = "ProductVideo",
    codec: str = "h264",
    crf: int = 18,
) -> tuple[bool, str, Optional[str]]:
    """
    Render a video using Remotion.
    
    Args:
        video_spec: The VideoSpec dict to render
        output_filename: Output filename (e.g., "promo-v1.mp4")
        composition_id: Remotion composition ID
        codec: Video codec (h264, h265, vp8, vp9, prores)
        crf: Constant rate factor (0-51, lower = better quality)
    
    Returns:
        (success, output_path, error_message)
    """
    # Ensure directories exist
    os.makedirs(RENDERS_DIR, exist_ok=True)
    os.makedirs(SPECS_DIR, exist_ok=True)
    
    # Save spec to temp file
    spec_path = os.path.join(SPECS_DIR, f"_render_{output_filename}.json")
    with open(spec_path, "w") as f:
        json.dump(video_spec, f, indent=2)
    
    output_path = os.path.join(RENDERS_DIR, output_filename)
    
    # Check if Remotion project exists
    if not os.path.exists(REMOTION_PROJECT_PATH):
        return (
            False,
            "",
            f"Remotion project not found at {REMOTION_PROJECT_PATH}. "
            "Run 'npx create-video@latest' to create it."
        )
    
    # Build the render command
    # Using npx to run the render script
    cmd = [
        "npx",
        "tsx",
        os.path.join(REMOTION_PROJECT_PATH, "scripts", "render.ts"),
        "--spec", spec_path,
        "--output", output_path,
        "--composition", composition_id,
        "--codec", codec,
        "--crf", str(crf),
    ]
    
    print(f"\n🎬 Starting Remotion render...")
    print(f"   Spec: {spec_path}")
    print(f"   Output: {output_path}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=REMOTION_PROJECT_PATH,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )
        
        if result.returncode == 0:
            # Clean up temp spec file
            os.remove(spec_path)
            return (True, output_path, None)
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            return (False, "", error_msg)
            
    except subprocess.TimeoutExpired:
        return (False, "", "Render timed out after 10 minutes")
    except FileNotFoundError:
        return (
            False,
            "",
            "npx not found. Ensure Node.js is installed and in PATH."
        )
    except Exception as e:
        return (False, "", str(e))


def render_still(
    video_spec: dict,
    output_filename: str,
    frame: int = 0,
    composition_id: str = "ProductVideo",
) -> tuple[bool, str, Optional[str]]:
    """
    Render a single frame as an image (for thumbnails).
    
    Args:
        video_spec: The VideoSpec dict
        output_filename: Output filename (e.g., "thumbnail.png")
        frame: Which frame to render
        composition_id: Remotion composition ID
    
    Returns:
        (success, output_path, error_message)
    """
    os.makedirs(RENDERS_DIR, exist_ok=True)
    os.makedirs(SPECS_DIR, exist_ok=True)
    
    spec_path = os.path.join(SPECS_DIR, f"_still_{output_filename}.json")
    with open(spec_path, "w") as f:
        json.dump(video_spec, f, indent=2)
    
    output_path = os.path.join(RENDERS_DIR, output_filename)
    
    cmd = [
        "npx",
        "remotion",
        "still",
        composition_id,
        output_path,
        "--props", spec_path,
        "--frame", str(frame),
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=REMOTION_PROJECT_PATH,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode == 0:
            os.remove(spec_path)
            return (True, output_path, None)
        else:
            return (False, "", result.stderr or "Unknown error")
            
    except Exception as e:
        return (False, "", str(e))


def check_remotion_available() -> tuple[bool, str]:
    """
    Check if Remotion is properly set up.
    
    Returns:
        (is_available, message)
    """
    if not os.path.exists(REMOTION_PROJECT_PATH):
        return (
            False,
            f"Remotion project not found at {REMOTION_PROJECT_PATH}"
        )
    
    package_json = os.path.join(REMOTION_PROJECT_PATH, "package.json")
    if not os.path.exists(package_json):
        return (False, "package.json not found in Remotion project")
    
    # Check for render script
    render_script = os.path.join(REMOTION_PROJECT_PATH, "scripts", "render.ts")
    if not os.path.exists(render_script):
        return (
            False,
            f"Render script not found at {render_script}. "
            "Create it to enable rendering."
        )
    
    return (True, "Remotion is available")


# ─────────────────────────────────────────────────────────────
# LangGraph Node
# ─────────────────────────────────────────────────────────────

def remotion_render_node(state: dict) -> dict:
    """
    LangGraph node: Render the video using Remotion.
    """
    from db.supabase_client import get_client
    
    video_spec = state.get("video_spec")
    video_project_id = state.get("video_project_id")
    video_spec_id = state.get("video_spec_id")
    
    if not video_spec:
        print("\n⚠️  No video spec to render")
        return {
            "render_status": "failed",
            "render_error": "No video spec provided",
        }
    
    # Check Remotion availability
    available, msg = check_remotion_available()
    if not available:
        print(f"\n⚠️  Remotion not available: {msg}")
        print("   Skipping render. VideoSpec is saved and ready for manual render.")
        return {
            "render_status": "skipped",
            "render_error": msg,
        }
    
    # Generate output filename
    output_filename = f"{video_project_id}.mp4"
    
    # Update status
    client = get_client()
    if video_spec_id:
        client.table("video_specs").update({
            "render_status": "rendering",
            "render_started_at": "now()",
        }).eq("id", video_spec_id).execute()
    
    client.table("video_projects").update({
        "editor_status": "rendering",
    }).eq("id", video_project_id).execute()
    
    # Render
    success, output_path, error = render_video(video_spec, output_filename)
    
    if success:
        print(f"\n✓ Render complete: {output_path}")
        
        # Update DB
        if video_spec_id:
            client.table("video_specs").update({
                "render_status": "complete",
                "render_path": output_path,
                "render_completed_at": "now()",
            }).eq("id", video_spec_id).execute()
        
        client.table("video_projects").update({
            "editor_status": "rendered",
        }).eq("id", video_project_id).execute()
        
        return {
            "render_status": "complete",
            "render_path": output_path,
        }
    else:
        print(f"\n❌ Render failed: {error}")
        
        if video_spec_id:
            client.table("video_specs").update({
                "render_status": "failed",
                "render_error": error,
            }).eq("id", video_spec_id).execute()
        
        return {
            "render_status": "failed",
            "render_error": error,
        }
