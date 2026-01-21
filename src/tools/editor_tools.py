"""
Editor Tools

Tools for the edit planner and clip composer.
All state changes go through tools (no parsing LLM output).

## Key Changes (Layer-Based Architecture)

1. Removed text_task tools - text is now a layer within clips
2. submit_clip_spec now accepts a layers array
3. Added generate_enhanced_image for AI image generation
4. Clips are self-contained "moments" with multiple layers
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
) -> str:
    """
    Create a clip task - a "moment" in the video timeline.
    
    This is your creative unit. Put ALL your vision in composer_notes:
    - What feeling/energy should this moment have?
    - Should the original asset be enhanced with AI generation?
    - Should there be text overlays? What text, what style?
    - Should there be transitions between visual versions?
    - How should elements be animated/composed?
    
    The composer will interpret your notes and decide what layers to create:
    - Image layers (the original asset)
    - Generated image layers (AI-enhanced versions)
    - Text layers (typography, callouts)
    
    Args:
        asset_path: Path to the main screenshot/recording
        start_time_s: When this moment starts in the video (seconds)
        duration_s: How long this moment lasts (seconds)
        composer_notes: Your FULL creative vision for this moment
    
    Returns:
        Task ID
    
    Example composer_notes:
    
    "Hero moment - make this feel magical. Start with the plain dashboard,
    then crossfade to an AI-enhanced version with subtle glow effects.
    Add 'NEVER FORGET' text that types in dramatically at 0.5s.
    Slow zoom towards the task counter. Calm, confident energy."
    
    "Quick feature flash - energetic. Use the screenshot as-is but add
    bold 'SWIPE' text that slides in from the left. Fast zoom in.
    No fancy enhancements, just raw energy."
    """
    from db.supabase_client import get_client
    
    video_project_id = state.get("video_project_id")
    if not video_project_id:
        return "ERROR: No video_project_id in state"
    
    client = get_client()
    
    task_data = {
        "video_project_id": video_project_id,
        "asset_path": asset_path,
        "start_time_s": start_time_s,
        "duration_s": duration_s,
        "composer_notes": composer_notes,
        "status": "pending",
    }
    
    result = client.table("clip_tasks").insert(task_data).execute()
    
    if result.data:
        task_id = result.data[0]["id"]
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
    source_asset_path: Optional[str] = None,
    state: Annotated[dict, InjectedState] = None,
) -> str:
    """
    Generate an AI-enhanced image for use as a layer in the clip.
    
    Use this when you want to create visual enhancements:
    - Add glow/atmosphere to a screenshot
    - Create artistic variations
    - Generate background effects
    - Create transition frames
    
    The generated image will be stored and can be referenced as a layer.
    
    Args:
        task_id: The clip task ID this image belongs to
        prompt: Detailed prompt for the image generation
               Be specific about style, colors, effects
        source_asset_path: Optional - path to source image to enhance
                          If provided, the generation can reference it
    
    Returns:
        Generated asset ID and path
    
    Examples:
        "A glowing, ethereal version of a task management dashboard.
         Soft purple and blue ambient lighting. Dreamy atmosphere.
         Clean UI elements with subtle glow effects around buttons."
        
        "Abstract flowing gradient background in purple and teal.
         Smooth transitions. Premium SaaS aesthetic. No text."
    """
    from db.supabase_client import get_client
    import asyncio
    
    # Note: In production, this would call the image generation MCP
    # For now, we create a placeholder record
    
    video_project_id = state.get("video_project_id") if state else None
    
    client = get_client()
    
    # Create a record for the generated asset
    asset_data = {
        "video_project_id": video_project_id,
        "clip_task_id": task_id,
        "source_asset_path": source_asset_path,
        "prompt": prompt,
        "status": "pending",
        "generation_model": "gemini-3-pro-image-preview",
    }
    
    result = client.table("generated_assets").insert(asset_data).execute()
    
    if result.data:
        asset_id = result.data[0]["id"]
        
        # TODO: Actually call image generation MCP here
        # For now, mark as pending - actual generation happens separately
        
        print(f"   🎨 Generation requested: {prompt[:50]}...")
        return f"Generated asset {asset_id} - generation pending"
    else:
        return "ERROR: Failed to create generated asset record"


@tool
def submit_clip_spec(
    task_id: str,
    layers_json: str,
    enter_transition_type: Optional[str] = None,
    enter_transition_frames: int = 15,
    exit_transition_type: Optional[str] = None,
    exit_transition_frames: int = 15,
    notes: str = "",
) -> str:
    """
    Submit the complete layer-based specification for a clip.
    
    A clip can have multiple layers that composite together:
    - Image layers (original assets)
    - Generated image layers (AI-enhanced)
    - Text layers (typography)
    
    Args:
        task_id: The clip task ID
        layers_json: JSON array of layers. Each layer has:
        
            Image layer:
            {
                "type": "image",
                "src": "path/to/asset.png",
                "zIndex": 1,
                "transform": {
                    "type": "zoom_in",  // static, ken_burns, zoom_in, zoom_out, pan
                    "startScale": 1.0,
                    "endScale": 1.2,
                    "startX": 0, "endX": 5,
                    "startY": 0, "endY": -3,
                    "easing": "ease_out"  // spring, ease_out, ease_in_out, linear
                },
                "opacity": {"start": 1, "end": 1},
                "deviceFrame": {"type": "iphone_15", "shadow": true}  // optional
            }
            
            Generated image layer:
            {
                "type": "generated_image",
                "generatedAssetId": "uuid-from-generate-tool",
                "src": "path/to/generated.png",  // filled after generation
                "zIndex": 2,
                "transform": {...},
                "opacity": {"start": 0, "end": 1}  // fade in the enhanced version
            }
            
            Text layer:
            {
                "type": "text",
                "content": "FOCUS",
                "zIndex": 3,
                "style": {
                    "fontSize": 72,
                    "fontWeight": 800,
                    "color": "#FFFFFF",
                    "fontFamily": "Inter"
                },
                "animation": {
                    "enter": "scale",  // fade, slide_up, slide_down, slide_left, slide_right, scale, typewriter
                    "exit": "fade",
                    "enterDurationFrames": 12,
                    "exitDurationFrames": 10
                },
                "position": {
                    "preset": "center"  // center, top, bottom, top-left, etc.
                    // OR "x": 50, "y": 40 for custom positioning
                },
                "startFrame": 15,  // relative to clip start
                "durationFrames": 30
            }
        
        enter_transition_type: fade | slide | wipe | zoom | None
        enter_transition_frames: Duration of enter transition
        exit_transition_type: Same options
        exit_transition_frames: Duration of exit transition
        notes: Your reasoning for this composition
    
    Returns:
        Confirmation message
    """
    from db.supabase_client import get_client
    
    client = get_client()
    
    # Parse the layers JSON
    try:
        layers = json.loads(layers_json)
        if not isinstance(layers, list):
            return "ERROR: layers_json must be a JSON array"
    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON in layers_json: {e}"
    
    # Get the task to know duration
    task_result = client.table("clip_tasks").select("duration_s").eq("id", task_id).single().execute()
    if not task_result.data:
        return f"ERROR: Task {task_id} not found"
    
    duration_s = task_result.data["duration_s"]
    fps = 30
    duration_frames = int(duration_s * fps)
    
    # Build the clip spec
    clip_spec = {
        "durationFrames": duration_frames,
        "layers": layers,
        "composerNotes": notes,
    }
    
    if enter_transition_type:
        clip_spec["enterTransition"] = {
            "type": enter_transition_type,
            "durationFrames": enter_transition_frames,
        }
    
    if exit_transition_type:
        clip_spec["exitTransition"] = {
            "type": exit_transition_type,
            "durationFrames": exit_transition_frames,
        }
    
    # Update the task
    result = client.table("clip_tasks").update({
        "clip_spec": clip_spec,
        "status": "composed",
    }).eq("id", task_id).execute()
    
    if result.data:
        layer_summary = ", ".join([f"{l.get('type', 'unknown')}" for l in layers])
        print(f"   ✓ Clip spec submitted: [{layer_summary}]")
        return f"Clip spec submitted for task {task_id} with {len(layers)} layers"
    else:
        return f"ERROR: Failed to update clip task {task_id}"


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
