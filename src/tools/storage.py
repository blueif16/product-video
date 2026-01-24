"""
Supabase Storage utilities for cloud asset management.

Cloud-First Architecture:
    1. Capture → Validate → Upload → Store URL in DB
    2. All downstream (composer, assembler, Remotion) reference URL
    3. Local asset_path is kept for fallback/debugging

Usage:
    from tools.storage import upload_asset, upload_and_update_task
    
    # Simple upload
    url = upload_asset("/tmp/screenshot.png", project_id="abc-123")
    
    # Upload and update task in DB
    url = upload_and_update_task(
        local_path="/tmp/screenshot.png",
        task_id="task-uuid",
        project_id="abc-123",
        capture_type="screenshot"
    )
"""
import os
from pathlib import Path
from typing import Optional
import mimetypes

from supabase import create_client, Client
from config import Config


def get_storage_client() -> Client:
    """Get Supabase client for storage operations."""
    return create_client(
        Config.SUPABASE_URL,
        Config.get_supabase_key(elevated=True)
    )


def upload_asset(
    local_path: str,
    project_id: str,
    bucket: str = "captures",
    subfolder: Optional[str] = None,
) -> str:
    """
    Upload a file to Supabase Storage.
    
    Args:
        local_path: Path to local file
        project_id: Video project ID (used as folder)
        bucket: Storage bucket name
        subfolder: Additional subfolder (e.g., "screenshots", "recordings")
    
    Returns:
        Public URL to the uploaded file
    
    Example:
        url = upload_asset("/tmp/screen.png", "abc-123", subfolder="screenshots")
        # -> https://xxx.supabase.co/storage/v1/object/public/captures/abc-123/screenshots/screen.png
    
    Raises:
        FileNotFoundError: If local file doesn't exist
        Exception: On upload failure
    """
    # Validate file exists
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"File not found: {local_path}")
    
    supabase = get_storage_client()
    
    # Build storage path
    filename = Path(local_path).name
    path_parts = [project_id]
    if subfolder:
        path_parts.append(subfolder)
    path_parts.append(filename)
    storage_path = "/".join(path_parts)
    
    # Detect content type
    content_type, _ = mimetypes.guess_type(local_path)
    content_type = content_type or "application/octet-stream"
    
    # Upload
    with open(local_path, "rb") as f:
        result = supabase.storage.from_(bucket).upload(
            storage_path,
            f,
            file_options={"content-type": content_type, "upsert": "true"}
        )
    
    # Get public URL
    public_url = supabase.storage.from_(bucket).get_public_url(storage_path)
    
    return public_url


def upload_and_update_task(
    local_path: str,
    task_id: str,
    project_id: str,
    capture_type: str = "screenshot",
) -> str:
    """
    Upload asset to cloud storage and update capture_task with URL.
    
    This is the primary function for cloud-first asset management.
    Called by capturer after validation passes.
    
    Args:
        local_path: Path to validated local asset
        task_id: capture_tasks.id
        project_id: video_projects.id
        capture_type: "screenshot" or "recording"
    
    Returns:
        Public URL of uploaded asset
    
    Side effects:
        - Uploads file to Supabase Storage
        - Updates capture_tasks.asset_url in database
    """
    from db.supabase_client import get_client  # Fixed import
    
    # Determine subfolder based on type
    subfolder = "recordings" if capture_type == "recording" else "screenshots"
    
    # Upload to cloud
    url = upload_asset(local_path, project_id, subfolder=subfolder)
    
    # Update DB with both local path and cloud URL
    client = get_client()
    client.table("capture_tasks").update({
        "asset_url": url,
        "asset_path": local_path,
    }).eq("id", task_id).execute()
    
    return url


def upload_generated_asset(
    local_path: str,
    generated_asset_id: str,
    project_id: str,
) -> str:
    """
    Upload a generated (AI-enhanced) asset and update generated_assets table.
    
    Args:
        local_path: Path to generated image
        generated_asset_id: generated_assets.id
        project_id: video_projects.id
    
    Returns:
        Public URL
    """
    from db.supabase_client import get_client
    
    # Upload to generated subfolder
    url = upload_asset(local_path, project_id, subfolder="generated")
    
    # Update DB
    client = get_client()
    client.table("generated_assets").update({
        "asset_url": url,
        "asset_path": local_path,
        "status": "completed",
    }).eq("id", generated_asset_id).execute()
    
    return url


def get_project_assets(project_id: str, bucket: str = "captures") -> list[dict]:
    """
    List all assets for a project from storage.
    
    Returns:
        List of {name, url, size, created_at}
    """
    supabase = get_storage_client()
    
    try:
        result = supabase.storage.from_(bucket).list(project_id)
        
        assets = []
        for item in result:
            if item.get("name"):
                url = supabase.storage.from_(bucket).get_public_url(
                    f"{project_id}/{item['name']}"
                )
                assets.append({
                    "name": item["name"],
                    "url": url,
                    "size": item.get("metadata", {}).get("size"),
                    "created_at": item.get("created_at"),
                })
        
        return assets
    except Exception as e:
        print(f"Error listing assets: {e}")
        return []


def delete_project_assets(project_id: str, bucket: str = "captures") -> bool:
    """
    Delete all assets for a project from storage.
    
    Returns:
        True if successful
    """
    supabase = get_storage_client()
    
    try:
        # List all files in project folder
        files = supabase.storage.from_(bucket).list(project_id)
        
        if files:
            paths = [f"{project_id}/{f['name']}" for f in files if f.get("name")]
            if paths:
                supabase.storage.from_(bucket).remove(paths)
        
        return True
    except Exception as e:
        print(f"Error deleting assets: {e}")
        return False


def resolve_asset_url(task: dict) -> Optional[str]:
    """
    Resolve the best URL for a capture task.
    
    Cloud-first: Prefers asset_url, falls back to asset_path.
    
    Args:
        task: Dict with asset_url and/or asset_path
    
    Returns:
        URL string (cloud URL or local path) or None
    """
    # Prefer cloud URL
    if task.get("asset_url"):
        return task["asset_url"]
    
    # Fall back to local path
    if task.get("asset_path"):
        return task["asset_path"]
    
    return None


def is_remote_url(path: str) -> bool:
    """Check if a path is a remote URL (http/https)."""
    return path.startswith("http://") or path.startswith("https://")


def resolve_asset_src(
    asset_url: Optional[str] = None,
    asset_path: Optional[str] = None,
    default: str = "none://text-only"
) -> str:
    """
    Resolve the best asset source for rendering.
    
    Cloud-first: Prefers asset_url, falls back to asset_path.
    Used by composer and assembler for consistent resolution.
    
    Args:
        asset_url: Cloud storage URL (preferred)
        asset_path: Local file path (fallback)
        default: Value to return if both are None
    
    Returns:
        The best available source or default
    """
    if asset_url:
        return asset_url
    if asset_path:
        return asset_path
    return default
