"""
Unified Pipeline State

Supports both full pipeline (capture → editor) and editor-only mode.
"""
from typing import Annotated, Optional, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

from orchestrator.state import AppManifest
from editor.core.state import ClipSpec, VideoSpec


class UnifiedPipelineState(TypedDict):
    """
    Complete state for the unified pipeline.
    
    Supports:
    - Full pipeline: capture → editor → render → music
    - Editor-only: skip capture, start from assets
    - Upload mode: create project from uploaded files
    """
    # ─────────────────────────────────────────────────────────
    # LangGraph Internals
    # ─────────────────────────────────────────────────────────
    messages: Annotated[list, add_messages]
    
    # ─────────────────────────────────────────────────────────
    # Entry Mode
    # ─────────────────────────────────────────────────────────
    pipeline_mode: Literal["full", "editor_only", "upload"]
    
    # ─────────────────────────────────────────────────────────
    # User Input
    # ─────────────────────────────────────────────────────────
    user_input: str
    
    # ─────────────────────────────────────────────────────────
    # Capture Phase State
    # ─────────────────────────────────────────────────────────
    project_path: Optional[str]
    app_bundle_id: Optional[str]
    url_schemes: Optional[list[str]]
    app_manifest: Optional[AppManifest]
    intake_complete: bool
    
    # Capture progress
    pending_task_ids: Optional[list[str]]
    current_task_index: Optional[int]
    current_task_attempts: Optional[int]
    completed_task_ids: Optional[list[str]]
    last_capture_success: Optional[bool]
    
    # ─────────────────────────────────────────────────────────
    # Shared Identity
    # ─────────────────────────────────────────────────────────
    video_project_id: Optional[str]
    status: Optional[str]  # Current pipeline status
    
    # ─────────────────────────────────────────────────────────
    # Editor Phase State
    # ─────────────────────────────────────────────────────────
    analysis_summary: Optional[str]
    assets: Optional[list[dict]]  # [{id, path, url, description}]
    
    # Planner
    edit_plan_summary: Optional[str]
    style_guide: Optional[dict]
    clip_task_ids: Optional[list[str]]
    
    # Composer
    clip_specs: Optional[list[ClipSpec]]
    
    # Assembler
    video_spec: Optional[VideoSpec]
    video_spec_id: Optional[str]
    
    # ─────────────────────────────────────────────────────────
    # Render Phase State
    # ─────────────────────────────────────────────────────────
    render_status: Optional[str]
    render_path: Optional[str]
    render_error: Optional[str]
    
    # ─────────────────────────────────────────────────────────
    # Music Phase State
    # ─────────────────────────────────────────────────────────
    music_analysis: Optional[dict]
    audio_path: Optional[str]
    final_video_path: Optional[str]
    
    # ─────────────────────────────────────────────────────────
    # AG-UI Display State (for frontend)
    # ─────────────────────────────────────────────────────────
    progress_percent: Optional[int]
    current_stage: Optional[str]
    stage_message: Optional[str]


def create_initial_state(
    user_input: str,
    mode: Literal["full", "editor_only", "upload"] = "full",
    video_project_id: Optional[str] = None,
) -> UnifiedPipelineState:
    """Create initial state for pipeline invocation."""
    return UnifiedPipelineState(
        messages=[],
        pipeline_mode=mode,
        user_input=user_input,
        video_project_id=video_project_id,
        
        # Capture defaults
        project_path=None,
        app_bundle_id=None,
        url_schemes=[],
        app_manifest=None,
        intake_complete=False,
        pending_task_ids=[],
        current_task_index=0,
        current_task_attempts=0,
        completed_task_ids=[],
        last_capture_success=None,
        
        # Editor defaults
        analysis_summary=None,
        assets=[],
        edit_plan_summary=None,
        style_guide=None,
        clip_task_ids=[],
        clip_specs=[],
        video_spec=None,
        video_spec_id=None,
        
        # Render defaults
        render_status=None,
        render_path=None,
        render_error=None,
        
        # Music defaults
        music_analysis=None,
        audio_path=None,
        final_video_path=None,
        
        # UI defaults
        progress_percent=0,
        current_stage="initializing",
        stage_message="Starting pipeline...",
        status="pending",
    )
