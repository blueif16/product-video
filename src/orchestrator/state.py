"""State definitions for the orchestrator pipeline."""
from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AppManifest(TypedDict, total=False):
    """
    Structured knowledge about the app, built by analyzer.
    This flows through state to all downstream agents.
    """
    bundle_id: str                      # e.g., "com.ran.yiban"
    app_name: str                       # e.g., "Yiban"
    url_schemes: list[str]              # e.g., ["yiban://"]
    screens: list[dict]                 # [{name, description, tab_index?, deep_link?}]
    tab_structure: list[str]            # e.g., ["Home", "Closet", "Outfits", "Settings"]
    navigation_notes: str               # Free-form notes about nav
    app_description: str                # What the app does (for validator context)


class PipelineState(TypedDict):
    """Main pipeline state — passes context between nodes."""
    messages: Annotated[list, add_messages]
    user_input: str                         # Raw user request - flows through unchanged
    project_path: Optional[str]             # Validated Xcode project path
    app_bundle_id: Optional[str]            # For DB queries (also in app_manifest)
    url_schemes: Optional[list[str]]        # Deep link schemes from project (e.g., ["yiban://"])
    app_manifest: Optional[AppManifest]     # Structured app knowledge from analyzer
    video_project_id: Optional[str]         # Created by analyzer
    intake_complete: bool
    
    # Sequential capture state
    pending_task_ids: Optional[list[str]]   # Tasks waiting to be captured
    current_task_index: Optional[int]       # Index of current task being processed
    current_task_attempts: Optional[int]    # Attempts on current task (for retry logic)
    completed_task_ids: Optional[list[str]] # Successfully completed tasks
    last_capture_success: Optional[bool]    # Result of last capture attempt


class CaptureTaskState(TypedDict):
    """State for individual capture task (used in fan-out)."""
    task_id: str
    task_description: str
    capture_type: str
    app_bundle_id: str
    messages: Annotated[list, add_messages]
