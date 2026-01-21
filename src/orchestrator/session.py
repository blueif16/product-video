"""
Session management for tracking resources created during a pipeline run.

Used for graceful shutdown and cleanup on Ctrl+C.
"""
from dataclasses import dataclass, field
from typing import Optional
import threading


@dataclass
class PipelineSession:
    """
    Tracks resources created during a single pipeline run.
    
    This allows us to:
    - Know what to clean up on Ctrl+C
    - Show the user what will be deleted
    - Optionally preserve partial results
    """
    # Identifiers
    video_project_id: Optional[str] = None
    app_bundle_id: Optional[str] = None
    
    # Created resources
    task_ids: list[str] = field(default_factory=list)
    
    # Execution state
    is_running: bool = False
    was_interrupted: bool = False
    current_stage: str = "not_started"  # intake, analyzing, capturing, aggregating
    
    # Progress tracking
    total_tasks: int = 0
    completed_tasks: int = 0
    
    def add_task(self, task_id: str) -> None:
        """Track a created task."""
        if task_id not in self.task_ids:
            self.task_ids.append(task_id)
            self.total_tasks = len(self.task_ids)
    
    def mark_task_complete(self, task_id: str) -> None:
        """Mark a task as completed."""
        if task_id in self.task_ids:
            self.completed_tasks += 1
    
    def get_summary(self) -> dict:
        """Get session summary for display."""
        return {
            "video_project_id": self.video_project_id,
            "app_bundle_id": self.app_bundle_id,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "pending_tasks": self.total_tasks - self.completed_tasks,
            "stage": self.current_stage,
            "interrupted": self.was_interrupted,
        }


# Global session instance (singleton for signal handler access)
_current_session: Optional[PipelineSession] = None
_session_lock = threading.Lock()


def get_session() -> PipelineSession:
    """Get or create the current session."""
    global _current_session
    with _session_lock:
        if _current_session is None:
            _current_session = PipelineSession()
        return _current_session


def reset_session() -> PipelineSession:
    """Reset and return a fresh session."""
    global _current_session
    with _session_lock:
        _current_session = PipelineSession()
        return _current_session


def end_session() -> None:
    """Clear the current session."""
    global _current_session
    with _session_lock:
        _current_session = None
