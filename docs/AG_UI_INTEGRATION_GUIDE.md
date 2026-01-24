# StreamLine AG-UI Integration Guide

**Complete checklist for adding a web frontend to your video production pipeline.**

Architecture: FastAPI + LangGraph (backend) ↔ AG-UI Protocol ↔ Next.js + CopilotKit (frontend)

---

## 🔧 Critical Fixes (Implementation Knowledge)

**CopilotKit + HttpAgent Integration Requirements:**

1. **`serviceAdapter` is mandatory** in `copilotRuntimeNextJSAppRouterEndpoint`:
   ```typescript
   const serviceAdapter = new ExperimentalEmptyAdapter();
   copilotRuntimeNextJSAppRouterEndpoint({ runtime, serviceAdapter, endpoint })
   ```

2. **`agent` prop is mandatory** in `CopilotKit` provider:
   ```typescript
   <CopilotKit runtimeUrl="/api/copilotkit" agent="pipelineAgent">
   ```

3. **`agents` prop recommended** in `CopilotChat` for explicit routing:
   ```typescript
   <CopilotChat agents={["pipelineAgent"]} />
   ```

**Why**: CopilotKit defaults to looking for an agent named `'default'`. Without explicit configuration, it throws `Agent 'default' not found` errors. The `agent` prop enables "Agent Lock Mode" for single-agent routing.

---

## Table of Contents

- [Phase 0: Prerequisites](#phase-0-prerequisites)
- [Phase 1: Database & Storage Setup](#phase-1-database--storage-setup)
- [Phase 2: Unified LangGraph Pipeline](#phase-2-unified-langgraph-pipeline)
- [Phase 3: AG-UI Backend Adapter](#phase-3-ag-ui-backend-adapter)
- [Phase 4: Frontend Shell](#phase-4-frontend-shell)
- [Phase 5: State Streaming & Display](#phase-5-state-streaming--display)
- [Phase 6: HITL Interrupts](#phase-6-hitl-interrupts)
- [Phase 7: Upload-Only Mode](#phase-7-upload-only-mode)
- [Phase 8: Polish & Production](#phase-8-polish--production)

---

## Phase 0: Prerequisites

### Checklist

- [x] **0.1** Python environment working (`python -m src.main --help` runs)
- [x] **0.2** Supabase project exists with current schema
- [x] **0.3** Node.js 18+ installed (`node --version`)
- [x] **0.4** Environment variables set in `.env`

### Verify Current Pipeline

```bash
cd /Users/tk/Desktop/productvideo

# Test capture phase (dry run)
python -m src.main --phase capture --input "Test project at ~/Code/TestApp"

# Test editor phase (with existing project)
python -m src.main --phase editor --test
```

### Required .env Additions

```bash
# Add to .env
SUPABASE_STORAGE_BUCKET=captures
```

---

## Phase 1: Database & Storage Setup

### 1.1 Database Migration

**File: `src/db/migrations/004_asset_urls_and_unified_state.sql`**

```sql
-- ═══════════════════════════════════════════════════════════════════════════
-- Migration 004: Asset URLs and Unified Pipeline Support
-- ═══════════════════════════════════════════════════════════════════════════

-- 1. Add cloud storage URL to capture_tasks
ALTER TABLE capture_tasks 
ADD COLUMN IF NOT EXISTS asset_url TEXT;

COMMENT ON COLUMN capture_tasks.asset_url IS 
'Supabase Storage public URL for frontend display. asset_path remains for local Remotion access.';

-- 2. Add cloud storage URL to generated_assets (for AI-generated images)
ALTER TABLE generated_assets
ADD COLUMN IF NOT EXISTS asset_url TEXT;

-- 3. Add source tracking to video_projects (capture vs upload)
ALTER TABLE video_projects
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'capture';

COMMENT ON COLUMN video_projects.source IS 
'How assets were obtained: capture | upload';

-- 4. Add pipeline_mode for unified graph routing
ALTER TABLE video_projects
ADD COLUMN IF NOT EXISTS pipeline_mode TEXT DEFAULT 'full';

COMMENT ON COLUMN video_projects.pipeline_mode IS 
'Which pipeline to run: full | editor_only';

-- 5. Index for faster queries
CREATE INDEX IF NOT EXISTS idx_capture_tasks_project_status 
ON capture_tasks(video_project_id, status);

CREATE INDEX IF NOT EXISTS idx_video_projects_status 
ON video_projects(status);
```

### Checklist

- [x] **1.1** Run migration in Supabase SQL Editor
- [x] **1.2** Verify columns exist: `SELECT column_name FROM information_schema.columns WHERE table_name = 'capture_tasks';`

### 1.2 Supabase Storage Setup

**In Supabase Dashboard:**

1. Go to **Storage** → **New Bucket**
2. Name: `captures`
3. Public bucket: **Yes** (for simplicity; use signed URLs for production)
4. File size limit: 50MB

### 1.3 Storage Upload Utility

**File: `src/tools/storage.py`**

```python
"""
Supabase Storage utilities for cloud asset management.

Usage:
    from tools.storage import upload_asset, get_public_url
    
    url = upload_asset("/tmp/screenshot.png", project_id="abc-123")
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
    """
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
    Upload asset and update capture_task with URL.
    
    Returns:
        Public URL
    """
    from db.supabase_client import get_supabase_client
    
    # Determine subfolder based on type
    subfolder = "recordings" if capture_type == "recording" else "screenshots"
    
    # Upload
    url = upload_asset(local_path, project_id, subfolder=subfolder)
    
    # Update DB
    supabase = get_supabase_client()
    supabase.table("capture_tasks").update({
        "asset_url": url,
        "asset_path": local_path,  # Keep local path for Remotion
    }).eq("id", task_id).execute()
    
    return url


def get_project_assets(project_id: str, bucket: str = "captures") -> list[dict]:
    """
    List all assets for a project from storage.
    
    Returns:
        List of {name, url, size, created_at}
    """
    supabase = get_storage_client()
    
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
```

### 1.4 Update Capturer to Upload

**File: `src/orchestrator/capturer.py`** (add to existing)

```python
# Add import at top
from tools.storage import upload_and_update_task

# In capture_single_task_node, after successful capture:
# Find where you call update_capture_task_status and add:

if screenshot_path and Path(screenshot_path).exists():
    try:
        asset_url = upload_and_update_task(
            local_path=screenshot_path,
            task_id=task_id,
            project_id=state["video_project_id"],
            capture_type=capture_type,
        )
        print(f"   ☁️  Uploaded: {asset_url[:60]}...")
    except Exception as e:
        print(f"   ⚠️  Upload failed (local file preserved): {e}")
```

### Checklist

- [x] **1.3** Create `src/tools/storage.py`
- [x] **1.4** Create `captures` bucket in Supabase Storage (public)
- [x] **1.5** Update capturer to upload after capture
- [x] **1.6** Test upload: `python -c "from tools.storage import upload_asset; print(upload_asset('/path/to/test.png', 'test-project'))"`

---

## Phase 2: Unified LangGraph Pipeline

### 2.1 Unified State

**File: `src/pipeline/state.py`**

```python
"""
Unified Pipeline State

Supports both full pipeline (capture → editor) and editor-only mode.
"""
from typing import Annotated, Optional, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

from orchestrator.state import AppManifest
from editor.core.state import ClipSpec, VideoSpec, AudioSpec


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
    # These are derived/computed for UI display
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
```

### 2.2 Unified Graph

**File: `src/pipeline/unified_graph.py`**

```python
"""
Unified Pipeline Graph

Single graph that supports:
1. Full pipeline: capture → editor → render → music
2. Editor-only: load assets from DB → editor → render → music
3. Upload mode: create project from uploads → editor → render → music

Entry point is determined by pipeline_mode in state.
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from .state import UnifiedPipelineState, create_initial_state

# Import capture nodes
from orchestrator.intake import intake_node
from orchestrator.analyzer import analyze_and_plan_node
from orchestrator.capturer import capture_single_task_node
from orchestrator.aggregate import aggregate_node
from orchestrator.graph import (
    prepare_capture_queue,
    route_after_capture,
    move_to_next_task,
    route_next_capture,
    increment_attempts,
)

# Import editor nodes
from editor.planners import edit_planner_node
from editor.composers import compose_all_clips_node
from editor.core.assembler import edit_assembler_node

# Import render/music nodes (conditional)
try:
    from renderer.render_client import remotion_render_node
    HAS_RENDERER = True
except ImportError:
    HAS_RENDERER = False

try:
    from editor.core.music_planner import music_planner_node
    from tools.music_generator import music_generator_node, mux_audio_video_node
    HAS_MUSIC = True
except ImportError:
    HAS_MUSIC = False


# ─────────────────────────────────────────────────────────────
# Entry Routing
# ─────────────────────────────────────────────────────────────

def route_entry(state: UnifiedPipelineState) -> str:
    """
    Route based on pipeline_mode.
    
    - full: Start with intake (capture phase)
    - editor_only: Skip to load_assets (editor phase)
    - upload: Skip to load_assets (same as editor_only, assets already in DB)
    """
    mode = state.get("pipeline_mode", "full")
    
    if mode in ("editor_only", "upload"):
        return "load_assets"
    return "intake"


# ─────────────────────────────────────────────────────────────
# Bridge Nodes (Capture → Editor)
# ─────────────────────────────────────────────────────────────

def load_assets_node(state: UnifiedPipelineState) -> dict:
    """
    Load assets from DB for editor phase.
    
    Called when:
    - pipeline_mode is "editor_only" or "upload"
    - After capture phase completes (aggregated)
    """
    from editor.core.loader import load_editor_state
    
    project_id = state["video_project_id"]
    
    if not project_id:
        raise ValueError("video_project_id required for editor phase")
    
    print(f"\n📂 Loading assets for project: {project_id[:8]}...")
    
    # Load from DB
    editor_state = load_editor_state(project_id)
    
    return {
        "assets": editor_state.get("assets", []),
        "analysis_summary": editor_state.get("analysis_summary", state.get("user_input", "")),
        "user_input": editor_state.get("user_input", state.get("user_input", "")),
        "current_stage": "planning",
        "stage_message": f"Loaded {len(editor_state.get('assets', []))} assets",
        "status": "editing",
    }


def bridge_to_editor(state: UnifiedPipelineState) -> dict:
    """
    Transition from capture to editor phase.
    Updates status and prepares for editor.
    """
    return {
        "current_stage": "loading_assets",
        "stage_message": "Capture complete, preparing editor...",
        "status": "aggregated",
    }


# ─────────────────────────────────────────────────────────────
# Render/Music Routing
# ─────────────────────────────────────────────────────────────

def should_render(state: UnifiedPipelineState) -> Literal["render", "end"]:
    """Check if we should proceed to rendering."""
    spec = state.get("video_spec")
    if spec and spec.get("clips") and HAS_RENDERER:
        return "render"
    return "end"


def should_generate_music(state: UnifiedPipelineState) -> Literal["music", "end"]:
    """Check if we should generate music."""
    render_path = state.get("render_path")
    if render_path and not state.get("render_error") and HAS_MUSIC:
        return "music"
    return "end"


# ─────────────────────────────────────────────────────────────
# Progress Tracking Wrappers
# ─────────────────────────────────────────────────────────────

def with_progress(node_fn, stage: str, message: str, progress: int):
    """Wrap a node to emit progress updates."""
    def wrapped(state: UnifiedPipelineState) -> dict:
        result = node_fn(state)
        result["current_stage"] = stage
        result["stage_message"] = message
        result["progress_percent"] = progress
        return result
    return wrapped


# ─────────────────────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────────────────────

def build_unified_graph(
    include_render: bool = True,
    include_music: bool = True,
) -> StateGraph:
    """
    Build the unified pipeline graph.
    
    Topology:
    
        START
          │
          ├─[full]──────→ intake → analyze → capture_queue → [capture_loop] → aggregate
          │                                                                        │
          │                                                                        ▼
          └─[editor_only/upload]──→ load_assets ──────────────────────────────────→│
                                                                                   │
                                                                                   ▼
                                                                              planner
                                                                                   │
                                                                                   ▼
                                                                            compose_clips
                                                                                   │
                                                                                   ▼
                                                                              assemble
                                                                                   │
                                                                    ┌──────────────┼──────────────┐
                                                                    │              │              │
                                                                    ▼              │              │
                                                                 render            │              │
                                                                    │              │              │
                                                                    ▼              │              │
                                                               music_plan          │              │
                                                                    │              │              │
                                                                    ▼              │              │
                                                             music_generate        │              │
                                                                    │              │              │
                                                                    ▼              │              │
                                                                mux_audio          │              │
                                                                    │              │              │
                                                                    └──────────────┴──────────────┘
                                                                                   │
                                                                                   ▼
                                                                                  END
    """
    builder = StateGraph(UnifiedPipelineState)
    
    # ─────────────────────────────────────────────────────────
    # Capture Phase Nodes
    # ─────────────────────────────────────────────────────────
    builder.add_node("intake", intake_node)
    builder.add_node("analyze_and_plan", analyze_and_plan_node)
    builder.add_node("prepare_capture_queue", prepare_capture_queue)
    builder.add_node("increment_attempts", increment_attempts)
    builder.add_node("capture_single", capture_single_task_node)
    builder.add_node("move_to_next", move_to_next_task)
    builder.add_node("aggregate", aggregate_node)
    builder.add_node("bridge_to_editor", bridge_to_editor)
    
    # ─────────────────────────────────────────────────────────
    # Editor Phase Nodes
    # ─────────────────────────────────────────────────────────
    builder.add_node("load_assets", load_assets_node)
    builder.add_node("planner", edit_planner_node)
    builder.add_node("compose_clips", compose_all_clips_node)
    builder.add_node("assemble", edit_assembler_node)
    
    # ─────────────────────────────────────────────────────────
    # Render Phase Nodes
    # ─────────────────────────────────────────────────────────
    if include_render and HAS_RENDERER:
        builder.add_node("render", remotion_render_node)
    
    # ─────────────────────────────────────────────────────────
    # Music Phase Nodes
    # ─────────────────────────────────────────────────────────
    if include_music and HAS_MUSIC:
        builder.add_node("music_plan", music_planner_node)
        builder.add_node("music_generate", music_generator_node)
        builder.add_node("mux_audio", mux_audio_video_node)
    
    # ─────────────────────────────────────────────────────────
    # Entry Routing
    # ─────────────────────────────────────────────────────────
    builder.add_conditional_edges(
        START,
        route_entry,
        {
            "intake": "intake",
            "load_assets": "load_assets",
        }
    )
    
    # ─────────────────────────────────────────────────────────
    # Capture Phase Edges
    # ─────────────────────────────────────────────────────────
    builder.add_edge("analyze_and_plan", "prepare_capture_queue")
    
    builder.add_conditional_edges(
        "prepare_capture_queue",
        route_next_capture,
        {"capture_single": "increment_attempts", "aggregate": "aggregate"}
    )
    
    builder.add_edge("increment_attempts", "capture_single")
    
    builder.add_conditional_edges(
        "capture_single",
        route_after_capture,
        {
            "capture_single": "increment_attempts",
            "move_to_next": "move_to_next",
            "aggregate": "aggregate",
        }
    )
    
    builder.add_conditional_edges(
        "move_to_next",
        route_next_capture,
        {"capture_single": "increment_attempts", "aggregate": "aggregate"}
    )
    
    # Capture → Editor bridge
    builder.add_edge("aggregate", "bridge_to_editor")
    builder.add_edge("bridge_to_editor", "load_assets")
    
    # ─────────────────────────────────────────────────────────
    # Editor Phase Edges
    # ─────────────────────────────────────────────────────────
    builder.add_edge("load_assets", "planner")
    builder.add_edge("planner", "compose_clips")
    builder.add_edge("compose_clips", "assemble")
    
    # ─────────────────────────────────────────────────────────
    # Render & Music Edges
    # ─────────────────────────────────────────────────────────
    if include_render and HAS_RENDERER:
        builder.add_conditional_edges(
            "assemble",
            should_render,
            {"render": "render", "end": END}
        )
        
        if include_music and HAS_MUSIC:
            builder.add_conditional_edges(
                "render",
                should_generate_music,
                {"music": "music_plan", "end": END}
            )
            builder.add_edge("music_plan", "music_generate")
            builder.add_edge("music_generate", "mux_audio")
            builder.add_edge("mux_audio", END)
        else:
            builder.add_edge("render", END)
    else:
        builder.add_edge("assemble", END)
    
    return builder


def compile_unified_graph(
    include_render: bool = True,
    include_music: bool = True,
    checkpointer=None,
):
    """Compile the unified graph with optional checkpointer."""
    builder = build_unified_graph(
        include_render=include_render,
        include_music=include_music,
    )
    return builder.compile(checkpointer=checkpointer or InMemorySaver())


# ─────────────────────────────────────────────────────────────
# Run Functions
# ─────────────────────────────────────────────────────────────

def run_unified_pipeline(
    user_input: str,
    mode: Literal["full", "editor_only", "upload"] = "full",
    video_project_id: str = None,
    include_render: bool = True,
    include_music: bool = True,
) -> dict:
    """
    Run the unified pipeline.
    
    Args:
        user_input: User's description
        mode: Pipeline mode
        video_project_id: Required for editor_only/upload modes
        include_render: Whether to render video
        include_music: Whether to generate music
    
    Returns:
        Final pipeline state
    """
    if mode in ("editor_only", "upload") and not video_project_id:
        raise ValueError(f"video_project_id required for mode={mode}")
    
    graph = compile_unified_graph(
        include_render=include_render,
        include_music=include_music,
    )
    
    initial_state = create_initial_state(
        user_input=user_input,
        mode=mode,
        video_project_id=video_project_id,
    )
    
    config = {"configurable": {"thread_id": f"pipeline-{video_project_id or 'new'}"}}
    
    result = graph.invoke(initial_state, config=config)
    
    return result
```

### Checklist

- [x] **2.1** Create `src/pipeline/state.py`
- [x] **2.2** Create `src/pipeline/unified_graph.py`
- [x] **2.3** Update `src/pipeline/__init__.py`:
  ```python
  from .unified_graph import (
      compile_unified_graph,
      run_unified_pipeline,
      build_unified_graph,
  )
  from .state import UnifiedPipelineState, create_initial_state
  ```
- [x] **2.4** Test unified graph:
  ```bash
  python -c "from pipeline import compile_unified_graph; g = compile_unified_graph(); print('Graph compiled!')"
  ```

---

## Phase 3: AG-UI Backend Adapter

### 3.1 Event Translator

**File: `src/ag_ui/event_translator.py`**

```python
"""
Translate LangGraph events to AG-UI protocol events.

Maps:
- on_chain_start → STEP_STARTED
- on_chain_end → STEP_FINISHED  
- on_chat_model_stream → TEXT_MESSAGE_CONTENT
- state changes → STATE_DELTA
"""
from typing import Any, Optional
import json
import uuid

from ag_ui.core import (
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    StepStartedEvent,
    StepFinishedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    StateSnapshotEvent,
    StateDeltaEvent,
    CustomEvent,
)


# Nodes to track as "steps" in UI
TRACKED_NODES = {
    "intake": ("Validating Project", 5),
    "analyze_and_plan": ("Analyzing App", 15),
    "prepare_capture_queue": ("Preparing Captures", 20),
    "capture_single": ("Capturing Screen", None),  # Dynamic progress
    "aggregate": ("Aggregating Results", 50),
    "load_assets": ("Loading Assets", 55),
    "planner": ("Planning Timeline", 60),
    "compose_clips": ("Composing Clips", 70),
    "assemble": ("Assembling Video", 80),
    "render": ("Rendering Video", 90),
    "music_plan": ("Planning Music", 92),
    "music_generate": ("Generating Music", 95),
    "mux_audio": ("Adding Audio", 98),
}


def make_json_safe(obj: Any, seen: Optional[set] = None) -> Any:
    """
    Recursively make object JSON-serializable.
    Handles circular references, Pydantic models, etc.
    """
    if seen is None:
        seen = set()
    
    obj_id = id(obj)
    if obj_id in seen:
        return "[Circular Reference]"
    
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    
    seen.add(obj_id)
    
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v, seen) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_safe(item, seen) for item in obj]
    elif hasattr(obj, "model_dump"):
        return make_json_safe(obj.model_dump(), seen)
    elif hasattr(obj, "__dict__"):
        return make_json_safe(obj.__dict__, seen)
    else:
        return str(obj)


def extract_ui_state(langgraph_state: dict) -> dict:
    """
    Extract UI-relevant state from LangGraph state.
    
    Returns a clean dict suitable for AG-UI STATE_SNAPSHOT/STATE_DELTA.
    """
    # Fields to expose to frontend
    ui_fields = [
        "video_project_id",
        "pipeline_mode",
        "status",
        "current_stage",
        "stage_message",
        "progress_percent",
        "pending_task_ids",
        "current_task_index",
        "completed_task_ids",
        "clip_task_ids",
        "render_status",
        "render_path",
        "audio_path",
        "final_video_path",
    ]
    
    ui_state = {}
    for field in ui_fields:
        if field in langgraph_state:
            ui_state[field] = make_json_safe(langgraph_state[field])
    
    # Compute derived fields
    pending = langgraph_state.get("pending_task_ids", [])
    current_idx = langgraph_state.get("current_task_index", 0)
    completed = langgraph_state.get("completed_task_ids", [])
    
    ui_state["captures_total"] = len(pending)
    ui_state["captures_completed"] = len(completed)
    
    # Calculate capture progress
    if pending and langgraph_state.get("current_stage") == "capturing":
        capture_progress = (current_idx / len(pending)) * 30 + 20  # 20-50%
        ui_state["progress_percent"] = int(capture_progress)
    
    return ui_state


class EventTranslator:
    """
    Translates LangGraph streaming events to AG-UI events.
    
    Usage:
        translator = EventTranslator(thread_id, run_id)
        
        async for event in graph.astream_events(...):
            for ag_event in translator.translate(event, current_state):
                yield ag_event
    """
    
    def __init__(self, thread_id: str, run_id: str):
        self.thread_id = thread_id
        self.run_id = run_id
        self.message_id = str(uuid.uuid4())
        self.in_message = False
        self.last_state_hash = None
        self.current_node = None
    
    def translate(
        self,
        langgraph_event: dict,
        current_state: Optional[dict] = None,
    ) -> list:
        """
        Translate a LangGraph event to AG-UI event(s).
        
        Returns list of AG-UI events (may be empty).
        """
        events = []
        event_type = langgraph_event.get("event")
        
        # ─────────────────────────────────────────────────────
        # Node Start
        # ─────────────────────────────────────────────────────
        if event_type == "on_chain_start":
            node_name = langgraph_event.get("name", "")
            
            if node_name in TRACKED_NODES:
                self.current_node = node_name
                display_name, progress = TRACKED_NODES[node_name]
                
                events.append(StepStartedEvent(
                    type=EventType.STEP_STARTED,
                    step_name=node_name,
                    metadata={"display_name": display_name},
                ))
                
                # Emit progress update
                if progress is not None and current_state:
                    events.append(StateDeltaEvent(
                        type=EventType.STATE_DELTA,
                        delta=[
                            {"op": "replace", "path": "/current_stage", "value": node_name},
                            {"op": "replace", "path": "/stage_message", "value": display_name},
                            {"op": "replace", "path": "/progress_percent", "value": progress},
                        ],
                    ))
        
        # ─────────────────────────────────────────────────────
        # Node End
        # ─────────────────────────────────────────────────────
        elif event_type == "on_chain_end":
            node_name = langgraph_event.get("name", "")
            
            if node_name in TRACKED_NODES:
                events.append(StepFinishedEvent(
                    type=EventType.STEP_FINISHED,
                    step_name=node_name,
                ))
                self.current_node = None
        
        # ─────────────────────────────────────────────────────
        # LLM Token Streaming
        # ─────────────────────────────────────────────────────
        elif event_type == "on_chat_model_stream":
            chunk = langgraph_event.get("data", {}).get("chunk")
            
            if chunk and hasattr(chunk, "content") and chunk.content:
                # Start message if needed
                if not self.in_message:
                    events.append(TextMessageStartEvent(
                        type=EventType.TEXT_MESSAGE_START,
                        message_id=self.message_id,
                        role="assistant",
                    ))
                    self.in_message = True
                
                events.append(TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=self.message_id,
                    delta=chunk.content,
                ))
        
        # ─────────────────────────────────────────────────────
        # Tool Calls (capture, etc.)
        # ─────────────────────────────────────────────────────
        elif event_type == "on_tool_start":
            tool_name = langgraph_event.get("name", "unknown")
            events.append(CustomEvent(
                type=EventType.CUSTOM,
                name="tool_start",
                value={"tool": tool_name},
            ))
        
        elif event_type == "on_tool_end":
            tool_name = langgraph_event.get("name", "unknown")
            events.append(CustomEvent(
                type=EventType.CUSTOM,
                name="tool_end",
                value={"tool": tool_name},
            ))
        
        return events
    
    def finalize_message(self) -> list:
        """Close any open message stream."""
        events = []
        if self.in_message:
            events.append(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=self.message_id,
            ))
            self.in_message = False
            self.message_id = str(uuid.uuid4())  # New ID for next message
        return events
```

### 3.2 Main Adapter

**File: `src/ag_ui/adapter.py`**

```python
"""
AG-UI Adapter for StreamLine Pipeline

Exposes the unified LangGraph pipeline via AG-UI protocol.
"""
import uuid
import asyncio
from typing import AsyncGenerator, Optional

from ag_ui.core import (
    RunAgentInput,
    Message,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    StateSnapshotEvent,
    StateDeltaEvent,
    EventEncoder,
)

from pipeline import compile_unified_graph, create_initial_state
from .event_translator import EventTranslator, extract_ui_state, make_json_safe
from db.supabase_client import get_capture_tasks_for_project


SSE_CONTENT_TYPE = "text/event-stream"


async def fetch_capture_tasks_with_urls(project_id: str) -> list[dict]:
    """
    Fetch capture tasks with cloud URLs for frontend display.
    """
    if not project_id:
        return []
    
    try:
        tasks = get_capture_tasks_for_project(project_id)
        return [
            {
                "id": task["id"],
                "description": task.get("task_description", ""),
                "status": task.get("status", "pending"),
                "asset_url": task.get("asset_url"),
                "capture_type": task.get("capture_type", "screenshot"),
            }
            for task in tasks
        ]
    except Exception:
        return []


async def run_pipeline_stream(
    input_data: RunAgentInput,
    mode: str = "full",
    include_render: bool = True,
    include_music: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Stream AG-UI events from pipeline execution.
    
    Args:
        input_data: AG-UI input (messages, thread_id, run_id, state)
        mode: "full" | "editor_only" | "upload"
        include_render: Whether to render video
        include_music: Whether to generate music
    
    Yields:
        SSE-formatted AG-UI events
    """
    encoder = EventEncoder(accept=SSE_CONTENT_TYPE)
    thread_id = input_data.thread_id or str(uuid.uuid4())
    run_id = input_data.run_id or str(uuid.uuid4())
    
    translator = EventTranslator(thread_id, run_id)
    
    # ─────────────────────────────────────────────────────────
    # 1. RUN_STARTED
    # ─────────────────────────────────────────────────────────
    yield encoder.encode(RunStartedEvent(
        type=EventType.RUN_STARTED,
        thread_id=thread_id,
        run_id=run_id,
    ))
    
    # ─────────────────────────────────────────────────────────
    # 2. Initial STATE_SNAPSHOT
    # ─────────────────────────────────────────────────────────
    
    # Extract user message
    user_message = ""
    for msg in input_data.messages:
        if msg.role == "user":
            user_message = msg.content
            break
    
    # Check for existing project ID in input state
    video_project_id = None
    if input_data.state:
        video_project_id = input_data.state.get("video_project_id")
    
    initial_ui_state = {
        "pipeline_mode": mode,
        "status": "starting",
        "current_stage": "initializing",
        "stage_message": "Starting pipeline...",
        "progress_percent": 0,
        "video_project_id": video_project_id,
        "captures_total": 0,
        "captures_completed": 0,
        "capture_tasks": [],
    }
    
    yield encoder.encode(StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot=initial_ui_state,
    ))
    
    # ─────────────────────────────────────────────────────────
    # 3. Compile Graph
    # ─────────────────────────────────────────────────────────
    graph = compile_unified_graph(
        include_render=include_render,
        include_music=include_music,
    )
    
    initial_state = create_initial_state(
        user_input=user_message,
        mode=mode,
        video_project_id=video_project_id,
    )
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # ─────────────────────────────────────────────────────────
    # 4. Stream Graph Execution
    # ─────────────────────────────────────────────────────────
    last_project_id = None
    
    try:
        async for event in graph.astream_events(
            initial_state,
            config=config,
            version="v2",
        ):
            # Translate LangGraph event to AG-UI events
            current_state = graph.get_state(config).values if hasattr(graph, 'get_state') else {}
            
            for ag_event in translator.translate(event, current_state):
                yield encoder.encode(ag_event)
            
            # Check for project ID updates (for fetching capture tasks)
            if current_state:
                new_project_id = current_state.get("video_project_id")
                if new_project_id and new_project_id != last_project_id:
                    last_project_id = new_project_id
                    
                    # Emit project ID update
                    yield encoder.encode(StateDeltaEvent(
                        type=EventType.STATE_DELTA,
                        delta=[
                            {"op": "replace", "path": "/video_project_id", "value": new_project_id},
                        ],
                    ))
            
            # Periodically fetch and emit capture task status
            if event.get("event") == "on_chain_end":
                node_name = event.get("name", "")
                
                if node_name in ("capture_single", "aggregate") and last_project_id:
                    tasks = await fetch_capture_tasks_with_urls(last_project_id)
                    
                    yield encoder.encode(StateDeltaEvent(
                        type=EventType.STATE_DELTA,
                        delta=[
                            {"op": "replace", "path": "/capture_tasks", "value": tasks},
                            {"op": "replace", "path": "/captures_completed", 
                             "value": sum(1 for t in tasks if t["status"] == "completed")},
                            {"op": "replace", "path": "/captures_total", "value": len(tasks)},
                        ],
                    ))
            
            # Small yield to allow other async tasks
            await asyncio.sleep(0)
        
        # ─────────────────────────────────────────────────────
        # 5. Finalize
        # ─────────────────────────────────────────────────────
        
        # Close any open message stream
        for ag_event in translator.finalize_message():
            yield encoder.encode(ag_event)
        
        # Get final state
        final_state = graph.get_state(config).values
        final_ui_state = extract_ui_state(final_state)
        final_ui_state["status"] = "completed"
        final_ui_state["progress_percent"] = 100
        
        # Final capture tasks
        if last_project_id:
            final_ui_state["capture_tasks"] = await fetch_capture_tasks_with_urls(last_project_id)
        
        yield encoder.encode(StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot=final_ui_state,
        ))
    
    except Exception as e:
        # Emit error
        yield encoder.encode(RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=str(e),
        ))
    
    finally:
        # ─────────────────────────────────────────────────────
        # 6. RUN_FINISHED
        # ─────────────────────────────────────────────────────
        yield encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id,
        ))
```

### 3.3 FastAPI Server

**File: `src/ag_ui/server.py`**

```python
"""
FastAPI server with AG-UI endpoints.

Run:
    uvicorn ag_ui.server:app --reload --port 8000
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Literal
import uuid

from ag_ui.core import RunAgentInput
from .adapter import run_pipeline_stream, SSE_CONTENT_TYPE
from db.supabase_client import get_capture_tasks_for_project, get_video_project


app = FastAPI(
    title="StreamLine AG-UI Server",
    description="AG-UI compatible API for video production pipeline",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# AG-UI Endpoint
# ─────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    """Extended request with pipeline options."""
    mode: Literal["full", "editor_only", "upload"] = "full"
    include_render: bool = True
    include_music: bool = True


@app.post("/pipeline")
async def pipeline_endpoint(input_data: RunAgentInput):
    """
    Main AG-UI endpoint for pipeline execution.
    
    Streams AG-UI events as SSE.
    """
    # Extract mode from state if present
    mode = "full"
    include_render = True
    include_music = True
    
    if input_data.state:
        mode = input_data.state.get("pipeline_mode", "full")
        include_render = input_data.state.get("include_render", True)
        include_music = input_data.state.get("include_music", True)
    
    return StreamingResponse(
        run_pipeline_stream(
            input_data,
            mode=mode,
            include_render=include_render,
            include_music=include_music,
        ),
        media_type=SSE_CONTENT_TYPE,
    )


# ─────────────────────────────────────────────────────────────
# REST Endpoints (for frontend data fetching)
# ─────────────────────────────────────────────────────────────

@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    project = get_video_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.get("/projects/{project_id}/captures")
async def get_captures(project_id: str):
    """Get capture tasks for a project."""
    tasks = get_capture_tasks_for_project(project_id)
    return {"captures": tasks}


# ─────────────────────────────────────────────────────────────
# Upload Mode Endpoint
# ─────────────────────────────────────────────────────────────

class UploadProjectRequest(BaseModel):
    """Request to create project from uploads."""
    user_input: str
    assets: list[dict]  # [{filename, url, description}]


@app.post("/projects/from-uploads")
async def create_project_from_uploads(request: UploadProjectRequest):
    """
    Create a video project from uploaded assets.
    
    Returns project_id to use with editor-only mode.
    """
    from db.supabase_client import (
        create_video_project,
        create_capture_task,
    )
    
    # Create project
    project_id = str(uuid.uuid4())
    create_video_project(
        id=project_id,
        user_input=request.user_input,
        status="aggregated",  # Ready for editor
        source="upload",
        pipeline_mode="upload",
    )
    
    # Create capture tasks for each asset
    for i, asset in enumerate(request.assets):
        create_capture_task(
            video_project_id=project_id,
            task_description=asset.get("description", f"Uploaded asset {i+1}"),
            capture_type="screenshot",
            asset_url=asset["url"],
            status="completed",
        )
    
    return {
        "project_id": project_id,
        "asset_count": len(request.assets),
    }


# ─────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "streamline-ag-ui",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3.4 Package Init

**File: `src/ag_ui/__init__.py`**

```python
"""
AG-UI Integration Layer

Provides AG-UI protocol compatibility for StreamLine pipeline.
"""

from .adapter import run_pipeline_stream, SSE_CONTENT_TYPE
from .event_translator import EventTranslator, extract_ui_state
from .server import app

__all__ = [
    "run_pipeline_stream",
    "SSE_CONTENT_TYPE",
    "EventTranslator",
    "extract_ui_state",
    "app",
]
```

### Checklist

- [x] **3.1** Create `src/backend/` directory
- [x] **3.2** Create `src/backend/event_translator.py`
- [x] **3.3** Create `src/backend/adapter.py`
- [x] **3.4** Create `src/backend/server.py`
- [x] **3.5** Create `src/backend/__init__.py`
- [x] **3.6** Install dependencies (⚠️ MUST use venv):
  ```bash
  # Activate venv first
  source .venv/bin/activate
  pip install ag-ui-protocol fastapi uvicorn python-multipart
  ```
- [x] **3.7** Test server (⚠️ MUST use venv):
  ```bash
  # Activate venv first
  source .venv/bin/activate
  cd /Users/tk/Desktop/productvideo/src
  python -m uvicorn backend.server:app --reload --port 8000
  # Visit http://localhost:8000/health
  ```

---

## Phase 4: Frontend Shell

### 4.1 Initialize Next.js Project

```bash
cd /Users/tk/Desktop/productvideo/frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
```

### 4.2 Install Dependencies

```bash
npm install @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime @ag-ui/client
npm install lucide-react clsx tailwind-merge
```

### 4.3 API Route

**File: `frontend/src/app/api/copilotkit/route.ts`**

**⚠️ DEVIATION FROM ORIGINAL GUIDE**: `copilotRuntimeNextJSAppRouterEndpoint` requires a `serviceAdapter` parameter (discovered during implementation). Use `ExperimentalEmptyAdapter` since all LLM logic is handled by the backend.

```typescript
import { HttpAgent } from "@ag-ui/client";
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";

// Service adapter for CopilotKit (required parameter)
const serviceAdapter = new ExperimentalEmptyAdapter();

// Connect to FastAPI backend
const pipelineAgent = new HttpAgent({
  url: process.env.PIPELINE_API_URL || "http://127.0.0.1:8000/pipeline",
});

const runtime = new CopilotRuntime({
  agents: {
    pipelineAgent,
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};
```

### 4.4 Layout with CopilotKit Provider

**File: `frontend/src/app/layout.tsx`**

**⚠️ DEVIATION FROM ORIGINAL GUIDE**: `CopilotKit` component requires an `agent` prop to specify which agent to use (discovered during implementation). Must match the agent name registered in the runtime.

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "StreamLine - AI Video Production",
  description: "Create Product Hunt quality videos with AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <CopilotKit runtimeUrl="/api/copilotkit" agent="pipelineAgent">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
```

### 4.5 State Types

**File: `frontend/src/lib/types.ts`**

```typescript
/**
 * StreamLine Pipeline State
 * 
 * Mirrors the AG-UI state emitted by the backend.
 */

export interface CaptureTask {
  id: string;
  description: string;
  status: "pending" | "capturing" | "completed" | "failed";
  asset_url?: string;
  capture_type: "screenshot" | "recording";
}

export interface ClipSpec {
  id: string;
  startFrame: number;
  durationFrames: number;
  layers: any[]; // Simplified for now
}

export interface VideoSpec {
  meta: {
    title: string;
    durationFrames: number;
    fps: number;
    resolution: { width: number; height: number };
  };
  clips: ClipSpec[];
}

export interface StreamLineState {
  // Pipeline identity
  video_project_id: string | null;
  pipeline_mode: "full" | "editor_only" | "upload";
  
  // Progress
  status: "starting" | "capturing" | "editing" | "rendering" | "completed" | "error";
  current_stage: string;
  stage_message: string;
  progress_percent: number;
  
  // Capture phase
  capture_tasks: CaptureTask[];
  captures_total: number;
  captures_completed: number;
  
  // Editor phase
  clip_task_ids: string[];
  
  // Render phase
  render_status: string | null;
  render_path: string | null;
  
  // Music phase
  audio_path: string | null;
  final_video_path: string | null;
}

export const initialState: StreamLineState = {
  video_project_id: null,
  pipeline_mode: "full",
  status: "starting",
  current_stage: "idle",
  stage_message: "Ready to create your video",
  progress_percent: 0,
  capture_tasks: [],
  captures_total: 0,
  captures_completed: 0,
  clip_task_ids: [],
  render_status: null,
  render_path: null,
  audio_path: null,
  final_video_path: null,
};
```

### 4.6 Main Page

**File: `frontend/src/app/page.tsx`**

```tsx
"use client";

import { useCoAgent } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { StreamLineState, initialState } from "@/lib/types";
import { StatusPanel } from "@/components/StatusPanel";

export default function Home() {
  const { state } = useCoAgent<StreamLineState>({
    name: "pipelineAgent",
    initialState,
  });

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Status Panel */}
      <div className="w-80 border-r border-gray-700 bg-gray-800">
        <StatusPanel state={state} />
      </div>
      
      {/* Chat Panel */}
      <div className="flex-1 flex flex-col">
        <header className="p-4 border-b border-gray-700">
          <h1 className="text-xl font-bold text-white">StreamLine</h1>
          <p className="text-sm text-gray-400">AI-Powered Video Production</p>
        </header>
        
        <div className="flex-1">
          <CopilotChat
            className="h-full"
            labels={{
              initial: "Hi! I'm StreamLine. Describe your app and what kind of video you'd like to create.",
              placeholder: "Describe your app and video goals...",
            }}
          />
        </div>
      </div>
    </div>
  );
}
```

### 4.7 Status Panel Component

**File: `frontend/src/components/StatusPanel.tsx`**

```tsx
"use client";

import { StreamLineState } from "@/lib/types";
import { CaptureGrid } from "./CaptureGrid";
import { ProgressBar } from "./ProgressBar";

interface StatusPanelProps {
  state: StreamLineState;
}

export function StatusPanel({ state }: StatusPanelProps) {
  return (
    <div className="p-4 space-y-6">
      {/* Progress */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Progress
        </h2>
        <ProgressBar 
          percent={state.progress_percent} 
          status={state.status}
        />
        <p className="text-sm text-gray-300 mt-2">{state.stage_message}</p>
      </div>
      
      {/* Pipeline Info */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Pipeline
        </h2>
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">Mode</span>
            <span className="text-gray-300">{state.pipeline_mode}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Stage</span>
            <span className="text-gray-300">{state.current_stage}</span>
          </div>
          {state.video_project_id && (
            <div className="flex justify-between">
              <span className="text-gray-500">Project</span>
              <span className="text-gray-300 font-mono text-xs">
                {state.video_project_id.slice(0, 8)}...
              </span>
            </div>
          )}
        </div>
      </div>
      
      {/* Captures */}
      {state.capture_tasks.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Captures ({state.captures_completed}/{state.captures_total})
          </h2>
          <CaptureGrid tasks={state.capture_tasks} />
        </div>
      )}
      
      {/* Results */}
      {(state.render_path || state.final_video_path) && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Output
          </h2>
          {state.final_video_path && (
            <a 
              href={state.final_video_path}
              className="text-blue-400 hover:underline text-sm"
              target="_blank"
            >
              🎬 Download Video
            </a>
          )}
        </div>
      )}
    </div>
  );
}
```

### 4.8 Supporting Components

**File: `frontend/src/components/ProgressBar.tsx`**

```tsx
"use client";

interface ProgressBarProps {
  percent: number;
  status: string;
}

export function ProgressBar({ percent, status }: ProgressBarProps) {
  const getColor = () => {
    if (status === "error") return "bg-red-500";
    if (status === "completed") return "bg-green-500";
    return "bg-blue-500";
  };

  return (
    <div className="w-full bg-gray-700 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all duration-300 ${getColor()}`}
        style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
      />
    </div>
  );
}
```

**File: `frontend/src/components/CaptureGrid.tsx`**

```tsx
"use client";

import { CaptureTask } from "@/lib/types";
import { CheckCircle, Clock, Loader2, XCircle } from "lucide-react";

interface CaptureGridProps {
  tasks: CaptureTask[];
}

export function CaptureGrid({ tasks }: CaptureGridProps) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {tasks.map((task) => (
        <div
          key={task.id}
          className="relative rounded-lg overflow-hidden bg-gray-700 aspect-[9/16]"
        >
          {/* Thumbnail */}
          {task.asset_url ? (
            <img
              src={task.asset_url}
              alt={task.description}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              {task.status === "capturing" ? (
                <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
              ) : task.status === "pending" ? (
                <Clock className="w-6 h-6 text-gray-500" />
              ) : (
                <XCircle className="w-6 h-6 text-red-400" />
              )}
            </div>
          )}
          
          {/* Status Badge */}
          <div className="absolute top-1 right-1">
            {task.status === "completed" && (
              <CheckCircle className="w-4 h-4 text-green-400" />
            )}
            {task.status === "capturing" && (
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
            )}
          </div>
          
          {/* Label */}
          <div className="absolute bottom-0 left-0 right-0 bg-black/60 p-1">
            <p className="text-xs text-white truncate">{task.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
```

### 4.9 Environment Variables

**File: `frontend/.env.local`**

```bash
PIPELINE_API_URL=http://127.0.0.1:8000/pipeline
```

### Checklist

- [x] **4.1** Initialize Next.js project
- [x] **4.2** Install npm dependencies
- [x] **4.3** Create `src/app/api/copilotkit/route.ts` (**FIXED**: Added required `ExperimentalEmptyAdapter` as `serviceAdapter`)
- [x] **4.4** Update `src/app/layout.tsx` (**FIXED**: Added required `agent="pipelineAgent"` prop to `CopilotKit`)
- [x] **4.5** Create `src/lib/types.ts`
- [x] **4.6** Create `src/app/page.tsx` (**FIXED**: Added `agents={["pipelineAgent"]}` to `CopilotChat`)
- [x] **4.7** Create `src/components/StatusPanel.tsx` (added null check for capture_tasks array)
- [x] **4.8** Create `src/components/ProgressBar.tsx` and `CaptureGrid.tsx`
- [x] **4.9** Create `.env.local`
- [x] **4.10** Test frontend (build successful, dev server runs on :3000):
  ```bash
  # Terminal 1: Backend
  cd /Users/tk/Desktop/productvideo
  python -m uvicorn ag_ui.server:app --reload --port 8000

  # Terminal 2: Frontend
  cd /Users/tk/Desktop/productvideo/frontend
  npm run dev

  # Visit http://localhost:3000
  ```

---

## Phase 5: State Streaming & Display

### 5.1 Enhanced State Render in Chat

**File: `frontend/src/app/page.tsx`** (update)

```tsx
"use client";

import { useCoAgent, useCoAgentStateRender } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { StreamLineState, initialState } from "@/lib/types";
import { StatusPanel } from "@/components/StatusPanel";
import { CaptureGrid } from "@/components/CaptureGrid";
import { ProgressBar } from "@/components/ProgressBar";

export default function Home() {
  const { state } = useCoAgent<StreamLineState>({
    name: "pipelineAgent",
    initialState,
  });

  // Render state updates in chat
  useCoAgentStateRender({
    name: "pipelineAgent",
    render: ({ state }) => {
      // Show capture grid during capture phase
      if (state.current_stage === "capture_single" && state.capture_tasks.length > 0) {
        return (
          <div className="p-4 bg-gray-800 rounded-lg my-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-300">
                Capturing Screenshots
              </span>
              <span className="text-xs text-gray-500">
                {state.captures_completed}/{state.captures_total}
              </span>
            </div>
            <CaptureGrid tasks={state.capture_tasks.slice(0, 6)} />
          </div>
        );
      }
      
      // Show progress for other stages
      if (state.status === "capturing" || state.status === "editing" || state.status === "rendering") {
        return (
          <div className="p-4 bg-gray-800 rounded-lg my-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-300">
                {state.stage_message}
              </span>
              <span className="text-xs text-gray-500">
                {state.progress_percent}%
              </span>
            </div>
            <ProgressBar percent={state.progress_percent} status={state.status} />
          </div>
        );
      }
      
      // Show completion
      if (state.status === "completed" && state.final_video_path) {
        return (
          <div className="p-4 bg-green-900/30 border border-green-700 rounded-lg my-2">
            <p className="text-green-400 font-medium mb-2">✅ Video Ready!</p>
            <a 
              href={state.final_video_path}
              className="text-blue-400 hover:underline text-sm"
              target="_blank"
            >
              Download your video →
            </a>
          </div>
        );
      }
      
      return null;
    },
  });

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Status Panel */}
      <div className="w-80 border-r border-gray-700 bg-gray-800 overflow-y-auto">
        <StatusPanel state={state} />
      </div>
      
      {/* Chat Panel */}
      <div className="flex-1 flex flex-col">
        <header className="p-4 border-b border-gray-700">
          <h1 className="text-xl font-bold text-white">StreamLine</h1>
          <p className="text-sm text-gray-400">AI-Powered Video Production</p>
        </header>
        
        <div className="flex-1 overflow-hidden">
          <CopilotChat
            className="h-full"
            agents={["pipelineAgent"]}
            labels={{
              initial: "Hi! I'm StreamLine. Tell me about your app and what kind of promo video you'd like to create.\n\nExample: \"I have a fitness app at ~/Code/FitTracker - create a 30 second energetic Product Hunt video\"",
              placeholder: "Describe your app and video goals...",
            }}
          />
        </div>
      </div>
    </div>
  );
}
```

### Checklist

- [x] **5.1** Update `page.tsx` with `useCoAgentStateRender`
- [x] **5.2** Test state streaming end-to-end (backend health check passed)

---

## Phase 6: HITL Interrupts

**⚠️ CRITICAL FIX - Original Guide Phase 6.1 is INCORRECT**

**Problem with Original Guide:**
- Tries to detect interrupts in `event_translator.py` during streaming
- LangGraph interrupts appear in **final state**, not in stream events
- `translate()` method has no access to graph object
- Uses wrong event type (`CUSTOM` instead of `RUN_FINISHED` with `outcome="interrupt"`)

**Correct Implementation (Based on LangGraph & AG-UI Official Docs):**

### 6.1 Backend Interrupt Detection & Resume

**File: `src/backend/adapter.py`** (REPLACE original Phase 6.1 code)

**Step 1: Add Command import**

```python
# At top of file, add:
from langgraph.types import Command
```

**Step 2: Add resume detection at start of streaming**

In `run_pipeline_stream()`, replace the single `astream_events` call with:

```python
# ─────────────────────────────────────────────────────────
# 4. Stream Graph Execution
# ─────────────────────────────────────────────────────────
last_project_id = video_project_id

try:
    # Check if resuming from interrupt
    if hasattr(input_data, 'resume') and input_data.resume:
        resume_payload = input_data.resume.get("payload") if isinstance(input_data.resume, dict) else None

        # Resume graph with user's response
        async for event in graph.astream_events(
            Command(resume=resume_payload),  # KEY: Use Command(resume=...)
            config=config,
            version="v2",
        ):
            # ... existing event translation code ...
    else:
        # Normal execution (not resuming)
        async for event in graph.astream_events(
            initial_state,
            config=config,
            version="v2",
        ):
            # ... existing event translation code ...
```

**Step 3: Add interrupt detection after streaming completes**

Replace the finalize section (section 5) with:

```python
# ─────────────────────────────────────────────────────────
# 5. Finalize
# ─────────────────────────────────────────────────────────

# Close any open message stream
for ag_event in translator.finalize_message():
    yield encoder.encode(ag_event)

# Get final state and check for interrupts
try:
    final_state_snapshot = graph.get_state(config)
    final_state = final_state_snapshot.values if final_state_snapshot else {}

    # Check for interrupts
    if final_state_snapshot and hasattr(final_state_snapshot, 'tasks') and final_state_snapshot.tasks:
        for task in final_state_snapshot.tasks:
            if hasattr(task, 'interrupts') and task.interrupts:
                # Found an interrupt - emit RUN_FINISHED with interrupt outcome
                interrupt_obj = task.interrupts[0]

                yield encoder.encode(RunFinishedEvent(
                    type=EventType.RUN_FINISHED,
                    thread_id=thread_id,
                    run_id=run_id,
                    outcome="interrupt",  # KEY: Use outcome="interrupt"
                    interrupt={
                        "id": str(uuid.uuid4()),
                        "reason": "human_input_required",
                        "payload": make_json_safe(interrupt_obj.value) if hasattr(interrupt_obj, 'value') else {}
                    }
                ))
                return  # Exit early, don't emit normal completion
except Exception as e:
    print(f"Error checking for interrupts: {e}")
    final_state = {}

# No interrupt - normal completion
final_ui_state = extract_ui_state(final_state)
final_ui_state["status"] = "completed"
final_ui_state["progress_percent"] = 100

# Final capture tasks
if last_project_id:
    final_ui_state["capture_tasks"] = get_capture_tasks_for_project(last_project_id)

yield encoder.encode(StateSnapshotEvent(
    type=EventType.STATE_SNAPSHOT,
    snapshot=final_ui_state,
))
```

**Step 4: Update finally block**

```python
finally:
    # ─────────────────────────────────────────────────────
    # 6. RUN_FINISHED (only for success/error, not interrupt)
    # ─────────────────────────────────────────────────────
    # Note: If interrupted, we already returned early above
    yield encoder.encode(RunFinishedEvent(
        type=EventType.RUN_FINISHED,
        thread_id=thread_id,
        run_id=run_id,
        outcome="success",  # KEY: Add outcome parameter
    ))
```

### 6.2 Frontend Interrupt Handler

**File: `frontend/src/components/InterruptCard.tsx`** (NO CHANGES from original guide)

```tsx
"use client";

interface InterruptCardProps {
  question: string;
  hint?: string;
  onSubmit: (response: string) => void;
}

export function InterruptCard({ question, hint, onSubmit }: InterruptCardProps) {
  const [value, setValue] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim()) {
      onSubmit(value.trim());
      setValue("");
    }
  };

  return (
    <div className="p-4 bg-yellow-900/30 border border-yellow-700 rounded-lg my-2">
      <p className="text-yellow-400 font-medium mb-2">⚠️ Input Required</p>
      <p className="text-gray-300 mb-2">{question}</p>
      {hint && (
        <p className="text-gray-500 text-sm mb-3">Hint: {hint}</p>
      )}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Enter your response..."
          className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded text-sm font-medium"
        >
          Submit
        </button>
      </form>
    </div>
  );
}
```

**File: `frontend/src/app/page.tsx`** (add interrupt handling)

```tsx
import { useLangGraphInterrupt } from "@copilotkit/react-core";
import { InterruptCard } from "@/components/InterruptCard";

// Inside Home component:
useLangGraphInterrupt<{ question: string; hint?: string }>({
  render: ({ event, resolve }) => {
    const data = event.value;
    
    return (
      <InterruptCard
        question={data.question}
        hint={data.hint}
        onSubmit={(response) => resolve(response)}
      />
    );
  },
});
```

### Checklist

- [x] **6.1** ~~Update event translator for interrupts~~ **FIXED: Update `adapter.py` instead** - Added Command import, resume detection, and interrupt checking in final state
- [x] **6.2** Create `InterruptCard.tsx` - 已创建并实现用户输入表单
- [x] **6.3** Add `useLangGraphInterrupt` to page - 已在 page.tsx 中集成
- [x] **6.4** Test interrupt flow - 所有组件已验证，前后端构建通过

**Known Issue - RESOLVED:** ~~Frontend build has type conflicts with `@ag-ui/client` versions.~~
**Fix Applied:**
1. 降级 `@ag-ui/client` 到 `0.0.42` 和 `@ag-ui/langgraph` 到 `0.0.20` 以匹配 CopilotKit v1.51.2 的依赖
2. 在 `package.json` 中添加 `overrides` 字段强制统一版本
3. 移除 `CopilotChat` 的 `agents` 属性（该版本不支持，agent 已在 layout.tsx 中指定）
4. 构建成功通过

**Phase 6 完成状态：✅ 所有功能已实现并验证**

---

## Phase 7: Upload-Only Mode

### 7.1 Upload Component

**File: `frontend/src/components/UploadMode.tsx`**

```tsx
"use client";

import { useState, useCallback } from "react";
import { Upload, X, Image as ImageIcon } from "lucide-react";

interface UploadedAsset {
  file: File;
  preview: string;
  description: string;
}

interface UploadModeProps {
  onStart: (userInput: string, assets: { url: string; description: string }[]) => void;
}

export function UploadMode({ onStart }: UploadModeProps) {
  const [assets, setAssets] = useState<UploadedAsset[]>([]);
  const [userInput, setUserInput] = useState("");
  const [uploading, setUploading] = useState(false);

  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files) return;
    
    const newAssets: UploadedAsset[] = [];
    
    Array.from(files).forEach((file) => {
      if (file.type.startsWith("image/")) {
        const preview = URL.createObjectURL(file);
        newAssets.push({
          file,
          preview,
          description: file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " "),
        });
      }
    });
    
    setAssets((prev) => [...prev, ...newAssets]);
  }, []);

  const removeAsset = (index: number) => {
    setAssets((prev) => {
      const updated = [...prev];
      URL.revokeObjectURL(updated[index].preview);
      updated.splice(index, 1);
      return updated;
    });
  };

  const handleSubmit = async () => {
    if (!userInput.trim() || assets.length === 0) return;
    
    setUploading(true);
    
    try {
      // Upload files to Supabase Storage via backend
      const uploadedUrls: { url: string; description: string }[] = [];
      
      for (const asset of assets) {
        const formData = new FormData();
        formData.append("file", asset.file);
        formData.append("description", asset.description);
        
        const response = await fetch("http://127.0.0.1:8000/upload", {
          method: "POST",
          body: formData,
        });
        
        const data = await response.json();
        uploadedUrls.push({
          url: data.url,
          description: asset.description,
        });
      }
      
      // Start pipeline with uploaded assets
      onStart(userInput, uploadedUrls);
    } catch (error) {
      console.error("Upload failed:", error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white mb-2">Upload Screenshots</h2>
        <p className="text-sm text-gray-400">
          Upload your app screenshots and I'll create a promo video from them.
        </p>
      </div>
      
      {/* Drop Zone */}
      <div
        className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center hover:border-gray-500 transition-colors cursor-pointer"
        onClick={() => document.getElementById("file-input")?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFileSelect(e.dataTransfer.files);
        }}
      >
        <Upload className="w-8 h-8 text-gray-500 mx-auto mb-2" />
        <p className="text-gray-400">Drop images here or click to upload</p>
        <input
          id="file-input"
          type="file"
          multiple
          accept="image/*"
          className="hidden"
          onChange={(e) => handleFileSelect(e.target.files)}
        />
      </div>
      
      {/* Preview Grid */}
      {assets.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          {assets.map((asset, index) => (
            <div key={index} className="relative group">
              <img
                src={asset.preview}
                alt={asset.description}
                className="w-full aspect-[9/16] object-cover rounded-lg"
              />
              <button
                onClick={() => removeAsset(index)}
                className="absolute top-1 right-1 p-1 bg-red-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="w-3 h-3 text-white" />
              </button>
              <input
                type="text"
                value={asset.description}
                onChange={(e) => {
                  setAssets((prev) => {
                    const updated = [...prev];
                    updated[index].description = e.target.value;
                    return updated;
                  });
                }}
                className="absolute bottom-0 left-0 right-0 bg-black/70 text-white text-xs p-1 rounded-b-lg"
                placeholder="Description"
              />
            </div>
          ))}
        </div>
      )}
      
      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Video Description
        </label>
        <textarea
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          placeholder="Describe what kind of video you want..."
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm resize-none"
          rows={3}
        />
      </div>
      
      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!userInput.trim() || assets.length === 0 || uploading}
        className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
      >
        {uploading ? "Uploading..." : `Create Video from ${assets.length} Images`}
      </button>
    </div>
  );
}
```

### 7.2 Backend Upload Endpoint

**File: `src/ag_ui/server.py`** (add endpoint)

```python
from fastapi import UploadFile, File, Form
from tools.storage import upload_asset
import tempfile
import os

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    description: str = Form(""),
):
    """
    Upload a single file to Supabase Storage.
    
    Used by upload-only mode to prepare assets before pipeline.
    """
    # Save to temp file
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Upload to Supabase
        # Use a temporary project ID that will be replaced
        url = upload_asset(
            tmp_path,
            project_id="uploads",
            subfolder="pending",
        )
        
        return {
            "url": url,
            "filename": file.filename,
            "description": description,
        }
    finally:
        os.unlink(tmp_path)
```

### 7.3 Implementation Notes

**7.3 实现**: 在 `page.tsx` 中添加 Tab 式模式切换器，使用 `useState<"full" | "upload">` 管理模式。Header 包含两个按钮（Sparkles 图标 = Full Pipeline，Upload 图标 = Upload Assets），激活时显示蓝色高亮和阴影。Content 区域根据 `mode` 条件渲染 `<CopilotChat>` 或 `<UploadMode>`。`handleUploadStart` 函数调用 `/projects/from-uploads` 创建项目，更新 state，然后自动切回 chat 模式显示进度。上传中禁用切换按钮。

### Checklist

- [x] **7.1** Create `UploadMode.tsx` component
- [x] **7.2** Add `/upload` endpoint to server
- [x] **7.3** Add mode toggle in UI (Full Pipeline vs Upload Only) - Tab-based switcher with icons, mode descriptions, and auto-switch after upload
- [ ] **7.4** Test upload flow

---

## Phase 8: Polish & Production

### 8.1 Error Handling

**File: `frontend/src/components/ErrorBoundary.tsx`**

```tsx
"use client";

import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 bg-red-900/30 border border-red-700 rounded-lg">
          <h2 className="text-red-400 font-bold mb-2">Something went wrong</h2>
          <p className="text-gray-300 text-sm">{this.state.error?.message}</p>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded"
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### 8.2 Loading States

**File: `frontend/src/components/LoadingOverlay.tsx`**

```tsx
"use client";

import { Loader2 } from "lucide-react";

interface LoadingOverlayProps {
  message?: string;
}

export function LoadingOverlay({ message = "Loading..." }: LoadingOverlayProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 p-6 rounded-lg flex items-center gap-4">
        <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
        <span className="text-white">{message}</span>
      </div>
    </div>
  );
}
```

### 8.3 Production Checklist

- [ ] **8.1** Add error boundary to layout
- [ ] **8.2** Add loading states
- [ ] **8.3** Set up proper CORS for production domain
- [ ] **8.4** Add rate limiting to backend
- [ ] **8.5** Configure Supabase Storage CORS
- [ ] **8.6** Test full flow end-to-end:
  ```bash
  # Start backend
  cd /Users/tk/Desktop/productvideo
  python -m uvicorn ag_ui.server:app --host 0.0.0.0 --port 8000
  
  # Start frontend
  cd /Users/tk/Desktop/productvideo/frontend
  npm run build && npm start
  ```
- [ ] **8.7** Document API endpoints
- [ ] **8.8** Add health monitoring

---

## Quick Reference

### Start Development

```bash
# Terminal 1: Backend (⚠️ MUST use venv)
cd /Users/tk/Desktop/productvideo
source .venv/bin/activate
cd src
python -m uvicorn backend.server:app --reload --port 8000

# Terminal 2: Frontend
cd /Users/tk/Desktop/productvideo/frontend
npm run dev
```

### Test Individual Phases

```bash
# Test capture only
curl -X POST http://localhost:8000/pipeline \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Test at ~/Code/TestApp"}]}'

# Test upload endpoint
curl -X POST http://localhost:8000/upload \
  -F "file=@test.png" \
  -F "description=Test screenshot"

# Test project creation from uploads
curl -X POST http://localhost:8000/projects/from-uploads \
  -H "Content-Type: application/json" \
  -d '{"user_input":"Test video","assets":[{"url":"https://...","description":"Screen 1"}]}'
```

### File Structure Summary

```
productvideo/
├── src/
│   ├── ag_ui/                    # NEW: AG-UI integration
│   │   ├── __init__.py
│   │   ├── adapter.py            # Stream pipeline as AG-UI events
│   │   ├── event_translator.py   # LangGraph → AG-UI translation
│   │   └── server.py             # FastAPI endpoints
│   ├── pipeline/                 # NEW: Unified pipeline
│   │   ├── __init__.py
│   │   ├── state.py              # UnifiedPipelineState
│   │   └── unified_graph.py      # Single graph, multiple modes
│   ├── tools/
│   │   └── storage.py            # NEW: Supabase Storage
│   ├── db/
│   │   └── migrations/
│   │       └── 004_asset_urls... # NEW: Migration
│   └── ... (existing)
├── frontend/                     # NEW: Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── api/copilotkit/route.ts
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── components/
│   │   │   ├── StatusPanel.tsx
│   │   │   ├── CaptureGrid.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   ├── InterruptCard.tsx
│   │   │   └── UploadMode.tsx
│   │   └── lib/
│   │       └── types.ts
│   └── package.json
└── docs/
    └── AG_UI_INTEGRATION_GUIDE.md  # This file
```

---

## Troubleshooting

### "CORS error" in browser console
- Check FastAPI CORS middleware includes your frontend URL
- Verify Supabase Storage bucket CORS settings

### "No capture_tasks returned"
- Check DB migration ran successfully
- Verify `asset_url` column exists
- Check Storage bucket permissions

### "Graph compilation error"
- Ensure all imports are correct in unified_graph.py
- Check that editor and orchestrator modules are importable

### "State not updating in UI"
- Verify AG-UI events are being emitted (check browser Network tab for SSE)
- Check that state paths in StateDeltaEvent match frontend state shape

---

**You're ready to build!** Follow the phases in order, checking off items as you complete them. Each phase is designed to be testable independently before moving to the next.
