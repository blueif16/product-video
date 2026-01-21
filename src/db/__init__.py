from .supabase_client import (
    # Tasks
    create_task,
    get_task,
    update_task_status,
    increment_attempt,
    get_pending_tasks,
    get_successful_tasks,
    # Analysis
    save_analysis,
    get_latest_analysis,
    # Video projects
    create_video_project,
    update_video_project,
    get_video_project,
    get_assets_for_project,
)

__all__ = [
    "create_task",
    "get_task", 
    "update_task_status",
    "increment_attempt",
    "get_pending_tasks",
    "get_successful_tasks",
    "save_analysis",
    "get_latest_analysis",
    "create_video_project",
    "update_video_project",
    "get_video_project",
    "get_assets_for_project",
]
