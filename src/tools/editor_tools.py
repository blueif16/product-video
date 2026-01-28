"""
Editor Tools

Tools for the edit planner and clip composer.
All state changes go through tools (no parsing LLM output).

## Simplification: Unified Image Type

We removed the distinction between "image" and "generated_image" layers.
Why? The model knows what it generated - it wrote the prompt.
Remotion just needs a src path, it doesn't care about provenance.

generate_enhanced_image now:
- Takes aspect_ratio param (image gen APIs need this)
- Returns just {path} - model doesn't need description back
- Stores prompt in DB for debugging/regeneration
"""
from typing import Annotated, Optional, Any
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
import json
import uuid


# ─────────────────────────────────────────────────────────────
# Planner Tools
# ─────────────────────────────────────────────────────────────

@tool
def create_clip_task(
    asset_path: str,
    start_time_s: float,
    duration_s: float,
    composer_notes: str,
    state: Annotated[dict, InjectedState],
    asset_url: Optional[str] = None,
) -> str:
    """
    Create a clip task - a "moment" in the video timeline.
    
    This is your creative unit. Put ALL your vision in composer_notes:
    - What feeling/energy should this moment have?
    - Should the original asset be enhanced with AI generation?
    - What text, important info is needed to be passed and rendered out in this clip

    The composer will interpret your notes and decide what layers to create:
    - Background layers (for solid colors, gradients, animated orbs)
    - Image layers (original screenshots OR AI-generated images)
    - Text layers (typography, callouts)
    
    Args:
        asset_path: Path to the main screenshot/recording
                   Use "none://text-only" for text-only clips
        start_time_s: When this moment starts in the video (seconds)
        duration_s: How long this moment lasts (seconds)
        composer_notes: Your FULL creative vision for this moment
        asset_url: Cloud URL for the asset (preferred over asset_path)
    
    Returns:
        Task ID
    
    """
    from db.supabase_client import get_client
    
    # Debug: Check if state was properly injected
    video_project_id = state.get("video_project_id") if state else None
    
    if not video_project_id:
        # Detailed error to help debug InjectedState issues
        state_keys = list(state.keys()) if state else []
        print(f"   ❌ ERROR: No video_project_id in state. State keys: {state_keys}")
        return f"ERROR: No video_project_id in state. Available keys: {state_keys}. Make sure the agent is invoked with video_project_id in the state dict."
    
    client = get_client()
    
    task_data = {
        "video_project_id": video_project_id,
        "asset_path": asset_path,
        "asset_url": asset_url,  # Cloud URL (preferred over asset_path)
        "start_time_s": start_time_s,
        "duration_s": duration_s,
        "composer_notes": composer_notes,
        "status": "pending",
    }
    
    result = client.table("clip_tasks").insert(task_data).execute()

    if result.data:
        task_id = result.data[0]["id"]

        # 验证是否真的写入了数据库
        verify = client.table("clip_tasks").select("id").eq("id", task_id).execute()
        if not verify.data:
            return f"ERROR: Task {task_id} was returned by insert but not found in database. Possible transaction/commit issue."

        print(f"   📎 Clip task created: {start_time_s}s-{start_time_s + duration_s}s")
        return f"Created clip task {task_id}"
    else:
        return "ERROR: Failed to create clip task"


@tool
def finalize_edit_plan(
    plan_summary: str,
    total_duration_s: float,
    state: Annotated[dict, InjectedState],
) -> str:
    """
    Finalize the edit plan after creating all clip tasks.
    
    Call this AFTER you've created all your tasks with create_clip_task.
    
    Args:
        plan_summary: Your overall creative vision and reasoning
        total_duration_s: Expected total video duration in seconds
    
    Returns:
        Confirmation with task count
    """
    from db.supabase_client import get_client
    
    video_project_id = state.get("video_project_id")
    if not video_project_id:
        return "ERROR: No video_project_id in state"
    
    client = get_client()
    
    # Count tasks
    clip_count = client.table("clip_tasks").select("id", count="exact").eq(
        "video_project_id", video_project_id
    ).execute().count or 0
    
    # Update project status
    client.table("video_projects").update({
        "editor_status": "planning",
    }).eq("id", video_project_id).execute()
    
    print(f"\n📋 Edit plan finalized:")
    print(f"   {clip_count} clip tasks (moments)")
    print(f"   ~{total_duration_s}s total duration")
    
    return f"Plan finalized: {clip_count} moments, ~{total_duration_s}s"


# ─────────────────────────────────────────────────────────────
# Composer Tools
# ─────────────────────────────────────────────────────────────

@tool
def generate_enhanced_image(
    task_id: str,
    prompt: str,
    aspect_ratio: str = "16:9",
    source_asset_path: Optional[str] = None,
    description: Optional[str] = None,
    state: Annotated[dict, InjectedState] = None,
) -> str:
    """
    Generate an AI-enhanced image for use as a layer.
    
    Use this when you want to create visual enhancements:
    - Add glow/atmosphere to a screenshot
    - Create artistic variations
    - Generate background effects
    - Create transition frames
    
    The generated image is just an image - use it in an ImageLayer.
    You already know what you're generating (you wrote the prompt).
    
    Args:
        task_id: The clip task ID this image belongs to
        prompt: Detailed prompt for the image generation
               Be specific about style, colors, effects
        aspect_ratio: Output aspect ratio. Options:
                     "16:9" - Landscape video (default, 1920x1080)
                     "9:16" - Portrait/mobile
                     "1:1"  - Square
                     "4:3"  - Classic
                     Match the source asset's ratio when enhancing
        source_asset_path: Optional - path to source image to enhance
                          If provided, the generation can reference it
        description: Optional label for storage (defaults to prompt summary)
                    You don't need this back - you know what you asked for
    
    Returns:
        Path to generated image (e.g., "Generated: /path/to/gen_001.png")
        Use this path in your ImageLayer src field.
    
    Examples:
        prompt="A glowing, ethereal version of a task management dashboard.
                Soft purple and blue ambient lighting. Dreamy atmosphere.
                Clean UI elements with subtle glow effects around buttons."
        aspect_ratio="16:9"
        
        prompt="Abstract flowing gradient background in purple and teal.
                Smooth transitions. Premium SaaS aesthetic. No text."
        aspect_ratio="16:9"
    """
    from db.supabase_client import get_client
    from tools.image_gen import generate_enhanced_screenshot
    from tools.storage import is_remote_url
    
    video_project_id = state.get("video_project_id") if state else None
    client = get_client()
    
    # Map aspect_ratio to dimensions (for storage/debugging)
    dimensions_map = {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
        "4:3": (1440, 1080),
    }
    width, height = dimensions_map.get(aspect_ratio, (1920, 1080))
    
    # Store description - defaults to prompt summary if not provided
    stored_description = description or prompt[:100]
    
    # Create a record for the generated asset (status=pending)
    asset_data = {
        "video_project_id": video_project_id,
        "clip_task_id": task_id,
        "source_asset_path": source_asset_path,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "description": f"{stored_description} [{width}×{height}]",
        "status": "pending",
        "generation_model": "gemini-3-pro-image-preview",
    }
    
    result = client.table("generated_assets").insert(asset_data).execute()
    
    if not result.data:
        return "ERROR: Failed to create generated asset record"
    
    asset_id = result.data[0]["id"]
    
    # Resolve source path: if it's a URL, we can't use it as local reference
    # The image gen API needs a local file
    local_source = None
    if source_asset_path and not is_remote_url(source_asset_path):
        local_source = source_asset_path
    
    try:
        print(f"   🎨 Generating ({aspect_ratio}): {prompt[:50]}...")
        
        # Actually generate the image
        gen_result = generate_enhanced_screenshot(
            prompt=prompt,
            source_path=local_source,
            aspect_ratio=aspect_ratio,
            project_id=video_project_id,
        )
        
        local_path = gen_result["local_path"]
        cloud_url = gen_result.get("cloud_url")
        
        # Update the DB record with paths
        update_data = {
            "asset_path": local_path,
            "status": "completed",
        }
        if cloud_url:
            update_data["asset_url"] = cloud_url
        
        client.table("generated_assets").update(update_data).eq("id", asset_id).execute()
        
        # Return the best available path (prefer cloud URL)
        output_path = cloud_url or local_path
        print(f"   ✓ Generated: {output_path[-50:]}")
        
        return f"Generated: {output_path}"
        
    except Exception as e:
        # Update record with error status
        client.table("generated_assets").update({
            "status": "failed",
            "description": f"{stored_description} [ERROR: {str(e)[:100]}]",
        }).eq("id", asset_id).execute()
        
        print(f"   ❌ Generation failed: {e}")
        return f"ERROR: Image generation failed - {str(e)}"


@tool
def submit_clip_spec(
    enter_transition_type: Optional[str] = None,
    enter_transition_frames: int = 15,
    exit_transition_type: Optional[str] = None,
    exit_transition_frames: int = 15,
    background_color: Optional[str] = None,
    notes: str = "",
    state: Annotated[dict, InjectedState] = None,
    # Legacy support - will be deprecated
    task_id: Optional[str] = None,
    layers_json: Optional[str] = None,
) -> str:
    """
    Submit validated clip spec to database. Reads from draft file.

    Args:
        enter_transition_type: fade | slide | slide_left | slide_right | slide_up | slide_down | wipe | none
        enter_transition_frames: Duration (default 15)
        exit_transition_type: Same options as enter
        exit_transition_frames: Duration (default 15)
        background_color: Fallback color (hex, e.g., "#0f172a")
        notes: Composition reasoning

    Returns:
        Confirmation message
    """
    from db.supabase_client import get_client
    from tools.draft_tools import read_draft, get_draft_path
    
    # Get clip_id from state or legacy task_id param
    clip_id = state.get("clip_id") if state else task_id
    if not clip_id:
        return "ERROR: No clip_id in state"
    
    # Try to read from draft file first (new workflow)
    layers = read_draft(clip_id)
    
    # Fall back to legacy layers_json parameter
    if layers is None and layers_json:
        try:
            layers = json.loads(layers_json)
            if not isinstance(layers, list):
                return "ERROR: layers_json must be a JSON array"
        except json.JSONDecodeError as e:
            return f"ERROR: Invalid JSON in layers_json: {e}"
    
    if layers is None:
        return "ERROR: No draft found and no layers_json provided. Call draft_clip_spec first."
    
    client = get_client()
    
    # Get the task to know duration
    task_result = client.table("clip_tasks").select("duration_s").eq("id", clip_id).single().execute()
    if not task_result.data:
        return f"ERROR: Task {clip_id} not found"
    
    duration_s = task_result.data["duration_s"]
    fps = 30
    duration_frames = int(duration_s * fps)
    
    # Build the clip spec
    clip_spec = {
        "durationFrames": duration_frames,
        "layers": layers,
        "composerNotes": notes,
    }
    
    if enter_transition_type and enter_transition_type != "none":
        clip_spec["enterTransition"] = {
            "type": enter_transition_type,
            "durationFrames": enter_transition_frames,
        }
    
    if exit_transition_type and exit_transition_type != "none":
        clip_spec["exitTransition"] = {
            "type": exit_transition_type,
            "durationFrames": exit_transition_frames,
        }
    
    if background_color:
        clip_spec["backgroundColor"] = background_color

    # Update the task
    result = client.table("clip_tasks").update({
        "clip_spec": clip_spec,
        "status": "composed",
    }).eq("id", clip_id).execute()
    
    if result.data:
        layer_types = [l.get('type', 'unknown') for l in layers]
        layer_summary = ", ".join(layer_types)
        print(f"   ✓ Clip spec submitted: [{layer_summary}]")
        
        # Clean up draft file
        draft_path = get_draft_path(clip_id)
        if draft_path.exists():
            draft_path.unlink()
        
        return f"Clip spec submitted for task {clip_id} with {len(layers)} layers: {layer_summary}"
    else:
        return f"ERROR: Failed to update clip task {clip_id}"


# ─────────────────────────────────────────────────────────────
# Helper functions (not tools, for internal use)
# ─────────────────────────────────────────────────────────────

def get_pending_clip_tasks(video_project_id: str) -> list[dict]:
    """Get all pending clip tasks for a project."""
    from db.supabase_client import get_client
    
    client = get_client()
    result = client.table("clip_tasks").select("*").eq(
        "video_project_id", video_project_id
    ).eq(
        "status", "pending"
    ).order("start_time_s").execute()
    
    return result.data or []


def get_composed_clip_specs(video_project_id: str) -> list[dict]:
    """Get all composed clip specs for assembly."""
    from db.supabase_client import get_client
    
    client = get_client()
    result = client.table("clip_tasks").select("*").eq(
        "video_project_id", video_project_id
    ).eq(
        "status", "composed"
    ).order("start_time_s").execute()
    
    return result.data or []


def get_generated_assets(video_project_id: str, status: str = "success") -> list[dict]:
    """Get generated assets for a project."""
    from db.supabase_client import get_client
    
    client = get_client()
    result = client.table("generated_assets").select("*").eq(
        "video_project_id", video_project_id
    ).eq(
        "status", status
    ).execute()
    
    return result.data or []
