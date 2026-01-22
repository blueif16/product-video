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
    - Background layers (for solid colors, gradients, animated orbs)
    - Image layers (original screenshots OR AI-generated images)
    - Text layers (typography, callouts)
    
    Args:
        asset_path: Path to the main screenshot/recording
                   Use "none://text-only" for text-only clips
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
    
    "Text-only hero - dark gradient background with glowing orbs.
    'STREAMLINE' scales in dramatically, centered.
    Subtitle fades in below after 0.5s. Premium, confident."
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
    
    # Note: In production, this calls the image generation MCP
    # For now, we create a record and return a placeholder path
    
    video_project_id = state.get("video_project_id") if state else None
    
    client = get_client()
    
    # Map aspect_ratio to dimensions (for storage/debugging)
    # The actual generation API uses aspect_ratio directly
    dimensions_map = {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
        "4:3": (1440, 1080),
    }
    width, height = dimensions_map.get(aspect_ratio, (1920, 1080))
    
    # Store description - defaults to prompt summary if not provided
    stored_description = description or prompt[:100]
    
    # Create a record for the generated asset
    # Stores prompt + aspect_ratio for regeneration/debugging
    asset_data = {
        "video_project_id": video_project_id,
        "clip_task_id": task_id,
        "source_asset_path": source_asset_path,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,  # Store for regeneration
        "description": f"{stored_description} [{width}×{height}]",  # Bake in dimensions
        "status": "pending",
        "generation_model": "gemini-3-pro-image-preview",
    }
    
    result = client.table("generated_assets").insert(asset_data).execute()
    
    if result.data:
        asset_id = result.data[0]["id"]
        
        # TODO: Actually call image generation MCP here
        # For now, return a placeholder path
        # Real implementation would:
        # 1. Call MCP with prompt + aspect_ratio
        # 2. Get back the generated image URL/path
        # 3. Update the DB record with asset_url
        # 4. Return that path
        
        placeholder_path = f"/assets/generated/{asset_id}.png"
        
        print(f"   🎨 Generation requested ({aspect_ratio}): {prompt[:50]}...")
        
        # Return just the path - model knows what it asked for
        return f"Generated: {placeholder_path}"
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
    background_color: Optional[str] = None,
    notes: str = "",
) -> str:
    """
    Submit the complete layer-based specification for a clip.
    
    A clip can have multiple layers that composite together:
    - Background layers (solid colors, gradients, animated orbs)
    - Image layers (original assets OR generated images - same type!)
    - Text layers (typography)
    
    NOTE: There's no separate "generated_image" type anymore.
    Generated images are just images with a src path.
    
    Args:
        task_id: The clip task ID
        layers_json: JSON array of layers. Each layer has:
        
            ═══════════════════════════════════════════════════════════
            BACKGROUND LAYER (for text-only clips or custom backgrounds)
            ═══════════════════════════════════════════════════════════
            {
                "type": "background",
                "zIndex": 0,
                "color": "#0f172a",  // Solid color
                "gradient": {"colors": ["#0f172a", "#1e1b4b"], "angle": 180},  // OR gradient
                "orbs": true,  // OR animated glowing orbs
                "orbColors": ["#6366f1", "#ec4899", "#8b5cf6"]  // Custom orb colors
            }
        
            ═══════════════════════════════════════════════════════════
            IMAGE LAYER (screenshots, recordings, OR generated images)
            ═══════════════════════════════════════════════════════════
            {
                "type": "image",
                "src": "path/to/asset.png",  // Captured OR generated path
                "zIndex": 1,
                "transform": {
                    "type": "zoom_in",  // static, ken_burns, zoom_in, zoom_out, pan_left, pan_right, pan_up, pan_down, focus
                    "startScale": 1.0,
                    "endScale": 1.2,
                    "focusX": 50,  // For focus type (% from left)
                    "focusY": 30,  // For focus type (% from top)
                    "intensity": 1.0  // 0.5=subtle, 1.0=normal, 1.5=dramatic
                },
                "opacity": {"start": 1, "end": 1},  // Animate opacity over clip duration
                "device": "iphone"  // none, iphone, iphonePro, macbook, ipad
            }
            
            ═══════════════════════════════════════════════════════════
            TEXT LAYER (typography and callouts)
            ═══════════════════════════════════════════════════════════
            {
                "type": "text",
                "content": "STREAMLINE",
                "zIndex": 3,
                "style": {
                    "fontSize": 80,        // 24-32 caption, 36-48 callout, 56-72 headline, 80-120 hero
                    "fontWeight": 800,     // 400 regular, 600 semibold, 700 bold, 800 extrabold
                    "color": "#FFFFFF",
                    "textAlign": "center", // left, center, right
                    "letterSpacing": "-0.02em",  // Tighter for large text
                    "textShadow": "0 0 60px rgba(99, 102, 241, 0.5)",  // Glow effect
                    "lineHeight": 1.2,     // Line spacing
                    "maxWidth": 800        // Max width in pixels
                },
                "animation": {
                    "enter": "scale",      // fade, typewriter, slide_up, slide_down, slide_left, slide_right, scale, stagger, reveal, none
                    "exit": "fade",        // fade, slide_up, slide_down, scale, none
                    "enterDuration": 20,   // Custom enter duration in frames
                    "exitDuration": 15     // Custom exit duration in frames
                },
                "position": {
                    "preset": "center"     // center, top, bottom, left, right, top_left, top_right, bottom_left, bottom_right
                    // OR custom position:
                    // "x": 50, "y": 40     // Percentage from top-left (50,50 = center)
                },
                "startFrame": 0,           // When text appears (relative to clip start)
                "durationFrames": 90       // How long text is visible
            }
        
        enter_transition_type: fade | slide | slide_left | slide_right | slide_up | slide_down | wipe | none | null
        enter_transition_frames: Duration of enter transition (default 15)
        exit_transition_type: Same options as enter
        exit_transition_frames: Duration of exit transition (default 15)
        background_color: Fallback background color (hex, e.g., "#0f172a")
        notes: Your reasoning for this composition
    
    Returns:
        Confirmation message
        
    ═══════════════════════════════════════════════════════════
    EXAMPLE: Screenshot with AI-enhanced crossfade
    ═══════════════════════════════════════════════════════════
    
    // First call generate_enhanced_image to get the path
    // Then use BOTH as image layers with opacity crossfade:
    
    layers_json = '''[
        {
            "type": "image",
            "src": "/path/to/original.png",
            "zIndex": 1,
            "transform": {"type": "zoom_in", "startScale": 1.0, "endScale": 1.15},
            "opacity": {"start": 1, "end": 0}
        },
        {
            "type": "image",
            "src": "/assets/generated/xxx.png",
            "zIndex": 2,
            "transform": {"type": "zoom_in", "startScale": 1.0, "endScale": 1.15},
            "opacity": {"start": 0, "end": 1}
        },
        {
            "type": "text",
            "content": "FOCUS",
            "zIndex": 3,
            "style": {"fontSize": 80, "fontWeight": 800, "color": "#FFFFFF"},
            "animation": {"enter": "typewriter", "exit": "fade"},
            "position": {"preset": "center"},
            "startFrame": 15,
            "durationFrames": 60
        }
    ]'''
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
    }).eq("id", task_id).execute()
    
    if result.data:
        layer_types = [l.get('type', 'unknown') for l in layers]
        layer_summary = ", ".join(layer_types)
        print(f"   ✓ Clip spec submitted: [{layer_summary}]")
        return f"Clip spec submitted for task {task_id} with {len(layers)} layers: {layer_summary}"
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
