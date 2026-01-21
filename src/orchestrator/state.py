"""State definitions for the orchestrator pipeline."""
from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class PipelineState(TypedDict):
    """Main pipeline state — minimal, no domain knowledge."""
    messages: Annotated[list, add_messages]
    user_input: str                      # Raw user request - flows through unchanged
    project_path: Optional[str]          # Validated Xcode project path
    app_bundle_id: Optional[str]         # For DB queries
    video_project_id: Optional[str]      # Created by analyzer
    intake_complete: bool
    # Sequential capture state
    pending_task_ids: Optional[list[str]]   # Tasks waiting to be captured
    current_task_index: Optional[int]       # Index of current task being processed
    completed_task_ids: Optional[list[str]] # Successfully completed tasks


class CaptureTaskState(TypedDict):
    """State for individual capture task (used in fan-out)."""
    task_id: str
    task_description: str
    capture_type: str
    app_bundle_id: str
    messages: Annotated[list, add_messages]
