"""
Supabase client. Schema defined in migrations/001_initial_schema.sql

API Key Usage:
- This module uses the SECRET key (sb_secret_...) by default
- The secret key bypasses RLS for full database access
- For RLS-respecting operations, pass elevated=False to get_supabase()
"""
from supabase import create_client, Client
from config import Config
from typing import Optional


def get_supabase(elevated: bool = True) -> Client:
    """
    Get Supabase client with appropriate API key.

    Args:
        elevated: If True, use secret key (bypasses RLS, full access).
                 If False, use publishable key (respects RLS).

    Returns:
        Supabase Client instance
    """
    api_key = Config.get_supabase_key(elevated=elevated)
    return create_client(Config.SUPABASE_URL, api_key)


# Alias for backward compatibility
get_client = get_supabase


# ─────────────────────────────────────────────────────────────
# Video Project Operations
# ─────────────────────────────────────────────────────────────

def create_video_project(
    user_input: str,
    project_path: str,
    app_bundle_id: str,
    analysis_summary: str
) -> str:
    """
    Create a video project with full context.
    Called by Analyzer after it completes its analysis.
    Returns project ID.
    """
    db = get_supabase()
    result = db.table("video_projects").insert({
        "user_input": user_input,
        "project_path": project_path,
        "app_bundle_id": app_bundle_id,
        "analysis_summary": analysis_summary,
        "status": "analyzed"
    }).execute()
    return result.data[0]["id"]


def update_video_project_status(project_id: str, status: str) -> None:
    """Update video project status: 'analyzed', 'capturing', 'aggregated'"""
    db = get_supabase()
    db.table("video_projects").update({
        "status": status,
        "updated_at": "now()"
    }).eq("id", project_id).execute()


def get_video_project(project_id: str) -> Optional[dict]:
    """Get video project by ID."""
    db = get_supabase()
    result = db.table("video_projects").select("*").eq("id", project_id).single().execute()
    return result.data


def delete_video_project(project_id: str) -> bool:
    """Delete a video project by ID. Returns True if deleted."""
    try:
        db = get_supabase()
        db.table("video_projects").delete().eq("id", project_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting video project: {e}")
        return False


# ─────────────────────────────────────────────────────────────
# Capture Task Operations
# ─────────────────────────────────────────────────────────────

def create_task(
    app_bundle_id: str,
    task_description: str,
    capture_type: str
) -> str:
    """Create a capture task. Returns task ID."""
    db = get_supabase()
    result = db.table("capture_tasks").insert({
        "app_bundle_id": app_bundle_id,
        "task_description": task_description,
        "capture_type": capture_type,
        "status": "pending"
    }).execute()
    return result.data[0]["id"]


def get_task(task_id: str) -> dict:
    """Get task by ID."""
    db = get_supabase()
    result = db.table("capture_tasks").select("*").eq("id", task_id).single().execute()
    return result.data


def update_task_status(
    task_id: str, 
    status: str, 
    asset_path: Optional[str] = None,
    validation_notes: Optional[str] = None
) -> None:
    """Update task status: 'pending', 'success', 'failed'"""
    db = get_supabase()
    update_data = {"status": status, "updated_at": "now()"}
    if asset_path:
        update_data["asset_path"] = asset_path
    if validation_notes:
        update_data["validation_notes"] = validation_notes
    db.table("capture_tasks").update(update_data).eq("id", task_id).execute()


def increment_attempt(task_id: str) -> int:
    """Increment attempt count, return new count."""
    db = get_supabase()
    task = get_task(task_id)
    new_count = task["attempt_count"] + 1
    db.table("capture_tasks").update({
        "attempt_count": new_count,
        "updated_at": "now()"
    }).eq("id", task_id).execute()
    return new_count


def get_pending_tasks(app_bundle_id: str) -> list[dict]:
    """Get all pending tasks for an app."""
    db = get_supabase()
    result = db.table("capture_tasks").select("*").eq(
        "app_bundle_id", app_bundle_id
    ).eq("status", "pending").execute()
    return result.data


def get_successful_tasks(app_bundle_id: str) -> list[dict]:
    """Get all successful captures for an app."""
    db = get_supabase()
    result = db.table("capture_tasks").select("*").eq(
        "app_bundle_id", app_bundle_id
    ).eq("status", "success").execute()
    return result.data


def get_all_tasks(app_bundle_id: str) -> list[dict]:
    """Get all tasks for an app (any status)."""
    db = get_supabase()
    result = db.table("capture_tasks").select("*").eq(
        "app_bundle_id", app_bundle_id
    ).execute()
    return result.data


def delete_task(task_id: str) -> bool:
    """Delete a capture task by ID. Returns True if deleted."""
    try:
        db = get_supabase()
        db.table("capture_tasks").delete().eq("id", task_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting task: {e}")
        return False


def delete_tasks_by_ids(task_ids: list[str]) -> int:
    """Delete multiple capture tasks by IDs. Returns count deleted."""
    if not task_ids:
        return 0
    try:
        db = get_supabase()
        db.table("capture_tasks").delete().in_("id", task_ids).execute()
        return len(task_ids)
    except Exception as e:
        print(f"Error deleting tasks: {e}")
        return 0


def delete_tasks_by_bundle_id(app_bundle_id: str) -> int:
    """Delete all capture tasks for an app. Returns count deleted."""
    try:
        db = get_supabase()
        # First get count
        tasks = get_all_tasks(app_bundle_id)
        count = len(tasks)
        if count > 0:
            db.table("capture_tasks").delete().eq("app_bundle_id", app_bundle_id).execute()
        return count
    except Exception as e:
        print(f"Error deleting tasks: {e}")
        return 0


# ─────────────────────────────────────────────────────────────
# Session Cleanup (for graceful shutdown)
# ─────────────────────────────────────────────────────────────

def cleanup_session(video_project_id: Optional[str], task_ids: list[str]) -> dict:
    """
    Clean up all records created during a session.
    
    Args:
        video_project_id: The video project to delete (if any)
        task_ids: List of task IDs to delete
    
    Returns:
        Dict with counts of deleted records
    """
    deleted = {"video_project": False, "tasks": 0}
    
    # Delete tasks first (might have foreign key constraints)
    if task_ids:
        deleted["tasks"] = delete_tasks_by_ids(task_ids)
    
    # Delete video project
    if video_project_id:
        deleted["video_project"] = delete_video_project(video_project_id)
    
    return deleted
