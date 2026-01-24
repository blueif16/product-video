"""
Editor State Loader

Load EditorState from database for standalone execution,
or create test states for development without DB.

## Simplification: Dimensions in Description

Asset metadata (width, height, capture_type) is now baked into the description:
    "Dashboard view [1920×1080, screenshot]"

Why? The model reads text. Separate fields vs. embedded text are identical to an LLM.
This avoids schema changes and keeps everything in one place.

## Text-Only Videos

Videos with no captured assets are valid (text-only promos).
The loader returns an empty assets list, and the planner creates text-only clips.
"""
from typing import Optional
from .state import EditorState
import subprocess
import os


def get_image_dimensions(path: str) -> tuple[int, int]:
    """
    Get image dimensions using file command or sips (macOS).
    Returns (width, height) or (0, 0) if unable to determine.
    """
    if not path or not os.path.exists(path):
        return (0, 0)
    
    try:
        # Use sips on macOS for reliable dimension extraction
        result = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout
        
        width = 0
        height = 0
        for line in output.split("\n"):
            if "pixelWidth" in line:
                width = int(line.split(":")[-1].strip())
            elif "pixelHeight" in line:
                height = int(line.split(":")[-1].strip())
        
        return (width, height)
    except Exception:
        # Fallback: assume standard sizes based on capture type
        return (0, 0)


def format_asset_description(
    description: str,
    capture_type: str,
    width: int = 0,
    height: int = 0,
) -> str:
    """
    Append dimensions and type to description if not already present.
    
    Input:  "Dashboard with task list"
    Output: "Dashboard with task list [1920×1080, screenshot]"
    
    The model reads this naturally - no need for separate fields.
    """
    # Check if already formatted (contains dimension pattern)
    if "[" in description and "×" in description:
        return description
    
    # Build the suffix
    parts = []
    if width > 0 and height > 0:
        parts.append(f"{width}×{height}")
    if capture_type:
        parts.append(capture_type)
    
    if parts:
        suffix = f" [{', '.join(parts)}]"
        return description.rstrip() + suffix
    
    return description


def load_editor_state(video_project_id: str) -> EditorState:
    """
    Load all context needed for editor phase from database.
    
    Requires:
    - video_projects row with status='aggregated'
    - capture_tasks rows with status='success' (optional for text-only)
    
    Text-only videos are valid - they have no captured assets.
    The planner will create text-only clips based on user_input.
    
    Raises:
        ValueError: If project not found or not ready for editing
    """
    from db.supabase_client import get_client
    
    client = get_client()
    
    # Load project
    result = client.table("video_projects").select("*").eq(
        "id", video_project_id
    ).single().execute()
    
    project = result.data
    if not project:
        raise ValueError(f"Project {video_project_id} not found")
    
    if project["status"] != "aggregated":
        raise ValueError(
            f"Project status is '{project['status']}', expected 'aggregated'. "
            "Run capture phase first."
        )
    
    # Load successful captures for THIS project only (may be empty for text-only videos)
    captures_result = client.table("capture_tasks").select("*").eq(
        "video_project_id", video_project_id
    ).eq(
        "status", "success"
    ).execute()
    
    captures = captures_result.data or []
    
    assets = []
    for c in captures:
        path = c["asset_path"]
        url = c.get("asset_url")  # Cloud URL (preferred)
        description = c["task_description"]
        capture_type = c["capture_type"]
        
        # Try to get actual dimensions from file (if local path exists)
        width, height = get_image_dimensions(path) if path else (0, 0)
        
        # Default dimensions if file not found
        if width == 0 and height == 0:
            if capture_type == "screenshot":
                width, height = 1170, 2532  # iPhone 14 Pro
            elif capture_type == "recording":
                width, height = 1170, 2532  # Assume same
        
        # Bake dimensions into description
        formatted_desc = format_asset_description(
            description,
            capture_type,
            width,
            height,
        )
        
        # Cloud-first: include both path and URL, prefer URL for rendering
        assets.append({
            "id": c["id"],
            "path": path,
            "url": url,  # Cloud URL when available
            "description": formatted_desc,
        })
    
    # NOTE: Empty assets is valid for text-only videos
    # The planner will create text-only clips using user_input as guidance
    if not assets:
        print("   ℹ️  No captured assets - this is a text-only video")
    else:
        print(f"   Loaded {len(assets)} assets")
    
    return EditorState(
        video_project_id=video_project_id,
        user_input=project["user_input"],
        analysis_summary=project.get("analysis_summary", ""),
        assets=assets,  # May be empty for text-only
        edit_plan_summary=None,
        clip_task_ids=[],
        clip_specs=[],
        generated_asset_ids=[],
        pending_clip_task_ids=None,
        current_clip_index=None,
        video_spec=None,
        video_spec_id=None,
        # Music generation fields
        music_analysis=None,
        composition_plan=None,
        refined_composition_plan=None,
        audio_path=None,
        # Render outputs
        render_status=None,
        render_path=None,
        render_error=None,
        # Final outputs (video + audio muxed)
        final_video_path=None,
        mux_error=None,
    )


def create_test_state(
    video_project_id: str = "test-project-001",
    user_input: str = "30s energetic promo for my task management app FocusFlow",
    analysis_summary: str = "Focus on quick task entry, smooth swipe gestures, and the focus timer feature. Target audience: productivity enthusiasts on Product Hunt.",
    assets: Optional[list[dict]] = None,
    text_only: bool = False,
) -> EditorState:
    """
    Create a mock EditorState for testing without database.
    
    Args:
        video_project_id: Test project ID
        user_input: What the user wants
        analysis_summary: Analysis context
        assets: Custom assets list (overrides defaults)
        text_only: If True, return empty assets list
    
    Test assets have dimensions baked into description:
        "Main dashboard showing task list [1170×2532, screenshot]"

    Usage:
        from editor.core.loader import create_test_state
        state = create_test_state()
        # Text-only test:
        state = create_test_state(text_only=True)
    """
    # For text-only tests, return empty assets
    if text_only:
        return EditorState(
            video_project_id=video_project_id,
            user_input=user_input,
            analysis_summary=analysis_summary,
            assets=[],  # Empty for text-only
            edit_plan_summary=None,
            clip_task_ids=[],
            clip_specs=[],
            generated_asset_ids=[],
            pending_clip_task_ids=None,
            current_clip_index=None,
            video_spec=None,
            video_spec_id=None,
            # Music generation fields
            music_analysis=None,
            composition_plan=None,
            refined_composition_plan=None,
            audio_path=None,
            # Render outputs
            render_status=None,
            render_path=None,
            render_error=None,
            # Final outputs (video + audio muxed)
            final_video_path=None,
            mux_error=None,
        )
    
    # Default assets with dimensions in description (the new format)
    # Note: url=None for test assets (no cloud upload in test mode)
    default_assets = [
        {
            "id": "asset-001",
            "path": "/assets/captures/dashboard.png",
            "url": None,  # No cloud URL in test mode
            "description": "Main dashboard showing task list with 5 sample tasks, clean UI [1170×2532, screenshot]",
        },
        {
            "id": "asset-002",
            "path": "/assets/captures/quick_add.png",
            "url": None,
            "description": "Quick task entry modal with keyboard visible, placeholder text 'Add a task...' [1170×2532, screenshot]",
        },
        {
            "id": "asset-003",
            "path": "/assets/captures/swipe_complete.mov",
            "url": None,
            "description": "2-second recording of swipe-to-complete gesture on a task [1170×2532, recording]",
        },
        {
            "id": "asset-004",
            "path": "/assets/captures/focus_timer.png",
            "url": None,
            "description": "Focus timer screen showing 25:00 countdown with calming purple gradient [1170×2532, screenshot]",
        },
        {
            "id": "asset-005",
            "path": "/assets/captures/completed_tasks.png",
            "url": None,
            "description": "Completed tasks view showing checked-off items with subtle strikethrough [1170×2532, screenshot]",
        },
    ]
    
    return EditorState(
        video_project_id=video_project_id,
        user_input=user_input,
        analysis_summary=analysis_summary,
        assets=assets or default_assets,
        edit_plan_summary=None,
        clip_task_ids=[],
        clip_specs=[],
        generated_asset_ids=[],
        pending_clip_task_ids=None,
        current_clip_index=None,
        video_spec=None,
        video_spec_id=None,
        # Music generation fields
        music_analysis=None,
        composition_plan=None,
        refined_composition_plan=None,
        audio_path=None,
        # Render outputs
        render_status=None,
        render_path=None,
        render_error=None,
        # Final outputs (video + audio muxed)
        final_video_path=None,
        mux_error=None,
    )


def load_or_create_state(
    video_project_id: Optional[str] = None,
    test_mode: bool = False,
    text_only: bool = False,
) -> EditorState:
    """
    Convenience function: load from DB or create test state.
    
    Args:
        video_project_id: If provided and not test_mode, loads from DB
        test_mode: If True, creates test state regardless of project_id
        text_only: If test_mode and text_only, creates empty assets
    """
    if test_mode:
        return create_test_state(
            video_project_id=video_project_id or "test-project",
            text_only=text_only,
        )
    
    if not video_project_id:
        raise ValueError("video_project_id required when not in test_mode")
    
    return load_editor_state(video_project_id)
