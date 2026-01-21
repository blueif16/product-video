"""
Editor State Loader

Load EditorState from database for standalone execution,
or create test states for development without DB.

## Layer-Based Architecture

The loader now creates EditorState without text_task_ids - text overlays
are now layers within clips, not separate tasks.
"""
from typing import Optional
from .state import EditorState


def load_editor_state(video_project_id: str) -> EditorState:
    """
    Load all context needed for editor phase from database.
    
    Requires:
    - video_projects row with status='aggregated'
    - capture_tasks rows with status='success'
    
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
    
    # Load successful captures
    captures_result = client.table("capture_tasks").select("*").eq(
        "video_project_id", video_project_id
    ).eq(
        "status", "success"
    ).execute()
    
    captures = captures_result.data or []
    
    assets = [
        {
            "id": c["id"],
            "path": c["asset_path"],
            "description": c["task_description"],
            "capture_type": c["capture_type"],
            "validation_notes": c.get("validation_notes", ""),
        }
        for c in captures
    ]
    
    if not assets:
        raise ValueError(
            f"No successful captures found for project {video_project_id}. "
            "Check capture_tasks table."
        )
    
    return EditorState(
        video_project_id=video_project_id,
        user_input=project["user_input"],
        analysis_summary=project.get("analysis_summary", ""),
        assets=assets,
        edit_plan_summary=None,
        clip_task_ids=[],
        clip_specs=[],
        generated_asset_ids=[],
        pending_clip_task_ids=None,
        current_clip_index=None,
        video_spec=None,
        video_spec_id=None,
        render_status=None,
        render_path=None,
        render_error=None,
    )


def create_test_state(
    video_project_id: str = "test-project-001",
    user_input: str = "30s energetic promo for my task management app FocusFlow",
    analysis_summary: str = "Focus on quick task entry, smooth swipe gestures, and the focus timer feature. Target audience: productivity enthusiasts on Product Hunt.",
    assets: Optional[list[dict]] = None,
) -> EditorState:
    """
    Create a mock EditorState for testing without database.
    
    Usage:
        from editor.loader import create_test_state
        state = create_test_state()
        # or with custom assets:
        state = create_test_state(assets=[...])
    """
    default_assets = [
        {
            "id": "asset-001",
            "path": "/assets/captures/dashboard.png",
            "description": "Main dashboard showing task list with 5 sample tasks, clean UI",
            "capture_type": "screenshot",
            "validation_notes": "Clean capture, no loading states, good composition",
        },
        {
            "id": "asset-002",
            "path": "/assets/captures/quick_add.png",
            "description": "Quick task entry modal with keyboard visible, placeholder text 'Add a task...'",
            "capture_type": "screenshot",
            "validation_notes": "Modal centered, keyboard visible, input focused",
        },
        {
            "id": "asset-003",
            "path": "/assets/captures/swipe_complete.mov",
            "description": "2-second recording of swipe-to-complete gesture on a task",
            "capture_type": "recording",
            "validation_notes": "Smooth gesture, green checkmark appears, task animates out",
        },
        {
            "id": "asset-004",
            "path": "/assets/captures/focus_timer.png",
            "description": "Focus timer screen showing 25:00 countdown with calming purple gradient",
            "capture_type": "screenshot",
            "validation_notes": "Timer prominent, start button visible, clean layout",
        },
        {
            "id": "asset-005",
            "path": "/assets/captures/completed_tasks.png",
            "description": "Completed tasks view showing checked-off items with subtle strikethrough",
            "capture_type": "screenshot",
            "validation_notes": "Good contrast, completion dates visible",
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
        render_status=None,
        render_path=None,
        render_error=None,
    )


def load_or_create_state(
    video_project_id: Optional[str] = None,
    test_mode: bool = False,
) -> EditorState:
    """
    Convenience function: load from DB or create test state.
    
    Args:
        video_project_id: If provided and not test_mode, loads from DB
        test_mode: If True, creates test state regardless of project_id
    """
    if test_mode:
        return create_test_state(video_project_id=video_project_id or "test-project")
    
    if not video_project_id:
        raise ValueError("video_project_id required when not in test_mode")
    
    return load_editor_state(video_project_id)
