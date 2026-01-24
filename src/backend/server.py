"""
FastAPI server with AG-UI endpoints.

Run:
    cd /Users/tk/Desktop/productvideo
    python -m uvicorn ag_ui.server:app --reload --port 8000
    
Or from src:
    python -m uvicorn src.ag_ui.server:app --reload --port 8000
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Literal
import uuid
import tempfile
import os

from ag_ui.core import RunAgentInput
from .adapter import run_pipeline_stream, SSE_CONTENT_TYPE, get_capture_tasks_for_project


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
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# AG-UI Endpoint
# ─────────────────────────────────────────────────────────────

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
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
        },
    )


# ─────────────────────────────────────────────────────────────
# REST Endpoints (for frontend data fetching)
# ─────────────────────────────────────────────────────────────

@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    from db.supabase_client import get_supabase

    supabase = get_supabase()
    result = supabase.table("video_projects") \
        .select("*") \
        .eq("id", project_id) \
        .single() \
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return result.data


@app.get("/projects/{project_id}/captures")
async def get_captures(project_id: str):
    """Get capture tasks for a project."""
    tasks = get_capture_tasks_for_project(project_id)
    return {"captures": tasks}


# ─────────────────────────────────────────────────────────────
# Upload Mode Endpoints
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
    from db.supabase_client import get_supabase

    supabase = get_supabase()
    
    # Create project
    project_id = str(uuid.uuid4())
    
    supabase.table("video_projects").insert({
        "id": project_id,
        "user_input": request.user_input,
        "status": "aggregated",  # Ready for editor
        "source": "upload",
        "pipeline_mode": "upload",
    }).execute()
    
    # Create capture tasks for each asset
    for i, asset in enumerate(request.assets):
        supabase.table("capture_tasks").insert({
            "id": str(uuid.uuid4()),
            "video_project_id": project_id,
            "task_description": asset.get("description", f"Uploaded asset {i+1}"),
            "capture_type": "screenshot",
            "asset_url": asset["url"],
            "status": "success",
        }).execute()
    
    return {
        "project_id": project_id,
        "asset_count": len(request.assets),
    }


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    description: str = Form(""),
):
    """
    Upload a single file to Supabase Storage.
    
    Used by upload-only mode to prepare assets before pipeline.
    """
    from tools.storage import upload_asset
    
    # Save to temp file
    suffix = os.path.splitext(file.filename or ".png")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Upload to Supabase with a temp project ID
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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "StreamLine AG-UI Server",
        "version": "1.0.0",
        "endpoints": {
            "pipeline": "POST /pipeline - AG-UI streaming endpoint",
            "project": "GET /projects/{id} - Get project details",
            "captures": "GET /projects/{id}/captures - Get capture tasks",
            "upload": "POST /upload - Upload single file",
            "from_uploads": "POST /projects/from-uploads - Create project from uploads",
            "health": "GET /health - Health check",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
